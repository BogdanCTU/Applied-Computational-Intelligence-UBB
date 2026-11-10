"""Unit tests for TaskPlanner: fallback generation, JSON parsing, tool validation, and LLM fallback handling."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
import pytest

from agent.ollama_client import (
    OllamaChatResponse,
    OllamaClient,
    OllamaConnectionError,
    OllamaEmptyResponseError,
)
from agent.task_manager import (
    CyclicDependencyError,
    MissingDependencyError,
    SelfDependencyError,
    TaskValidationError,
)
from agent.task_models import StepStatus
from agent.task_planner import TaskPlanner
from agent.tool_handler import PERMITTED_TOOLS


def test_fallback_plan_pdf_workflow() -> None:
    planner = TaskPlanner()
    plan = planner.create_fallback_plan("task_100", "Please generate a monthly revenue report")

    assert plan.task_id == "task_100"
    assert len(plan.steps) == 4

    step_ids = [s.step_id for s in plan.steps]
    assert step_ids == [
        "step_schema_discovery",
        "step_sql_formulation",
        "step_sql_execution",
        "step_report_generation",
    ]

    # Verify dependencies form a valid pipeline
    assert plan.steps[0].dependencies == []
    assert plan.steps[1].dependencies == ["step_schema_discovery"]
    assert plan.steps[2].dependencies == ["step_sql_formulation"]
    assert plan.steps[3].dependencies == ["step_sql_execution"]

    # Verify report tool is PDF
    assert "generate_pdf_report" in plan.steps[3].required_tools
    assert "generate_csv_report" not in plan.steps[3].required_tools

    # All tools must be in PERMITTED_TOOLS
    for s in plan.steps:
        for t in s.required_tools:
            assert t in PERMITTED_TOOLS


def test_fallback_plan_csv_workflow() -> None:
    planner = TaskPlanner()
    plan = planner.create_fallback_plan("task_101", "Export active customers to CSV file")

    assert plan.task_id == "task_101"
    assert len(plan.steps) == 4
    assert "generate_csv_report" in plan.steps[3].required_tools
    assert "generate_pdf_report" not in plan.steps[3].required_tools


def test_fallback_plan_schema_only() -> None:
    planner = TaskPlanner()
    plan = planner.create_fallback_plan("task_102", "What tables are in the database?")

    assert plan.task_id == "task_102"
    assert len(plan.steps) == 2
    assert plan.steps[0].required_tools == ["inspect_database_schema"]
    assert plan.steps[1].required_tools == ["get_table_sample"]
    assert "report" not in [t for s in plan.steps for t in s.required_tools]


def test_parse_valid_json_plan_from_dict() -> None:
    planner = TaskPlanner()
    raw = {
        "rationale": "Direct SQL pipeline",
        "steps": [
            {
                "step_id": "step_inspect",
                "name": "Inspect schema",
                "required_tools": ["inspect_database_schema"],
                "dependencies": [],
            },
            {
                "step_id": "step_exec",
                "name": "Run SQL",
                "required_tools": ["execute_readonly_sql"],
                "dependencies": ["step_inspect"],
            },
        ],
    }
    plan = planner.parse_and_validate_plan(raw, task_id="task_200")
    assert plan.task_id == "task_200"
    assert len(plan.steps) == 2
    assert plan.steps[0].step_id == "step_inspect"
    assert plan.steps[1].dependencies == ["step_inspect"]


def test_parse_valid_json_plan_from_markdown_block() -> None:
    planner = TaskPlanner()
    raw_markdown = """
Here is the plan for your request:
```json
{
  "rationale": "Markdown formatted plan",
  "steps": [
    {
      "step_id": "s1",
      "name": "Prepare query",
      "required_tools": ["prepare_sql_query"],
      "dependencies": []
    }
  ]
}
```
Hope this helps!
"""
    plan = planner.parse_and_validate_plan(raw_markdown, task_id="task_201")
    assert len(plan.steps) == 1
    assert plan.steps[0].step_id == "s1"
    assert plan.rationale == "Markdown formatted plan"


def test_parse_valid_json_plan_from_xml_tags() -> None:
    planner = TaskPlanner()
    raw_xml = """
<plan>
{
  "rationale": "XML tagged plan",
  "steps": [
    {
      "step_id": "s1",
      "name": "Sample table",
      "required_tools": ["get_table_sample"],
      "dependencies": []
    }
  ]
}
</plan>
"""
    plan = planner.parse_and_validate_plan(raw_xml, task_id="task_202")
    assert len(plan.steps) == 1
    assert plan.steps[0].step_id == "s1"


def test_reject_plan_missing_steps() -> None:
    planner = TaskPlanner()
    with pytest.raises(TaskValidationError) as exc:
        planner.parse_and_validate_plan({"rationale": "No steps"}, task_id="task_err")
    assert "must contain a non-empty 'steps' list" in str(exc.value)

    with pytest.raises(TaskValidationError):
        planner.parse_and_validate_plan({"steps": []}, task_id="task_err")


def test_reject_plan_step_missing_name() -> None:
    planner = TaskPlanner()
    raw = {
        "steps": [
            {"step_id": "s1", "dependencies": []}
        ]
    }
    with pytest.raises(TaskValidationError) as exc:
        planner.parse_and_validate_plan(raw, task_id="task_err")
    assert "missing a valid 'name'" in str(exc.value)


def test_reject_plan_unknown_tool() -> None:
    planner = TaskPlanner()
    raw = {
        "steps": [
            {
                "step_id": "s1",
                "name": "Dangerous operation",
                "required_tools": ["drop_table_unauthorized"],
                "dependencies": [],
            }
        ]
    }
    with pytest.raises(TaskValidationError) as exc:
        planner.parse_and_validate_plan(raw, task_id="task_err")
    assert "requires unknown tool 'drop_table_unauthorized'" in str(exc.value)


def test_reject_plan_cyclic_dependency() -> None:
    planner = TaskPlanner()
    raw = {
        "steps": [
            {"step_id": "s1", "name": "A", "dependencies": ["s2"]},
            {"step_id": "s2", "name": "B", "dependencies": ["s1"]},
        ]
    }
    with pytest.raises(CyclicDependencyError):
        planner.parse_and_validate_plan(raw, task_id="task_err")


def test_reject_plan_missing_dependency() -> None:
    planner = TaskPlanner()
    raw = {
        "steps": [
            {"step_id": "s1", "name": "A", "dependencies": ["missing_upstream"]},
        ]
    }
    with pytest.raises(MissingDependencyError):
        planner.parse_and_validate_plan(raw, task_id="task_err")


def test_reject_plan_self_dependency() -> None:
    planner = TaskPlanner()
    raw = {
        "steps": [
            {"step_id": "s1", "name": "Self reliant", "dependencies": ["s1"]},
        ]
    }
    with pytest.raises(SelfDependencyError):
        planner.parse_and_validate_plan(raw, task_id="task_err")


def test_reject_malformed_json_string() -> None:
    planner = TaskPlanner()
    with pytest.raises(TaskValidationError) as exc:
        planner.parse_and_validate_plan("{not valid json at all", task_id="task_err")
    assert "Could not parse valid JSON plan" in str(exc.value)


def test_reject_invalid_input_type() -> None:
    planner = TaskPlanner()
    with pytest.raises(TaskValidationError):
        planner.parse_and_validate_plan(12345, task_id="task_err")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_plan_task_without_ollama_uses_fallback() -> None:
    # When no ollama_client is provided, falls back cleanly to deterministic plan
    planner = TaskPlanner(ollama_client=None)
    plan = await planner.plan_task("task_no_llm", "Generate monthly revenue report")
    assert plan.task_id == "task_no_llm"
    assert len(plan.steps) == 4
    assert plan.steps[-1].required_tools == ["generate_pdf_report"]


@pytest.mark.asyncio
async def test_plan_task_with_mocked_ollama_success() -> None:
    mock_ollama = MagicMock(spec=OllamaClient)
    llm_json_response = """
{
  "rationale": "Custom AI plan",
  "steps": [
    {
      "step_id": "custom_schema",
      "name": "Custom Schema Scan",
      "required_tools": ["inspect_database_schema"],
      "dependencies": []
    },
    {
      "step_id": "custom_query",
      "name": "Custom Query Exec",
      "required_tools": ["prepare_sql_query"],
      "dependencies": ["custom_schema"]
    }
  ]
}
"""
    mock_ollama.chat = AsyncMock(
        return_value=OllamaChatResponse(content=llm_json_response)
    )

    planner = TaskPlanner(ollama_client=mock_ollama)
    plan = await planner.plan_task("task_llm", "Custom user request")

    assert plan.task_id == "task_llm"
    assert len(plan.steps) == 2
    assert plan.steps[0].step_id == "custom_schema"
    assert plan.steps[1].step_id == "custom_query"
    assert plan.rationale == "Custom AI plan"


@pytest.mark.asyncio
async def test_plan_task_with_mocked_ollama_failure_falls_back() -> None:
    mock_ollama = MagicMock(spec=OllamaClient)
    # Simulate LLM returning malformed/unparseable content
    mock_ollama.chat = AsyncMock(
        return_value=OllamaChatResponse(content="I cannot formulate a plan.")
    )

    planner = TaskPlanner(ollama_client=mock_ollama)
    plan = await planner.plan_task("task_fallback", "Generate monthly PDF report")

    # Should fall back cleanly to deterministic plan
    assert plan.task_id == "task_fallback"
    assert len(plan.steps) == 4
    assert plan.steps[-1].required_tools == ["generate_pdf_report"]


@pytest.mark.asyncio
async def test_plan_task_with_mocked_ollama_exception_falls_back() -> None:
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_ollama.chat = AsyncMock(
        side_effect=OllamaConnectionError("Connection refused by Ollama daemon")
    )

    planner = TaskPlanner(ollama_client=mock_ollama)
    plan = await planner.plan_task("task_err_fallback", "Generate revenue PDF report")

    assert plan.task_id == "task_err_fallback"
    assert len(plan.steps) == 4
    assert plan.steps[0].step_id == "step_schema_discovery"

