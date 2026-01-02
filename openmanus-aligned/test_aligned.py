"""
Test script for the Manus-Aligned agent.

This script demonstrates the new architectural features:
- Event-driven context with 7 event types
- Planner module (separate from tools)
- Knowledge injection
- Datasource integration
- Context engineering optimizations
"""

import asyncio
import sys
import os

# Add the app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.agent.manus_aligned import ManusAligned
from app.core import (
    EventStream,
    Planner,
    KnowledgeModule,
    DatasourceModule,
    ContextEngine,
)
from app.logger import logger


async def test_planner_module():
    """Test the Planner module independently."""
    print("\n" + "=" * 60)
    print("Testing Planner Module (System Component, NOT a tool)")
    print("=" * 60)

    planner = Planner()

    # Analyze a request
    request = "Build a web scraper to collect weather data from multiple sources"
    print(f"\nRequest: {request}")

    # Create a plan
    print("\nPlanner creating structured plan...")
    plan = await planner.create_plan(request)

    print(f"\nPlan Title: {plan.title}")
    print(f"Plan ID: {plan.id}")
    print(f"Steps ({len(plan.steps)}):")
    for step in plan.steps:
        print(f"  {step.to_pseudocode()}")

    print(f"\nProgress: {plan.get_progress()}")
    return True


async def test_knowledge_module():
    """Test the Knowledge module."""
    print("\n" + "=" * 60)
    print("Testing Knowledge Module")
    print("=" * 60)

    knowledge = KnowledgeModule()

    # Test knowledge retrieval for different contexts
    test_contexts = [
        "I need to automate browser actions",
        "Let me write some Python code",
        "I'm analyzing this dataset with pandas",
    ]

    for context in test_contexts:
        print(f"\nContext: '{context}'")
        relevant = knowledge.get_relevant_knowledge(context)
        print(f"  Found {len(relevant)} relevant knowledge items:")
        for item in relevant[:2]:
            print(f"    - [{item.scope.value}] {item.content[:80]}...")

    return True


async def test_datasource_module():
    """Test the Datasource module."""
    print("\n" + "=" * 60)
    print("Testing Datasource Module")
    print("=" * 60)

    datasource = DatasourceModule()

    # Test datasource discovery
    test_queries = [
        "weather forecast",
        "github repository",
        "country information",
    ]

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        relevant = datasource.find_relevant(query)
        print(f"  Found {len(relevant)} relevant datasources:")
        for source in relevant:
            print(f"    - {source.name} (priority: {source.priority})")
            print(f"      {source.description}")

    return True


async def test_context_engine():
    """Test the Context Engineering module."""
    print("\n" + "=" * 60)
    print("Testing Context Engineering Module")
    print("=" * 60)

    context_engine = ContextEngine()

    # Test KV-cache prefix
    print("\n1. KV-Cache Optimization:")
    context_engine.set_stable_prefix("You are Manus, an AI agent.")
    print(f"   Prefix hash: {context_engine.prefix_hash}")

    # Test tool masking
    print("\n2. Tool Masking (not removal):")
    context_engine.mask_tool("browser_use", reason="Browser not available in this environment")
    masked_ctx = context_engine.get_masked_tools_context()
    print(f"   {masked_ctx}")

    # Test todo recitation
    print("\n3. Todo Recitation:")
    context_engine.update_todo(
        plan_steps=["Analyze requirements", "Implement solution", "Test results"],
        current_step=1,
        completed_steps=[0],
    )
    recitation = context_engine.get_recitation_context()
    print(f"   {recitation}")

    # Test error retention
    print("\n4. Error Retention:")
    context_engine.record_error(
        tool_name="python_execute",
        error_message="ModuleNotFoundError: No module named 'pandas'",
    )
    error_ctx = context_engine.get_error_context()
    print(f"   {error_ctx}")

    return True


async def test_event_stream():
    """Test the Event Stream."""
    print("\n" + "=" * 60)
    print("Testing Event Stream (7 Event Types)")
    print("=" * 60)

    from app.core.events import (
        MessageEvent,
        ActionEvent,
        ObservationEvent,
        PlanEvent,
        KnowledgeEvent,
        DatasourceEvent,
        SystemEvent,
    )

    stream = EventStream()

    # Add different event types
    stream.append(MessageEvent(role="user", content="Hello, analyze this data"))
    stream.append(ActionEvent(tool_name="python_execute", tool_input={"code": "print('test')"}))
    stream.append(ObservationEvent(tool_name="python_execute", tool_call_id="1", output="test"))
    stream.append(PlanEvent(plan_id="p1", title="Data Analysis", steps=["Load", "Analyze", "Report"], step_statuses=["completed", "in_progress", "pending"]))
    stream.append(KnowledgeEvent(category="best_practice", scope="coding", content="Always validate input"))
    stream.append(DatasourceEvent(source_id="api1", name="Test API", description="Test", endpoint="http://test.com"))
    stream.append(SystemEvent(event_name="step_complete", data={"step": 1}))

    print(f"\nEvent Stream contains {len(stream.events)} events:")
    for event in stream.events:
        print(f"  - {event.type.value}: {event.to_context()[:60]}...")

    return True


async def test_aligned_agent_creation():
    """Test creating the ManusAligned agent."""
    print("\n" + "=" * 60)
    print("Testing ManusAligned Agent Creation")
    print("=" * 60)

    try:
        # Note: Full agent creation may require LLM configuration
        # This tests the basic instantiation
        from app.agent.manus_aligned import ManusAligned

        print("\nManusAligned agent class loaded successfully!")
        print(f"  Name: {ManusAligned.__name__}")
        print(f"  Description: Agent with event-driven architecture and system modules")
        print("\n  Key differences from original Manus:")
        print("    - Planner is a system module, not a tool")
        print("    - Event stream with 7 event types")
        print("    - Knowledge injection for best practices")
        print("    - Datasource integration for authoritative APIs")
        print("    - Context engineering optimizations")

        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("  MANUS-ALIGNED OPENMANUS TEST SUITE")
    print("=" * 60)

    tests = [
        ("Planner Module", test_planner_module),
        ("Knowledge Module", test_knowledge_module),
        ("Datasource Module", test_datasource_module),
        ("Context Engine", test_context_engine),
        ("Event Stream", test_event_stream),
        ("Aligned Agent", test_aligned_agent_creation),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\nError in {name}: {e}")
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


if __name__ == "__main__":
    asyncio.run(main())
