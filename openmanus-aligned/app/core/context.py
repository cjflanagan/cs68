"""
Context Engineering Module for Manus-aligned agent.

This module implements production-grade context engineering techniques
described in the Manus blog "Context Engineering for AI Agents":

1. KV-Cache Optimization:
   - Stable prompt prefix
   - Append-only context
   - Deterministic serialization

2. Tool Masking (not removal):
   - Context-aware state machine
   - Logit manipulation for unavailable tools
   - Consistent tool name prefixes (e.g., browser_*)

3. Attention Manipulation via Recitation:
   - Dynamic todo.md file updates
   - Pushing global plan into recent attention
   - Combating goal drift in long tasks

4. Error Retention:
   - Keep failed actions and error messages
   - Enable learning from mistakes

5. Few-Shot Trap Avoidance:
   - Structured variation in serialization
   - Alternate phrasing
   - Prevent overgeneralization
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field
import json
import hashlib
import random


class ToolState(str, Enum):
    """State of a tool in the context-aware state machine."""
    AVAILABLE = "available"
    MASKED = "masked"  # Tool exists but currently unavailable
    HIDDEN = "hidden"  # Tool completely hidden from context


class ToolMask(BaseModel):
    """Represents a masked tool with conditions for availability."""

    tool_name: str
    state: ToolState = ToolState.AVAILABLE
    mask_reason: str = ""
    conditions: List[str] = Field(default_factory=list)
    priority: int = 1

    def should_unmask(self, context: Dict[str, Any]) -> bool:
        """Check if tool should be unmasked based on context."""
        if self.state == ToolState.AVAILABLE:
            return True
        if not self.conditions:
            return False
        # Check conditions against context
        for condition in self.conditions:
            if condition in str(context):
                return True
        return False


class TodoRecitation(BaseModel):
    """Manages the todo.md file for attention manipulation.

    The actual Manus creates and constantly updates a todo.md file to push
    the global plan into the model's recent attention span, combating
    goal drift in long tasks.
    """

    title: str = "Task Progress"
    items: List[Dict[str, Any]] = Field(default_factory=list)
    completed_items: List[Dict[str, Any]] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    update_frequency: int = 3  # Update every N steps

    def add_item(self, description: str, priority: int = 1) -> None:
        """Add a todo item."""
        self.items.append({
            "description": description,
            "priority": priority,
            "status": "pending",
            "added_at": datetime.utcnow().isoformat(),
        })
        self.last_updated = datetime.utcnow()

    def complete_item(self, index: int, notes: str = "") -> None:
        """Mark an item as complete."""
        if 0 <= index < len(self.items):
            item = self.items.pop(index)
            item["status"] = "completed"
            item["completed_at"] = datetime.utcnow().isoformat()
            if notes:
                item["notes"] = notes
            self.completed_items.append(item)
            self.last_updated = datetime.utcnow()

    def add_note(self, note: str) -> None:
        """Add a progress note."""
        self.notes.append(f"[{datetime.utcnow().isoformat()}] {note}")
        self.last_updated = datetime.utcnow()

    def to_markdown(self) -> str:
        """Generate markdown content for todo.md file."""
        lines = [f"# {self.title}", ""]

        # Current tasks
        if self.items:
            lines.append("## Current Tasks")
            for i, item in enumerate(self.items):
                priority_marker = "!" * item.get("priority", 1)
                lines.append(f"- [ ] {priority_marker} {item['description']}")
            lines.append("")

        # Completed tasks (recent only)
        recent_completed = self.completed_items[-5:]
        if recent_completed:
            lines.append("## Recently Completed")
            for item in recent_completed:
                lines.append(f"- [x] {item['description']}")
            lines.append("")

        # Notes
        if self.notes:
            lines.append("## Progress Notes")
            for note in self.notes[-3:]:
                lines.append(f"- {note}")
            lines.append("")

        lines.append(f"*Last updated: {self.last_updated.isoformat()}*")
        return "\n".join(lines)

    def to_recitation_string(self) -> str:
        """Generate a concise recitation string for context injection."""
        parts = ["[CURRENT PROGRESS]"]

        # Active tasks
        if self.items:
            parts.append(f"Active: {len(self.items)} tasks remaining")
            for i, item in enumerate(self.items[:3]):
                parts.append(f"  {i+1}. {item['description']}")

        # Progress
        total = len(self.items) + len(self.completed_items)
        if total > 0:
            pct = len(self.completed_items) / total * 100
            parts.append(f"Progress: {len(self.completed_items)}/{total} ({pct:.0f}%)")

        return "\n".join(parts)


class ErrorRetention(BaseModel):
    """Manages error retention for learning from mistakes.

    Failed actions and their error messages are deliberately kept in the
    context to allow the model to learn from its mistakes and avoid
    repeating the same errors.
    """

    errors: List[Dict[str, Any]] = Field(default_factory=list)
    max_retained: int = 10
    summary_threshold: int = 5  # Summarize when more than N errors

    def record_error(
        self,
        tool_name: str,
        error_message: str,
        input_args: Dict[str, Any] = None,
        context: str = "",
    ) -> None:
        """Record an error for retention."""
        self.errors.append({
            "tool_name": tool_name,
            "error_message": error_message,
            "input_args": input_args or {},
            "context": context,
            "timestamp": datetime.utcnow().isoformat(),
        })

        # Trim old errors
        if len(self.errors) > self.max_retained:
            self.errors = self.errors[-self.max_retained:]

    def get_relevant_errors(self, tool_name: str = None, limit: int = 3) -> List[Dict[str, Any]]:
        """Get recent errors, optionally filtered by tool."""
        if tool_name:
            filtered = [e for e in self.errors if e["tool_name"] == tool_name]
            return filtered[-limit:]
        return self.errors[-limit:]

    def to_context_string(self) -> str:
        """Generate context string for error injection."""
        if not self.errors:
            return ""

        parts = ["[PREVIOUS ERRORS - Avoid repeating these mistakes:]"]
        recent = self.errors[-self.summary_threshold:]

        for error in recent:
            parts.append(f"- {error['tool_name']}: {error['error_message']}")

        return "\n".join(parts)

    def clear(self) -> None:
        """Clear all retained errors."""
        self.errors = []


class SerializationVariation(BaseModel):
    """Implements few-shot trap avoidance through structured variation.

    Introduces variation in serialization templates and phrasing to prevent
    the model from overgeneralizing on repetitive tasks.
    """

    templates: List[str] = Field(default_factory=list)
    current_template_index: int = 0
    variation_seed: int = Field(default_factory=lambda: random.randint(0, 10000))

    def __init__(self, **data):
        super().__init__(**data)
        if not self.templates:
            self._load_default_templates()

    def _load_default_templates(self) -> None:
        """Load default serialization templates."""
        self.templates = [
            # Template 1: Standard
            "Action: {action}\nInput: {input}\nResult: {result}",
            # Template 2: Detailed
            "Executing {action} with parameters:\n{input}\n\nOutput received:\n{result}",
            # Template 3: Compact
            "[{action}] {input} -> {result}",
            # Template 4: Narrative
            "The {action} was invoked. Parameters provided: {input}. Response: {result}",
        ]

    def get_template(self) -> str:
        """Get current template with rotation."""
        template = self.templates[self.current_template_index]
        self.current_template_index = (self.current_template_index + 1) % len(self.templates)
        return template

    def serialize_action(
        self,
        action: str,
        input_data: Dict[str, Any],
        result: str,
    ) -> str:
        """Serialize an action with variation."""
        template = self.get_template()

        # Add slight variations to prevent exact repetition
        input_str = json.dumps(input_data, indent=2)

        return template.format(
            action=action,
            input=input_str,
            result=result,
        )

    def add_variation(self, text: str) -> str:
        """Add subtle variations to prevent exact pattern matching."""
        variations = [
            lambda t: t,  # No change
            lambda t: t.replace(":", " -"),  # Alternate punctuation
            lambda t: t.replace("\n\n", "\n"),  # Compact whitespace
        ]

        variation_fn = variations[self.variation_seed % len(variations)]
        self.variation_seed += 1
        return variation_fn(text)


class ContextEngine(BaseModel):
    """Main context engineering module.

    This is the central component that orchestrates all context engineering
    techniques to optimize the agent's performance:

    1. Maintains stable prompt prefix for KV-cache optimization
    2. Manages tool masking instead of removal
    3. Handles todo.md recitation for attention manipulation
    4. Retains errors for learning
    5. Applies serialization variation to avoid few-shot traps
    """

    # Stable prefix for KV-cache optimization
    system_prefix: str = ""
    prefix_hash: str = ""

    # Tool masking
    tool_masks: Dict[str, ToolMask] = Field(default_factory=dict)
    tool_prefixes: Dict[str, str] = Field(default_factory=dict)  # e.g., "browser": "browser_*"

    # Todo recitation
    todo: TodoRecitation = Field(default_factory=TodoRecitation)
    recitation_enabled: bool = True

    # Error retention
    error_retention: ErrorRetention = Field(default_factory=ErrorRetention)
    retain_errors: bool = True

    # Serialization variation
    serialization: SerializationVariation = Field(default_factory=SerializationVariation)
    vary_serialization: bool = True

    # Context tracking
    context_version: int = 0
    step_count: int = 0

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data):
        super().__init__(**data)
        self._initialize_tool_prefixes()

    def _initialize_tool_prefixes(self) -> None:
        """Initialize consistent tool name prefixes."""
        self.tool_prefixes = {
            "browser": "browser_",
            "file": "file_",
            "shell": "shell_",
            "python": "python_",
            "search": "search_",
            "api": "api_",
        }

    # === KV-Cache Optimization ===

    def set_stable_prefix(self, prefix: str) -> None:
        """Set the stable system prefix for KV-cache optimization.

        The prefix should be stable across sessions to maximize cache hits.
        """
        self.system_prefix = prefix
        self.prefix_hash = hashlib.sha256(prefix.encode()).hexdigest()[:16]

    def get_deterministic_context(self, events: List[Dict[str, Any]]) -> str:
        """Generate deterministic context string for consistent caching.

        Uses sorted keys and consistent formatting to ensure the same
        content produces the same string representation.
        """
        return json.dumps(events, sort_keys=True, separators=(',', ':'))

    def check_prefix_stability(self, new_prefix: str) -> bool:
        """Check if a new prefix would invalidate the KV-cache."""
        new_hash = hashlib.sha256(new_prefix.encode()).hexdigest()[:16]
        return new_hash == self.prefix_hash

    # === Tool Masking ===

    def mask_tool(
        self,
        tool_name: str,
        reason: str = "",
        conditions: List[str] = None,
    ) -> None:
        """Mask a tool instead of removing it.

        Masked tools remain in the context but are marked as unavailable,
        maintaining KV-cache stability.
        """
        self.tool_masks[tool_name] = ToolMask(
            tool_name=tool_name,
            state=ToolState.MASKED,
            mask_reason=reason,
            conditions=conditions or [],
        )

    def unmask_tool(self, tool_name: str) -> None:
        """Unmask a previously masked tool."""
        if tool_name in self.tool_masks:
            self.tool_masks[tool_name].state = ToolState.AVAILABLE

    def get_available_tools(self, all_tools: List[str]) -> List[str]:
        """Get list of available tools, excluding masked ones."""
        return [
            tool for tool in all_tools
            if tool not in self.tool_masks
            or self.tool_masks[tool].state == ToolState.AVAILABLE
        ]

    def get_masked_tools_context(self) -> str:
        """Get context string indicating which tools are currently masked."""
        masked = [
            mask for mask in self.tool_masks.values()
            if mask.state == ToolState.MASKED
        ]
        if not masked:
            return ""

        lines = ["[UNAVAILABLE TOOLS - Do not attempt to use:]"]
        for mask in masked:
            reason = f" ({mask.mask_reason})" if mask.mask_reason else ""
            lines.append(f"- {mask.tool_name}{reason}")

        return "\n".join(lines)

    def get_tool_with_prefix(self, category: str, tool_name: str) -> str:
        """Get tool name with consistent prefix for the category."""
        prefix = self.tool_prefixes.get(category, "")
        if not tool_name.startswith(prefix):
            return f"{prefix}{tool_name}"
        return tool_name

    # === Todo Recitation ===

    def update_todo(
        self,
        plan_steps: List[str],
        current_step: int,
        completed_steps: List[int],
    ) -> None:
        """Update todo recitation from plan state."""
        self.todo = TodoRecitation(title="Task Progress")

        # Add remaining items
        for i, step in enumerate(plan_steps):
            if i not in completed_steps:
                self.todo.add_item(step, priority=1 if i == current_step else 2)

        # Mark completed
        for i in completed_steps:
            if i < len(plan_steps):
                self.todo.completed_items.append({
                    "description": plan_steps[i],
                    "status": "completed",
                    "completed_at": datetime.utcnow().isoformat(),
                })

    def get_recitation_context(self) -> str:
        """Get todo recitation for context injection."""
        if not self.recitation_enabled:
            return ""
        return self.todo.to_recitation_string()

    def should_recite(self) -> bool:
        """Check if recitation should be included based on step count."""
        return self.step_count % self.todo.update_frequency == 0

    # === Error Retention ===

    def record_error(
        self,
        tool_name: str,
        error_message: str,
        input_args: Dict[str, Any] = None,
    ) -> None:
        """Record an error for retention and learning."""
        if not self.retain_errors:
            return
        self.error_retention.record_error(
            tool_name=tool_name,
            error_message=error_message,
            input_args=input_args,
        )

    def get_error_context(self) -> str:
        """Get retained errors for context injection."""
        if not self.retain_errors:
            return ""
        return self.error_retention.to_context_string()

    # === Serialization Variation ===

    def serialize_with_variation(
        self,
        action: str,
        input_data: Dict[str, Any],
        result: str,
    ) -> str:
        """Serialize action with variation to avoid few-shot traps."""
        if not self.vary_serialization:
            return f"Action: {action}\nInput: {json.dumps(input_data)}\nResult: {result}"
        return self.serialization.serialize_action(action, input_data, result)

    # === Combined Context Generation ===

    def build_context(
        self,
        base_events: List[Dict[str, Any]],
        include_todo: bool = True,
        include_errors: bool = True,
        include_tool_masks: bool = True,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Build optimized context with all context engineering techniques.

        Returns:
            Tuple of (prefix_context, event_context) where:
            - prefix_context: Stable prefix for KV-cache optimization
            - event_context: Dynamic events with variations applied
        """
        self.step_count += 1

        # Build prefix (stable)
        prefix_parts = [self.system_prefix]

        # Add masked tools context (relatively stable)
        if include_tool_masks:
            masks_ctx = self.get_masked_tools_context()
            if masks_ctx:
                prefix_parts.append(masks_ctx)

        prefix = "\n\n".join(filter(None, prefix_parts))

        # Build dynamic context
        dynamic_parts = []

        # Add todo recitation
        if include_todo and self.should_recite():
            recitation = self.get_recitation_context()
            if recitation:
                dynamic_parts.append(recitation)

        # Add error retention
        if include_errors:
            errors = self.get_error_context()
            if errors:
                dynamic_parts.append(errors)

        # Process events with variation
        processed_events = []
        for event in base_events:
            if self.vary_serialization and event.get("type") == "observation":
                # Apply variation to observations
                event = dict(event)
                event["output"] = self.serialization.add_variation(event.get("output", ""))
            processed_events.append(event)

        return prefix, processed_events

    def increment_step(self) -> None:
        """Increment step counter for context management."""
        self.step_count += 1
        self.context_version += 1
