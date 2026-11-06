"""Persistent SQLite Repository for Agent Working, Episodic, and Semantic Memory.

Manages dedicated `data/agent_memory.db` with thread-safe connections,
versioned schema migrations, strict parameterized queries, and ACID transactions.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Sequence

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

    def initialize_schema(self) -> int:
        """Run migrations and configure WAL mode."""
        with self.connection() as conn:
            # Enable WAL mode for high concurrency
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            return apply_migrations(conn)

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
            conn.execute(
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
            conn.execute(
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
        decision = TaskDecision(
            task_id=task_id,
            step_id=step_id,
            decision_type=decision_type,
            summary=summary,
            rationale=rationale,
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
        record = TaskToolCallRecord(
            task_id=task_id,
            step_id=step_id,
            tool_name=tool_name,
            arguments=arguments or {},
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
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record a discovered skill definition in the registry table."""
        now_str = _utc_iso_now()
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO skill_registry (
                    skill_id, name, domain, version, file_path, description, metadata, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(skill_id) DO UPDATE SET
                    name = excluded.name,
                    domain = excluded.domain,
                    version = excluded.version,
                    file_path = excluded.file_path,
                    description = excluded.description,
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
        }

    def get_registered_skills(self, domain: str | None = None) -> list[dict[str, Any]]:
        """Fetch registered skills, optionally filtered by domain."""
        query = "SELECT * FROM skill_registry"
        params: list[Any] = []
        if domain:
            query += " WHERE domain = ?"
            params.append(domain)
        query += " ORDER BY domain ASC, name ASC;"

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
                    "metadata": _json_loads(r["metadata"], {}),
                }
                for r in rows
            ]

