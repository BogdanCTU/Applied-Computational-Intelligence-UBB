"""SQLite schema definitions for C# bug detection system."""

CREATE_TABLES_SQL = """
-- Repositories metadata table
CREATE TABLE IF NOT EXISTS repositories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    owner TEXT NOT NULL,
    url TEXT NOT NULL,
    description TEXT,
    license TEXT,
    default_branch TEXT DEFAULT 'main',
    stars INTEGER DEFAULT 0,
    forks INTEGER DEFAULT 0,
    size_kb INTEGER DEFAULT 0,
    is_cloned INTEGER DEFAULT 0,
    local_path TEXT,
    status TEXT DEFAULT 'registered', -- registered, cloning, cloned, failed, updated
    last_sync_at TIMESTAMP,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Commits metadata table
CREATE TABLE IF NOT EXISTS commits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    commit_sha TEXT NOT NULL,
    parent_sha TEXT,          -- First parent or primary parent
    parent_shas TEXT,         -- Comma-separated or JSON list of all parents
    author_name TEXT,
    author_email TEXT,
    committed_date TIMESTAMP, -- Author timestamp
    committer_date TIMESTAMP, -- Committer timestamp
    message TEXT,
    files_changed_count INTEGER DEFAULT 0,
    insertions INTEGER DEFAULT 0,
    deletions INTEGER DEFAULT 0,
    modifies_csharp INTEGER DEFAULT 0,
    is_bug_fix INTEGER DEFAULT 0,
    bug_fix_confidence REAL DEFAULT 0.0,
    bug_fix_evidence TEXT,
    analyzed_at TIMESTAMP,
    UNIQUE(repository_id, commit_sha)
);

-- Commit File Modifications Table
CREATE TABLE IF NOT EXISTS commit_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    commit_id INTEGER NOT NULL REFERENCES commits(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    change_type TEXT NOT NULL, -- A (added), M (modified), D (deleted), R (renamed)
    insertions INTEGER DEFAULT 0,
    deletions INTEGER DEFAULT 0,
    is_csharp INTEGER DEFAULT 0,
    UNIQUE(commit_id, file_path)
);

-- SZZ Bug-Inducing Commit (BIC) Traceability Table
CREATE TABLE IF NOT EXISTS szz_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    fixing_commit_sha TEXT NOT NULL,
    inducing_commit_sha TEXT NOT NULL,
    file_path TEXT NOT NULL,
    deleted_line_number INTEGER,
    deleted_line_content TEXT,
    inducing_line_number INTEGER,
    confidence REAL DEFAULT 1.0,
    evidence TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(repository_id, fixing_commit_sha, inducing_commit_sha, file_path, deleted_line_number)
);

-- Methods catalogue
CREATE TABLE IF NOT EXISTS methods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    class_name TEXT NOT NULL,
    method_name TEXT NOT NULL,
    method_signature TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    is_static INTEGER DEFAULT 0,
    is_async INTEGER DEFAULT 0,
    is_generic INTEGER DEFAULT 0,
    visibility TEXT DEFAULT 'private',
    UNIQUE(repository_id, file_path, class_name, method_signature)
);

-- Method Observations with Defect Labels
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    method_id INTEGER REFERENCES methods(id) ON DELETE SET NULL,
    repository_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    commit_sha TEXT NOT NULL,
    parent_sha TEXT,
    bug_fix_commit_sha TEXT,
    file_path TEXT NOT NULL,
    class_name TEXT NOT NULL,
    method_name TEXT NOT NULL,
    method_signature TEXT NOT NULL,
    source_code TEXT NOT NULL,
    corrected_code TEXT,
    label INTEGER NOT NULL, -- 1: buggy, 0: candidate non-buggy, -1: uncertain
    label_confidence REAL DEFAULT 1.0,
    evidence_category TEXT NOT NULL, -- e.g. 'szz_bic', 'stable_version', 'manual_audit', 'ambiguous'
    bug_fixing_commit_message TEXT,
    issue_or_pr_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(repository_id, commit_sha, file_path, method_signature, label)
);

-- Static Code Features Extracted via Roslyn
CREATE TABLE IF NOT EXISTS features (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    observation_id INTEGER UNIQUE NOT NULL REFERENCES observations(id) ON DELETE CASCADE,
    loc INTEGER,
    method_length INTEGER,
    num_statements INTEGER,
    num_parameters INTEGER,
    num_local_vars INTEGER,
    num_returns INTEGER,
    num_assignments INTEGER,
    cyclomatic_complexity INTEGER,
    max_nesting_depth INTEGER,
    num_conditionals INTEGER,
    num_boolean_expressions INTEGER,
    num_logical_operators INTEGER,
    num_loops INTEGER,
    num_try_catch INTEGER,
    num_throw INTEGER,
    num_method_calls INTEGER,
    num_field_references INTEGER,
    num_property_references INTEGER,
    is_static INTEGER DEFAULT 0,
    is_async INTEGER DEFAULT 0,
    is_generic INTEGER DEFAULT 0,
    num_comments INTEGER DEFAULT 0,
    num_lambdas INTEGER DEFAULT 0,
    num_linq_operations INTEGER DEFAULT 0,
    raw_metrics_json TEXT,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dataset Generation Runs (Versioned Datasets)
CREATE TABLE IF NOT EXISTS datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    version TEXT NOT NULL,
    description TEXT,
    total_count INTEGER NOT NULL DEFAULT 0,
    buggy_count INTEGER NOT NULL DEFAULT 0,
    non_buggy_count INTEGER NOT NULL DEFAULT 0,
    uncertain_count INTEGER NOT NULL DEFAULT 0,
    feature_names TEXT NOT NULL, -- JSON list of features included
    export_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Association between Dataset and Observations
CREATE TABLE IF NOT EXISTS dataset_observations (
    dataset_id INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    observation_id INTEGER NOT NULL REFERENCES observations(id) ON DELETE CASCADE,
    PRIMARY KEY(dataset_id, observation_id)
);

-- Trained ML Models
CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    algorithm TEXT NOT NULL DEFAULT 'RandomForestClassifier',
    dataset_id INTEGER REFERENCES datasets(id) ON DELETE SET NULL,
    parameters_json TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    feature_names_json TEXT NOT NULL,
    model_file_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inference and Prediction History
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id INTEGER REFERENCES models(id) ON DELETE SET NULL,
    model_name TEXT NOT NULL,
    method_name TEXT NOT NULL,
    class_name TEXT,
    file_name TEXT,
    source_code TEXT,
    metrics_json TEXT NOT NULL,
    predicted_label INTEGER NOT NULL,
    risk_score REAL NOT NULL,
    risk_category TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_commits_repo ON commits(repository_id);
CREATE INDEX IF NOT EXISTS idx_commits_sha ON commits(commit_sha);
CREATE INDEX IF NOT EXISTS idx_commits_bugfix ON commits(is_bug_fix);
CREATE INDEX IF NOT EXISTS idx_commit_files_commit ON commit_files(commit_id);
CREATE INDEX IF NOT EXISTS idx_szz_fixing ON szz_results(fixing_commit_sha);
CREATE INDEX IF NOT EXISTS idx_szz_inducing ON szz_results(inducing_commit_sha);
CREATE INDEX IF NOT EXISTS idx_observations_repo ON observations(repository_id);
CREATE INDEX IF NOT EXISTS idx_observations_label ON observations(label);
CREATE INDEX IF NOT EXISTS idx_observations_commit ON observations(commit_sha);
CREATE INDEX IF NOT EXISTS idx_features_obs ON features(observation_id);
CREATE INDEX IF NOT EXISTS idx_predictions_model ON predictions(model_id);
CREATE INDEX IF NOT EXISTS idx_predictions_created ON predictions(created_at);
"""
