"""
Planner Module for Manus-aligned agent.

This module implements the Planner as an independent system component, NOT as a
tool that the agent can invoke. The Planner operates as an external orchestrator
that:
- Analyzes user requests and generates structured task plans
- Injects Plan events into the agent's context
- Monitors execution and updates plans dynamically
- Guides the agent through a series of numbered steps

The key distinction from OpenManus's tool-based approach is that the Planner
is a system-level module that guides the agent's behavior, rather than a tool
the agent must choose to use.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from pydantic import BaseModel, Field
import uuid
import logging

# Lazy import to avoid config loading at module import time
if TYPE_CHECKING:
    from app.llm import LLM

logger = logging.getLogger(__name__)


class StepStatus(str, Enum):
    """Status of a plan step."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class PlanStep(BaseModel):
    """A single step in a task plan."""

    index: int
    description: str
    status: StepStatus = StepStatus.PENDING
    notes: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    dependencies: List[int] = Field(default_factory=list)

    def start(self) -> None:
        """Mark step as in progress."""
        self.status = StepStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()

    def complete(self, notes: str = "") -> None:
        """Mark step as completed."""
        self.status = StepStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if notes:
            self.notes = notes

    def block(self, reason: str = "") -> None:
        """Mark step as blocked."""
        self.status = StepStatus.BLOCKED
        self.notes = reason

    def to_pseudocode(self) -> str:
        """Convert step to numbered pseudocode format."""
        status_icons = {
            StepStatus.PENDING: "[ ]",
            StepStatus.IN_PROGRESS: "[→]",
            StepStatus.COMPLETED: "[✓]",
            StepStatus.BLOCKED: "[!]",
            StepStatus.SKIPPED: "[-]",
        }
        return f"{self.index + 1}. {status_icons[self.status]} {self.description}"


class Plan(BaseModel):
    """A structured task plan.

    Plans guide the agent's execution through a series of numbered steps.
    The plan is dynamic and can be updated based on progress or changes
    in the overall objective.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str
    objective: str
    steps: List[PlanStep] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    current_step_index: int = 0
    is_complete: bool = False

    class Config:
        arbitrary_types_allowed = True

    def add_step(self, description: str, dependencies: List[int] = None) -> PlanStep:
        """Add a new step to the plan."""
        step = PlanStep(
            index=len(self.steps),
            description=description,
            dependencies=dependencies or [],
        )
        self.steps.append(step)
        self.updated_at = datetime.utcnow()
        return step

    def get_current_step(self) -> Optional[PlanStep]:
        """Get the current active step."""
        if self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def advance(self) -> Optional[PlanStep]:
        """Advance to the next step."""
        if self.current_step_index < len(self.steps):
            current = self.steps[self.current_step_index]
            if current.status != StepStatus.COMPLETED:
                current.complete()

        self.current_step_index += 1
        self.updated_at = datetime.utcnow()

        if self.current_step_index >= len(self.steps):
            self.is_complete = True
            return None

        next_step = self.steps[self.current_step_index]
        next_step.start()
        return next_step

    def get_progress(self) -> Dict[str, Any]:
        """Get plan progress summary."""
        completed = sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)
        total = len(self.steps)
        return {
            "completed": completed,
            "total": total,
            "percentage": (completed / total * 100) if total > 0 else 0,
            "current_step": self.current_step_index,
            "is_complete": self.is_complete,
        }

    def to_pseudocode(self) -> str:
        """Convert plan to numbered pseudocode format."""
        lines = [f"PLAN: {self.title}", "=" * 40]
        lines.append(f"Objective: {self.objective}")
        lines.append("")
        for step in self.steps:
            marker = "→ " if step.index == self.current_step_index else "  "
            lines.append(f"{marker}{step.to_pseudocode()}")
            if step.notes:
                lines.append(f"     Notes: {step.notes}")
        lines.append("")
        progress = self.get_progress()
        lines.append(f"Progress: {progress['completed']}/{progress['total']} ({progress['percentage']:.1f}%)")
        return "\n".join(lines)


class Planner(BaseModel):
    """Planner module that operates as an independent system component.

    The Planner is responsible for:
    1. Analyzing user requests to generate structured plans
    2. Injecting Plan events into the agent's context
    3. Monitoring execution and updating plans dynamically
    4. Deciding when to re-plan based on observed progress

    Unlike the tool-based PlanningTool in OpenManus, this Planner acts as
    an external orchestrator that guides the agent's behavior without the
    agent needing to explicitly invoke it.
    """

    llm: Optional[Any] = None  # LLM instance, lazily loaded
    current_plan: Optional[Plan] = None
    plan_history: List[Plan] = Field(default_factory=list)

    # Planner configuration
    auto_plan: bool = True  # Automatically create plans for complex tasks
    complexity_threshold: int = 3  # Minimum steps to trigger automatic planning
    replan_on_error: bool = True  # Re-plan when encountering errors

    class Config:
        arbitrary_types_allowed = True

    def _get_llm(self):
        """Lazily load and return the LLM instance."""
        if self.llm is None:
            from app.llm import LLM
            self.llm = LLM()
        return self.llm

    async def analyze_request(self, request: str) -> Dict[str, Any]:
        """Analyze a user request to determine if planning is needed.

        Returns analysis including:
        - complexity: estimated task complexity
        - needs_planning: whether a structured plan is recommended
        - suggested_steps: initial step suggestions
        """
        analysis_prompt = f"""Analyze this user request and determine if it requires structured planning.

User Request: {request}

Provide your analysis in the following format:
1. Complexity (1-10): How complex is this task?
2. Needs Planning: Yes/No - Does this task benefit from a structured plan?
3. Estimated Steps: How many distinct steps might be needed?
4. Key Subtasks: List the main subtasks involved.

Focus on identifying:
- Tasks that require multiple distinct actions
- Tasks with dependencies between steps
- Tasks that benefit from systematic execution
"""
        response = await self._get_llm().ask(
            messages=[{"role": "user", "content": analysis_prompt}],
            system_msgs=[{
                "role": "system",
                "content": "You are a task analysis expert. Provide concise, actionable analysis."
            }],
        )

        # Parse response (simplified - in production would use structured output)
        return {
            "request": request,
            "response": response.content if response else "",
            "needs_planning": self.auto_plan and len(request) > 50,
        }

    async def create_plan(self, request: str, context: str = "") -> Plan:
        """Create a structured plan for a user request.

        This method is called by the system orchestrator (not by the agent)
        to generate a plan that will guide the agent's execution.
        """
        planning_prompt = f"""Create a detailed execution plan for this task.

User Request: {request}
{f'Context: {context}' if context else ''}

Generate a step-by-step plan in pseudocode format:
1. Each step should be a clear, actionable instruction
2. Steps should be atomic (one main action per step)
3. Include any necessary validation or verification steps
4. Consider error handling and fallback options

Format your response as:
TITLE: [Brief plan title]
OBJECTIVE: [The main goal]
STEPS:
1. [First step]
2. [Second step]
...

Keep steps focused and achievable. Do not include meta-steps like "create a plan".
"""
        response = await self._get_llm().ask(
            messages=[{"role": "user", "content": planning_prompt}],
            system_msgs=[{
                "role": "system",
                "content": "You are an expert task planner. Create clear, executable plans."
            }],
        )

        # Parse response into Plan (simplified parsing)
        plan = self._parse_plan_response(request, response.content if response else "")

        self.current_plan = plan
        self.plan_history.append(plan)
        logger.info(f"Planner created plan: {plan.title} with {len(plan.steps)} steps")

        return plan

    def _parse_plan_response(self, request: str, response: str) -> Plan:
        """Parse LLM response into a Plan object."""
        lines = response.strip().split("\n")
        title = request[:50] + "..." if len(request) > 50 else request
        objective = request
        steps = []

        for line in lines:
            line = line.strip()
            if line.startswith("TITLE:"):
                title = line[6:].strip()
            elif line.startswith("OBJECTIVE:"):
                objective = line[10:].strip()
            elif line and line[0].isdigit() and "." in line:
                # Parse numbered step
                step_text = line.split(".", 1)[1].strip() if "." in line else line
                # Remove status markers if present
                for marker in ["[ ]", "[→]", "[✓]", "[!]", "[-]"]:
                    step_text = step_text.replace(marker, "").strip()
                if step_text:
                    steps.append(step_text)

        # If no steps were parsed, create default steps
        if not steps:
            steps = [
                "Analyze the request requirements",
                "Execute the main task",
                "Verify the results",
            ]

        plan = Plan(title=title, objective=objective)
        for step_desc in steps:
            plan.add_step(step_desc)

        # Start the first step
        if plan.steps:
            plan.steps[0].start()

        return plan

    def get_plan_event(self) -> Optional[Dict[str, Any]]:
        """Get the current plan as a Plan event for context injection.

        This method is called by the event stream to inject the plan
        into the agent's context as a system-level event.
        """
        if not self.current_plan:
            return None

        return {
            "type": "plan",
            "plan_id": self.current_plan.id,
            "title": self.current_plan.title,
            "steps": [s.description for s in self.current_plan.steps],
            "step_statuses": [s.status.value for s in self.current_plan.steps],
            "current_step_index": self.current_plan.current_step_index,
            "is_complete": self.current_plan.is_complete,
            "pseudocode": self.current_plan.to_pseudocode(),
        }

    def update_step_status(
        self,
        step_index: int,
        status: StepStatus,
        notes: str = ""
    ) -> bool:
        """Update the status of a specific step.

        Called by the system to track progress based on agent actions.
        """
        if not self.current_plan:
            return False

        if 0 <= step_index < len(self.current_plan.steps):
            step = self.current_plan.steps[step_index]
            step.status = status
            if notes:
                step.notes = notes
            if status == StepStatus.IN_PROGRESS:
                step.started_at = datetime.utcnow()
            elif status == StepStatus.COMPLETED:
                step.completed_at = datetime.utcnow()

            self.current_plan.updated_at = datetime.utcnow()
            logger.info(f"Planner updated step {step_index}: {status.value}")
            return True
        return False

    def advance_plan(self) -> Optional[PlanStep]:
        """Advance the plan to the next step.

        Called by the system when the current step is determined to be complete.
        """
        if not self.current_plan:
            return None

        return self.current_plan.advance()

    async def should_replan(self, observation: str) -> bool:
        """Determine if re-planning is needed based on an observation.

        This is called when the agent encounters unexpected results or errors.
        """
        if not self.replan_on_error:
            return False

        if not self.current_plan:
            return False

        # Check for indicators that replanning might be needed
        error_indicators = ["error", "failed", "unable", "cannot", "blocked"]
        return any(indicator in observation.lower() for indicator in error_indicators)

    async def replan(self, reason: str, context: str = "") -> Plan:
        """Create a new plan based on current progress and new information.

        Called when the current plan needs adjustment due to errors,
        new information, or changed objectives.
        """
        current_progress = ""
        if self.current_plan:
            current_progress = f"Previous plan progress:\n{self.current_plan.to_pseudocode()}"
            # Archive current plan
            self.current_plan.is_complete = True

        replan_prompt = f"""A task requires replanning.

Reason for replanning: {reason}

{current_progress}
{f'Additional context: {context}' if context else ''}

Create a new plan that:
1. Accounts for work already completed
2. Addresses the reason for replanning
3. Provides a clear path forward

Format as before with TITLE, OBJECTIVE, and numbered STEPS.
"""
        response = await self._get_llm().ask(
            messages=[{"role": "user", "content": replan_prompt}],
            system_msgs=[{
                "role": "system",
                "content": "You are an expert task planner. Create adaptive recovery plans."
            }],
        )

        new_plan = self._parse_plan_response(reason, response.content if response else "")
        self.current_plan = new_plan
        self.plan_history.append(new_plan)

        logger.info(f"Planner created revised plan: {new_plan.title}")
        return new_plan

    def is_plan_complete(self) -> bool:
        """Check if the current plan is complete."""
        if not self.current_plan:
            return True
        return self.current_plan.is_complete

    def get_remaining_steps(self) -> List[PlanStep]:
        """Get remaining incomplete steps."""
        if not self.current_plan:
            return []
        return [
            s for s in self.current_plan.steps
            if s.status not in (StepStatus.COMPLETED, StepStatus.SKIPPED)
        ]
