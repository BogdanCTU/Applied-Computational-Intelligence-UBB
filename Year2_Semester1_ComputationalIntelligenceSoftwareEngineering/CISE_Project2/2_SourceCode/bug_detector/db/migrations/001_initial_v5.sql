-- CISE Project v5.0.0 Initial SQLite Schema
-- Normalized, content-addressed source storage with strict provenance and foreign keys.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_id TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS repositories (
    repository_id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    repository_url TEXT NOT NULL,
    source_origin TEXT NOT NULL,
    default_branch TEXT,
    stars INTEGER DEFAULT 0,
    language TEXT NOT NULL DEFAULT 'C#',
    local_path TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS commits (
    commit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id TEXT NOT NULL REFERENCES repositories(repository_id) ON DELETE CASCADE,
    commit_sha TEXT NOT NULL,
    parent_commit_sha TEXT,
    commit_message TEXT,
    author_date TEXT,
    is_bug_fix INTEGER NOT NULL DEFAULT 0 CHECK (is_bug_fix IN (0, 1)),
    classification_reason TEXT,
    issue_or_pr_ref TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (repository_id, commit_sha)
);

CREATE TABLE IF NOT EXISTS source_blobs (
    source_hash TEXT PRIMARY KEY,
    raw_source TEXT NOT NULL,
    normalized_source TEXT,
    byte_length INTEGER NOT NULL,
    line_count INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS source_files (
    source_file_id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id TEXT NOT NULL REFERENCES repositories(repository_id) ON DELETE CASCADE,
    commit_sha TEXT,
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL REFERENCES source_blobs(source_hash),
    has_syntax_errors INTEGER NOT NULL DEFAULT 0 CHECK (has_syntax_errors IN (0, 1)),
    syntax_error_count INTEGER NOT NULL DEFAULT 0,
    semantic_model_available INTEGER NOT NULL DEFAULT 0 CHECK (semantic_model_available IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (repository_id, commit_sha, file_path, file_hash)
);

CREATE TABLE IF NOT EXISTS bug_fix_records (
    bug_fix_id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id TEXT NOT NULL REFERENCES repositories(repository_id) ON DELETE CASCADE,
    commit_sha TEXT NOT NULL,
    parent_commit_sha TEXT,
    file_path TEXT NOT NULL,
    bug_type TEXT NOT NULL,
    severity TEXT,
    bug_fix_reference TEXT,
    source_origin TEXT NOT NULL,
    metadata_json TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS methods (
    method_id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id TEXT NOT NULL REFERENCES repositories(repository_id) ON DELETE CASCADE,
    source_file_id INTEGER REFERENCES source_files(source_file_id) ON DELETE SET NULL,
    file_path TEXT NOT NULL,
    class_name TEXT NOT NULL,
    type_kind TEXT NOT NULL DEFAULT 'class',
    method_name TEXT NOT NULL,
    method_signature TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    is_constructor INTEGER NOT NULL DEFAULT 0 CHECK (is_constructor IN (0, 1)),
    is_static INTEGER NOT NULL DEFAULT 0 CHECK (is_static IN (0, 1)),
    is_async INTEGER NOT NULL DEFAULT 0 CHECK (is_async IN (0, 1)),
    is_generic INTEGER NOT NULL DEFAULT 0 CHECK (is_generic IN (0, 1)),
    is_expression_bodied INTEGER NOT NULL DEFAULT 0 CHECK (is_expression_bodied IN (0, 1)),
    source_hash TEXT NOT NULL REFERENCES source_blobs(source_hash),
    structural_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS dataset_versions (
    dataset_version TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    total_records_collected INTEGER NOT NULL DEFAULT 0,
    valid_records INTEGER NOT NULL DEFAULT 0,
    invalid_records INTEGER NOT NULL DEFAULT 0,
    bug_count INTEGER NOT NULL DEFAULT 0,
    clean_count INTEGER NOT NULL DEFAULT 0,
    repository_count INTEGER NOT NULL DEFAULT 0,
    dataset_sha256 TEXT,
    parquet_path TEXT,
    csv_path TEXT,
    audit_report_path TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS dataset_samples (
    sample_id TEXT PRIMARY KEY,
    dataset_version TEXT NOT NULL REFERENCES dataset_versions(dataset_version) ON DELETE CASCADE,
    repository_id TEXT NOT NULL REFERENCES repositories(repository_id),
    method_id INTEGER REFERENCES methods(method_id) ON DELETE SET NULL,
    bug_fix_id INTEGER REFERENCES bug_fix_records(bug_fix_id) ON DELETE SET NULL,
    pair_id TEXT,
    commit_sha TEXT NOT NULL,
    parent_commit_sha TEXT,
    commit_timestamp TEXT,
    file_path TEXT NOT NULL,
    class_name TEXT NOT NULL,
    method_name TEXT NOT NULL,
    method_signature TEXT NOT NULL,
    source_hash TEXT NOT NULL REFERENCES source_blobs(source_hash),
    structural_hash TEXT NOT NULL,
    label INTEGER NOT NULL CHECK (label IN (0, 1)),
    label_source TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    bug_type TEXT NOT NULL,
    bug_fix_reference TEXT,
    extraction_mode TEXT NOT NULL DEFAULT 'file',
    split_partition TEXT NOT NULL DEFAULT 'unassigned',
    collection_timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dataset_exclusions (
    exclusion_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_version TEXT NOT NULL REFERENCES dataset_versions(dataset_version) ON DELETE CASCADE,
    source_origin TEXT NOT NULL,
    repository_id TEXT,
    external_ref TEXT,
    file_path TEXT,
    method_name TEXT,
    exclusion_reason TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS feature_extractions (
    sample_id TEXT PRIMARY KEY REFERENCES dataset_samples(sample_id) ON DELETE CASCADE,
    extractor_version TEXT NOT NULL DEFAULT '1.0.0',
    semantic_model_available INTEGER NOT NULL DEFAULT 0 CHECK (semantic_model_available IN (0, 1)),
    cfg_available INTEGER NOT NULL DEFAULT 0 CHECK (cfg_available IN (0, 1)),
    dfg_available INTEGER NOT NULL DEFAULT 0 CHECK (dfg_available IN (0, 1)),
    extraction_failed INTEGER NOT NULL DEFAULT 0 CHECK (extraction_failed IN (0, 1)),
    tokens_json TEXT NOT NULL,
    api_calls_json TEXT NOT NULL,
    lexical_json TEXT NOT NULL,
    ast_json TEXT NOT NULL,
    cfg_json TEXT NOT NULL,
    dfg_json TEXT NOT NULL,
    structural_json TEXT NOT NULL,
    warnings_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS training_experiments (
    experiment_id TEXT PRIMARY KEY,
    dataset_version TEXT NOT NULL REFERENCES dataset_versions(dataset_version),
    experiment_code TEXT NOT NULL,
    algorithm TEXT NOT NULL,
    feature_groups_json TEXT NOT NULL,
    hyperparameters_json TEXT NOT NULL,
    cv_metrics_json TEXT NOT NULL,
    test_metrics_json TEXT NOT NULL,
    hard_negative_metrics_json TEXT,
    temporal_metrics_json TEXT,
    duration_seconds REAL NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('COMPLETED', 'FAILED', 'RUNNING')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS model_versions (
    model_version TEXT PRIMARY KEY,
    experiment_id TEXT REFERENCES training_experiments(experiment_id) ON DELETE SET NULL,
    dataset_version TEXT NOT NULL REFERENCES dataset_versions(dataset_version),
    dataset_sha256 TEXT,
    algorithm TEXT NOT NULL,
    experiment_code TEXT NOT NULL,
    feature_groups_json TEXT NOT NULL,
    feature_schema_json TEXT NOT NULL,
    hyperparameters_json TEXT NOT NULL,
    threshold_low REAL NOT NULL,
    threshold_center REAL NOT NULL,
    threshold_high REAL NOT NULL,
    calibration_method TEXT NOT NULL,
    artifact_path TEXT NOT NULL,
    manifest_path TEXT NOT NULL,
    dependency_versions_json TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 0 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS evaluation_results (
    evaluation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_version TEXT NOT NULL REFERENCES model_versions(model_version) ON DELETE CASCADE,
    evaluation_split TEXT NOT NULL,
    sample_count INTEGER NOT NULL,
    bug_count INTEGER NOT NULL,
    clean_count INTEGER NOT NULL,
    repository_count INTEGER NOT NULL,
    accuracy REAL,
    precision_score REAL,
    recall_score REAL,
    f1_score REAL,
    specificity REAL,
    fpr REAL,
    fnr REAL,
    roc_auc REAL,
    pr_auc REAL,
    brier_score REAL,
    uncertain_count INTEGER NOT NULL DEFAULT 0,
    uncertain_rate REAL NOT NULL DEFAULT 0.0,
    selective_precision REAL,
    selective_recall REAL,
    selective_f1 REAL,
    selective_fpr REAL,
    confusion_matrix_json TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS detection_runs (
    run_id TEXT PRIMARY KEY,
    model_version TEXT NOT NULL REFERENCES model_versions(model_version),
    input_mode TEXT NOT NULL CHECK (input_mode IN ('paste', 'upload', 'cli')),
    file_name TEXT NOT NULL,
    source_hash TEXT NOT NULL REFERENCES source_blobs(source_hash),
    analysis_status TEXT NOT NULL CHECK (analysis_status IN ('OK', 'ANALYSIS_ERROR', 'NO_METHODS')),
    syntax_error_count INTEGER NOT NULL DEFAULT 0,
    method_count INTEGER NOT NULL DEFAULT 0,
    bug_count INTEGER NOT NULL DEFAULT 0,
    clean_count INTEGER NOT NULL DEFAULT 0,
    uncertain_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS prediction_results (
    prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES detection_runs(run_id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    class_name TEXT NOT NULL,
    method_name TEXT NOT NULL,
    method_signature TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    classification TEXT NOT NULL CHECK (classification IN ('BUG', 'CLEAN', 'UNCERTAIN', 'ANALYSIS_ERROR')),
    probability REAL,
    threshold_low REAL NOT NULL,
    threshold_center REAL NOT NULL,
    threshold_high REAL NOT NULL,
    uncertainty_status TEXT NOT NULL,
    feature_extraction_status TEXT NOT NULL,
    suspicious_rank INTEGER,
    historical_match_sample_id TEXT,
    historical_provenance_json TEXT,
    local_evidence_json TEXT,
    method_source_hash TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_samples_dataset_repo ON dataset_samples(dataset_version, repository_id);
CREATE INDEX IF NOT EXISTS idx_samples_label ON dataset_samples(label, label_source, verification_status);
CREATE INDEX IF NOT EXISTS idx_samples_pair ON dataset_samples(pair_id);
CREATE INDEX IF NOT EXISTS idx_samples_source_hash ON dataset_samples(source_hash);
CREATE INDEX IF NOT EXISTS idx_samples_partition ON dataset_samples(split_partition);
CREATE INDEX IF NOT EXISTS idx_exclusions_dataset_reason ON dataset_exclusions(dataset_version, exclusion_reason);
CREATE INDEX IF NOT EXISTS idx_commits_repo ON commits(repository_id, is_bug_fix);
CREATE INDEX IF NOT EXISTS idx_eval_model_split ON evaluation_results(model_version, evaluation_split);
CREATE INDEX IF NOT EXISTS idx_predictions_run ON prediction_results(run_id, classification);
