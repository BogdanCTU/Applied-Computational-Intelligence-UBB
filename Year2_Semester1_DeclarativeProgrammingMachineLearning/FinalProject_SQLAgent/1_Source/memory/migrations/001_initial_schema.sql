-- Migration 001: Initial schema for Persistent SQLite Agent Memory

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- Task Runs (Working & Episodic root)
CREATE TABLE IF NOT EXISTS task_runs (
    task_id TEXT PRIMARY KEY,
    user_request TEXT NOT NULL,
    status TEXT NOT NULL,
    current_step TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    error TEXT,
    metadata JSON
);

CREATE INDEX IF NOT EXISTS idx_task_runs_status ON task_runs(status);
CREATE INDEX IF NOT EXISTS idx_task_runs_created_at ON task_runs(created_at);

-- Task Steps (DAG Execution Units)
CREATE TABLE IF NOT EXISTS task_steps (
    step_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    step_order INTEGER NOT NULL DEFAULT 0,
    name TEXT NOT NULL,
    description TEXT,
    required_skill TEXT,
    required_tools JSON,
    dependencies JSON,
    optional_dependencies JSON,
    status TEXT NOT NULL,
    output_reference TEXT,
    error TEXT,
    metadata JSON,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES task_runs(task_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_task_steps_task_id ON task_steps(task_id);
CREATE INDEX IF NOT EXISTS idx_task_steps_status ON task_steps(status);

-- Task Plans (Associated Plan Meta)
CREATE TABLE IF NOT EXISTS task_plans (
    plan_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL UNIQUE,
    rationale TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES task_runs(task_id) ON DELETE CASCADE
);

-- Task Decisions (Reasoning & Strategic Choices)
CREATE TABLE IF NOT EXISTS task_decisions (
    decision_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    step_id TEXT,
    decision_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    rationale TEXT,
    metadata JSON,
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES task_runs(task_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_task_decisions_task_id ON task_decisions(task_id);

-- Task Tool Calls (Tool Invocation Audits)
CREATE TABLE IF NOT EXISTS task_tool_calls (
    call_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    step_id TEXT,
    tool_name TEXT NOT NULL,
    arguments JSON,
    result_summary TEXT,
    duration_ms REAL,
    status TEXT NOT NULL,
    error TEXT,
    metadata JSON,
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES task_runs(task_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_task_tool_calls_task_id ON task_tool_calls(task_id);

-- Task Artifacts (Report PDF/CSV & Dataset References)
CREATE TABLE IF NOT EXISTS task_artifacts (
    artifact_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    step_id TEXT,
    artifact_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size_bytes INTEGER,
    checksum TEXT,
    metadata JSON,
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES task_runs(task_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_task_artifacts_task_id ON task_artifacts(task_id);

-- Semantic Facts (Validated Domain Knowledge)
CREATE TABLE IF NOT EXISTS semantic_facts (
    fact_id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    subject TEXT NOT NULL,
    fact TEXT NOT NULL,
    provenance TEXT NOT NULL,
    is_validated INTEGER NOT NULL DEFAULT 1,
    metadata JSON,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_semantic_facts_category ON semantic_facts(category);
CREATE INDEX IF NOT EXISTS idx_semantic_facts_subject ON semantic_facts(subject);
CREATE INDEX IF NOT EXISTS idx_semantic_facts_validated ON semantic_facts(is_validated);

-- Skill Registry (Metadata for discovered skills)
CREATE TABLE IF NOT EXISTS skill_registry (
    skill_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    domain TEXT NOT NULL,
    version TEXT NOT NULL,
    file_path TEXT NOT NULL,
    description TEXT,
    metadata JSON,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_skill_registry_domain ON skill_registry(domain);

