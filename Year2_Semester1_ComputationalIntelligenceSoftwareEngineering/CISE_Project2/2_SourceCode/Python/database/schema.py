"""SQLite schema definitions for C# class/file-level and legacy method-level bug detection."""

CLASS_FEATURE_COLUMNS = [
    ("class_loc", "INTEGER DEFAULT 0"),
    ("class_logical_loc", "INTEGER DEFAULT 0"),
    ("method_count", "INTEGER DEFAULT 0"),
    ("constructor_count", "INTEGER DEFAULT 0"),
    ("property_count", "INTEGER DEFAULT 0"),
    ("field_count", "INTEGER DEFAULT 0"),
    ("nested_type_count", "INTEGER DEFAULT 0"),
    ("total_parameter_count", "INTEGER DEFAULT 0"),
    ("max_parameter_count", "INTEGER DEFAULT 0"),
    ("total_local_variable_count", "INTEGER DEFAULT 0"),
    ("total_statement_count", "INTEGER DEFAULT 0"),
    ("total_return_count", "INTEGER DEFAULT 0"),
    ("total_cyclomatic_complexity", "INTEGER DEFAULT 0"),
    ("mean_method_complexity", "REAL DEFAULT 0.0"),
    ("max_method_complexity", "INTEGER DEFAULT 0"),
    ("std_method_complexity", "REAL DEFAULT 0.0"),
    ("max_nesting_depth", "INTEGER DEFAULT 0"),
    ("mean_nesting_depth", "REAL DEFAULT 0.0"),
    ("total_boolean_operator_count", "INTEGER DEFAULT 0"),
    ("total_logical_operator_count", "INTEGER DEFAULT 0"),
    ("total_conditional_expression_count", "INTEGER DEFAULT 0"),
    ("total_if_count", "INTEGER DEFAULT 0"),
    ("total_switch_count", "INTEGER DEFAULT 0"),
    ("total_loop_count", "INTEGER DEFAULT 0"),
    ("total_try_catch_count", "INTEGER DEFAULT 0"),
    ("total_throw_count", "INTEGER DEFAULT 0"),
    ("total_break_continue_count", "INTEGER DEFAULT 0"),
    ("total_method_call_count", "INTEGER DEFAULT 0"),
    ("total_field_access_count", "INTEGER DEFAULT 0"),
    ("total_property_access_count", "INTEGER DEFAULT 0"),
    ("total_assignment_count", "INTEGER DEFAULT 0"),
    ("total_object_creation_count", "INTEGER DEFAULT 0"),
    ("static_method_count", "INTEGER DEFAULT 0"),
    ("async_method_count", "INTEGER DEFAULT 0"),
    ("generic_method_count", "INTEGER DEFAULT 0"),
    ("high_complexity_method_count", "INTEGER DEFAULT 0"),
    ("large_method_count", "INTEGER DEFAULT 0"),
    ("complexity_concentration", "REAL DEFAULT 0.0"),
    ("structural_density", "REAL DEFAULT 0.0"),
    ("wmc_density", "REAL DEFAULT 0.0"),
]

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
    status TEXT DEFAULT 'registered',
    last_sync_at TIMESTAMP,
    selection_score REAL DEFAULT 0.0,
    selection_rank INTEGER,
    selection_reason TEXT,
    exclusion_reason TEXT,
    is_selected INTEGER DEFAULT 1,
    is_fork INTEGER DEFAULT 0,
    is_archived INTEGER DEFAULT 0,
    pushed_at TEXT,
    created_at_gh TEXT,
    production_cs_files_count INTEGER DEFAULT 0,
    commits_mined_count INTEGER DEFAULT 0,
    bug_fixes_count INTEGER DEFAULT 0,
    szz_traces_count INTEGER DEFAULT 0,
    class_observations_count INTEGER DEFAULT 0,
    processing_error TEXT,
    collection_run_id TEXT,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Collection runs table for resumable 100+ repository execution
CREATE TABLE IF NOT EXISTS repository_collection_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT UNIQUE NOT NULL,
    target_repositories INTEGER NOT NULL DEFAULT 100,
    discovered_count INTEGER DEFAULT 0,
    selected_count INTEGER DEFAULT 0,
    processed_count INTEGER DEFAULT 0,
    excluded_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'running',
    config_json TEXT,
    checkpoint_path TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Commits metadata table
CREATE TABLE IF NOT EXISTS commits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    commit_sha TEXT NOT NULL,
    parent_sha TEXT,
    parent_shas TEXT,
    author_name TEXT,
    author_email TEXT,
    committed_date TIMESTAMP,
    committer_date TIMESTAMP,
    message TEXT,
    files_changed_count INTEGER DEFAULT 0,
    insertions INTEGER DEFAULT 0,
    deletions INTEGER DEFAULT 0,
    modifies_csharp INTEGER DEFAULT 0,
    is_bug_fix INTEGER DEFAULT 0,
    bug_fix_confidence REAL DEFAULT 0.0,
    bug_fix_evidence TEXT,
    review_status TEXT DEFAULT 'unreviewed',
    analyzed_at TIMESTAMP,
    UNIQUE(repository_id, commit_sha)
);

-- Commit File Modifications Table
CREATE TABLE IF NOT EXISTS commit_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    commit_id INTEGER NOT NULL REFERENCES commits(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    change_type TEXT NOT NULL,
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

-- Historical Methods catalogue (preserved for method-level backward compatibility)
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

-- Historical Method Observations with Defect Labels (preserved for backward compatibility)
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
    label INTEGER NOT NULL,
    label_confidence REAL DEFAULT 1.0,
    evidence_category TEXT NOT NULL,
    bug_fixing_commit_message TEXT,
    issue_or_pr_url TEXT,
    review_status TEXT DEFAULT 'unreviewed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(repository_id, commit_sha, file_path, method_signature, label)
);

-- Static Code Features Extracted via Roslyn for Method Observations (preserved)
CREATE TABLE IF NOT EXISTS features (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    observation_id INTEGER UNIQUE NOT NULL REFERENCES observations(id) ON DELETE CASCADE,
    loc INTEGER,
    logical_loc INTEGER DEFAULT 0,
    method_length INTEGER,
    parameter_count INTEGER DEFAULT 0,
    local_variable_count INTEGER DEFAULT 0,
    statement_count INTEGER DEFAULT 0,
    return_count INTEGER DEFAULT 0,
    num_statements INTEGER,
    num_parameters INTEGER,
    num_local_vars INTEGER,
    num_returns INTEGER,
    num_assignments INTEGER,
    cyclomatic_complexity INTEGER,
    max_nesting_depth INTEGER,
    boolean_operator_count INTEGER DEFAULT 0,
    logical_operator_count INTEGER DEFAULT 0,
    conditional_expression_count INTEGER DEFAULT 0,
    if_count INTEGER DEFAULT 0,
    switch_count INTEGER DEFAULT 0,
    loop_count INTEGER DEFAULT 0,
    try_catch_count INTEGER DEFAULT 0,
    throw_count INTEGER DEFAULT 0,
    break_continue_count INTEGER DEFAULT 0,
    method_call_count INTEGER DEFAULT 0,
    field_access_count INTEGER DEFAULT 0,
    property_access_count INTEGER DEFAULT 0,
    assignment_count INTEGER DEFAULT 0,
    object_creation_count INTEGER DEFAULT 0,
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
    status TEXT DEFAULT 'success',
    error_message TEXT,
    analyzer_version TEXT DEFAULT '1.0.0',
    raw_metrics_json TEXT,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- File-level observations aggregating class provenance per .cs file revision
CREATE TABLE IF NOT EXISTS file_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    commit_sha TEXT NOT NULL,
    file_path TEXT NOT NULL,
    total_lines INTEGER DEFAULT 0,
    namespace_count INTEGER DEFAULT 0,
    class_count INTEGER DEFAULT 0,
    method_count INTEGER DEFAULT 0,
    file_fingerprint TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(repository_id, commit_sha, file_path)
);

-- Primary Class-Level Observations with SZZ Defect Provenance
CREATE TABLE IF NOT EXISTS class_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_observation_id INTEGER REFERENCES file_observations(id) ON DELETE SET NULL,
    repository_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    commit_sha TEXT NOT NULL,
    parent_sha TEXT,
    bug_fix_commit_sha TEXT,
    bug_inducing_commit_sha TEXT,
    file_path TEXT NOT NULL,
    namespace_name TEXT DEFAULT 'Global',
    class_name TEXT NOT NULL,
    qualified_class_name TEXT NOT NULL,
    type_kind TEXT DEFAULT 'class',
    start_line INTEGER DEFAULT 1,
    end_line INTEGER DEFAULT 1,
    is_nested INTEGER DEFAULT 0,
    enclosing_type_name TEXT,
    source_code TEXT NOT NULL,
    corrected_code TEXT,
    source_fingerprint TEXT NOT NULL,
    structural_fingerprint TEXT NOT NULL,
    label INTEGER NOT NULL,
    label_confidence REAL DEFAULT 1.0,
    szz_trace_count INTEGER DEFAULT 0,
    blamed_lines_json TEXT,
    evidence_category TEXT NOT NULL,
    bug_fixing_commit_message TEXT,
    issue_or_pr_url TEXT,
    review_status TEXT DEFAULT 'unreviewed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(repository_id, commit_sha, file_path, qualified_class_name, label)
);

-- 40 Class-Level Static Code Features Extracted via Roslyn
CREATE TABLE IF NOT EXISTS class_features (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_observation_id INTEGER UNIQUE NOT NULL REFERENCES class_observations(id) ON DELETE CASCADE,
    class_loc INTEGER DEFAULT 0,
    class_logical_loc INTEGER DEFAULT 0,
    method_count INTEGER DEFAULT 0,
    constructor_count INTEGER DEFAULT 0,
    property_count INTEGER DEFAULT 0,
    field_count INTEGER DEFAULT 0,
    nested_type_count INTEGER DEFAULT 0,
    total_parameter_count INTEGER DEFAULT 0,
    max_parameter_count INTEGER DEFAULT 0,
    total_local_variable_count INTEGER DEFAULT 0,
    total_statement_count INTEGER DEFAULT 0,
    total_return_count INTEGER DEFAULT 0,
    total_cyclomatic_complexity INTEGER DEFAULT 0,
    mean_method_complexity REAL DEFAULT 0.0,
    max_method_complexity INTEGER DEFAULT 0,
    std_method_complexity REAL DEFAULT 0.0,
    max_nesting_depth INTEGER DEFAULT 0,
    mean_nesting_depth REAL DEFAULT 0.0,
    total_boolean_operator_count INTEGER DEFAULT 0,
    total_logical_operator_count INTEGER DEFAULT 0,
    total_conditional_expression_count INTEGER DEFAULT 0,
    total_if_count INTEGER DEFAULT 0,
    total_switch_count INTEGER DEFAULT 0,
    total_loop_count INTEGER DEFAULT 0,
    total_try_catch_count INTEGER DEFAULT 0,
    total_throw_count INTEGER DEFAULT 0,
    total_break_continue_count INTEGER DEFAULT 0,
    total_method_call_count INTEGER DEFAULT 0,
    total_field_access_count INTEGER DEFAULT 0,
    total_property_access_count INTEGER DEFAULT 0,
    total_assignment_count INTEGER DEFAULT 0,
    total_object_creation_count INTEGER DEFAULT 0,
    static_method_count INTEGER DEFAULT 0,
    async_method_count INTEGER DEFAULT 0,
    generic_method_count INTEGER DEFAULT 0,
    high_complexity_method_count INTEGER DEFAULT 0,
    large_method_count INTEGER DEFAULT 0,
    complexity_concentration REAL DEFAULT 0.0,
    structural_density REAL DEFAULT 0.0,
    wmc_density REAL DEFAULT 0.0,
    feature_schema_version TEXT DEFAULT '3.0.0',
    analyzer_version TEXT DEFAULT '2.0.0',
    status TEXT DEFAULT 'success',
    error_message TEXT,
    raw_metrics_json TEXT,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dataset Generation Runs (Versioned Datasets across Method or Class Granularity)
CREATE TABLE IF NOT EXISTS datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    version TEXT NOT NULL,
    description TEXT,
    granularity TEXT DEFAULT 'method',
    repository_count INTEGER DEFAULT 0,
    total_count INTEGER NOT NULL DEFAULT 0,
    buggy_count INTEGER NOT NULL DEFAULT 0,
    non_buggy_count INTEGER NOT NULL DEFAULT 0,
    uncertain_count INTEGER NOT NULL DEFAULT 0,
    feature_names TEXT NOT NULL,
    feature_schema_version TEXT DEFAULT '1.0.0',
    export_path TEXT,
    manifest_path TEXT,
    sha256_checksum TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Association between Dataset and Historical Method Observations
CREATE TABLE IF NOT EXISTS dataset_observations (
    dataset_id INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    observation_id INTEGER NOT NULL REFERENCES observations(id) ON DELETE CASCADE,
    PRIMARY KEY(dataset_id, observation_id)
);

-- Association between Dataset and Class Observations
CREATE TABLE IF NOT EXISTS dataset_class_observations (
    dataset_id INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    class_observation_id INTEGER NOT NULL REFERENCES class_observations(id) ON DELETE CASCADE,
    PRIMARY KEY(dataset_id, class_observation_id)
);

-- Trained ML Models
CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    algorithm TEXT NOT NULL DEFAULT 'RandomForestClassifier',
    version TEXT DEFAULT '1.0.0',
    granularity TEXT DEFAULT 'method',
    dataset_id INTEGER REFERENCES datasets(id) ON DELETE SET NULL,
    dataset_version TEXT,
    decision_threshold REAL DEFAULT 0.50,
    threshold_selection_criterion TEXT,
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
    granularity TEXT DEFAULT 'method',
    dataset_version TEXT,
    decision_threshold REAL DEFAULT 0.50,
    method_name TEXT NOT NULL,
    class_name TEXT,
    namespace_name TEXT,
    file_name TEXT,
    start_line INTEGER,
    end_line INTEGER,
    method_count INTEGER,
    loc INTEGER,
    cyclomatic_complexity INTEGER,
    source_code TEXT,
    metrics_json TEXT NOT NULL,
    file_summary_json TEXT,
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
CREATE INDEX IF NOT EXISTS idx_file_obs_repo ON file_observations(repository_id);
CREATE INDEX IF NOT EXISTS idx_class_obs_repo ON class_observations(repository_id);
CREATE INDEX IF NOT EXISTS idx_class_obs_label ON class_observations(label);
CREATE INDEX IF NOT EXISTS idx_class_obs_commit ON class_observations(commit_sha);
CREATE INDEX IF NOT EXISTS idx_class_obs_fp ON class_observations(source_fingerprint);
CREATE INDEX IF NOT EXISTS idx_class_obs_struct_fp ON class_observations(structural_fingerprint);
CREATE INDEX IF NOT EXISTS idx_class_features_obs ON class_features(class_observation_id);
CREATE INDEX IF NOT EXISTS idx_predictions_model ON predictions(model_id);
CREATE INDEX IF NOT EXISTS idx_predictions_created ON predictions(created_at);
CREATE INDEX IF NOT EXISTS idx_predictions_granularity ON predictions(granularity);
"""
