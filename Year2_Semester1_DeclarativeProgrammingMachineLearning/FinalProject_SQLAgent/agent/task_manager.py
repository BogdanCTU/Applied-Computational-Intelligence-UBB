"""Deterministic Task Manager for Agent Intelligence Layer.

Controls task lifecycle, step transitions, DAG dependency validation,
and ready-step determination without GUI or external LLM dependencies.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from agent.task_models import (
    AgentTask,
    InvalidStateTransitionError,
    StepStatus,
    TaskPlan,
    TaskStatus,
    TaskStep,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TaskError(Exception):
    """Base exception for task management errors."""


class TaskNotFoundError(TaskError):
    """Raised when a task_id is not found in the repository."""


class StepNotFoundError(TaskError):
    """Raised when a step_id is not found in the task."""


class TaskValidationError(TaskError):
    """Raised when task or plan structure fails validation."""


class DependencyError(TaskValidationError):
    """Base exception for step dependency failures."""


class MissingDependencyError(DependencyError):
    """Raised when a step references a dependency that does not exist in the plan."""


class SelfDependencyError(DependencyError):
    """Raised when a step depends directly or indirectly on itself."""


class CyclicDependencyError(DependencyError):
    """Raised when cyclic dependencies are detected in the task execution graph."""


# ---------------------------------------------------------------------------
# Repository Interface & In-Memory Implementation
# ---------------------------------------------------------------------------


class TaskRepository(Protocol):
    """Interface for persisting and retrieving tasks."""

    def save(self, task: AgentTask) -> AgentTask:
        ...

    def get(self, task_id: str) -> AgentTask | None:
        ...

    def list_all(self) -> list[AgentTask]:
        ...

    def delete(self, task_id: str) -> bool:
        ...


class InMemoryTaskRepository:
    """Thread-safe in-memory store for task instances during Phase 1."""

    def __init__(self) -> None:
        self._tasks: dict[str, AgentTask] = {}

    def save(self, task: AgentTask) -> AgentTask:
        # Clone via Pydantic model_copy to emulate persistence isolation
        cloned = task.model_copy(deep=True)
        self._tasks[cloned.task_id] = cloned
        return cloned

    def get(self, task_id: str) -> AgentTask | None:
        task = self._tasks.get(task_id)
        return task.model_copy(deep=True) if task else None

    def list_all(self) -> list[AgentTask]:
        return [t.model_copy(deep=True) for t in self._tasks.values()]

    def delete(self, task_id: str) -> bool:
        return self._tasks.pop(task_id, None) is not None

    def clear(self) -> None:
        self._tasks.clear()


# ---------------------------------------------------------------------------
# DAG Graph Validation Helpers
# ---------------------------------------------------------------------------


def validate_plan_dag(
    steps: list[TaskStep],
    permitted_tools: set[str] | frozenset[str] | None = None,
) -> list[str]:
    """Validate that steps form a valid Directed Acyclic Graph (DAG).

    Checks:
    1. Duplicate step_ids.
    2. Self-dependencies.
    3. Missing / unknown dependencies.
    4. Cyclic dependencies (using Kahn's algorithm).
    5. Permitted tools validation (if permitted_tools is provided).

    Returns:
        List of step_ids in a valid topological execution order.
    """
    if not steps:
        return []

    step_map: dict[str, TaskStep] = {}
    for s in steps:
        if s.step_id in step_map:
            raise TaskValidationError(f"Duplicate step ID in plan: '{s.step_id}'")
        step_map[s.step_id] = s

    # 1. Check self-dependencies and unknown dependencies
    for s in steps:
        all_deps = list(s.dependencies) + list(getattr(s, "optional_dependencies", []))
        for dep in all_deps:
            if dep == s.step_id:
                raise SelfDependencyError(
                    f"Step '{s.step_id}' ('{s.name}') cannot depend on itself."
                )
            if dep not in step_map:
                raise MissingDependencyError(
                    f"Step '{s.step_id}' ('{s.name}') references unknown dependency '{dep}'."
                )

        # 2. Check permitted tools if specified
        if permitted_tools is not None:
            for tool in s.required_tools:
                if tool not in permitted_tools:
                    raise TaskValidationError(
                        f"Step '{s.step_id}' ('{s.name}') requires unknown tool '{tool}'. "
                        f"Permitted tools: {sorted(permitted_tools)}"
                    )

    # 3. Detect cycles using Kahn's algorithm (topological sort)
    in_degree: dict[str, int] = {s.step_id: 0 for s in steps}
    graph: dict[str, list[str]] = {s.step_id: [] for s in steps}

    for s in steps:
        all_deps = list(s.dependencies) + list(getattr(s, "optional_dependencies", []))
        for dep in all_deps:
            graph[dep].append(s.step_id)
            in_degree[s.step_id] += 1

    queue: list[str] = [sid for sid, deg in in_degree.items() if deg == 0]
    topological_order: list[str] = []

    while queue:
        curr = queue.pop(0)
        topological_order.append(curr)
        for neighbor in graph[curr]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(topological_order) != len(steps):
        unresolved = [sid for sid, deg in in_degree.items() if deg > 0]
        raise CyclicDependencyError(
            f"Cyclic dependency detected in task plan. Involved steps: {unresolved}"
        )

    return topological_order


# ---------------------------------------------------------------------------
# Task Manager Implementation
# ---------------------------------------------------------------------------


class TaskManager:
    """Manages the full lifecycle, dependencies, and state transitions of AgentTasks."""

    def __init__(
        self,
        repository: TaskRepository | None = None,
        permitted_tools: set[str] | frozenset[str] | None = None,
    ) -> None:
        self.repository = repository or InMemoryTaskRepository()
        self.permitted_tools = permitted_tools

    # -----------------------------------------------------------------------
    # Task Lifecycle Operations
    # -----------------------------------------------------------------------

    def create_task(
        self,
        user_request: str,
        *,
        task_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentTask:
        """Instantiate and persist a new AgentTask in PENDING state."""
        cleaned_request = (user_request or "").strip()
        if not cleaned_request:
            raise TaskValidationError("User request cannot be empty.")

        task_kwargs: dict[str, Any] = {
            "user_request": cleaned_request,
            "status": TaskStatus.PENDING,
            "metadata": metadata or {},
        }
        if task_id:
            task_kwargs["task_id"] = task_id

        task = AgentTask(**task_kwargs)
        return self.repository.save(task)

    def get_task(self, task_id: str) -> AgentTask:
        """Fetch task by ID or raise TaskNotFoundError."""
        task = self.repository.get(task_id)
        if not task:
            raise TaskNotFoundError(f"Task with ID '{task_id}' not found.")
        return task

    def register_plan(self, task_id: str, plan: TaskPlan) -> AgentTask:
        """Register, validate, and attach an execution plan to the task.

        Validates the DAG dependencies and transitions step statuses that have
        no dependencies to READY.
        """
        task = self.get_task(task_id)
        if task.is_terminal:
            raise InvalidStateTransitionError(
                f"Cannot register plan for terminal task '{task_id}' (status={task.status.value})"
            )

        # Validate DAG and obtain topological order
        topo_order = validate_plan_dag(plan.steps, permitted_tools=self.permitted_tools)

        # Set initial step readiness: steps with no dependencies become READY
        step_map = {s.step_id: s for s in plan.steps}
        for s in plan.steps:
            all_deps = list(s.dependencies) + list(getattr(s, "optional_dependencies", []))
            if not all_deps and s.status == StepStatus.PENDING:
                s.status = StepStatus.READY

        # Sort steps by topological order for clear linear review
        ordered_steps = [step_map[sid] for sid in topo_order]

        task.plan = plan
        task.steps = ordered_steps
        if task.status == TaskStatus.PENDING:
            task.transition_to(TaskStatus.PLANNING)

        return self.repository.save(task)

    def start_task(self, task_id: str) -> AgentTask:
        """Transition task from PENDING/PLANNING to RUNNING state."""
        task = self.get_task(task_id)
        if not task.steps:
            raise TaskValidationError(f"Cannot start task '{task_id}' without registered steps.")

        task.transition_to(TaskStatus.RUNNING)
        self._refresh_step_readiness(task)
        return self.repository.save(task)

    def cancel_task(self, task_id: str, reason: str = "") -> AgentTask:
        """Cancel task and all its non-terminal steps."""
        task = self.get_task(task_id)
        if task.is_terminal:
            log.info("Task '%s' is already in terminal state %s", task_id, task.status.value)
            return task

        task.transition_to(TaskStatus.CANCELLED, error=reason or "Task cancelled by user.")
        for s in task.steps:
            if not s.is_terminal:
                try:
                    s.transition_to(StepStatus.CANCELLED)
                except InvalidStateTransitionError:
                    pass

        task.current_step = None
        return self.repository.save(task)

    # -----------------------------------------------------------------------
    # Step Execution Transitions
    # -----------------------------------------------------------------------

    def get_ready_steps(self, task_id: str) -> list[TaskStep]:
        """Return all steps in task that are ready for execution (all dependencies COMPLETED)."""
        task = self.get_task(task_id)
        self._refresh_step_readiness(task)
        self.repository.save(task)
        return [s for s in task.steps if s.status == StepStatus.READY]

    def start_step(self, task_id: str, step_id: str) -> TaskStep:
        """Mark a step as RUNNING and update task.current_step.

        Ensures all dependencies of this step are in COMPLETED status.
        """
        task = self.get_task(task_id)
        step = task.get_step(step_id)
        if not step:
            raise StepNotFoundError(f"Step '{step_id}' not found in task '{task_id}'.")

        # Verify all mandatory dependencies are COMPLETED
        step_dict = {s.step_id: s for s in task.steps}
        for dep_id in step.dependencies:
            dep_step = step_dict.get(dep_id)
            if not dep_step or dep_step.status != StepStatus.COMPLETED:
                raise DependencyError(
                    f"Cannot start step '{step_id}': mandatory dependency '{dep_id}' is not COMPLETED "
                    f"(current status: {dep_step.status.value if dep_step else 'missing'})."
                )

        # Verify all optional dependencies are COMPLETED or SKIPPED
        for opt_id in getattr(step, "optional_dependencies", []):
            dep_step = step_dict.get(opt_id)
            if not dep_step or dep_step.status not in {StepStatus.COMPLETED, StepStatus.SKIPPED}:
                raise DependencyError(
                    f"Cannot start step '{step_id}': optional dependency '{opt_id}' is not finished "
                    f"(current status: {dep_step.status.value if dep_step else 'missing'})."
                )

        if task.status != TaskStatus.RUNNING:
            task.transition_to(TaskStatus.RUNNING)

        # If step is PENDING, transition through READY first if needed
        if step.status == StepStatus.PENDING:
            step.transition_to(StepStatus.READY)

        step.transition_to(StepStatus.RUNNING)
        task.current_step = step_id
        self.repository.save(task)
        return step

    def complete_step(
        self,
        task_id: str,
        step_id: str,
        *,
        output_reference: str | None = None,
    ) -> TaskStep:
        """Mark step COMPLETED, record output reference, and update downstream readiness."""
        task = self.get_task(task_id)
        step = task.get_step(step_id)
        if not step:
            raise StepNotFoundError(f"Step '{step_id}' not found in task '{task_id}'.")

        step.transition_to(StepStatus.COMPLETED, output_reference=output_reference)
        if task.current_step == step_id:
            task.current_step = None

        self._refresh_step_readiness(task)

        # Check if entire task is finished
        if all(s.is_terminal for s in task.steps):
            if any(s.status == StepStatus.FAILED for s in task.steps):
                task.transition_to(TaskStatus.FAILED, error="One or more steps failed.")
            elif all(s.status in {StepStatus.COMPLETED, StepStatus.SKIPPED} for s in task.steps):
                task.transition_to(TaskStatus.COMPLETED)

        self.repository.save(task)
        return step

    def fail_step(
        self,
        task_id: str,
        step_id: str,
        error: str,
        *,
        fail_task: bool = True,
    ) -> TaskStep:
        """Mark step as FAILED with an error explanation, optionally failing the task."""
        task = self.get_task(task_id)
        step = task.get_step(step_id)
        if not step:
            raise StepNotFoundError(f"Step '{step_id}' not found in task '{task_id}'.")

        step.transition_to(StepStatus.FAILED, error=error)
        if task.current_step == step_id:
            task.current_step = None

        if fail_task and not task.is_terminal:
            task.transition_to(TaskStatus.FAILED, error=f"Step '{step_id}' failed: {error}")

        self.repository.save(task)
        return step

    def skip_step(self, task_id: str, step_id: str, reason: str = "") -> TaskStep:
        """Mark step as SKIPPED and update downstream step readiness."""
        task = self.get_task(task_id)
        step = task.get_step(step_id)
        if not step:
            raise StepNotFoundError(f"Step '{step_id}' not found in task '{task_id}'.")

        step.transition_to(StepStatus.SKIPPED, error=reason or "Skipped")
        if task.current_step == step_id:
            task.current_step = None

        self._refresh_step_readiness(task)
        self.repository.save(task)
        return step

    def request_step_approval(self, task_id: str, step_id: str) -> TaskStep:
        """Mark step and task as WAITING_FOR_APPROVAL."""
        task = self.get_task(task_id)
        step = task.get_step(step_id)
        if not step:
            raise StepNotFoundError(f"Step '{step_id}' not found in task '{task_id}'.")

        if task.status != TaskStatus.RUNNING:
            task.transition_to(TaskStatus.RUNNING)

        step.transition_to(StepStatus.WAITING_FOR_APPROVAL)
        task.transition_to(TaskStatus.WAITING_FOR_APPROVAL)
        task.current_step = step_id
        self.repository.save(task)
        return step

    def approve_step(self, task_id: str, step_id: str) -> TaskStep:
        """Resume step and task after user approval."""
        task = self.get_task(task_id)
        step = task.get_step(step_id)
        if not step:
            raise StepNotFoundError(f"Step '{step_id}' not found in task '{task_id}'.")

        step.transition_to(StepStatus.RUNNING)
        task.transition_to(TaskStatus.RUNNING)
        self.repository.save(task)
        return step

    # -----------------------------------------------------------------------
    # Progress & Observability
    # -----------------------------------------------------------------------

    def get_progress_summary(self, task_id: str) -> dict[str, Any]:
        """Compute structured execution progress metrics for the task."""
        task = self.get_task(task_id)
        total = len(task.steps)
        counts = {
            status.value: sum(1 for s in task.steps if s.status == status)
            for status in StepStatus
        }

        completed = counts.get(StepStatus.COMPLETED.value, 0)
        skipped = counts.get(StepStatus.SKIPPED.value, 0)
        percent = round(((completed + skipped) / total) * 100, 1) if total > 0 else 0.0

        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "current_step": task.current_step,
            "total_steps": total,
            "completed_steps": completed,
            "ready_steps": counts.get(StepStatus.READY.value, 0),
            "pending_steps": counts.get(StepStatus.PENDING.value, 0),
            "running_steps": counts.get(StepStatus.RUNNING.value, 0),
            "waiting_approval_steps": counts.get(StepStatus.WAITING_FOR_APPROVAL.value, 0),
            "failed_steps": counts.get(StepStatus.FAILED.value, 0),
            "skipped_steps": skipped,
            "cancelled_steps": counts.get(StepStatus.CANCELLED.value, 0),
            "percent_complete": percent,
            "error": task.error,
        }

    # -----------------------------------------------------------------------
    # Internal Helpers
    # -----------------------------------------------------------------------

    def _refresh_step_readiness(self, task: AgentTask) -> None:
        """Promote PENDING steps to READY when all their dependencies are satisfied."""
        step_dict = {s.step_id: s for s in task.steps}
        for step in task.steps:
            if step.status == StepStatus.PENDING:
                all_deps_done = True
                # Mandatory dependencies must strictly be COMPLETED
                for dep_id in step.dependencies:
                    dep = step_dict.get(dep_id)
                    if not dep or dep.status != StepStatus.COMPLETED:
                        all_deps_done = False
                        break

                # Optional dependencies may be COMPLETED or SKIPPED
                if all_deps_done:
                    for opt_id in getattr(step, "optional_dependencies", []):
                        dep = step_dict.get(opt_id)
                        if not dep or dep.status not in {StepStatus.COMPLETED, StepStatus.SKIPPED}:
                            all_deps_done = False
                            break

                if all_deps_done:
                    step.status = StepStatus.READY
