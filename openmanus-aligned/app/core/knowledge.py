"""
Knowledge Module for Manus-aligned agent.

This module injects task-relevant best practices and reference information
into the event stream. Unlike OpenManus which has no equivalent, this module
provides domain-specific expertise with:
- Specific scopes (browser, coding, data_analysis, etc.)
- Conditions for adoption
- Priority levels

The Knowledge module is a system component that enriches the agent's context
without requiring explicit tool invocation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field
import re


class KnowledgeScope(str, Enum):
    """Scopes for knowledge application."""
    BROWSER = "browser"
    CODING = "coding"
    DATA_ANALYSIS = "data_analysis"
    FILE_OPERATIONS = "file_operations"
    WEB_SEARCH = "web_search"
    API_INTERACTION = "api_interaction"
    SHELL = "shell"
    GENERAL = "general"


class KnowledgeCategory(str, Enum):
    """Categories of knowledge."""
    BEST_PRACTICE = "best_practice"
    WARNING = "warning"
    REFERENCE = "reference"
    TIP = "tip"
    CONSTRAINT = "constraint"


class KnowledgeItem(BaseModel):
    """A piece of knowledge that can be injected into the context.

    Knowledge items have:
    - Scope: The domain this knowledge applies to
    - Category: The type of knowledge (best practice, warning, etc.)
    - Conditions: When this knowledge should be activated
    - Priority: Higher priority knowledge appears first
    """

    id: str
    scope: KnowledgeScope
    category: KnowledgeCategory
    content: str
    conditions: List[str] = Field(default_factory=list)
    triggers: List[str] = Field(default_factory=list)  # Keywords that activate this knowledge
    priority: int = 1  # 1-10, higher is more important
    enabled: bool = True
    usage_count: int = 0
    last_used: Optional[datetime] = None

    class Config:
        arbitrary_types_allowed = True

    def matches(self, context: str, active_tools: Set[str] = None) -> bool:
        """Check if this knowledge item should be activated for the given context."""
        if not self.enabled:
            return False

        # Check triggers in context
        context_lower = context.lower()
        for trigger in self.triggers:
            if trigger.lower() in context_lower:
                return True

        # Check if relevant tools are active
        if active_tools:
            scope_tools = {
                KnowledgeScope.BROWSER: {"browser", "browser_use", "web"},
                KnowledgeScope.CODING: {"python", "code", "execute"},
                KnowledgeScope.DATA_ANALYSIS: {"pandas", "data", "analyze"},
                KnowledgeScope.FILE_OPERATIONS: {"file", "read", "write", "edit"},
                KnowledgeScope.WEB_SEARCH: {"search", "google", "bing"},
                KnowledgeScope.API_INTERACTION: {"api", "http", "request"},
                KnowledgeScope.SHELL: {"bash", "shell", "terminal"},
            }
            relevant_tools = scope_tools.get(self.scope, set())
            if active_tools & relevant_tools:
                return True

        return False

    def to_context(self) -> str:
        """Format this knowledge item for context injection."""
        category_prefix = {
            KnowledgeCategory.BEST_PRACTICE: "BEST PRACTICE",
            KnowledgeCategory.WARNING: "WARNING",
            KnowledgeCategory.REFERENCE: "REFERENCE",
            KnowledgeCategory.TIP: "TIP",
            KnowledgeCategory.CONSTRAINT: "CONSTRAINT",
        }
        prefix = category_prefix.get(self.category, "KNOWLEDGE")
        lines = [f"[{prefix}:{self.scope.value.upper()}]", self.content]
        if self.conditions:
            lines.append(f"Apply when: {', '.join(self.conditions)}")
        return "\n".join(lines)

    def mark_used(self) -> None:
        """Mark this knowledge item as used."""
        self.usage_count += 1
        self.last_used = datetime.utcnow()


class KnowledgeModule(BaseModel):
    """Knowledge module that injects domain expertise into the agent's context.

    This module maintains a knowledge base of best practices, warnings, and
    reference information that can be selectively injected based on:
    - The current task context
    - Active tools being used
    - Explicit conditions

    Unlike OpenManus, which has no knowledge system, this module provides
    the agent with domain-specific expertise without requiring explicit queries.
    """

    knowledge_base: List[KnowledgeItem] = Field(default_factory=list)
    active_scopes: Set[KnowledgeScope] = Field(default_factory=set)
    max_injections: int = 5  # Maximum knowledge items to inject at once

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data):
        super().__init__(**data)
        if not self.knowledge_base:
            self._load_default_knowledge()

    def _load_default_knowledge(self) -> None:
        """Load default knowledge items covering common scenarios."""
        defaults = [
            # Browser best practices
            KnowledgeItem(
                id="browser_wait",
                scope=KnowledgeScope.BROWSER,
                category=KnowledgeCategory.BEST_PRACTICE,
                content="When interacting with web pages, always wait for elements to load before interacting. Use explicit waits rather than fixed delays.",
                triggers=["browser", "click", "navigate", "web page"],
                conditions=["Using browser automation"],
                priority=8,
            ),
            KnowledgeItem(
                id="browser_screenshot",
                scope=KnowledgeScope.BROWSER,
                category=KnowledgeCategory.TIP,
                content="Take screenshots after important actions to verify visual state. This helps identify rendering issues or unexpected UI changes.",
                triggers=["browser", "verify", "check"],
                conditions=["Debugging browser automation"],
                priority=5,
            ),
            KnowledgeItem(
                id="browser_selector",
                scope=KnowledgeScope.BROWSER,
                category=KnowledgeCategory.BEST_PRACTICE,
                content="Prefer stable selectors: data-testid > id > aria-label > unique class. Avoid fragile selectors based on DOM structure or index.",
                triggers=["selector", "element", "locate", "find"],
                conditions=["Selecting elements on web pages"],
                priority=9,
            ),

            # Coding best practices
            KnowledgeItem(
                id="code_error_handling",
                scope=KnowledgeScope.CODING,
                category=KnowledgeCategory.BEST_PRACTICE,
                content="Always wrap external operations (file I/O, network requests, etc.) in try-except blocks. Log errors with sufficient context for debugging.",
                triggers=["file", "network", "request", "api call"],
                conditions=["Performing I/O operations"],
                priority=8,
            ),
            KnowledgeItem(
                id="code_validation",
                scope=KnowledgeScope.CODING,
                category=KnowledgeCategory.BEST_PRACTICE,
                content="Validate input data before processing. Check for None, empty strings, and expected types. Fail fast with clear error messages.",
                triggers=["input", "parameter", "validate", "check"],
                conditions=["Processing user or external input"],
                priority=7,
            ),
            KnowledgeItem(
                id="code_incremental",
                scope=KnowledgeScope.CODING,
                category=KnowledgeCategory.TIP,
                content="For complex tasks, implement and test incrementally. Verify each component works before integrating. This makes debugging easier.",
                triggers=["complex", "multiple", "steps", "components"],
                conditions=["Building multi-step solutions"],
                priority=6,
            ),

            # Data analysis best practices
            KnowledgeItem(
                id="data_explore_first",
                scope=KnowledgeScope.DATA_ANALYSIS,
                category=KnowledgeCategory.BEST_PRACTICE,
                content="Before analysis, explore the data: check shape, dtypes, null values, and basic statistics. Use df.info(), df.describe(), df.head().",
                triggers=["data", "dataframe", "analyze", "pandas"],
                conditions=["Starting data analysis"],
                priority=9,
            ),
            KnowledgeItem(
                id="data_handle_missing",
                scope=KnowledgeScope.DATA_ANALYSIS,
                category=KnowledgeCategory.BEST_PRACTICE,
                content="Handle missing values explicitly. Document your strategy (drop, fill, impute) and reasoning. Check impact on analysis validity.",
                triggers=["missing", "null", "NaN", "empty"],
                conditions=["Dealing with incomplete data"],
                priority=8,
            ),

            # File operations
            KnowledgeItem(
                id="file_backup",
                scope=KnowledgeScope.FILE_OPERATIONS,
                category=KnowledgeCategory.WARNING,
                content="Before modifying important files, create a backup or verify version control status. Destructive operations cannot be undone.",
                triggers=["modify", "delete", "overwrite", "change file"],
                conditions=["Modifying existing files"],
                priority=9,
            ),
            KnowledgeItem(
                id="file_encoding",
                scope=KnowledgeScope.FILE_OPERATIONS,
                category=KnowledgeCategory.TIP,
                content="When reading files, specify encoding explicitly (usually 'utf-8'). Handle encoding errors gracefully with errors='replace' or errors='ignore'.",
                triggers=["read file", "open file", "encoding"],
                conditions=["Reading text files"],
                priority=6,
            ),

            # Web search
            KnowledgeItem(
                id="search_specific",
                scope=KnowledgeScope.WEB_SEARCH,
                category=KnowledgeCategory.BEST_PRACTICE,
                content="Use specific, targeted search queries. Include relevant technical terms. Prefer official documentation and authoritative sources.",
                triggers=["search", "find information", "look up"],
                conditions=["Performing web searches"],
                priority=7,
            ),

            # API interaction
            KnowledgeItem(
                id="api_rate_limit",
                scope=KnowledgeScope.API_INTERACTION,
                category=KnowledgeCategory.WARNING,
                content="Respect API rate limits. Implement exponential backoff for retries. Cache responses when appropriate to reduce API calls.",
                triggers=["api", "request", "rate limit", "throttle"],
                conditions=["Interacting with external APIs"],
                priority=8,
            ),
            KnowledgeItem(
                id="api_auth",
                scope=KnowledgeScope.API_INTERACTION,
                category=KnowledgeCategory.CONSTRAINT,
                content="Never hardcode API keys or secrets. Use environment variables or secure configuration. Check that secrets are not logged or exposed.",
                triggers=["api key", "secret", "token", "auth"],
                conditions=["Handling API authentication"],
                priority=10,
            ),

            # Shell operations
            KnowledgeItem(
                id="shell_verify",
                scope=KnowledgeScope.SHELL,
                category=KnowledgeCategory.BEST_PRACTICE,
                content="Before running destructive shell commands (rm, mv, chmod), verify paths and use dry-run options when available.",
                triggers=["rm", "delete", "remove", "mv", "chmod"],
                conditions=["Running destructive commands"],
                priority=9,
            ),

            # General
            KnowledgeItem(
                id="general_verify",
                scope=KnowledgeScope.GENERAL,
                category=KnowledgeCategory.BEST_PRACTICE,
                content="After completing a task, verify the result meets expectations. Check output correctness, not just successful execution.",
                triggers=["complete", "done", "finished", "result"],
                conditions=["Completing tasks"],
                priority=7,
            ),
        ]
        self.knowledge_base = defaults

    def add_knowledge(self, item: KnowledgeItem) -> None:
        """Add a knowledge item to the base."""
        self.knowledge_base.append(item)

    def remove_knowledge(self, item_id: str) -> bool:
        """Remove a knowledge item by ID."""
        for i, item in enumerate(self.knowledge_base):
            if item.id == item_id:
                self.knowledge_base.pop(i)
                return True
        return False

    def activate_scope(self, scope: KnowledgeScope) -> None:
        """Activate a knowledge scope."""
        self.active_scopes.add(scope)

    def deactivate_scope(self, scope: KnowledgeScope) -> None:
        """Deactivate a knowledge scope."""
        self.active_scopes.discard(scope)

    def get_relevant_knowledge(
        self,
        context: str,
        active_tools: Set[str] = None,
        scopes: Set[KnowledgeScope] = None,
    ) -> List[KnowledgeItem]:
        """Get knowledge items relevant to the current context.

        Args:
            context: The current task context or user message
            active_tools: Set of currently active tool names
            scopes: Specific scopes to filter by (uses active_scopes if None)
        """
        relevant = []
        target_scopes = scopes or self.active_scopes or set(KnowledgeScope)

        for item in self.knowledge_base:
            if not item.enabled:
                continue

            # Check scope
            if item.scope not in target_scopes and item.scope != KnowledgeScope.GENERAL:
                continue

            # Check if item matches context
            if item.matches(context, active_tools):
                relevant.append(item)

        # Sort by priority and limit
        relevant.sort(key=lambda x: x.priority, reverse=True)
        return relevant[:self.max_injections]

    def inject_knowledge(
        self,
        context: str,
        active_tools: Set[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get knowledge events to inject into the event stream.

        Returns a list of knowledge event dictionaries ready for injection.
        """
        relevant = self.get_relevant_knowledge(context, active_tools)
        events = []

        for item in relevant:
            item.mark_used()
            events.append({
                "type": "knowledge",
                "category": item.category.value,
                "scope": item.scope.value,
                "content": item.content,
                "conditions": item.conditions,
                "priority": item.priority,
            })

        return events

    def get_context_string(
        self,
        context: str,
        active_tools: Set[str] = None,
    ) -> str:
        """Get knowledge as a formatted context string for LLM injection."""
        relevant = self.get_relevant_knowledge(context, active_tools)

        if not relevant:
            return ""

        parts = ["[KNOWLEDGE BASE - Apply the following guidance:]", ""]
        for item in relevant:
            item.mark_used()
            parts.append(item.to_context())
            parts.append("")

        return "\n".join(parts)

    def detect_scope_from_tools(self, tools: Set[str]) -> Set[KnowledgeScope]:
        """Detect active scopes based on available/used tools."""
        detected = set()
        tool_scope_map = {
            "browser": KnowledgeScope.BROWSER,
            "browser_use": KnowledgeScope.BROWSER,
            "python": KnowledgeScope.CODING,
            "python_execute": KnowledgeScope.CODING,
            "code": KnowledgeScope.CODING,
            "pandas": KnowledgeScope.DATA_ANALYSIS,
            "data": KnowledgeScope.DATA_ANALYSIS,
            "file": KnowledgeScope.FILE_OPERATIONS,
            "read": KnowledgeScope.FILE_OPERATIONS,
            "write": KnowledgeScope.FILE_OPERATIONS,
            "search": KnowledgeScope.WEB_SEARCH,
            "web_search": KnowledgeScope.WEB_SEARCH,
            "api": KnowledgeScope.API_INTERACTION,
            "http": KnowledgeScope.API_INTERACTION,
            "bash": KnowledgeScope.SHELL,
            "shell": KnowledgeScope.SHELL,
        }

        for tool in tools:
            tool_lower = tool.lower()
            for key, scope in tool_scope_map.items():
                if key in tool_lower:
                    detected.add(scope)

        return detected
