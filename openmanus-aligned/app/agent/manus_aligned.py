"""
Manus-Aligned Agent Implementation.

This agent implementation aligns with the actual Manus architecture by:

1. Using an event-driven architecture with 7 distinct event types:
   - Message, Action, Observation, Plan, Knowledge, Datasource, System

2. Separating the Planner as a system component (not a tool):
   - Planner operates independently to guide execution
   - Plans are injected as system events, not requested by the agent

3. Integrating Knowledge and Datasource modules:
   - Knowledge module provides domain-specific best practices
   - Datasource module provides authoritative API access

4. Implementing context engineering optimizations:
   - KV-cache optimization with stable prefixes
   - Tool masking instead of removal
   - Todo.md recitation for attention manipulation
   - Error retention for learning from mistakes
   - Few-shot trap avoidance through serialization variation
"""

from typing import Any, Dict, List, Optional, Set
import json

from pydantic import Field, model_validator

from app.agent.browser import BrowserContextHelper
from app.agent.toolcall import ToolCallAgent
from app.config import config
from app.logger import logger
from app.prompt.manus import NEXT_STEP_PROMPT
from app.schema import AgentState, Message
from app.tool import Terminate, ToolCollection
from app.tool.ask_human import AskHuman
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.mcp import MCPClients, MCPClientTool
from app.tool.python_execute import PythonExecute
from app.tool.str_replace_editor import StrReplaceEditor

# Import new Manus-aligned core modules
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
from app.core.planner import Planner, Plan, StepStatus
from app.core.knowledge import KnowledgeModule, KnowledgeScope
from app.core.datasource import DatasourceModule
from app.core.context import ContextEngine


# System prompt aligned with actual Manus principles
ALIGNED_SYSTEM_PROMPT = """You are Manus, an AI agent designed to accomplish complex tasks autonomously.

CORE PRINCIPLES:
1. You receive guidance from the Planner module. Follow the plan steps systematically.
2. Use authoritative data sources before falling back to web search.
3. Apply best practices from the Knowledge module.
4. Learn from errors - do not repeat failed approaches.
5. Complete all plan steps to finish the task.

EXECUTION MODEL:
- Each step should be atomic and verifiable
- Report progress after each action
- If blocked, explain why and suggest alternatives
- Always verify results before marking steps complete

Your current working directory is: {directory}
"""


class ManusAligned(ToolCallAgent):
    """A Manus-aligned agent with proper architectural separation.

    This agent implementation follows the actual Manus architecture:
    - Event-driven context with 7 event types
    - Planner as a system module (not a tool)
    - Knowledge injection for best practices
    - Datasource integration for authoritative APIs
    - Context engineering optimizations
    """

    name: str = "ManusAligned"
    description: str = "A Manus-aligned agent with event-driven architecture and system-level modules"

    system_prompt: str = ALIGNED_SYSTEM_PROMPT.format(directory=config.workspace_root)
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_observe: int = 10000
    max_steps: int = 30

    # MCP clients for remote tool access
    mcp_clients: MCPClients = Field(default_factory=MCPClients)

    # Core tools (note: planning is NOT a tool here)
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            PythonExecute(),
            BrowserUseTool(),
            StrReplaceEditor(),
            AskHuman(),
            Terminate(),
        )
    )

    special_tool_names: list[str] = Field(default_factory=lambda: [Terminate().name])
    browser_context_helper: Optional[BrowserContextHelper] = None

    # === NEW: Manus-aligned system modules ===

    # Event stream for multi-source context
    event_stream: EventStream = Field(default_factory=EventStream)

    # Planner module (system component, NOT a tool)
    planner: Planner = Field(default_factory=Planner)

    # Knowledge module for best practices
    knowledge: KnowledgeModule = Field(default_factory=KnowledgeModule)

    # Datasource module for authoritative APIs
    datasource: DatasourceModule = Field(default_factory=DatasourceModule)

    # Context engineering
    context_engine: ContextEngine = Field(default_factory=ContextEngine)

    # Track connected MCP servers
    connected_servers: Dict[str, str] = Field(default_factory=dict)
    _initialized: bool = False
    _plan_created: bool = False

    @model_validator(mode="after")
    def initialize_helper(self) -> "ManusAligned":
        """Initialize basic components synchronously."""
        self.browser_context_helper = BrowserContextHelper(self)
        # Set stable prefix for KV-cache optimization
        self.context_engine.set_stable_prefix(self.system_prompt)
        return self

    @classmethod
    async def create(cls, **kwargs) -> "ManusAligned":
        """Factory method to create and properly initialize a ManusAligned instance."""
        instance = cls(**kwargs)
        await instance.initialize_mcp_servers()
        instance._initialized = True
        return instance

    async def initialize_mcp_servers(self) -> None:
        """Initialize connections to configured MCP servers."""
        for server_id, server_config in config.mcp_config.servers.items():
            try:
                if server_config.type == "sse":
                    if server_config.url:
                        await self.connect_mcp_server(server_config.url, server_id)
                        logger.info(f"Connected to MCP server {server_id}")
                elif server_config.type == "stdio":
                    if server_config.command:
                        await self.connect_mcp_server(
                            server_config.command,
                            server_id,
                            use_stdio=True,
                            stdio_args=server_config.args,
                        )
                        logger.info(f"Connected to MCP server {server_id}")
            except Exception as e:
                logger.error(f"Failed to connect to MCP server {server_id}: {e}")

    async def connect_mcp_server(
        self,
        server_url: str,
        server_id: str = "",
        use_stdio: bool = False,
        stdio_args: List[str] = None,
    ) -> None:
        """Connect to an MCP server and add its tools."""
        if use_stdio:
            await self.mcp_clients.connect_stdio(
                server_url, stdio_args or [], server_id
            )
            self.connected_servers[server_id or server_url] = server_url
        else:
            await self.mcp_clients.connect_sse(server_url, server_id)
            self.connected_servers[server_id or server_url] = server_url

        # Update available tools with only the new tools from this server
        new_tools = [
            tool for tool in self.mcp_clients.tools if tool.server_id == server_id
        ]
        self.available_tools.add_tools(*new_tools)

    async def disconnect_mcp_server(self, server_id: str = "") -> None:
        """Disconnect from an MCP server and remove its tools."""
        await self.mcp_clients.disconnect(server_id)
        if server_id:
            self.connected_servers.pop(server_id, None)
        else:
            self.connected_servers.clear()

        # Rebuild available tools without the disconnected server's tools
        base_tools = [
            tool
            for tool in self.available_tools.tools
            if not isinstance(tool, MCPClientTool)
        ]
        self.available_tools = ToolCollection(*base_tools)
        self.available_tools.add_tools(*self.mcp_clients.tools)

    # === Event-Driven Methods ===

    def _add_message_event(self, role: str, content: str, base64_image: str = None) -> None:
        """Add a message event to the event stream."""
        event = MessageEvent(
            role=role,
            content=content,
            base64_image=base64_image,
        )
        self.event_stream.append(event)

    def _add_action_event(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_call_id: str,
    ) -> None:
        """Add an action event to the event stream."""
        event = ActionEvent(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_call_id=tool_call_id,
        )
        self.event_stream.append(event)

    def _add_observation_event(
        self,
        tool_name: str,
        tool_call_id: str,
        output: str,
        error: str = None,
        base64_image: str = None,
    ) -> None:
        """Add an observation event to the event stream."""
        event = ObservationEvent(
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            output=output,
            error=error,
            base64_image=base64_image,
        )
        self.event_stream.append(event)

        # Record errors for error retention
        if error:
            self.context_engine.record_error(
                tool_name=tool_name,
                error_message=error,
            )

    def _inject_plan_event(self) -> None:
        """Inject current plan as a Plan event."""
        if not self.planner.current_plan:
            return

        plan = self.planner.current_plan
        event = PlanEvent(
            plan_id=plan.id,
            title=plan.title,
            steps=[s.description for s in plan.steps],
            step_statuses=[s.status.value for s in plan.steps],
            current_step_index=plan.current_step_index,
            is_complete=plan.is_complete,
        )
        self.event_stream.append(event)

    def _inject_knowledge_events(self, context: str) -> None:
        """Inject relevant knowledge as Knowledge events."""
        active_tools = set(self.available_tools.tool_map.keys())
        relevant = self.knowledge.get_relevant_knowledge(context, active_tools)

        for item in relevant[:3]:  # Limit to top 3
            event = KnowledgeEvent(
                category=item.category.value,
                scope=item.scope.value,
                content=item.content,
                conditions=item.conditions,
                priority=item.priority,
            )
            self.event_stream.append(event)

    def _inject_datasource_events(self, context: str) -> None:
        """Inject relevant datasources as Datasource events."""
        relevant = self.datasource.find_relevant(context, limit=2)

        for source in relevant:
            event = DatasourceEvent(
                source_id=source.id,
                name=source.name,
                description=source.description,
                endpoint=source.base_url,
                auth_method=source.auth_method.value if source.auth_method else None,
                documentation=source.to_documentation(),
                priority=source.priority,
            )
            self.event_stream.append(event)

    # === Override Core Agent Methods ===

    async def run(self, request: Optional[str] = None) -> str:
        """Execute the agent with Manus-aligned architecture.

        This method:
        1. Analyzes the request through the Planner module
        2. Creates a structured plan (if needed)
        3. Injects plan, knowledge, and datasource events
        4. Executes steps with context engineering optimizations
        """
        if self.state != AgentState.IDLE:
            raise RuntimeError(f"Cannot run agent from state: {self.state}")

        if request:
            # Add user message to event stream
            self._add_message_event("user", request)
            self.update_memory("user", request)

            # === PLANNER MODULE: Analyze and create plan ===
            if not self._plan_created:
                logger.info("Planner analyzing request...")
                analysis = await self.planner.analyze_request(request)

                if analysis.get("needs_planning", True):
                    logger.info("Planner creating structured plan...")
                    plan = await self.planner.create_plan(request)
                    self._plan_created = True

                    # Inject plan event
                    self._inject_plan_event()

                    # Update todo recitation
                    self.context_engine.update_todo(
                        [s.description for s in plan.steps],
                        plan.current_step_index,
                        [],
                    )

            # === KNOWLEDGE MODULE: Inject relevant knowledge ===
            self._inject_knowledge_events(request)

            # === DATASOURCE MODULE: Inject relevant datasources ===
            self._inject_datasource_events(request)

        # Execute main loop
        return await super().run()

    async def think(self) -> bool:
        """Process current state with context engineering optimizations."""
        if not self._initialized:
            await self.initialize_mcp_servers()
            self._initialized = True

        # Increment step for context engineering
        self.context_engine.increment_step()

        # Build optimized context
        if self.context_engine.should_recite():
            # Update todo recitation with current plan state
            if self.planner.current_plan:
                completed = [
                    i for i, s in enumerate(self.planner.current_plan.steps)
                    if s.status == StepStatus.COMPLETED
                ]
                self.context_engine.update_todo(
                    [s.description for s in self.planner.current_plan.steps],
                    self.planner.current_plan.current_step_index,
                    completed,
                )

        # Build context with all optimizations
        prefix, events = self.context_engine.build_context(
            [e.to_dict() for e in self.event_stream.events],
            include_todo=True,
            include_errors=True,
            include_tool_masks=True,
        )

        # Inject recitation into next step prompt if needed
        original_prompt = self.next_step_prompt
        recitation = self.context_engine.get_recitation_context()
        if recitation:
            self.next_step_prompt = f"{recitation}\n\n{original_prompt}"

        # Get masked tools context
        masked_context = self.context_engine.get_masked_tools_context()
        if masked_context:
            self.next_step_prompt = f"{masked_context}\n\n{self.next_step_prompt}"

        # Handle browser context
        recent_messages = self.memory.messages[-3:] if self.memory.messages else []
        browser_in_use = any(
            tc.function.name == BrowserUseTool().name
            for msg in recent_messages
            if msg.tool_calls
            for tc in msg.tool_calls
        )

        if browser_in_use:
            self.next_step_prompt = (
                await self.browser_context_helper.format_next_step_prompt()
            )

        # Call parent think
        result = await super().think()

        # Restore original prompt
        self.next_step_prompt = original_prompt

        return result

    async def act(self) -> str:
        """Execute tool calls and record to event stream."""
        if not self.tool_calls:
            return await super().act()

        results = []
        for command in self.tool_calls:
            tool_name = command.function.name
            tool_input = json.loads(command.function.arguments or "{}")

            # Add action event to stream
            self._add_action_event(tool_name, tool_input, command.id)

            # Execute tool
            result = await self.execute_tool(command)

            # Determine if there was an error
            is_error = result.startswith("Error:") if result else False

            # Add observation event
            self._add_observation_event(
                tool_name=tool_name,
                tool_call_id=command.id,
                output=result if not is_error else "",
                error=result if is_error else None,
            )

            # Check if we should replan due to error
            if is_error and self.planner.replan_on_error:
                should_replan = await self.planner.should_replan(result)
                if should_replan:
                    logger.info("Planner initiating replan due to error...")
                    await self.planner.replan(
                        reason=f"Error in {tool_name}: {result}",
                        context=self._get_current_context_summary(),
                    )
                    self._inject_plan_event()

            # Update plan progress if step completed successfully
            if not is_error and self.planner.current_plan:
                current_step = self.planner.current_plan.get_current_step()
                if current_step and self._step_appears_complete(tool_name, result):
                    self.planner.advance_plan()
                    self._inject_plan_event()

            if self.max_observe:
                result = result[:self.max_observe]

            results.append(result)

        return "\n\n".join(results)

    def _get_current_context_summary(self) -> str:
        """Get a summary of current context for replanning."""
        parts = []
        if self.planner.current_plan:
            parts.append(f"Plan: {self.planner.current_plan.title}")
            parts.append(f"Progress: {self.planner.current_plan.get_progress()}")

        recent_errors = self.context_engine.error_retention.get_relevant_errors(limit=3)
        if recent_errors:
            parts.append(f"Recent errors: {len(recent_errors)}")

        return "\n".join(parts)

    def _step_appears_complete(self, tool_name: str, result: str) -> bool:
        """Heuristic to determine if current step appears complete."""
        # This is a simplified heuristic - in production would use LLM judgment
        if not self.planner.current_plan:
            return False

        current_step = self.planner.current_plan.get_current_step()
        if not current_step:
            return False

        # Check for success indicators
        success_indicators = ["success", "completed", "done", "created", "updated"]
        return any(ind in result.lower() for ind in success_indicators)

    async def cleanup(self):
        """Clean up ManusAligned agent resources."""
        if self.browser_context_helper:
            await self.browser_context_helper.cleanup_browser()
        if self._initialized:
            await self.disconnect_mcp_server()
            self._initialized = False

    # === Utility Methods ===

    def get_event_stream_summary(self) -> Dict[str, Any]:
        """Get summary of the event stream."""
        return {
            "total_events": len(self.event_stream.events),
            "by_type": {
                event_type.value: len(self.event_stream.get_by_type(event_type))
                for event_type in EventType
            },
            "latest_plan": self.event_stream.get_latest_plan(),
            "recent_errors": len(self.event_stream.get_recent_errors()),
        }

    def get_plan_status(self) -> Optional[Dict[str, Any]]:
        """Get current plan status."""
        if not self.planner.current_plan:
            return None
        return self.planner.current_plan.get_progress()
