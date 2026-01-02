# OpenManus Architecture Alignment

This document describes the architectural changes made to align OpenManus with the actual Manus AI implementation, addressing the discrepancies identified in the technical analysis.

## Overview

The aligned implementation introduces several major architectural improvements:

1. **Event-Driven Architecture** - Rich event stream with 7 distinct event types
2. **Planner Module** - Separate system component (not a tool)
3. **Knowledge Module** - Best practices and domain expertise injection
4. **Datasource Module** - Authoritative API access
5. **Context Engineering** - Production-grade optimizations

## Architecture Comparison

| Feature | Original OpenManus | Aligned Implementation | Severity |
|---------|-------------------|----------------------|----------|
| **Planner Module** | Tool-based (`PlanningTool`) | Separate system component | **Fixed** |
| **Event Stream** | Simple `Memory` class | 7 distinct event types | **Fixed** |
| **Knowledge Module** | None | Full implementation | **Fixed** |
| **Datasource Module** | None | Full implementation | **Fixed** |
| **KV-Cache Optimization** | None | Stable prefix, deterministic serialization | **Fixed** |
| **Tool Masking** | Dynamic removal | Masking with availability states | **Fixed** |
| **Todo Recitation** | None | Attention manipulation via todo.md | **Fixed** |
| **Error Retention** | None | Retained for learning | **Fixed** |
| **Few-Shot Trap Avoidance** | None | Serialization variation | **Fixed** |

## Module Details

### 1. Event-Driven Architecture (`app/core/events.py`)

The event stream now supports 7 distinct event types:

```python
class EventType(str, Enum):
    MESSAGE = "message"      # User/assistant communication
    ACTION = "action"        # Tool calls
    OBSERVATION = "observation"  # Tool results
    PLAN = "plan"           # Task plans from Planner
    KNOWLEDGE = "knowledge" # Best practices from Knowledge module
    DATASOURCE = "datasource"  # API documentation
    SYSTEM = "system"       # Internal system events
```

Key features:
- Append-only operations (for KV-cache stability)
- Deterministic serialization
- Multi-source context enrichment

### 2. Planner Module (`app/core/planner.py`)

The Planner is now an **independent system component**, not a tool:

```python
class Planner(BaseModel):
    """Planner module that operates as an independent system component."""

    async def analyze_request(self, request: str) -> Dict[str, Any]:
        """Analyze if planning is needed."""

    async def create_plan(self, request: str, context: str = "") -> Plan:
        """Create structured plan for execution."""

    async def replan(self, reason: str, context: str = "") -> Plan:
        """Create revised plan based on errors or changes."""
```

Key differences from `PlanningTool`:
- Plans are **injected** into context, not requested by agent
- Planner monitors execution and updates dynamically
- Replanning triggered by system on errors

### 3. Knowledge Module (`app/core/knowledge.py`)

Injects domain-specific best practices:

```python
class KnowledgeItem(BaseModel):
    scope: KnowledgeScope      # browser, coding, data_analysis, etc.
    category: KnowledgeCategory  # best_practice, warning, tip
    content: str
    conditions: List[str]      # When to apply
    priority: int             # 1-10, higher is more important
```

Features:
- Automatic activation based on context
- Scope-based filtering
- Priority-based injection limits

### 4. Datasource Module (`app/core/datasource.py`)

Provides authoritative API access:

```python
class Datasource(BaseModel):
    name: str
    base_url: str
    auth_method: AuthMethod
    endpoints: List[ApiEndpoint]
    priority: int  # Higher = more authoritative
```

Features:
- Pre-configured API documentation
- Authentication handling
- Code generation for API calls
- Priority over web search

### 5. Context Engineering (`app/core/context.py`)

Implements production-grade optimizations:

#### KV-Cache Optimization
```python
def set_stable_prefix(self, prefix: str) -> None:
    """Set stable prefix for KV-cache optimization."""

def get_deterministic_context(self, events: List[Dict]) -> str:
    """Generate deterministic context for consistent caching."""
```

#### Tool Masking
```python
def mask_tool(self, tool_name: str, reason: str = "") -> None:
    """Mask a tool instead of removing it."""
    # Maintains KV-cache stability
```

#### Todo Recitation
```python
class TodoRecitation(BaseModel):
    """Manages todo.md for attention manipulation."""

    def to_recitation_string(self) -> str:
        """Generate context for LLM injection."""
```

#### Error Retention
```python
class ErrorRetention(BaseModel):
    """Retains errors for learning from mistakes."""

    def record_error(self, tool_name: str, error_message: str) -> None:
        """Record error for context injection."""
```

#### Few-Shot Trap Avoidance
```python
class SerializationVariation(BaseModel):
    """Prevents overgeneralization through variation."""

    def serialize_action(self, action: str, input_data: Dict) -> str:
        """Serialize with template rotation."""
```

## Usage

### Using the Aligned Agent

```python
from app.agent import ManusAligned

# Create aligned agent
agent = await ManusAligned.create()

# Run task
result = await agent.run("Analyze sales data and create a report")

# Check plan status
status = agent.get_plan_status()

# Get event stream summary
summary = agent.get_event_stream_summary()
```

### Accessing Core Modules

```python
from app.core import (
    EventStream,
    Planner,
    KnowledgeModule,
    DatasourceModule,
    ContextEngine,
)

# Create planner
planner = Planner()
plan = await planner.create_plan("Build a web scraper")

# Get knowledge
knowledge = KnowledgeModule()
relevant = knowledge.get_relevant_knowledge("browser automation")

# Find datasources
datasource = DatasourceModule()
apis = datasource.find_relevant("weather data")

# Context engineering
context = ContextEngine()
context.mask_tool("browser_use", "Not available in this environment")
```

## Migration Guide

### From Original OpenManus

1. Replace `Manus` agent with `ManusAligned`
2. Remove `PlanningTool` from tool collections
3. Plans are now automatic - no need to invoke planning

### From `PlanningTool` Usage

Before:
```python
# Agent explicitly calls planning tool
await agent.available_tools.execute("planning", command="create", ...)
```

After:
```python
# Planning is automatic via Planner module
# Plans are injected into context as PlanEvent
agent = await ManusAligned.create()
result = await agent.run(request)  # Planning happens automatically
```

## References

- [Context Engineering for AI Agents](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)
- [Manus Tools and Prompts](https://gist.github.com/jlia0/db0a9695b3ca7609c9b1a08dcbf872c9)
- [Technical Investigation](https://gist.github.com/renschni/4fbc70b31bad8dd57f3370239dccd58f)
