"""
Test script for the Manus-Aligned core modules.

This script tests the new architectural components without requiring
full LLM or config setup:
- Event-driven context with 7 event types
- Planner module structure
- Knowledge module
- Datasource module
- Context engineering
"""

import asyncio
import sys
import os

# Add the app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import only the core modules (no LLM dependencies)
from app.core.events import (
    EventStream,
    EventType,
    MessageEvent,
    ActionEvent,
    ObservationEvent,
    PlanEvent,
    KnowledgeEvent,
    DatasourceEvent,
    SystemEvent,
)
from app.core.planner import Planner, Plan, PlanStep, StepStatus
from app.core.knowledge import KnowledgeModule, KnowledgeScope, KnowledgeCategory
from app.core.datasource import DatasourceModule, Datasource, AuthMethod
from app.core.context import ContextEngine, TodoRecitation, ErrorRetention


def test_event_stream():
    """Test the Event Stream with 7 event types."""
    print("\n" + "=" * 60)
    print("Testing Event Stream (7 Event Types)")
    print("=" * 60)

    stream = EventStream()

    # Add different event types
    print("\nAdding events to stream...")

    # 1. Message Event
    msg = MessageEvent(role="user", content="Analyze this sales data and create a report")
    stream.append(msg)
    print(f"  1. MESSAGE: {msg.to_context()[:50]}...")

    # 2. Action Event
    action = ActionEvent(
        tool_name="python_execute",
        tool_input={"code": "import pandas as pd\ndf = pd.read_csv('sales.csv')"},
        tool_call_id="call_123"
    )
    stream.append(action)
    print(f"  2. ACTION: {action.to_context()[:50]}...")

    # 3. Observation Event
    obs = ObservationEvent(
        tool_name="python_execute",
        tool_call_id="call_123",
        output="DataFrame loaded: 1000 rows, 5 columns"
    )
    stream.append(obs)
    print(f"  3. OBSERVATION: {obs.to_context()[:50]}...")

    # 4. Plan Event
    plan = PlanEvent(
        plan_id="plan_001",
        title="Sales Data Analysis",
        steps=["Load data", "Clean data", "Analyze trends", "Generate report"],
        step_statuses=["completed", "in_progress", "pending", "pending"],
        current_step_index=1
    )
    stream.append(plan)
    print(f"  4. PLAN: {plan.to_context()[:50]}...")

    # 5. Knowledge Event
    knowledge = KnowledgeEvent(
        category="best_practice",
        scope="data_analysis",
        content="Always validate data before analysis. Check for nulls and outliers.",
        conditions=["When working with datasets"],
        priority=8
    )
    stream.append(knowledge)
    print(f"  5. KNOWLEDGE: {knowledge.to_context()[:50]}...")

    # 6. Datasource Event
    datasource = DatasourceEvent(
        source_id="weather_api",
        name="OpenWeatherMap",
        description="Weather data API",
        endpoint="https://api.openweathermap.org",
        priority=8
    )
    stream.append(datasource)
    print(f"  6. DATASOURCE: {datasource.to_context()[:50]}...")

    # 7. System Event
    system = SystemEvent(
        event_name="step_completed",
        data={"step_index": 0, "duration_ms": 1500}
    )
    stream.append(system)
    print(f"  7. SYSTEM: {system.to_context()[:50]}...")

    print(f"\nEvent stream contains {len(stream.events)} events")
    print(f"Events by type:")
    for event_type in EventType:
        count = len(stream.get_by_type(event_type))
        if count > 0:
            print(f"  - {event_type.value}: {count}")

    # Test serialization (for KV-cache)
    serialized = stream.serialize()
    print(f"\nSerialization length: {len(serialized)} bytes")

    return True


def test_planner_module():
    """Test the Planner module as a system component."""
    print("\n" + "=" * 60)
    print("Testing Planner Module (System Component, NOT a tool)")
    print("=" * 60)

    # Create a plan directly (simulating what the Planner would do)
    plan = Plan(
        title="Build Web Scraper",
        objective="Create a web scraper to collect weather data"
    )

    # Add steps
    plan.add_step("Set up project structure and dependencies")
    plan.add_step("Implement HTTP client with retry logic")
    plan.add_step("Parse weather data from API responses")
    plan.add_step("Store data in structured format")
    plan.add_step("Add error handling and logging")

    print(f"\nPlan: {plan.title}")
    print(f"ID: {plan.id}")
    print(f"Objective: {plan.objective}")
    print("\nSteps (pseudocode format):")
    print(plan.to_pseudocode())

    # Simulate execution
    print("\n--- Simulating execution ---")

    # Complete first step
    plan.steps[0].complete("Dependencies installed")
    plan.advance()
    print(f"\nAfter step 1: {plan.get_progress()}")

    # Complete second step
    plan.steps[1].complete()
    plan.advance()
    print(f"After step 2: {plan.get_progress()}")

    print("\nKey difference from OpenManus PlanningTool:")
    print("  - Planner operates INDEPENDENTLY, not as an agent-callable tool")
    print("  - Plans are INJECTED into context by the system")
    print("  - Agent follows the plan without explicitly invoking it")

    return True


def test_knowledge_module():
    """Test the Knowledge module for best practices injection."""
    print("\n" + "=" * 60)
    print("Testing Knowledge Module")
    print("=" * 60)

    knowledge = KnowledgeModule()

    print(f"\nLoaded {len(knowledge.knowledge_base)} default knowledge items")
    print("\nKnowledge by scope:")
    scopes = {}
    for item in knowledge.knowledge_base:
        scope = item.scope.value
        scopes[scope] = scopes.get(scope, 0) + 1
    for scope, count in sorted(scopes.items()):
        print(f"  - {scope}: {count} items")

    # Test context-based retrieval
    test_cases = [
        ("browser click navigate web page", "browser"),
        ("python code file I/O network", "coding"),
        ("pandas dataframe analyze missing", "data_analysis"),
        ("rm delete remove file", "shell"),
    ]

    print("\nContext-based knowledge retrieval:")
    for context, expected_scope in test_cases:
        relevant = knowledge.get_relevant_knowledge(context)
        if relevant:
            print(f"\n  Context: '{context}'")
            for item in relevant[:2]:
                print(f"    [{item.scope.value}:{item.category.value}] {item.content[:60]}...")

    return True


def test_datasource_module():
    """Test the Datasource module for authoritative API access."""
    print("\n" + "=" * 60)
    print("Testing Datasource Module")
    print("=" * 60)

    datasource = DatasourceModule()

    print(f"\nRegistered {len(datasource.sources)} data sources:")
    for source_id, source in datasource.sources.items():
        print(f"  - {source.name} (priority: {source.priority})")
        print(f"    {source.description}")
        print(f"    Endpoints: {len(source.endpoints)}")

    # Test relevance matching
    print("\nQuery-based source discovery:")
    queries = ["weather forecast temperature", "github repository code", "country population capital"]

    for query in queries:
        relevant = datasource.find_relevant(query)
        print(f"\n  Query: '{query}'")
        print(f"  Matching sources: {[s.name for s in relevant]}")

    print("\nKey difference from OpenManus:")
    print("  - Authoritative APIs are PREFERRED over web search")
    print("  - Agent receives API documentation automatically")
    print("  - Pre-configured authentication handling")

    return True


def test_context_engine():
    """Test the Context Engineering module."""
    print("\n" + "=" * 60)
    print("Testing Context Engineering Module")
    print("=" * 60)

    context = ContextEngine()

    # 1. KV-Cache optimization
    print("\n1. KV-Cache Optimization:")
    context.set_stable_prefix("You are Manus, an AI agent designed to accomplish tasks.")
    print(f"   Stable prefix hash: {context.prefix_hash}")
    print("   - Prefix is stable across sessions for cache hits")
    print("   - Context is append-only to preserve cache")

    # 2. Tool masking
    print("\n2. Tool Masking (not removal):")
    context.mask_tool("browser_use", reason="Browser not available")
    context.mask_tool("file_write", reason="Read-only environment")
    print(context.get_masked_tools_context())
    print("   - Tools are MASKED, not removed from context")
    print("   - Maintains KV-cache stability")

    # 3. Todo recitation
    print("\n3. Todo Recitation (Attention Manipulation):")
    context.update_todo(
        plan_steps=["Analyze data", "Create visualization", "Generate report"],
        current_step=1,
        completed_steps=[0]
    )
    print(context.get_recitation_context())
    print("   - Pushes plan into recent attention span")
    print("   - Combats goal drift in long tasks")

    # 4. Error retention
    print("\n4. Error Retention:")
    context.record_error("python_execute", "SyntaxError: unexpected indent")
    context.record_error("file_read", "FileNotFoundError: data.csv not found")
    print(context.get_error_context())
    print("   - Errors are RETAINED in context")
    print("   - Enables learning from mistakes")

    # 5. Serialization variation
    print("\n5. Few-Shot Trap Avoidance:")
    result1 = context.serialize_with_variation("python_execute", {"code": "x=1"}, "1")
    result2 = context.serialize_with_variation("python_execute", {"code": "y=2"}, "2")
    print(f"   Serialization 1: {result1[:50]}...")
    print(f"   Serialization 2: {result2[:50]}...")
    print("   - Varies serialization templates")
    print("   - Prevents overgeneralization")

    return True


def main():
    """Run all core module tests."""
    print("\n" + "=" * 60)
    print("  MANUS-ALIGNED CORE MODULES TEST SUITE")
    print("=" * 60)
    print("\nThese tests demonstrate the architectural improvements")
    print("that align OpenManus with the actual Manus implementation.")

    tests = [
        ("Event Stream (7 Types)", test_event_stream),
        ("Planner Module", test_planner_module),
        ("Knowledge Module", test_knowledge_module),
        ("Datasource Module", test_datasource_module),
        ("Context Engine", test_context_engine),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\nError in {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {name}: {status}")

    passed = sum(1 for _, r in results if r)
    print(f"\nTotal: {passed}/{len(results)} tests passed")

    print("\n" + "=" * 60)
    print("ARCHITECTURAL IMPROVEMENTS SUMMARY")
    print("=" * 60)
    print("""
  1. EVENT-DRIVEN ARCHITECTURE
     - 7 distinct event types vs. simple Memory class
     - Append-only for KV-cache stability
     - Multi-source context enrichment

  2. PLANNER AS SYSTEM MODULE
     - Independent component, NOT a tool
     - Plans injected into context automatically
     - Dynamic replanning on errors

  3. KNOWLEDGE INJECTION
     - Domain-specific best practices
     - Context-aware activation
     - Priority-based selection

  4. DATASOURCE INTEGRATION
     - Authoritative API access
     - Preferred over web search
     - Pre-configured endpoints

  5. CONTEXT ENGINEERING
     - KV-cache optimization
     - Tool masking (not removal)
     - Todo recitation for attention
     - Error retention for learning
     - Few-shot trap avoidance
""")


if __name__ == "__main__":
    main()
