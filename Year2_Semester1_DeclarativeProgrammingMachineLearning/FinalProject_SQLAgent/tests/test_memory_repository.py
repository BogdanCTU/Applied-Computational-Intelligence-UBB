"""Unit tests for SQLite Working, Episodic, and Semantic Memory repository capabilities."""

from __future__ import annotations

from pathlib import Path
import pytest

from agent.task_models import (
    AgentTask,
    StepStatus,
    TaskPlan,
    TaskStatus,
    TaskStep,
)
from memory.models import (
    SemanticFact,
    TaskArtifactRecord,
    TaskDecision,
    TaskHistoryItem,
    TaskToolCallRecord,
)
from memory.repository import SQLiteMemoryRepository


# ---------------------------------------------------------------------------
# Working Memory Tests
# ---------------------------------------------------------------------------


def test_working_memory_task_lifecycle_persistence(tmp_path: Path) -> None:
    db_file = tmp_path / "working_mem.db"
    repo = SQLiteMemoryRepository(db_path=db_file)

    task = AgentTask(
        task_id="task_wm_1",
        user_request="Generate monthly revenue summary",
        status=TaskStatus.PENDING,
        metadata={"source": "gui_test"},
    )
    repo.save(task)

    # Verify retrieval
    loaded = repo.get("task_wm_1")
    assert loaded is not None
    assert loaded.task_id == "task_wm_1"
    assert loaded.status == TaskStatus.PENDING
    assert loaded.user_request == "Generate monthly revenue summary"
    assert loaded.metadata.get("source") == "gui_test"

    # Update task state
    task.transition_to(TaskStatus.RUNNING)
    task.current_step = "step_1"
    repo.save(task)

    loaded2 = repo.get("task_wm_1")
    assert loaded2 is not None
    assert loaded2.status == TaskStatus.RUNNING
    assert loaded2.current_step == "step_1"


def test_working_memory_plan_and_steps_persistence(tmp_path: Path) -> None:
    db_file = tmp_path / "working_plan.db"
    repo = SQLiteMemoryRepository(db_path=db_file)

    s1 = TaskStep(
        step_id="step_1",
        name="Inspect Schema",
        description="Extract tables",
        required_skill="sql/schema_analysis",
        required_tools=["inspect_database_schema"],
        status=StepStatus.COMPLETED,
        output_reference="ref_schema_v1",
    )
    s2 = TaskStep(
        step_id="step_2",
        name="Execute SQL",
        description="Run revenue query",
        required_tools=["execute_readonly_sql"],
        dependencies=["step_1"],
        optional_dependencies=[],
        status=StepStatus.RUNNING,
    )
    plan = TaskPlan(
        plan_id="plan_wm_1",
        task_id="task_wm_2",
        steps=[s1, s2],
        rationale="Two-stage analytical pipeline",
    )
    task = AgentTask(
        task_id="task_wm_2",
        user_request="Analyze annual revenue",
        status=TaskStatus.RUNNING,
        current_step="step_2",
        steps=[s1, s2],
        plan=plan,
    )

    repo.save(task)

    # Reopen fresh repository instance
    fresh_repo = SQLiteMemoryRepository(db_path=db_file)
    restored = fresh_repo.get("task_wm_2")
    assert restored is not None
    assert restored.task_id == "task_wm_2"
    assert restored.status == TaskStatus.RUNNING
    assert restored.current_step == "step_2"
    assert len(restored.steps) == 2
    assert restored.steps[0].step_id == "step_1"
    assert restored.steps[0].status == StepStatus.COMPLETED
    assert restored.steps[0].output_reference == "ref_schema_v1"
    assert restored.steps[1].step_id == "step_2"
    assert restored.steps[1].status == StepStatus.RUNNING
    assert restored.steps[1].dependencies == ["step_1"]
    assert restored.plan is not None
    assert restored.plan.plan_id == "plan_wm_1"
    assert restored.plan.rationale == "Two-stage analytical pipeline"


def test_working_memory_isolated_step_status_update(tmp_path: Path) -> None:
    db_file = tmp_path / "step_update.db"
    repo = SQLiteMemoryRepository(db_path=db_file)

    s1 = TaskStep(step_id="s1", name="Step 1", status=StepStatus.READY)
    s2 = TaskStep(step_id="s2", name="Step 2", status=StepStatus.PENDING, dependencies=["s1"])
    task = AgentTask(task_id="t_step_up", user_request="Step update test", steps=[s1, s2])
    repo.save(task)

    # Update only s1 status
    repo.update_step_status("t_step_up", "s1", StepStatus.COMPLETED, output_reference="out_s1")

    reloaded = repo.get("t_step_up")
    assert reloaded is not None
    assert reloaded.get_step("s1").status == StepStatus.COMPLETED
    assert reloaded.get_step("s1").output_reference == "out_s1"
    # Unrelated step s2 must remain untouched
    assert reloaded.get_step("s2").status == StepStatus.PENDING


def test_working_memory_decisions_tool_calls_and_artifacts(tmp_path: Path) -> None:
    db_file = tmp_path / "subsystems.db"
    repo = SQLiteMemoryRepository(db_path=db_file)

    task = AgentTask(task_id="t_meta", user_request="Generate KPI cards")
    repo.save(task)

    # 1. Decisions
    d1 = repo.save_decision(
        task_id="t_meta",
        decision_type="sql_strategy",
        summary="Use order_items for price aggregation to avoid fan-out",
        rationale="Orders join multiplies lines by items",
    )
    assert d1.decision_id.startswith("dec_")
    decisions = repo.get_decisions("t_meta")
    assert len(decisions) == 1
    assert decisions[0].decision_type == "sql_strategy"
    assert "order_items" in decisions[0].summary

    # 2. Tool Calls
    tc1 = repo.save_tool_call(
        task_id="t_meta",
        tool_name="prepare_sql_query",
        arguments={"sql_query": "SELECT SUM(price) FROM order_items;"},
        result_summary="Query validated successfully",
        duration_ms=42.5,
        status="success",
    )
    assert tc1.call_id.startswith("call_")
    tool_calls = repo.get_tool_calls("t_meta")
    assert len(tool_calls) == 1
    assert tool_calls[0].tool_name == "prepare_sql_query"
    assert tool_calls[0].duration_ms == 42.5

    # 3. Artifacts
    art1 = repo.save_artifact(
        task_id="t_meta",
        artifact_type="pdf_report",
        file_path="reports/revenue_q3.pdf",
        file_size_bytes=1048576,
        checksum="abc123hash",
        metadata={"page_count": 3},
    )
    assert art1.artifact_id.startswith("art_")
    artifacts = repo.get_artifacts("t_meta")
    assert len(artifacts) == 1
    assert artifacts[0].artifact_type == "pdf_report"
    assert artifacts[0].file_path == "reports/revenue_q3.pdf"
    assert artifacts[0].file_size_bytes == 1048576


def test_cascade_delete_removes_associated_records(tmp_path: Path) -> None:
    db_file = tmp_path / "cascade.db"
    repo = SQLiteMemoryRepository(db_path=db_file)

    s1 = TaskStep(step_id="s1", name="Step 1")
    task = AgentTask(task_id="t_cascade", user_request="To be deleted", steps=[s1])
    repo.save(task)
    repo.save_decision(task_id="t_cascade", decision_type="test", summary="Test decision")
    repo.save_tool_call(task_id="t_cascade", tool_name="inspect_database_schema")
    repo.save_artifact(task_id="t_cascade", artifact_type="pdf", file_path="dummy.pdf")

    assert repo.get("t_cascade") is not None
    assert len(repo.get_decisions("t_cascade")) == 1

    # Delete task
    assert repo.delete("t_cascade") is True

    assert repo.get("t_cascade") is None
    assert len(repo.get_decisions("t_cascade")) == 0
    assert len(repo.get_tool_calls("t_cascade")) == 0
    assert len(repo.get_artifacts("t_cascade")) == 0


# ---------------------------------------------------------------------------
# Episodic Memory Tests
# ---------------------------------------------------------------------------


def test_episodic_memory_search_and_filters(tmp_path: Path) -> None:
    db_file = tmp_path / "episodic.db"
    repo = SQLiteMemoryRepository(db_path=db_file)

    # Seed 3 historical tasks
    t1 = AgentTask(
        task_id="t_oct_revenue",
        user_request="Generate October revenue overview",
        status=TaskStatus.COMPLETED,
        created_at="2026-10-01T10:00:00",
    )
    t2 = AgentTask(
        task_id="t_nov_customers",
        user_request="Export top active customer list to CSV",
        status=TaskStatus.COMPLETED,
        created_at="2026-11-01T12:00:00",
    )
    t3 = AgentTask(
        task_id="t_failed_query",
        user_request="Query non-existent column syntax error",
        status=TaskStatus.FAILED,
        error="Syntax error near WHERE",
        created_at="2026-11-02T15:00:00",
    )

    repo.save(t1)
    repo.save(t2)
    repo.save(t3)

    # 1. Search by keyword
    kw_results = repo.search_task_history(keyword="revenue")
    assert len(kw_results) == 1
    assert kw_results[0].task_id == "t_oct_revenue"

    # Search by error keyword
    err_results = repo.search_task_history(keyword="Syntax error")
    assert len(err_results) == 1
    assert err_results[0].task_id == "t_failed_query"

    # 2. Filter by status
    completed = repo.search_task_history(status=TaskStatus.COMPLETED)
    assert len(completed) == 2

    failed = repo.search_task_history(status=TaskStatus.FAILED)
    assert len(failed) == 1

    # 3. Filter by date range
    oct_only = repo.search_task_history(
        start_date="2026-10-01T00:00:00", end_date="2026-10-31T23:59:59"
    )
    assert len(oct_only) == 1
    assert oct_only[0].task_id == "t_oct_revenue"

    # 4. Recent history
    recent = repo.get_recent_task_history(limit=2)
    assert len(recent) == 2
    # Ordered newest first
    assert recent[0].task_id == "t_failed_query"


def test_episodic_memory_task_execution_summary(tmp_path: Path) -> None:
    db_file = tmp_path / "exec_summary.db"
    repo = SQLiteMemoryRepository(db_path=db_file)

    s1 = TaskStep(step_id="s1", name="Prep", status=StepStatus.COMPLETED)
    s2 = TaskStep(step_id="s2", name="Exec", status=StepStatus.COMPLETED)
    task = AgentTask(
        task_id="t_summary_test",
        user_request="Generate executive summary report",
        status=TaskStatus.COMPLETED,
        steps=[s1, s2],
    )
    repo.save(task)
    repo.save_artifact(task_id="t_summary_test", artifact_type="pdf_report", file_path="exec.pdf")

    summary = repo.get_task_execution_summary("t_summary_test")
    assert summary["task_id"] == "t_summary_test"
    assert summary["status"] == "COMPLETED"
    assert summary["total_steps"] == 2
    assert summary["completed_steps"] == 2
    assert summary["failed_steps"] == 0
    assert summary["artifacts_count"] == 1


# ---------------------------------------------------------------------------
# Semantic Memory Tests
# ---------------------------------------------------------------------------


def test_semantic_memory_save_and_validated_retrieval(tmp_path: Path) -> None:
    db_file = tmp_path / "semantic.db"
    repo = SQLiteMemoryRepository(db_path=db_file)

    # Validated domain fact
    fact1 = repo.save_semantic_fact(
        category="business_metric",
        subject="revenue",
        fact="Revenue is defined as SUM(order_items.price), excluding shipping and refunds.",
        provenance="accounting_guidelines",
        is_validated=True,
    )
    assert fact1.fact_id.startswith("fact_")
    assert fact1.is_validated is True

    # Unvalidated observation (LLM hypothesis)
    repo.save_semantic_fact(
        category="data_quality",
        subject="payments",
        fact="Payment values seem to double-count voucher adjustments.",
        provenance="llm_observation",
        is_validated=False,
    )

    # 1. Default retrieval must strictly return validated facts only!
    agent_facts = repo.get_semantic_facts()
    assert len(agent_facts) == 1
    assert agent_facts[0].subject == "revenue"

    # 2. Explicit retrieval with validated_only=False returns unvalidated observations too
    all_facts = repo.get_semantic_facts(validated_only=False)
    assert len(all_facts) == 2


def test_semantic_memory_filtering_by_category_and_subject(tmp_path: Path) -> None:
    db_file = tmp_path / "semantic_filter.db"
    repo = SQLiteMemoryRepository(db_path=db_file)

    repo.save_semantic_fact(
        category="table_relationship",
        subject="orders",
        fact="orders.order_id has a 1-to-many relationship with order_items.order_id.",
        is_validated=True,
    )
    repo.save_semantic_fact(
        category="business_metric",
        subject="order_count",
        fact="Order count is COUNT(DISTINCT orders.order_id).",
        is_validated=True,
    )

    by_cat = repo.get_semantic_facts(category="table_relationship")
    assert len(by_cat) == 1
    assert by_cat[0].subject == "orders"

    by_subj = repo.get_semantic_facts(subject="order_count")
    assert len(by_subj) == 1
    assert by_subj[0].category == "business_metric"


def test_semantic_memory_update_and_invalidation(tmp_path: Path) -> None:
    db_file = tmp_path / "semantic_update.db"
    repo = SQLiteMemoryRepository(db_path=db_file)

    f = repo.save_semantic_fact(
        category="business_metric",
        subject="aov",
        fact="Average Order Value = SUM(price) / COUNT(order_id)",
        is_validated=True,
    )

    # Update fact definition
    updated = repo.update_semantic_fact(
        f.fact_id,
        fact="Average Order Value = SUM(order_items.price) / COUNT(DISTINCT orders.order_id)",
    )
    assert updated is not None
    assert "DISTINCT" in updated.fact

    # Invalidate fact
    assert repo.invalidate_semantic_fact(f.fact_id) is True
    # Now excluded from default validated retrieval
    assert len(repo.get_semantic_facts()) == 0
    # But still present when inspection includes unvalidated
    assert len(repo.get_semantic_facts(validated_only=False)) == 1

    # Delete fact
    assert repo.delete_semantic_fact(f.fact_id) is True
    assert len(repo.get_semantic_facts(validated_only=False)) == 0


# ---------------------------------------------------------------------------
# Skill Registry Tests (Foundation)
# ---------------------------------------------------------------------------


def test_skill_registry_registration_and_retrieval(tmp_path: Path) -> None:
    db_file = tmp_path / "skill_reg.db"
    repo = SQLiteMemoryRepository(db_path=db_file)

    s1 = repo.register_skill(
        skill_id="sql_schema_analysis",
        name="Schema Analysis",
        domain="sql",
        version="1.0.0",
        file_path="skills/sql/schema_analysis.md",
        description="Inspect tables and check relationships",
    )
    assert s1["skill_id"] == "sql_schema_analysis"

    repo.register_skill(
        skill_id="reporting_chart_selection",
        name="Chart Selection",
        domain="reporting",
        version="1.0.0",
        file_path="skills/reporting/chart_selection.md",
        description="Select optimal vector chart based on data distributions",
    )

    all_skills = repo.get_registered_skills()
    assert len(all_skills) == 2

    sql_skills = repo.get_registered_skills(domain="sql")
    assert len(sql_skills) == 1
    assert sql_skills[0]["skill_id"] == "sql_schema_analysis"

