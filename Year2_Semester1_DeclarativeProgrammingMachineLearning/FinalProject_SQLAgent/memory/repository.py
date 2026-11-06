"""Persistent SQLite Repository for Agent Working, Episodic, and Semantic Memory.

Manages dedicated `data/agent_memory.db` with thread-safe connections,
versioned schema migrations, strict parameterized queries, and ACID transactions.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Sequence

from agent.checkpoint_models import (
    CheckpointType,
    InterruptedOperationRecord,
    OperationStatus,
    PendingApprovalSnapshot,
    RecoveryAttemptRecord,
    RecoveryPolicy,
    RecoveryStatus,
    StepExecutionSnapshot,
    TaskCheckpoint,
)
from agent.events import mask_sensitive_data
from agent.task_manager import StepNotFoundError, TaskNotFoundError
from agent.task_models import (
    AgentTask,
    StepStatus,
    TaskPlan,
    TaskStatus,
    TaskStep,
)
from config.paths import get_memory_database_path, resolve_path
from memory.migrations import apply_migrations
from memory.models import (
    SemanticFact,
    TaskArtifactRecord,
    TaskDecision,
    TaskHistoryItem,
    TaskToolCallRecord,
)

log = logging.getLogger(__name__)


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(val: Any) -> str:
    return json.dumps(val, ensure_ascii=False)


def _json_loads(val: Any, default: Any = None) -> Any:
    if val is None or val == "":
        return default
    if isinstance(val, (dict, list)):
        return val
    try:
        return json.loads(val)
    except Exception:
        return default


def _strip_reasoning_tags(text: str) -> str:
    """Strip internal LLM reasoning/chain-of-thought blocks from text."""
    if not text:
        return ""
    # Strip <think>...</think> and unclosed <think>...
    cleaned = re.sub(r"(?is)<\s*think\s*>.*?(?:<\s*/\s*think\s*>|$)", "", text)
    return cleaned.strip()


class SQLiteMemoryRepository:
    """Thread-safe SQLite repository backing Working, Episodic, and Semantic memory."""

    def __init__(
        self,
        db_path: str | os.PathLike[str] | None = None,
        *,
        timeout_s: float = 30.0,
        auto_migrate: bool = True,
    ) -> None:
        self.db_path = get_memory_database_path(db_path)
        self.timeout_s = float(timeout_s)

        # Non-negotiable security invariant: Agent memory must NEVER point to ecommerce.db!
        ecommerce_path = resolve_path("data/ecommerce.db")
        if self.db_path.resolve() == ecommerce_path.resolve():
            raise ValueError(
                f"Critical security violation: Cannot use '{self.db_path}' as agent memory database! "
                "The primary ecommerce database is strictly read-only and immutable."
            )

        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        if auto_migrate:
            self.initialize_schema()

    def initialize_schema(self, *, migrations_dir: Path | None = None) -> int:
        """Run migrations and configure WAL mode."""
        with self.connection() as conn:
            # Enable WAL mode for high concurrency
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            return apply_migrations(conn, migrations_dir=migrations_dir)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Produce an isolated SQLite connection configured with foreign keys and timeout."""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=self.timeout_s,
            isolation_level=None,  # Autocommit mode; explicit transaction blocks managed via transaction()
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 30000;")
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Produce an isolated SQLite connection wrapped in an atomic BEGIN / COMMIT / ROLLBACK block."""
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE;")
            try:
                yield conn
                conn.execute("COMMIT;")
            except Exception:
                conn.execute("ROLLBACK;")
                raise

    # -----------------------------------------------------------------------
    # TaskRepository Protocol Implementation (Working Memory Root)
    # -----------------------------------------------------------------------

    def save(self, task: AgentTask) -> AgentTask:
        """Persist or update an AgentTask, its TaskPlan, and all TaskSteps in an atomic transaction."""
        now_str = _utc_iso_now()
        task.updated_at = now_str

        with self.transaction() as conn:
            # 1. Upsert task_runs
            conn.execute(
                """
                INSERT INTO task_runs (
                    task_id, user_request, status, current_step,
                    created_at, updated_at, error, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    user_request = excluded.user_request,
                    status = excluded.status,
                    current_step = excluded.current_step,
                    updated_at = excluded.updated_at,
                    error = excluded.error,
                    metadata = excluded.metadata;
                """,
                (
                    task.task_id,
                    task.user_request,
                    task.status.value,
                    task.current_step,
                    task.created_at,
                    task.updated_at,
                    task.error,
                    _json_dumps(task.metadata),
                ),
            )

            # 2. Upsert task_plans if present
            if task.plan:
                conn.execute(
                    """
                    INSERT INTO task_plans (plan_id, task_id, rationale, created_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(task_id) DO UPDATE SET
                        plan_id = excluded.plan_id,
                        rationale = excluded.rationale;
                    """,
                    (
                        task.plan.plan_id,
                        task.task_id,
                        task.plan.rationale,
                        task.plan.created_at,
                    ),
                )

            # 3. Upsert task_steps
            for idx, step in enumerate(task.steps):
                conn.execute(
                    """
                    INSERT INTO task_steps (
                        step_id, task_id, step_order, name, description,
                        required_skill, required_tools, dependencies, optional_dependencies,
                        status, output_reference, error, metadata, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(step_id) DO UPDATE SET
                        step_order = excluded.step_order,
                        name = excluded.name,
                        description = excluded.description,
                        required_skill = excluded.required_skill,
                        required_tools = excluded.required_tools,
                        dependencies = excluded.dependencies,
                        optional_dependencies = excluded.optional_dependencies,
                        status = excluded.status,
                        output_reference = excluded.output_reference,
                        error = excluded.error,
                        metadata = excluded.metadata,
                        updated_at = excluded.updated_at;
                    """,
                    (
                        step.step_id,
                        task.task_id,
                        idx,
                        step.name,
                        step.description,
                        step.required_skill,
                        _json_dumps(step.required_tools),
                        _json_dumps(step.dependencies),
                        _json_dumps(step.optional_dependencies),
                        step.status.value,
                        step.output_reference,
                        step.error,
                        _json_dumps(step.metadata),
                        step.created_at,
                        step.updated_at,
                    ),
                )

        return task

    def get(self, task_id: str) -> AgentTask | None:
        """Reconstruct a complete AgentTask from persistent SQLite storage."""
        with self.connection() as conn:
            # 1. Fetch task run
            cur = conn.execute(
                """
                SELECT task_id, user_request, status, current_step,
                       created_at, updated_at, error, metadata
                FROM task_runs
                WHERE task_id = ?;
                """,
                (task_id,),
            )
            t_row = cur.fetchone()
            if not t_row:
                return None

            # 2. Fetch steps
            cur = conn.execute(
                """
                SELECT step_id, step_order, name, description,
                       required_skill, required_tools, dependencies, optional_dependencies,
                       status, output_reference, error, metadata, created_at, updated_at
                FROM task_steps
                WHERE task_id = ?
                ORDER BY step_order ASC, rowid ASC;
                """,
                (task_id,),
            )
            step_rows = cur.fetchall()
            steps: list[TaskStep] = []
            for s in step_rows:
                steps.append(
                    TaskStep(
                        step_id=s["step_id"],
                        name=s["name"],
                        description=s["description"] or "",
                        required_skill=s["required_skill"],
                        required_tools=_json_loads(s["required_tools"], []),
                        dependencies=_json_loads(s["dependencies"], []),
                        optional_dependencies=_json_loads(s["optional_dependencies"], []),
                        status=StepStatus(s["status"]),
                        output_reference=s["output_reference"],
                        error=s["error"],
                        metadata=_json_loads(s["metadata"], {}),
                        created_at=s["created_at"],
                        updated_at=s["updated_at"],
                    )
                )

            # 3. Fetch plan if available
            cur = conn.execute(
                """
                SELECT plan_id, task_id, rationale, created_at
                FROM task_plans
                WHERE task_id = ?;
                """,
                (task_id,),
            )
            p_row = cur.fetchone()
            plan: TaskPlan | None = None
            if p_row:
                plan = TaskPlan(
                    plan_id=p_row["plan_id"],
                    task_id=p_row["task_id"],
                    steps=steps,
                    rationale=p_row["rationale"] or "",
                    created_at=p_row["created_at"],
                )

            return AgentTask(
                task_id=t_row["task_id"],
                user_request=t_row["user_request"],
                status=TaskStatus(t_row["status"]),
                current_step=t_row["current_step"],
                steps=steps,
                plan=plan,
                created_at=t_row["created_at"],
                updated_at=t_row["updated_at"],
                error=t_row["error"],
                metadata=_json_loads(t_row["metadata"], {}),
            )

    def get_task(self, task_id: str) -> AgentTask:
        """Fetch task by ID or raise TaskNotFoundError."""
        task = self.get(task_id)
        if not task:
            raise TaskNotFoundError(f"Task with ID '{task_id}' not found.")
        return task

    def list_all(self, limit: int = 100) -> list[AgentTask]:
        """Return all persisted tasks ordered newest to oldest."""
        with self.connection() as conn:
            cur = conn.execute(
                "SELECT task_id FROM task_runs ORDER BY created_at DESC LIMIT ?;",
                (limit,),
            )
            rows = cur.fetchall()

        tasks: list[AgentTask] = []
        for r in rows:
            t = self.get(r["task_id"])
            if t:
                tasks.append(t)
        return tasks

    def delete(self, task_id: str) -> bool:
        """Delete task and all associated cascade records (steps, plan, decisions, artifacts)."""
        with self.transaction() as conn:
            cur = conn.execute("DELETE FROM task_runs WHERE task_id = ?;", (task_id,))
            return cur.rowcount > 0

    # -----------------------------------------------------------------------
    # Working Memory: Step & Subsystem Updates
    # -----------------------------------------------------------------------

    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus | str,
        *,
        error: str | None = None,
        current_step: str | None = None,
    ) -> None:
        """Update task lifecycle state directly in SQLite storage."""
        st_val = status.value if isinstance(status, TaskStatus) else str(status)
        now_str = _utc_iso_now()
        with self.transaction() as conn:
            cur = conn.execute(
                """
                UPDATE task_runs
                SET status = ?,
                    error = COALESCE(?, error),
                    current_step = CASE WHEN ? THEN ? ELSE current_step END,
                    updated_at = ?
                WHERE task_id = ?;
                """,
                (
                    st_val,
                    error,
                    current_step is not None,
                    current_step,
                    now_str,
                    task_id,
                ),
            )
            if cur.rowcount == 0:
                raise TaskNotFoundError(f"Task with ID '{task_id}' not found.")

    def update_step_status(
        self,
        task_id: str,
        step_id: str,
        status: StepStatus | str,
        *,
        error: str | None = None,
        output_reference: str | None = None,
    ) -> None:
        """Update step status without affecting unrelated task state."""
        st_val = status.value if isinstance(status, StepStatus) else str(status)
        now_str = _utc_iso_now()
        with self.transaction() as conn:
            cur = conn.execute(
                """
                UPDATE task_steps
                SET status = ?,
                    error = COALESCE(?, error),
                    output_reference = COALESCE(?, output_reference),
                    updated_at = ?
                WHERE task_id = ? AND step_id = ?;
                """,
                (st_val, error, output_reference, now_str, task_id, step_id),
            )
            if cur.rowcount == 0:
                raise StepNotFoundError(f"Step '{step_id}' in task '{task_id}' not found.")

    def save_decision(
        self,
        task_id: str,
        decision_type: str,
        summary: str,
        *,
        rationale: str = "",
        step_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskDecision:
        """Persist a strategic or analytical choice made by the agent."""
        cleaned_rationale = _strip_reasoning_tags(rationale)
        decision = TaskDecision(
            task_id=task_id,
            step_id=step_id,
            decision_type=decision_type,
            summary=summary,
            rationale=cleaned_rationale,
            metadata=metadata or {},
        )
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO task_decisions (
                    decision_id, task_id, step_id, decision_type, summary,
                    rationale, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    decision.decision_id,
                    decision.task_id,
                    decision.step_id,
                    decision.decision_type,
                    decision.summary,
                    decision.rationale,
                    _json_dumps(decision.metadata),
                    decision.created_at,
                ),
            )
        return decision

    def get_decisions(self, task_id: str) -> list[TaskDecision]:
        """Fetch all decisions recorded for a specific task."""
        with self.connection() as conn:
            cur = conn.execute(
                """
                SELECT decision_id, task_id, step_id, decision_type,
                       summary, rationale, metadata, created_at
                FROM task_decisions
                WHERE task_id = ?
                ORDER BY created_at ASC;
                """,
                (task_id,),
            )
            rows = cur.fetchall()
            return [
                TaskDecision(
                    decision_id=r["decision_id"],
                    task_id=r["task_id"],
                    step_id=r["step_id"],
                    decision_type=r["decision_type"],
                    summary=r["summary"],
                    rationale=r["rationale"] or "",
                    metadata=_json_loads(r["metadata"], {}),
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    def save_tool_call(
        self,
        task_id: str,
        tool_name: str,
        *,
        arguments: dict[str, Any] | None = None,
        result_summary: str = "",
        duration_ms: float = 0.0,
        status: str = "success",
        error: str | None = None,
        step_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskToolCallRecord:
        """Audit an MCP tool execution in persistent memory."""
        clean_args = mask_sensitive_data(arguments or {})
        record = TaskToolCallRecord(
            task_id=task_id,
            step_id=step_id,
            tool_name=tool_name,
            arguments=clean_args,
            result_summary=result_summary,
            duration_ms=duration_ms,
            status=status,
            error=error,
            metadata=metadata or {},
        )
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO task_tool_calls (
                    call_id, task_id, step_id, tool_name, arguments,
                    result_summary, duration_ms, status, error, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    record.call_id,
                    record.task_id,
                    record.step_id,
                    record.tool_name,
                    _json_dumps(record.arguments),
                    record.result_summary,
                    record.duration_ms,
                    record.status,
                    record.error,
                    _json_dumps(record.metadata),
                    record.created_at,
                ),
            )
        return record

    def get_tool_calls(self, task_id: str) -> list[TaskToolCallRecord]:
        """Fetch chronological tool invocation records for a task."""
        with self.connection() as conn:
            cur = conn.execute(
                """
                SELECT call_id, task_id, step_id, tool_name, arguments,
                       result_summary, duration_ms, status, error, metadata, created_at
                FROM task_tool_calls
                WHERE task_id = ?
                ORDER BY created_at ASC;
                """,
                (task_id,),
            )
            rows = cur.fetchall()
            return [
                TaskToolCallRecord(
                    call_id=r["call_id"],
                    task_id=r["task_id"],
                    step_id=r["step_id"],
                    tool_name=r["tool_name"],
                    arguments=_json_loads(r["arguments"], {}),
                    result_summary=r["result_summary"] or "",
                    duration_ms=float(r["duration_ms"] or 0.0),
                    status=r["status"],
                    error=r["error"],
                    metadata=_json_loads(r["metadata"], {}),
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    def save_artifact(
        self,
        task_id: str,
        artifact_type: str,
        file_path: str,
        *,
        file_size_bytes: int = 0,
        checksum: str | None = None,
        step_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskArtifactRecord:
        """Register a report or dataset reference in persistent memory."""
        artifact = TaskArtifactRecord(
            task_id=task_id,
            step_id=step_id,
            artifact_type=artifact_type,
            file_path=file_path,
            file_size_bytes=file_size_bytes,
            checksum=checksum,
            metadata=metadata or {},
        )
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO task_artifacts (
                    artifact_id, task_id, step_id, artifact_type, file_path,
                    file_size_bytes, checksum, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    artifact.artifact_id,
                    artifact.task_id,
                    artifact.step_id,
                    artifact.artifact_type,
                    artifact.file_path,
                    artifact.file_size_bytes,
                    artifact.checksum,
                    _json_dumps(artifact.metadata),
                    artifact.created_at,
                ),
            )
        return artifact

    def get_artifacts(self, task_id: str) -> list[TaskArtifactRecord]:
        """Fetch generated document and dataset references for a task."""
        with self.connection() as conn:
            cur = conn.execute(
                """
                SELECT artifact_id, task_id, step_id, artifact_type,
                       file_path, file_size_bytes, checksum, metadata, created_at
                FROM task_artifacts
                WHERE task_id = ?
                ORDER BY created_at ASC;
                """,
                (task_id,),
            )
            rows = cur.fetchall()
            return [
                TaskArtifactRecord(
                    artifact_id=r["artifact_id"],
                    task_id=r["task_id"],
                    step_id=r["step_id"],
                    artifact_type=r["artifact_type"],
                    file_path=r["file_path"],
                    file_size_bytes=int(r["file_size_bytes"] or 0),
                    checksum=r["checksum"],
                    metadata=_json_loads(r["metadata"], {}),
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    # -----------------------------------------------------------------------
    # Episodic Memory: Historical Search and Retrieval
    # -----------------------------------------------------------------------

    def search_task_history(
        self,
        *,
        keyword: str | None = None,
        status: TaskStatus | str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 50,
    ) -> list[TaskHistoryItem]:
        """Search past tasks using keyword matching, status filtering, and date boundaries."""
        clauses: list[str] = []
        params: list[Any] = []

        if keyword and keyword.strip():
            kw = f"%{keyword.strip()}%"
            clauses.append("(t.user_request LIKE ? OR t.error LIKE ?)")
            params.extend([kw, kw])

        if status:
            st_val = status.value if isinstance(status, TaskStatus) else str(status)
            clauses.append("t.status = ?")
            params.append(st_val)

        if start_date:
            clauses.append("t.created_at >= ?")
            params.append(start_date)

        if end_date:
            clauses.append("t.created_at <= ?")
            params.append(end_date)

        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        query = f"""
            SELECT t.task_id, t.user_request, t.status, t.current_step,
                   t.created_at, t.updated_at, t.error, t.metadata,
                   COUNT(s.step_id) as total_steps,
                   SUM(CASE WHEN s.status = 'COMPLETED' THEN 1 ELSE 0 END) as completed_steps,
                   SUM(CASE WHEN s.status = 'FAILED' THEN 1 ELSE 0 END) as failed_steps
            FROM task_runs t
            LEFT JOIN task_steps s ON t.task_id = s.task_id
            {where_clause}
            GROUP BY t.task_id
            ORDER BY t.created_at DESC
            LIMIT ?;
        """
        params.append(limit)

        with self.connection() as conn:
            cur = conn.execute(query, params)
            rows = cur.fetchall()

            results: list[TaskHistoryItem] = []
            for r in rows:
                tid = r["task_id"]
                artifacts = [a.to_dict() for a in self.get_artifacts(tid)]
                summary = (
                    f"Task {tid} ({r['status']}): {r['user_request']} "
                    f"[{r['completed_steps'] or 0}/{r['total_steps'] or 0} steps completed]"
                )
                results.append(
                    TaskHistoryItem(
                        task_id=tid,
                        user_request=r["user_request"],
                        status=r["status"],
                        current_step=r["current_step"],
                        created_at=r["created_at"],
                        updated_at=r["updated_at"],
                        error=r["error"],
                        total_steps=int(r["total_steps"] or 0),
                        completed_steps=int(r["completed_steps"] or 0),
                        failed_steps=int(r["failed_steps"] or 0),
                        artifacts=artifacts,
                        execution_summary=summary,
                        metadata=_json_loads(r["metadata"], {}),
                    )
                )

            return results

    def get_recent_task_history(self, limit: int = 10) -> list[TaskHistoryItem]:
        """Fetch the most recent tasks completed or attempted."""
        return self.search_task_history(limit=limit)

    def get_task_execution_summary(self, task_id: str) -> dict[str, Any]:
        """Return comprehensive episodic metadata for a past task."""
        task = self.get(task_id)
        if not task:
            return {}

        decisions = self.get_decisions(task_id)
        tool_calls = self.get_tool_calls(task_id)
        artifacts = self.get_artifacts(task_id)

        return {
            "task_id": task.task_id,
            "user_request": task.user_request,
            "status": task.status.value,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "total_steps": len(task.steps),
            "completed_steps": sum(1 for s in task.steps if s.status == StepStatus.COMPLETED),
            "failed_steps": sum(1 for s in task.steps if s.status == StepStatus.FAILED),
            "decisions_count": len(decisions),
            "tool_calls_count": len(tool_calls),
            "artifacts_count": len(artifacts),
            "artifacts": [a.to_dict() for a in artifacts],
            "error": task.error,
        }

    # -----------------------------------------------------------------------
    # Semantic Memory: Validated Domain Knowledge
    # -----------------------------------------------------------------------

    def save_semantic_fact(
        self,
        category: str,
        subject: str,
        fact: str,
        *,
        provenance: str = "system",
        is_validated: bool = True,
        fact_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SemanticFact:
        """Persist or update domain knowledge.

        CRITICAL: Never automatically validate unverified LLM observations.
        Only facts explicitly marked `is_validated=True` serve as domain truth.
        """
        now_str = _utc_iso_now()
        f_id = fact_id or f"fact_{abs(hash((category, subject))) % 10000000:07d}"

        semantic_fact = SemanticFact(
            fact_id=f_id,
            category=category.strip(),
            subject=subject.strip(),
            fact=fact.strip(),
            provenance=provenance.strip(),
            is_validated=is_validated,
            metadata=metadata or {},
            created_at=now_str,
            updated_at=now_str,
        )

        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO semantic_facts (
                    fact_id, category, subject, fact, provenance,
                    is_validated, metadata, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(fact_id) DO UPDATE SET
                    category = excluded.category,
                    subject = excluded.subject,
                    fact = excluded.fact,
                    provenance = excluded.provenance,
                    is_validated = excluded.is_validated,
                    metadata = excluded.metadata,
                    updated_at = excluded.updated_at;
                """,
                (
                    semantic_fact.fact_id,
                    semantic_fact.category,
                    semantic_fact.subject,
                    semantic_fact.fact,
                    semantic_fact.provenance,
                    1 if semantic_fact.is_validated else 0,
                    _json_dumps(semantic_fact.metadata),
                    semantic_fact.created_at,
                    semantic_fact.updated_at,
                ),
            )

        return semantic_fact

    def get_semantic_facts(
        self,
        *,
        category: str | None = None,
        subject: str | None = None,
        validated_only: bool = True,
    ) -> list[SemanticFact]:
        """Retrieve domain facts.

        Excludes unvalidated observations by default to protect agent reasoning.
        """
        clauses: list[str] = []
        params: list[Any] = []

        if validated_only:
            clauses.append("is_validated = 1")

        if category:
            clauses.append("category = ?")
            params.append(category.strip())

        if subject:
            clauses.append("subject = ?")
            params.append(subject.strip())

        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        with self.connection() as conn:
            cur = conn.execute(
                f"""
                SELECT fact_id, category, subject, fact, provenance,
                       is_validated, metadata, created_at, updated_at
                FROM semantic_facts
                {where_clause}
                ORDER BY subject ASC, category ASC;
                """,
                params,
            )
            rows = cur.fetchall()
            return [
                SemanticFact(
                    fact_id=r["fact_id"],
                    category=r["category"],
                    subject=r["subject"],
                    fact=r["fact"],
                    provenance=r["provenance"],
                    is_validated=bool(r["is_validated"]),
                    metadata=_json_loads(r["metadata"], {}),
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                )
                for r in rows
            ]

    def update_semantic_fact(
        self,
        fact_id: str,
        *,
        fact: str | None = None,
        is_validated: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SemanticFact | None:
        """Update or validate an existing semantic fact."""
        existing_facts = [f for f in self.get_semantic_facts(validated_only=False) if f.fact_id == fact_id]
        if not existing_facts:
            return None

        target = existing_facts[0]
        now_str = _utc_iso_now()

        new_fact = fact if fact is not None else target.fact
        new_validated = is_validated if is_validated is not None else target.is_validated
        new_meta = metadata if metadata is not None else target.metadata

        with self.transaction() as conn:
            conn.execute(
                """
                UPDATE semantic_facts
                SET fact = ?,
                    is_validated = ?,
                    metadata = ?,
                    updated_at = ?
                WHERE fact_id = ?;
                """,
                (
                    new_fact,
                    1 if new_validated else 0,
                    _json_dumps(new_meta),
                    now_str,
                    fact_id,
                ),
            )

        target.fact = new_fact
        target.is_validated = new_validated
        target.metadata = new_meta
        target.updated_at = now_str
        return target

    def validate_semantic_fact(self, fact_id: str) -> bool:
        """Explicitly validate a semantic fact, admitting it into domain truth."""
        now_str = _utc_iso_now()
        with self.transaction() as conn:
            cur = conn.execute(
                "UPDATE semantic_facts SET is_validated = 1, updated_at = ? WHERE fact_id = ?;",
                (now_str, fact_id),
            )
            return cur.rowcount > 0

    def invalidate_semantic_fact(self, fact_id: str) -> bool:
        """Mark a fact as unvalidated/deprecated so it is excluded from agent execution."""
        now_str = _utc_iso_now()
        with self.transaction() as conn:
            cur = conn.execute(
                "UPDATE semantic_facts SET is_validated = 0, updated_at = ? WHERE fact_id = ?;",
                (now_str, fact_id),
            )
            return cur.rowcount > 0

    def delete_semantic_fact(self, fact_id: str) -> bool:
        """Permanently delete a semantic fact."""
        with self.transaction() as conn:
            cur = conn.execute("DELETE FROM semantic_facts WHERE fact_id = ?;", (fact_id,))
            return cur.rowcount > 0

    # -----------------------------------------------------------------------
    # Skill Registry (Initial Foundation)
    # -----------------------------------------------------------------------

    def register_skill(
        self,
        skill_id: str,
        name: str,
        domain: str,
        version: str,
        file_path: str,
        *,
        description: str = "",
        is_enabled: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record or refresh a discovered skill definition in the registry table."""
        now_str = _utc_iso_now()
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO skill_registry (
                    skill_id, name, domain, version, file_path, description, is_enabled,
                    last_discovered_at, metadata, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(skill_id) DO UPDATE SET
                    name = excluded.name,
                    domain = excluded.domain,
                    version = excluded.version,
                    file_path = excluded.file_path,
                    description = excluded.description,
                    is_enabled = excluded.is_enabled,
                    last_discovered_at = excluded.last_discovered_at,
                    metadata = excluded.metadata,
                    updated_at = excluded.updated_at;
                """,
                (
                    skill_id,
                    name,
                    domain,
                    version,
                    file_path,
                    description,
                    1 if is_enabled else 0,
                    now_str,
                    _json_dumps(metadata or {}),
                    now_str,
                    now_str,
                ),
            )
        return {
            "skill_id": skill_id,
            "name": name,
            "domain": domain,
            "version": version,
            "file_path": file_path,
            "description": description,
            "is_enabled": is_enabled,
        }

    def get_registered_skills(
        self,
        domain: str | None = None,
        *,
        enabled_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Fetch registered skills, optionally filtered by domain and enabled status."""
        clauses: list[str] = []
        params: list[Any] = []
        if domain:
            clauses.append("domain = ?")
            params.append(domain)
        if enabled_only:
            clauses.append("is_enabled = 1")
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"SELECT * FROM skill_registry{where} ORDER BY domain ASC, name ASC;"

        with self.connection() as conn:
            cur = conn.execute(query, params)
            rows = cur.fetchall()
            return [
                {
                    "skill_id": r["skill_id"],
                    "name": r["name"],
                    "domain": r["domain"],
                    "version": r["version"],
                    "file_path": r["file_path"],
                    "description": r["description"],
                    "is_enabled": bool(r["is_enabled"]) if "is_enabled" in r.keys() else True,
                    "last_discovered_at": r["last_discovered_at"] if "last_discovered_at" in r.keys() else None,
                    "metadata": _json_loads(r["metadata"], {}),
                }
                for r in rows
            ]

    def set_skill_enabled(self, skill_id: str, is_enabled: bool) -> bool:
        """Toggle active status of a skill in persistent memory."""
        now_str = _utc_iso_now()
        with self.transaction() as conn:
            cur = conn.execute(
                "UPDATE skill_registry SET is_enabled = ?, updated_at = ? WHERE skill_id = ?;",
                (1 if is_enabled else 0, now_str, skill_id),
            )
            return cur.rowcount > 0

    def get_registered_skill(self, skill_id: str) -> dict[str, Any] | None:
        """Fetch single skill metadata record by skill_id."""
        with self.connection() as conn:
            cur = conn.execute("SELECT * FROM skill_registry WHERE skill_id = ?;", (skill_id,))
            r = cur.fetchone()
            if not r:
                return None
            return {
                "skill_id": r["skill_id"],
                "name": r["name"],
                "domain": r["domain"],
                "version": r["version"],
                "file_path": r["file_path"],
                "description": r["description"],
                "is_enabled": bool(r["is_enabled"]) if "is_enabled" in r.keys() else True,
                "last_discovered_at": r["last_discovered_at"] if "last_discovered_at" in r.keys() else None,
                "metadata": _json_loads(r["metadata"], {}),
            }

    # -----------------------------------------------------------------------
    # Phase 3: Checkpointing & Task Recovery
    # -----------------------------------------------------------------------

    def get_next_checkpoint_sequence(self, task_id: str) -> int:
        """Get the next sequential checkpoint number for a task."""
        with self.connection() as conn:
            cur = conn.execute(
                "SELECT COALESCE(MAX(sequence_number), 0) + 1 FROM task_checkpoints WHERE task_id = ?;",
                (task_id,),
            )
            row = cur.fetchone()
            return int(row[0]) if row else 1

    def save_checkpoint(self, checkpoint: TaskCheckpoint) -> TaskCheckpoint:
        """Persist a cryptographically verified execution snapshot."""
        if not checkpoint.checksum:
            checkpoint.set_checksum()

        step_states_dict = {
            k: (v.model_dump(mode="json") if hasattr(v, "model_dump") else v)
            for k, v in checkpoint.step_states.items()
        }
        pending_approval_json = (
            checkpoint.pending_approval.model_dump(mode="json")
            if checkpoint.pending_approval
            else None
        )

        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO task_checkpoints (
                    checkpoint_id, task_id, sequence_number, checkpoint_type,
                    schema_version, task_status, current_stage, current_step_id,
                    completed_step_ids, pending_step_ids, failed_step_ids,
                    step_states, decision_ids, pending_approval, artifact_ids,
                    metadata, checksum, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id, sequence_number) DO UPDATE SET
                    checkpoint_type = excluded.checkpoint_type,
                    task_status = excluded.task_status,
                    current_stage = excluded.current_stage,
                    current_step_id = excluded.current_step_id,
                    completed_step_ids = excluded.completed_step_ids,
                    pending_step_ids = excluded.pending_step_ids,
                    failed_step_ids = excluded.failed_step_ids,
                    step_states = excluded.step_states,
                    decision_ids = excluded.decision_ids,
                    pending_approval = excluded.pending_approval,
                    artifact_ids = excluded.artifact_ids,
                    metadata = excluded.metadata,
                    checksum = excluded.checksum;
                """,
                (
                    checkpoint.checkpoint_id,
                    checkpoint.task_id,
                    checkpoint.sequence_number,
                    checkpoint.checkpoint_type.value,
                    checkpoint.schema_version,
                    checkpoint.task_status.value,
                    checkpoint.current_stage,
                    checkpoint.current_step_id,
                    _json_dumps(checkpoint.completed_step_ids),
                    _json_dumps(checkpoint.pending_step_ids),
                    _json_dumps(checkpoint.failed_step_ids),
                    _json_dumps(step_states_dict),
                    _json_dumps(checkpoint.decision_ids),
                    _json_dumps(pending_approval_json) if pending_approval_json else None,
                    _json_dumps(checkpoint.artifact_ids),
                    _json_dumps(checkpoint.metadata),
                    checkpoint.checksum,
                    checkpoint.created_at,
                ),
            )
        return checkpoint

    def _row_to_checkpoint(self, r: sqlite3.Row) -> TaskCheckpoint:
        raw_step_states = _json_loads(r["step_states"], {})
        step_states: dict[str, StepExecutionSnapshot] = {}
        for k, v in raw_step_states.items():
            if isinstance(v, dict):
                step_states[k] = StepExecutionSnapshot.model_validate(v)

        raw_pending = _json_loads(r["pending_approval"])
        pending_approval = (
            PendingApprovalSnapshot.model_validate(raw_pending)
            if raw_pending and isinstance(raw_pending, dict)
            else None
        )

        return TaskCheckpoint(
            checkpoint_id=r["checkpoint_id"],
            task_id=r["task_id"],
            sequence_number=int(r["sequence_number"]),
            checkpoint_type=CheckpointType(r["checkpoint_type"]),
            schema_version=int(r["schema_version"]),
            task_status=TaskStatus(r["task_status"]),
            current_stage=r["current_stage"] or "",
            current_step_id=r["current_step_id"],
            completed_step_ids=_json_loads(r["completed_step_ids"], []),
            pending_step_ids=_json_loads(r["pending_step_ids"], []),
            failed_step_ids=_json_loads(r["failed_step_ids"], []),
            step_states=step_states,
            decision_ids=_json_loads(r["decision_ids"], []),
            pending_approval=pending_approval,
            artifact_ids=_json_loads(r["artifact_ids"], []),
            metadata=_json_loads(r["metadata"], {}),
            checksum=r["checksum"],
            created_at=r["created_at"],
        )

    def get_checkpoint(self, checkpoint_id: str) -> TaskCheckpoint | None:
        """Fetch a specific checkpoint snapshot by ID."""
        with self.connection() as conn:
            cur = conn.execute(
                "SELECT * FROM task_checkpoints WHERE checkpoint_id = ?;",
                (checkpoint_id,),
            )
            row = cur.fetchone()
            return self._row_to_checkpoint(row) if row else None

    def get_latest_checkpoint(self, task_id: str) -> TaskCheckpoint | None:
        """Fetch the most recently recorded checkpoint for a task."""
        with self.connection() as conn:
            cur = conn.execute(
                "SELECT * FROM task_checkpoints WHERE task_id = ? ORDER BY sequence_number DESC LIMIT 1;",
                (task_id,),
            )
            row = cur.fetchone()
            return self._row_to_checkpoint(row) if row else None

    def get_checkpoint_history(self, task_id: str) -> list[TaskCheckpoint]:
        """Fetch all checkpoints for a task ordered from earliest to newest."""
        with self.connection() as conn:
            cur = conn.execute(
                "SELECT * FROM task_checkpoints WHERE task_id = ? ORDER BY sequence_number ASC;",
                (task_id,),
            )
            rows = cur.fetchall()
            return [self._row_to_checkpoint(r) for r in rows]

    # -----------------------------------------------------------------------
    # Recovery Attempts Persistence
    # -----------------------------------------------------------------------

    def save_recovery_attempt(self, attempt: RecoveryAttemptRecord) -> RecoveryAttemptRecord:
        """Persist a task recovery attempt log."""
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO recovery_attempts (
                    attempt_id, task_id, checkpoint_id, policy, status,
                    failure_reason, details, created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    attempt.attempt_id,
                    attempt.task_id,
                    attempt.checkpoint_id,
                    attempt.policy.value,
                    attempt.status.value,
                    attempt.failure_reason,
                    _json_dumps(attempt.details),
                    attempt.created_at,
                    attempt.completed_at,
                ),
            )
        return attempt

    def update_recovery_attempt(
        self,
        attempt_id: str,
        status: RecoveryStatus | str,
        *,
        failure_reason: str | None = None,
        completed_at: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Update an existing recovery attempt outcome."""
        st_val = status.value if isinstance(status, RecoveryStatus) else str(status)
        now_str = completed_at or _utc_iso_now()
        with self.transaction() as conn:
            conn.execute(
                """
                UPDATE recovery_attempts
                SET status = ?,
                    failure_reason = COALESCE(?, failure_reason),
                    completed_at = ?,
                    details = CASE WHEN ? THEN ? ELSE details END
                WHERE attempt_id = ?;
                """,
                (
                    st_val,
                    failure_reason,
                    now_str,
                    details is not None,
                    _json_dumps(details) if details else None,
                    attempt_id,
                ),
            )

    def get_recovery_history(self, task_id: str) -> list[RecoveryAttemptRecord]:
        """Fetch all recovery attempts recorded for a task."""
        with self.connection() as conn:
            cur = conn.execute(
                "SELECT * FROM recovery_attempts WHERE task_id = ? ORDER BY created_at ASC;",
                (task_id,),
            )
            rows = cur.fetchall()
            return [
                RecoveryAttemptRecord(
                    attempt_id=r["attempt_id"],
                    task_id=r["task_id"],
                    checkpoint_id=r["checkpoint_id"],
                    policy=RecoveryPolicy(r["policy"]),
                    status=RecoveryStatus(r["status"]),
                    failure_reason=r["failure_reason"],
                    details=_json_loads(r["details"], {}),
                    created_at=r["created_at"],
                    completed_at=r["completed_at"],
                )
                for r in rows
            ]

    # -----------------------------------------------------------------------
    # Interrupted Operations & Idempotency
    # -----------------------------------------------------------------------

    def _make_op_key(self, task_id: str, step_id: str | None, operation_type: str) -> str:
        s_id = step_id or "root"
        return f"{task_id}:{s_id}:{operation_type.strip().lower()}"

    def record_operation_started(
        self,
        task_id: str,
        operation_type: str,
        *,
        step_id: str | None = None,
        operation_key: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> InterruptedOperationRecord:
        """Record the start of an execution operation."""
        key = operation_key or self._make_op_key(task_id, step_id, operation_type)
        now_str = _utc_iso_now()
        clean_payload = mask_sensitive_data(payload or {})
        op = InterruptedOperationRecord(
            task_id=task_id,
            step_id=step_id,
            operation_type=operation_type,
            operation_key=key,
            status=OperationStatus.STARTED,
            payload=clean_payload,
            created_at=now_str,
            updated_at=now_str,
        )
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO interrupted_operations (
                    operation_id, task_id, step_id, operation_type, operation_key,
                    status, error, payload, result_summary, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id, operation_key) DO UPDATE SET
                    status = excluded.status,
                    error = NULL,
                    payload = excluded.payload,
                    updated_at = excluded.updated_at;
                """,
                (
                    op.operation_id,
                    op.task_id,
                    op.step_id,
                    op.operation_type,
                    op.operation_key,
                    op.status.value,
                    None,
                    _json_dumps(op.payload),
                    None,
                    op.created_at,
                    op.updated_at,
                ),
            )
        return op

    def record_operation_completed(
        self,
        task_id: str,
        operation_type: str,
        *,
        step_id: str | None = None,
        operation_key: str | None = None,
        result_summary: str | None = None,
    ) -> InterruptedOperationRecord:
        """Mark an execution operation as successfully finished."""
        key = operation_key or self._make_op_key(task_id, step_id, operation_type)
        now_str = _utc_iso_now()
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO interrupted_operations (
                    operation_id, task_id, step_id, operation_type, operation_key,
                    status, result_summary, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id, operation_key) DO UPDATE SET
                    status = 'COMPLETED',
                    result_summary = excluded.result_summary,
                    error = NULL,
                    updated_at = excluded.updated_at;
                """,
                (
                    f"op_{uuid.uuid4().hex[:8]}",
                    task_id,
                    step_id,
                    operation_type,
                    key,
                    OperationStatus.COMPLETED.value,
                    result_summary,
                    now_str,
                    now_str,
                ),
            )
        ret = self.get_operation(task_id, key)
        if ret:
            return ret
        return InterruptedOperationRecord(
            task_id=task_id,
            step_id=step_id,
            operation_type=operation_type,
            operation_key=key,
            status=OperationStatus.COMPLETED,
            result_summary=result_summary,
            created_at=now_str,
            updated_at=now_str,
        )

    def record_operation_failed(
        self,
        task_id: str,
        operation_type: str,
        *,
        step_id: str | None = None,
        operation_key: str | None = None,
        error: str = "",
    ) -> InterruptedOperationRecord:
        """Mark an execution operation as failed."""
        key = operation_key or self._make_op_key(task_id, step_id, operation_type)
        now_str = _utc_iso_now()
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO interrupted_operations (
                    operation_id, task_id, step_id, operation_type, operation_key,
                    status, error, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id, operation_key) DO UPDATE SET
                    status = 'FAILED',
                    error = excluded.error,
                    updated_at = excluded.updated_at;
                """,
                (
                    f"op_{uuid.uuid4().hex[:8]}",
                    task_id,
                    step_id,
                    operation_type,
                    key,
                    OperationStatus.FAILED.value,
                    error,
                    now_str,
                    now_str,
                ),
            )
        ret = self.get_operation(task_id, key)
        if ret:
            return ret
        return InterruptedOperationRecord(
            task_id=task_id,
            step_id=step_id,
            operation_type=operation_type,
            operation_key=key,
            status=OperationStatus.FAILED,
            error=error,
            created_at=now_str,
            updated_at=now_str,
        )

    def record_operation_interrupted(
        self,
        task_id: str,
        operation_type: str,
        *,
        step_id: str | None = None,
        operation_key: str | None = None,
        error: str = "",
    ) -> InterruptedOperationRecord:
        """Flag an execution operation as interrupted during recovery reconciliation."""
        key = operation_key or self._make_op_key(task_id, step_id, operation_type)
        now_str = _utc_iso_now()
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO interrupted_operations (
                    operation_id, task_id, step_id, operation_type, operation_key,
                    status, error, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id, operation_key) DO UPDATE SET
                    status = 'INTERRUPTED',
                    error = excluded.error,
                    updated_at = excluded.updated_at;
                """,
                (
                    f"op_{uuid.uuid4().hex[:8]}",
                    task_id,
                    step_id,
                    operation_type,
                    key,
                    OperationStatus.INTERRUPTED.value,
                    error,
                    now_str,
                    now_str,
                ),
            )
        ret = self.get_operation(task_id, key)
        if ret:
            return ret
        return InterruptedOperationRecord(
            task_id=task_id,
            step_id=step_id,
            operation_type=operation_type,
            operation_key=key,
            status=OperationStatus.INTERRUPTED,
            error=error,
            created_at=now_str,
            updated_at=now_str,
        )

    def get_operation(self, task_id: str, operation_key: str) -> InterruptedOperationRecord | None:
        """Fetch operation status by unique task and operation key."""
        with self.connection() as conn:
            cur = conn.execute(
                "SELECT * FROM interrupted_operations WHERE task_id = ? AND operation_key = ?;",
                (task_id, operation_key),
            )
            r = cur.fetchone()
            if not r:
                return None
            return InterruptedOperationRecord(
                operation_id=r["operation_id"],
                task_id=r["task_id"],
                step_id=r["step_id"],
                operation_type=r["operation_type"],
                operation_key=r["operation_key"],
                status=OperationStatus(r["status"]),
                error=r["error"],
                payload=_json_loads(r["payload"], {}),
                result_summary=r["result_summary"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )

    def get_interrupted_operations(self, task_id: str) -> list[InterruptedOperationRecord]:
        """Fetch all incomplete or interrupted operations for a task."""
        with self.connection() as conn:
            cur = conn.execute(
                """
                SELECT * FROM interrupted_operations
                WHERE task_id = ? AND status IN ('STARTED', 'INTERRUPTED', 'OUTCOME_UNKNOWN')
                ORDER BY updated_at ASC;
                """,
                (task_id,),
            )
            rows = cur.fetchall()
            return [
                InterruptedOperationRecord(
                    operation_id=r["operation_id"],
                    task_id=r["task_id"],
                    step_id=r["step_id"],
                    operation_type=r["operation_type"],
                    operation_key=r["operation_key"],
                    status=OperationStatus(r["status"]),
                    error=r["error"],
                    payload=_json_loads(r["payload"], {}),
                    result_summary=r["result_summary"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                )
                for r in rows
            ]

