"""Phase 6 End-to-End Integration Test Suite for Agent Intelligence Layer.

Tests:
1. End-to-end task lifecycle (creation -> DAG planning -> step execution -> completion).
2. Checkpoint creation across milestones and task recovery via `orchestrator.recover_task()`.
3. In-flight numerical consistency validation via `CanonicalSQLDataset`.
4. Model context capability validation and incompatibility reporting.
5. Dynamic settings updates and live context-window propagation.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.checkpoint_manager import CheckpointManager
from agent.checkpoint_models import CheckpointType, RecoveryPolicy, RecoveryStatus
from agent.context_builder import ContextBuilder
from agent.context_models import ExecutionStage
from agent.events import ActivityCategory
from agent.ollama_client import (
    ModelCapabilityStatus,
    ModelContextCapability,
    OllamaChatResponse,
    OllamaClient,
    OllamaToolCall,
)
from agent.orchestrator import AgentOrchestrator, AgentRunResult
from agent.skill_manager import SkillManager
from agent.task_manager import TaskManager
from agent.task_models import StepStatus, TaskPlan, TaskStatus, TaskStep
from agent.task_planner import TaskPlanner
from config.settings import AppSettings
from memory.models import TaskDecision, TaskToolCallRecord
from memory.repository import SQLiteMemoryRepository
from reporting.canonical_data import CanonicalSQLDataset


@pytest.fixture
def test_db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_memory.db"


@pytest.fixture
def memory_repo(test_db_path: Path) -> SQLiteMemoryRepository:
    return SQLiteMemoryRepository(db_path=test_db_path)


@pytest.fixture
def checkpoint_mgr(memory_repo: SQLiteMemoryRepository) -> CheckpointManager:
    return CheckpointManager(repository=memory_repo)


@pytest.fixture
def task_mgr(memory_repo: SQLiteMemoryRepository, checkpoint_mgr: CheckpointManager) -> TaskManager:
    return TaskManager(repository=memory_repo, checkpoint_manager=checkpoint_mgr)


@pytest.fixture
def skill_mgr(memory_repo: SQLiteMemoryRepository) -> SkillManager:
    return SkillManager(repository=memory_repo)


# ===========================================================================
# 1. Complete Task Lifecycle Integration
# ===========================================================================

@pytest.mark.asyncio
async def test_complete_task_lifecycle_integration(
    memory_repo: SQLiteMemoryRepository,
    checkpoint_mgr: CheckpointManager,
    task_mgr: TaskManager,
    skill_mgr: SkillManager,
) -> None:
    settings = AppSettings()
    settings.agent.agent_context_window = 131072

    mock_ollama = MagicMock(spec=OllamaClient)
    mock_ollama.settings = settings.ollama
    mock_ollama.check_connection = AsyncMock(return_value=(True, "0.40.14"))
    mock_ollama.probe_tool_capability = AsyncMock(return_value="native")

    # Mock Ollama validation capability as compatible
    mock_ollama.validate_model_context_capability = AsyncMock(
        return_value=ModelContextCapability(
            model="qwen3.5:4b",
            configured_window=131072,
            model_max_context=262144,
            effective_window=131072,
            status=ModelCapabilityStatus.COMPATIBLE,
            message="Model supports 256K, using configured 128K",
            is_compatible=True,
        )
    )

    # Sequence: 1. inspect schema, 2. execute query, 3. final summary
    schema_tool_call = OllamaToolCall(
        id="call_1",
        name="inspect_database_schema",
        arguments={},
    )
    sql_tool_call = OllamaToolCall(
        id="call_2",
        name="execute_readonly_sql",
        arguments={"query": "SELECT category, SUM(revenue) FROM sales GROUP BY category"},
    )

    mock_ollama.chat = AsyncMock(
        side_effect=[
            OllamaChatResponse(content="", tool_calls=[schema_tool_call]),
            OllamaChatResponse(content="", tool_calls=[sql_tool_call]),
            OllamaChatResponse(content="Analysis complete. Revenue breakdown verified across categories.", tool_calls=[]),
        ]
    )

    orchestrator = AgentOrchestrator(
        settings=settings,
        ollama_client=mock_ollama,
        memory_repo=memory_repo,
        checkpoint_manager=checkpoint_mgr,
        task_manager=task_mgr,
        skill_manager=skill_mgr,
    )
    orchestrator._initialized = True

    # Mock tool handler execution
    async def mock_execute_tool(name: str, args: dict) -> dict:
        if name == "inspect_database_schema":
            return {"tables": ["sales", "products"]}
        if name == "execute_readonly_sql":
            return {
                "status": "ok",
                "columns": ["category", "total_revenue"],
                "rows": [["Electronics", 125000.0], ["Home", 85000.0]],
            }
        return {"status": "ok"}

    orchestrator.tool_handler.execute_tool = AsyncMock(side_effect=mock_execute_tool)
    orchestrator.tool_handler.initialize = AsyncMock()

    result = await orchestrator.process_message("Generate category revenue breakdown report")

    assert result.status == "success"
    assert "Analysis complete" in result.final_message
    assert orchestrator.effective_context_window == 131072

    # Verify task persisted and marked complete in SQLite memory
    task = memory_repo.get_task(orchestrator.current_task_id)
    assert task is not None
    assert task.status == TaskStatus.COMPLETED

    # Verify checkpoints were created
    checkpoints = memory_repo.get_checkpoint_history(orchestrator.current_task_id)
    assert len(checkpoints) >= 1


# ===========================================================================
# 2. Checkpoint Creation and Task Recovery Integration
# ===========================================================================

@pytest.mark.asyncio
async def test_checkpoint_creation_and_task_recovery(
    memory_repo: SQLiteMemoryRepository,
    checkpoint_mgr: CheckpointManager,
    task_mgr: TaskManager,
) -> None:
    settings = AppSettings()
    orchestrator = AgentOrchestrator(
        settings=settings,
        memory_repo=memory_repo,
        checkpoint_manager=checkpoint_mgr,
        task_manager=task_mgr,
    )

    # 1. Create a task and register steps
    task = task_mgr.create_task("Monthly Performance Review")
    step1 = TaskStep(step_id="step_1", name="Query Sales", required_tools=["execute_readonly_sql"])
    step2 = TaskStep(step_id="step_2", name="Render PDF", required_tools=["generate_pdf_report"], dependencies=["step_1"])
    task_mgr.register_plan(task.task_id, TaskPlan(task_id=task.task_id, steps=[step1, step2], rationale="Test plan"))
    task_mgr.start_task(task.task_id)

    # 2. Complete step 1 and save checkpoint with metadata snapshot
    task_mgr.start_step(task.task_id, "step_1")
    task_mgr.complete_step(task.task_id, "step_1", output_reference="sales_summary_data")
    chk = checkpoint_mgr.create_checkpoint(
        task_id=task.task_id,
        checkpoint_type=CheckpointType.STEP_COMPLETED,
        current_step_id="step_1",
        metadata={"sales_total": 500000.0, "step_1_summary": "Query completed"},
    )
    assert chk is not None

    # 3. Simulate step 2 start and interruption
    task_mgr.start_step(task.task_id, "step_2")
    interrupted_tasks = orchestrator.get_interrupted_tasks()
    assert any(t.task_id == task.task_id for t in interrupted_tasks)

    # 4. Recover task via orchestrator recovery API
    recovery_res = orchestrator.recover_task(task.task_id, policy=RecoveryPolicy.AUTOMATIC_SAFE)
    assert recovery_res.success is True
    assert recovery_res.status == RecoveryStatus.SUCCESS
    assert recovery_res.resumed_step_id == "step_2"

    # 5. Verify task state reloaded correctly
    recovered = memory_repo.get(task.task_id)
    assert recovered is not None
    assert recovered.task_id == task.task_id
    assert recovered.status == TaskStatus.RUNNING
    assert recovered.get_step("step_1").status == StepStatus.COMPLETED
    assert recovered.get_step("step_2").status == StepStatus.READY

    # 6. Verify checkpoint metadata is intact
    saved_chk = memory_repo.get_checkpoint(chk.checkpoint_id)
    assert saved_chk is not None
    assert saved_chk.metadata.get("sales_total") == 500000.0

    # Verify latest recovery checkpoint links to resumed checkpoint
    latest_chk = memory_repo.get_latest_checkpoint(task.task_id)
    assert latest_chk is not None
    assert latest_chk.checkpoint_type == CheckpointType.RECOVERY_COMPLETED
    assert latest_chk.metadata.get("resumed_from") == recovery_res.resumed_from_checkpoint_id


# ===========================================================================
# 3. Report Numerical Consistency Gate Integration
# ===========================================================================

def test_report_numerical_consistency_gate() -> None:
    orchestrator = AgentOrchestrator(settings=AppSettings())

    # Build valid CanonicalSQLDataset
    columns = ["product", "revenue"]
    rows = [["Laptop", 1000.0], ["Phone", 500.0]]

    tool_args = {
        "title": "Hardware Sales",
        "columns": columns,
        "rows": rows,
        "kpi_summary": [{"label": "Total Revenue", "value": 1500.0, "format_type": "currency"}],
    }

    # Should validate cleanly without throwing
    component_status: dict[str, str] = {}
    validated = orchestrator._prepare_and_validate_report_args(
        tool_args,
        executed_sql="SELECT product, revenue FROM sales",
        sql_columns=columns,
        sql_rows=rows,
        cleaned_user_msg="Report on hardware sales",
        target_format="pdf",
        user_explicitly_wants_sql=False,
        component_status=component_status,
    )
    assert validated["title"] == "Hardware Sales"
    assert len(validated["rows"]) == 2


# ===========================================================================
# 4. Model Context Capability Incompatibility Gate
# ===========================================================================

@pytest.mark.asyncio
async def test_model_context_incompatibility_reported_cleanly() -> None:
    settings = AppSettings()
    settings.agent.agent_context_window = 131072  # User wants 128K

    mock_ollama = MagicMock(spec=OllamaClient)
    mock_ollama.settings = settings.ollama
    mock_ollama.check_connection = AsyncMock(return_value=(True, "0.40.14"))

    # Model metadata reveals model only supports 8K (8192)
    mock_ollama.validate_model_context_capability = AsyncMock(
        return_value=ModelContextCapability(
            model="tiny-model:1b",
            configured_window=131072,
            model_max_context=8192,
            effective_window=8192,
            status=ModelCapabilityStatus.INCOMPATIBLE,
            message="Model 'tiny-model:1b' maximum supported context window (8,192 tokens) is smaller than configured agent context window (131,072 tokens).",
            is_compatible=False,
        )
    )

    orchestrator = AgentOrchestrator(settings=settings, ollama_client=mock_ollama)

    result = await orchestrator.process_message("Generate analytics report")
    # Must report incompatibility error and prevent misleading success
    assert result.status == "error"
    assert "smaller than configured" in result.error
    assert "8,192" in result.final_message


# ===========================================================================
# 5. Dynamic Context Window Update Live Propagation
# ===========================================================================

def test_dynamic_context_window_propagation() -> None:
    settings = AppSettings()
    settings.agent.agent_context_window = 32768
    orchestrator = AgentOrchestrator(settings=settings)

    assert orchestrator.effective_context_window == 32768
    assert orchestrator.context_builder.num_ctx == 32768

    # Reconfigure to 128K live
    new_settings = AppSettings()
    new_settings.agent.agent_context_window = 131072
    orchestrator.update_settings(new_settings)

    assert orchestrator.effective_context_window == 131072
    assert orchestrator.context_builder.num_ctx == 131072
    assert orchestrator.ollama_client.settings.num_ctx == 131072

    ctx = orchestrator.context_builder.build(
        ExecutionStage.REQUEST_PLANNING,
        user_request="Test prompt",
    )
    assert ctx.report.effective_context_window == 131072
    assert ctx.report.configured_context_window == 131072
