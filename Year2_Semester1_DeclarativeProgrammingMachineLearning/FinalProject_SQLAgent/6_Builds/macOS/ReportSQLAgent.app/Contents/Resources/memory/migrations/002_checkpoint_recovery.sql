-- Migration 002: Checkpointing, Task Recovery, and Idempotent Operations
-- Enforces foreign keys, indexing for fast sequence retrieval, and crash recovery tables.

CREATE TABLE IF NOT EXISTS task_checkpoints (
    checkpoint_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES task_runs(task_id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL,
    checkpoint_type TEXT NOT NULL,
    schema_version INTEGER NOT NULL DEFAULT 1,
    task_status TEXT NOT NULL,
    current_stage TEXT NOT NULL DEFAULT '',
    current_step_id TEXT,
    completed_step_ids TEXT NOT NULL DEFAULT '[]',
    pending_step_ids TEXT NOT NULL DEFAULT '[]',
    failed_step_ids TEXT NOT NULL DEFAULT '[]',
    step_states TEXT NOT NULL DEFAULT '{}',
    decision_ids TEXT NOT NULL DEFAULT '[]',
    pending_approval TEXT,
    artifact_ids TEXT NOT NULL DEFAULT '[]',
    metadata TEXT NOT NULL DEFAULT '{}',
    checksum TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    CONSTRAINT uq_task_checkpoints_seq UNIQUE (task_id, sequence_number)
);

CREATE INDEX IF NOT EXISTS idx_checkpoints_task_id ON task_checkpoints(task_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_task_seq ON task_checkpoints(task_id, sequence_number);
CREATE INDEX IF NOT EXISTS idx_checkpoints_type ON task_checkpoints(checkpoint_type);

CREATE TABLE IF NOT EXISTS recovery_attempts (
    attempt_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES task_runs(task_id) ON DELETE CASCADE,
    checkpoint_id TEXT REFERENCES task_checkpoints(checkpoint_id) ON DELETE SET NULL,
    policy TEXT NOT NULL,
    status TEXT NOT NULL,
    failure_reason TEXT,
    details TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_recovery_task_id ON recovery_attempts(task_id);
CREATE INDEX IF NOT EXISTS idx_recovery_status ON recovery_attempts(status);

CREATE TABLE IF NOT EXISTS interrupted_operations (
    operation_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES task_runs(task_id) ON DELETE CASCADE,
    step_id TEXT,
    operation_type TEXT NOT NULL,
    operation_key TEXT NOT NULL,
    status TEXT NOT NULL,
    error TEXT,
    payload TEXT NOT NULL DEFAULT '{}',
    result_summary TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    CONSTRAINT uq_task_operation_key UNIQUE (task_id, operation_key)
);

CREATE INDEX IF NOT EXISTS idx_interrupted_ops_task ON interrupted_operations(task_id);
CREATE INDEX IF NOT EXISTS idx_interrupted_ops_status ON interrupted_operations(task_id, status);
CREATE INDEX IF NOT EXISTS idx_interrupted_ops_key ON interrupted_operations(operation_key);

