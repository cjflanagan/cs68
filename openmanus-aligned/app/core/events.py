"""
Event-Driven Architecture for Manus-aligned agent.

This module implements the rich event stream architecture used by the actual Manus
implementation, with 7 distinct event types:
- Message: User/assistant communication
- Action: Tool calls and executions
- Observation: Results from tool executions
- Plan: Structured task plans from the Planner module
- Knowledge: Best practices and reference information
- Datasource: API documentation and data sources
- System: Internal system events

The event stream is append-only and supports deterministic serialization
for KV-cache optimization.
"""

from abc import ABC
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
import hashlib
import json


class EventType(str, Enum):
    """Types of events in the Manus event stream."""
    MESSAGE = "message"
    ACTION = "action"
    OBSERVATION = "observation"
    PLAN = "plan"
    KNOWLEDGE = "knowledge"
    DATASOURCE = "datasource"
    SYSTEM = "system"


class Event(BaseModel, ABC):
    """Base class for all events in the event stream.

    Events are immutable and append-only. Each event has a unique ID,
    timestamp, and type for ordering and serialization.
    """

    id: str = Field(default_factory=lambda: "")
    type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True
        frozen = True  # Events are immutable

    def __init__(self, **data):
        super().__init__(**data)
        if not self.id:
            # Generate deterministic ID based on content
            object.__setattr__(self, 'id', self._generate_id())

    def _generate_id(self) -> str:
        """Generate a deterministic ID for the event."""
        content = f"{self.type}:{self.timestamp.isoformat()}:{self._content_hash()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _content_hash(self) -> str:
        """Override in subclasses to provide content-specific hash."""
        return ""

    def to_context(self) -> str:
        """Convert event to context string for LLM consumption."""
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to deterministic dictionary format."""
        return {
            "id": self.id,
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class MessageEvent(Event):
    """User or assistant message event."""

    type: EventType = EventType.MESSAGE
    role: str  # "user" or "assistant"
    content: str
    base64_image: Optional[str] = None

    def _content_hash(self) -> str:
        return f"{self.role}:{self.content}"

    def to_context(self) -> str:
        prefix = "[USER]" if self.role == "user" else "[ASSISTANT]"
        return f"{prefix} {self.content}"

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "role": self.role,
            "content": self.content,
        })
        if self.base64_image:
            d["base64_image"] = self.base64_image
        return d


class ActionEvent(Event):
    """Tool call/action event."""

    type: EventType = EventType.ACTION
    tool_name: str
    tool_input: Dict[str, Any] = Field(default_factory=dict)
    tool_call_id: str = ""

    def _content_hash(self) -> str:
        return f"{self.tool_name}:{json.dumps(self.tool_input, sort_keys=True)}"

    def to_context(self) -> str:
        args_str = json.dumps(self.tool_input, indent=2)
        return f"[ACTION] Calling {self.tool_name}\nArguments:\n{args_str}"

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "tool_call_id": self.tool_call_id,
        })
        return d


class ObservationEvent(Event):
    """Result from tool execution."""

    type: EventType = EventType.OBSERVATION
    tool_name: str
    tool_call_id: str
    output: str
    error: Optional[str] = None
    base64_image: Optional[str] = None

    def _content_hash(self) -> str:
        return f"{self.tool_name}:{self.output}:{self.error or ''}"

    def to_context(self) -> str:
        if self.error:
            return f"[OBSERVATION] Tool {self.tool_name} failed: {self.error}"
        return f"[OBSERVATION] Result from {self.tool_name}:\n{self.output}"

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "tool_name": self.tool_name,
            "tool_call_id": self.tool_call_id,
            "output": self.output,
        })
        if self.error:
            d["error"] = self.error
        if self.base64_image:
            d["base64_image"] = self.base64_image
        return d


class PlanEvent(Event):
    """Task plan from the Planner module.

    Plans are injected by the Planner module (not requested by the agent)
    and guide the agent's execution. Plans are represented as numbered
    pseudocode steps.
    """

    type: EventType = EventType.PLAN
    plan_id: str
    title: str
    steps: List[str] = Field(default_factory=list)
    step_statuses: List[str] = Field(default_factory=list)
    current_step_index: int = 0
    is_complete: bool = False

    def _content_hash(self) -> str:
        return f"{self.plan_id}:{self.title}:{len(self.steps)}"

    def to_context(self) -> str:
        """Format plan as numbered pseudocode for context injection."""
        lines = [f"[PLAN] {self.title}"]
        lines.append("=" * 40)
        for i, (step, status) in enumerate(zip(self.steps, self.step_statuses)):
            marker = "→" if i == self.current_step_index else " "
            status_icon = {"pending": "[ ]", "in_progress": "[→]", "completed": "[✓]", "blocked": "[!]"}.get(status, "[ ]")
            lines.append(f"{marker} {i+1}. {status_icon} {step}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "plan_id": self.plan_id,
            "title": self.title,
            "steps": self.steps,
            "step_statuses": self.step_statuses,
            "current_step_index": self.current_step_index,
            "is_complete": self.is_complete,
        })
        return d


class KnowledgeEvent(Event):
    """Best practices and reference information from the Knowledge module.

    Knowledge events inject task-relevant expertise into the event stream
    with specific scopes and conditions for adoption.
    """

    type: EventType = EventType.KNOWLEDGE
    category: str  # e.g., "best_practice", "reference", "warning"
    scope: str  # e.g., "browser", "coding", "data_analysis"
    content: str
    conditions: List[str] = Field(default_factory=list)  # When to apply
    priority: int = 1  # Higher = more important

    def _content_hash(self) -> str:
        return f"{self.category}:{self.scope}:{self.content[:50]}"

    def to_context(self) -> str:
        lines = [f"[KNOWLEDGE:{self.scope.upper()}] {self.category}"]
        lines.append(self.content)
        if self.conditions:
            lines.append("Apply when: " + ", ".join(self.conditions))
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "category": self.category,
            "scope": self.scope,
            "content": self.content,
            "conditions": self.conditions,
            "priority": self.priority,
        })
        return d


class DatasourceEvent(Event):
    """API documentation from the Datasource module.

    Datasource events provide documentation for authoritative data APIs,
    which are prioritized over general web search. The agent calls these
    APIs via generated Python code using a pre-configured ApiClient.
    """

    type: EventType = EventType.DATASOURCE
    source_id: str
    name: str
    description: str
    endpoint: str
    auth_method: Optional[str] = None
    documentation: str = ""
    example_usage: str = ""
    priority: int = 1  # Higher = more authoritative

    def _content_hash(self) -> str:
        return f"{self.source_id}:{self.name}"

    def to_context(self) -> str:
        lines = [f"[DATASOURCE] {self.name}"]
        lines.append(f"Endpoint: {self.endpoint}")
        if self.description:
            lines.append(f"Description: {self.description}")
        if self.documentation:
            lines.append(f"Documentation:\n{self.documentation}")
        if self.example_usage:
            lines.append(f"Example:\n{self.example_usage}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "source_id": self.source_id,
            "name": self.name,
            "description": self.description,
            "endpoint": self.endpoint,
            "auth_method": self.auth_method,
            "documentation": self.documentation,
            "example_usage": self.example_usage,
            "priority": self.priority,
        })
        return d


class SystemEvent(Event):
    """Internal system events for orchestration."""

    type: EventType = EventType.SYSTEM
    event_name: str
    data: Dict[str, Any] = Field(default_factory=dict)

    def _content_hash(self) -> str:
        return f"{self.event_name}:{json.dumps(self.data, sort_keys=True)}"

    def to_context(self) -> str:
        return f"[SYSTEM] {self.event_name}: {json.dumps(self.data)}"

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "event_name": self.event_name,
            "data": self.data,
        })
        return d


class EventStream(BaseModel):
    """Append-only event stream for multi-source context enrichment.

    The event stream maintains a chronological sequence of events from
    different sources (user, agent, planner, knowledge, datasource).
    It supports:
    - Append-only operations (for KV-cache stability)
    - Deterministic serialization
    - Filtering by event type
    - Context generation for LLM consumption
    """

    events: List[Event] = Field(default_factory=list)
    max_events: int = 1000

    class Config:
        arbitrary_types_allowed = True

    def append(self, event: Event) -> None:
        """Append an event to the stream (append-only)."""
        self.events.append(event)
        if len(self.events) > self.max_events:
            # Preserve system and plan events, trim older messages
            preserved = [e for e in self.events if e.type in (EventType.PLAN, EventType.SYSTEM)]
            other = [e for e in self.events if e.type not in (EventType.PLAN, EventType.SYSTEM)]
            keep_count = self.max_events - len(preserved)
            self.events = preserved + other[-keep_count:]

    def get_by_type(self, event_type: EventType) -> List[Event]:
        """Get all events of a specific type."""
        return [e for e in self.events if e.type == event_type]

    def get_latest_plan(self) -> Optional[PlanEvent]:
        """Get the most recent plan event."""
        plans = self.get_by_type(EventType.PLAN)
        return plans[-1] if plans else None

    def get_active_knowledge(self) -> List[KnowledgeEvent]:
        """Get active knowledge events sorted by priority."""
        knowledge = self.get_by_type(EventType.KNOWLEDGE)
        return sorted(knowledge, key=lambda k: k.priority, reverse=True)

    def get_datasources(self) -> List[DatasourceEvent]:
        """Get available datasource events sorted by priority."""
        datasources = self.get_by_type(EventType.DATASOURCE)
        return sorted(datasources, key=lambda d: d.priority, reverse=True)

    def get_recent_errors(self, limit: int = 5) -> List[ObservationEvent]:
        """Get recent error observations for error retention."""
        observations = self.get_by_type(EventType.OBSERVATION)
        errors = [o for o in observations if o.error]
        return errors[-limit:]

    def to_context(self, include_types: Optional[List[EventType]] = None) -> str:
        """Generate context string for LLM consumption.

        Args:
            include_types: Event types to include. If None, include all.
        """
        context_parts = []
        for event in self.events:
            if include_types is None or event.type in include_types:
                context_parts.append(event.to_context())
        return "\n\n".join(context_parts)

    def to_messages(self) -> List[Dict[str, Any]]:
        """Convert event stream to LLM message format."""
        messages = []
        for event in self.events:
            if event.type == EventType.MESSAGE:
                msg = {"role": event.role, "content": event.content}
                if event.base64_image:
                    msg["base64_image"] = event.base64_image
                messages.append(msg)
            elif event.type == EventType.ACTION:
                # Tool calls are embedded in assistant messages
                pass
            elif event.type == EventType.OBSERVATION:
                messages.append({
                    "role": "tool",
                    "content": event.output if not event.error else f"Error: {event.error}",
                    "tool_call_id": event.tool_call_id,
                    "name": event.tool_name,
                })
            elif event.type == EventType.PLAN:
                # Plans are injected as system context
                messages.append({
                    "role": "system",
                    "content": event.to_context(),
                })
            elif event.type == EventType.KNOWLEDGE:
                # Knowledge is injected as system context
                messages.append({
                    "role": "system",
                    "content": event.to_context(),
                })
            elif event.type == EventType.DATASOURCE:
                # Datasources are injected as system context
                messages.append({
                    "role": "system",
                    "content": event.to_context(),
                })
        return messages

    def serialize(self) -> str:
        """Deterministic serialization for KV-cache stability."""
        return json.dumps(
            [e.to_dict() for e in self.events],
            sort_keys=True,
            separators=(',', ':'),
        )

    def clear(self) -> None:
        """Clear all events."""
        self.events = []
