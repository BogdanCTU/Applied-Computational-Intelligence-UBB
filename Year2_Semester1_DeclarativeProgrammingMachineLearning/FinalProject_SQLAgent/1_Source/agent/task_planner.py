"""Task Planner converting user requests into structured, validated TaskPlans.

Supports LLM-guided planning with strict validation against permitted MCP tools
and deterministic fallback generation without external service dependencies.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Sequence

from agent.ollama_client import OllamaChatResponse, OllamaClient, OllamaClientError
from agent.task_manager import (
    CyclicDependencyError,
    DependencyError,
    MissingDependencyError,
    SelfDependencyError,
    TaskValidationError,
    validate_plan_dag,
)
from agent.task_models import StepStatus, TaskPlan, TaskStep
from agent.tool_handler import PERMITTED_TOOLS

log = logging.getLogger(__name__)

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{[\s\S]*?\}|\[[\s\S]*?\])\s*```", re.DOTALL)
_PLAN_TAG_RE = re.compile(r"<plan>\s*(\{[\s\S]*?\})\s*</plan>", re.IGNORECASE)
_CSV_INTENT_RE = re.compile(r"\b(?:csv|to\s+csv|as\s+csv|in\s+csv|\.csv)\b", re.IGNORECASE)
_SCHEMA_ONLY_RE = re.compile(
    r"\b(?:what\s+tables|show\s+tables|list\s+tables|describe\s+schema|inspect\s+schema|schema\s+info)\b",
    re.IGNORECASE,
)
_REPORT_INTENT_RE = re.compile(
    r"\b(?:report|pdf|csv|export|document|charts?|dashboard|graphs?|overview|summary\s+file)\b",
    re.IGNORECASE,
)


class TaskPlanner:
    """Creates, parses, and validates execution plans for AgentTasks."""

    def __init__(
        self,
        ollama_client: OllamaClient | None = None,
        permitted_tools: set[str] | frozenset[str] | None = None,
        num_ctx: int | None = None,
    ) -> None:
        self.ollama_client = ollama_client
        self.permitted_tools: frozenset[str] = (
            frozenset(permitted_tools) if permitted_tools is not None else PERMITTED_TOOLS
        )
        self.num_ctx = num_ctx or (
            getattr(ollama_client.settings, "num_ctx", None)
            if ollama_client and hasattr(ollama_client, "settings")
            else None
        )

    # -----------------------------------------------------------------------
    # Planning Entry Points
    # -----------------------------------------------------------------------

    async def plan_task(self, task_id: str, user_request: str) -> TaskPlan:
        """Generate a validated TaskPlan for a user request.

        Attempts LLM planning if OllamaClient is available; falls back to
        deterministic generic pipeline if LLM planning fails or is unavailable.
        """
        if self.ollama_client is not None:
            try:
                plan = await self._plan_with_llm(task_id, user_request)
                if plan is not None:
                    return plan
            except Exception as exc:  # noqa: BLE001
                log.warning("LLM planning encountered error (%s); using deterministic fallback", exc)

        return self.create_fallback_plan(task_id, user_request)

    # -----------------------------------------------------------------------
    # Fallback Deterministic Planner
    # -----------------------------------------------------------------------

    def create_fallback_plan(self, task_id: str, user_request: str) -> TaskPlan:
        """Create a generic, structured execution plan without an LLM.

        CRITICAL: Never invents SQL queries, tables, relationships, or metrics.
        Only establishes generic, validated execution stages.
        """
        is_schema_only = bool(_SCHEMA_ONLY_RE.search(user_request)) and not bool(
            _REPORT_INTENT_RE.search(user_request)
        )
        is_csv = bool(_CSV_INTENT_RE.search(user_request))
        report_tool = "generate_csv_report" if is_csv else "generate_pdf_report"
        format_label = "CSV" if is_csv else "PDF"

        steps: list[TaskStep] = []

        if is_schema_only:
            step1 = TaskStep(
                step_id="step_schema_discovery",
                name="Database Schema Inspection",
                description="Discover database tables, columns, and foreign keys.",
                required_skill="sql_generation",
                required_tools=["inspect_database_schema"],
                dependencies=[],
                status=StepStatus.PENDING,
            )
            step2 = TaskStep(
                step_id="step_table_sampling",
                name="Table Structure Verification",
                description="Sample representative records to confirm table contents.",
                required_skill="ecommerce_analysis",
                required_tools=["get_table_sample"],
                dependencies=["step_schema_discovery"],
                status=StepStatus.PENDING,
            )
            steps = [step1, step2]
            rationale = "Deterministic schema inspection pipeline without report generation."
        else:
            step1 = TaskStep(
                step_id="step_schema_discovery",
                name="Database Schema Discovery",
                description="Inspect relevant tables and schema metadata before formulating queries.",
                required_skill="sql_generation",
                required_tools=["inspect_database_schema", "get_table_sample"],
                dependencies=[],
                status=StepStatus.PENDING,
            )
            step2 = TaskStep(
                step_id="step_sql_formulation",
                name="SQL Query Formulation & Validation",
                description="Prepare and validate read-only SQL query avoiding join fan-out.",
                required_skill="sql_generation",
                required_tools=["prepare_sql_query"],
                dependencies=["step_schema_discovery"],
                status=StepStatus.PENDING,
            )
            step3 = TaskStep(
                step_id="step_sql_execution",
                name="Read-Only SQL Execution",
                description="Execute approved query and capture canonical result dataset.",
                required_skill="data_validation",
                required_tools=["execute_readonly_sql"],
                dependencies=["step_sql_formulation"],
                status=StepStatus.PENDING,
            )
            step4 = TaskStep(
                step_id="step_report_generation",
                name=f"Report Generation ({format_label})",
                description=f"Synthesize deterministic KPIs, chart specifications, and generate {format_label} report.",
                required_skill="report_design",
                required_tools=[report_tool],
                dependencies=["step_sql_execution"],
                status=StepStatus.PENDING,
            )
            steps = [step1, step2, step3, step4]
            rationale = (
                f"Deterministic 4-stage analytical workflow for {format_label} report generation."
            )

        # Validate our own fallback plan to ensure consistency
        validate_plan_dag(steps, permitted_tools=self.permitted_tools)

        return TaskPlan(
            task_id=task_id,
            steps=steps,
            rationale=rationale,
        )

    # -----------------------------------------------------------------------
    # Plan Parsing and Validation
    # -----------------------------------------------------------------------

    def parse_and_validate_plan(
        self,
        raw_input: str | dict[str, Any],
        task_id: str,
    ) -> TaskPlan:
        """Parse structured plan payload from JSON/dict and rigorously validate.

        Raises:
            TaskValidationError: If JSON is malformed, missing steps, or contains unknown tools.
            DependencyError: If dependencies are cyclic, missing, or self-referential.
        """
        data: dict[str, Any]
        if isinstance(raw_input, dict):
            data = raw_input
        elif isinstance(raw_input, str):
            data = self._extract_json_dict(raw_input)
        else:
            raise TaskValidationError(f"Expected dict or string input for plan, got {type(raw_input).__name__}")

        raw_steps = data.get("steps")
        if not isinstance(raw_steps, list) or not raw_steps:
            raise TaskValidationError("Plan must contain a non-empty 'steps' list.")

        steps: list[TaskStep] = []
        for idx, item in enumerate(raw_steps):
            if not isinstance(item, dict):
                raise TaskValidationError(f"Step at index {idx} must be a dictionary.")

            name = item.get("name")
            if not name or not str(name).strip():
                raise TaskValidationError(f"Step at index {idx} is missing a valid 'name'.")

            step_id = item.get("step_id") or f"step_{idx + 1}"
            dependencies = item.get("dependencies") or []
            if not isinstance(dependencies, list):
                raise TaskValidationError(f"Step '{step_id}' dependencies must be a list.")

            required_tools = item.get("required_tools") or []
            if not isinstance(required_tools, list):
                raise TaskValidationError(f"Step '{step_id}' required_tools must be a list.")

            step = TaskStep(
                step_id=str(step_id).strip(),
                name=str(name).strip(),
                description=str(item.get("description", "")).strip(),
                required_skill=item.get("required_skill"),
                required_tools=[str(t).strip() for t in required_tools],
                dependencies=[str(d).strip() for d in dependencies],
                status=StepStatus.PENDING,
                metadata=item.get("metadata", {}),
            )
            steps.append(step)

        # Validate DAG structure and permitted tools
        validate_plan_dag(steps, permitted_tools=self.permitted_tools)

        return TaskPlan(
            task_id=task_id,
            steps=steps,
            rationale=str(data.get("rationale", "")).strip(),
        )

    # -----------------------------------------------------------------------
    # LLM Interaction
    # -----------------------------------------------------------------------

    async def _plan_with_llm(self, task_id: str, user_request: str) -> TaskPlan | None:
        """Prompt Ollama to formulate a structured plan."""
        if self.ollama_client is None:
            return None

        prompt = (
            "You are an expert database task planning agent. "
            "Analyze the following user request and generate a structured JSON execution plan.\n\n"
            f"User Request: {user_request}\n\n"
            f"Permitted Tools: {sorted(self.permitted_tools)}\n\n"
            "Return ONLY valid JSON matching this schema:\n"
            "{\n"
            '  "rationale": "Brief strategy overview",\n'
            '  "steps": [\n'
            "    {\n"
            '      "step_id": "step_1",\n'
            '      "name": "Step Title",\n'
            '      "description": "Step details",\n'
            '      "required_tools": ["tool_name"],\n'
            '      "required_skill": "skill_category/skill_name",\n'
            '      "dependencies": []\n'
            "    }\n"
            "  ]\n"
            "}\n"
        )

        messages = [
            {"role": "system", "content": "You are a structured planning engine. Output valid JSON only."},
            {"role": "user", "content": prompt},
        ]

        response: OllamaChatResponse = await self.ollama_client.chat(
            messages=messages,
            tools=None,
            tool_mode="json",
            num_ctx=self.num_ctx,
        )

        content = response.content or ""
        if not content.strip():
            return None

        try:
            return self.parse_and_validate_plan(content, task_id=task_id)
        except (TaskValidationError, DependencyError) as exc:
            log.warning("LLM proposed plan failed validation (%s)", exc)
            return None

    # -----------------------------------------------------------------------
    # JSON Extraction
    # -----------------------------------------------------------------------

    @staticmethod
    def _extract_json_dict(text: str) -> dict[str, Any]:
        """Extract first valid JSON dictionary from raw text."""
        cleaned = text.strip()

        # 1. Direct parse attempt
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # 2. Check XML tags <plan>...</plan>
        tag_match = _PLAN_TAG_RE.search(cleaned)
        if tag_match:
            try:
                parsed = json.loads(tag_match.group(1))
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

        # 3. Check markdown fenced blocks ```json ... ```
        block_matches = _JSON_BLOCK_RE.findall(cleaned)
        for block in block_matches:
            try:
                parsed = json.loads(block)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue

        # 4. Search between first '{' and last '}'
        first_brace = cleaned.find("{")
        last_brace = cleaned.rfind("}")
        if first_brace != -1 and last_brace > first_brace:
            candidate = cleaned[first_brace : last_brace + 1]
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

        raise TaskValidationError(f"Could not parse valid JSON plan from input: '{cleaned[:120]}...'")

