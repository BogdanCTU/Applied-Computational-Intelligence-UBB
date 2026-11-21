CREATE TABLE experiments (
	id VARCHAR(64) NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	phase VARCHAR(64) NOT NULL, 
	description TEXT, 
	config_json TEXT NOT NULL, 
	dataset_version VARCHAR(32) NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at DATETIME NOT NULL, 
	completed_at DATETIME, 
	PRIMARY KEY (id)
);

CREATE TABLE models (
	id INTEGER NOT NULL, 
	identifier VARCHAR(128) NOT NULL, 
	provider VARCHAR(64) NOT NULL, 
	architecture VARCHAR(64), 
	parameter_count VARCHAR(64), 
	context_length INTEGER, 
	quantization VARCHAR(64), 
	capabilities_json TEXT, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (identifier)
);

CREATE TABLE test_categories (
	id VARCHAR(64) NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	description TEXT NOT NULL, 
	risk_domain VARCHAR(64) NOT NULL, 
	target_count INTEGER NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE training_examples (
	id VARCHAR(64) NOT NULL, 
	source_test_id VARCHAR(64), 
	template_family VARCHAR(128) NOT NULL, 
	risk_category VARCHAR(64) NOT NULL, 
	desired_behavior VARCHAR(64) NOT NULL, 
	training_source VARCHAR(64) NOT NULL, 
	split VARCHAR(32) NOT NULL, 
	validation_status VARCHAR(32) NOT NULL, 
	messages_json TEXT NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_train_ex_split_cat ON training_examples (split, risk_category);

CREATE TABLE training_runs (
	id VARCHAR(64) NOT NULL, 
	base_model VARCHAR(128) NOT NULL, 
	mlx_base_path VARCHAR(512) NOT NULL, 
	adapter_path VARCHAR(512) NOT NULL, 
	fused_model_path VARCHAR(512), 
	ollama_target_model VARCHAR(128), 
	method VARCHAR(32) NOT NULL, 
	hyperparameters_json TEXT NOT NULL, 
	train_examples_count INTEGER NOT NULL, 
	val_examples_count INTEGER NOT NULL, 
	initial_val_loss FLOAT, 
	final_val_loss FLOAT, 
	final_train_loss FLOAT, 
	duration_seconds FLOAT NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	conversion_verified BOOLEAN NOT NULL, 
	log_path VARCHAR(512) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE evaluation_runs (
	id VARCHAR(64) NOT NULL, 
	experiment_id VARCHAR(64) NOT NULL, 
	model_identifier VARCHAR(128) NOT NULL, 
	rule_version VARCHAR(32) NOT NULL, 
	total_evaluated INTEGER NOT NULL, 
	metrics_json TEXT NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(experiment_id) REFERENCES experiments (id) ON DELETE CASCADE
);

CREATE TABLE model_versions (
	id INTEGER NOT NULL, 
	model_id INTEGER NOT NULL, 
	version_tag VARCHAR(128) NOT NULL, 
	digest VARCHAR(128), 
	adapter_path VARCHAR(512), 
	training_run_id VARCHAR(64), 
	metadata_json TEXT, 
	verified_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_model_version UNIQUE (model_id, version_tag), 
	FOREIGN KEY(model_id) REFERENCES models (id) ON DELETE CASCADE
);

CREATE TABLE test_cases (
	test_id VARCHAR(64) NOT NULL, 
	category_id VARCHAR(64) NOT NULL, 
	subcategory VARCHAR(128) NOT NULL, 
	severity VARCHAR(32) NOT NULL, 
	risk_type VARCHAR(128) NOT NULL, 
	attack_pattern VARCHAR(128) NOT NULL, 
	expected_behavior VARCHAR(64) NOT NULL, 
	expected_risk VARCHAR(32) NOT NULL, 
	split VARCHAR(32) NOT NULL, 
	template_family VARCHAR(128) NOT NULL, 
	dataset_version VARCHAR(32) NOT NULL, 
	conversation_json TEXT NOT NULL, 
	evaluation_criteria_json TEXT NOT NULL, 
	tags_json TEXT NOT NULL, 
	prompt_hash VARCHAR(64) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (test_id), 
	FOREIGN KEY(category_id) REFERENCES test_categories (id) ON DELETE CASCADE
);

CREATE INDEX ix_test_cases_category_split ON test_cases (category_id, split);

CREATE INDEX ix_test_cases_template_family ON test_cases (template_family);

CREATE TABLE comparative_results (
	id INTEGER NOT NULL, 
	comparison_id VARCHAR(64) NOT NULL, 
	baseline_eval_run_id VARCHAR(64) NOT NULL, 
	mitigated_eval_run_id VARCHAR(64) NOT NULL, 
	category_id VARCHAR(64) NOT NULL, 
	n_paired INTEGER NOT NULL, 
	baseline_ucr FLOAT NOT NULL, 
	mitigated_ucr FLOAT NOT NULL, 
	absolute_improvement FLOAT NOT NULL, 
	relative_improvement FLOAT NOT NULL, 
	mcnemar_statistic FLOAT, 
	p_value_raw FLOAT NOT NULL, 
	p_value_fdr FLOAT NOT NULL, 
	p_value_holm FLOAT NOT NULL, 
	statistically_significant BOOLEAN NOT NULL, 
	details_json TEXT NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(baseline_eval_run_id) REFERENCES evaluation_runs (id) ON DELETE CASCADE, 
	FOREIGN KEY(mitigated_eval_run_id) REFERENCES evaluation_runs (id) ON DELETE CASCADE
);

CREATE INDEX ix_comparative_results_comparison_id ON comparative_results (comparison_id);

CREATE TABLE test_executions (
	id INTEGER NOT NULL, 
	experiment_id VARCHAR(64) NOT NULL, 
	test_id VARCHAR(64) NOT NULL, 
	category_id VARCHAR(64) NOT NULL, 
	subcategory VARCHAR(128) NOT NULL, 
	model_identifier VARCHAR(128) NOT NULL, 
	model_version_digest VARCHAR(128), 
	system_prompt_version VARCHAR(64) NOT NULL, 
	dataset_version VARCHAR(32) NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	duration_seconds FLOAT NOT NULL, 
	prompt_tokens INTEGER, 
	completion_tokens INTEGER, 
	error_message TEXT, 
	executed_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_exp_test UNIQUE (experiment_id, test_id), 
	FOREIGN KEY(experiment_id) REFERENCES experiments (id) ON DELETE CASCADE, 
	FOREIGN KEY(test_id) REFERENCES test_cases (test_id) ON DELETE CASCADE
);

CREATE INDEX ix_exec_experiment_cat ON test_executions (experiment_id, category_id);

CREATE TABLE conversations (
	id INTEGER NOT NULL, 
	execution_id INTEGER NOT NULL, 
	turn_index INTEGER NOT NULL, 
	role VARCHAR(32) NOT NULL, 
	content TEXT NOT NULL, 
	raw_message_json TEXT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(execution_id) REFERENCES test_executions (id) ON DELETE CASCADE
);

CREATE INDEX ix_conv_exec_turn ON conversations (execution_id, turn_index);

CREATE TABLE model_responses (
	id INTEGER NOT NULL, 
	execution_id INTEGER NOT NULL, 
	final_response_text TEXT NOT NULL, 
	thinking_text TEXT, 
	raw_payload_json TEXT NOT NULL, 
	done_reason VARCHAR(64), 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (execution_id), 
	FOREIGN KEY(execution_id) REFERENCES test_executions (id) ON DELETE CASCADE
);

CREATE TABLE safety_evaluations (
	id INTEGER NOT NULL, 
	evaluation_run_id VARCHAR(64) NOT NULL, 
	execution_id INTEGER NOT NULL, 
	test_id VARCHAR(64) NOT NULL, 
	category_id VARCHAR(64) NOT NULL, 
	severity VARCHAR(32) NOT NULL, 
	expected_behavior VARCHAR(64) NOT NULL, 
	classification VARCHAR(64) NOT NULL, 
	is_safe BOOLEAN NOT NULL, 
	is_unsafe_failure BOOLEAN NOT NULL, 
	is_over_refusal BOOLEAN NOT NULL, 
	provides_operational_harm BOOLEAN NOT NULL, 
	discloses_protected_info BOOLEAN NOT NULL, 
	follows_malicious_instructions BOOLEAN NOT NULL, 
	violates_instruction_hierarchy BOOLEAN NOT NULL, 
	unauthorized_tool_action BOOLEAN NOT NULL, 
	provides_safe_alternative BOOLEAN NOT NULL, 
	appropriate_sensitive_handling BOOLEAN NOT NULL, 
	confidence FLOAT NOT NULL, 
	rationale TEXT NOT NULL, 
	rule_version VARCHAR(32) NOT NULL, 
	evaluated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(evaluation_run_id) REFERENCES evaluation_runs (id) ON DELETE CASCADE, 
	FOREIGN KEY(execution_id) REFERENCES test_executions (id) ON DELETE CASCADE
);

CREATE INDEX ix_eval_run_label ON safety_evaluations (evaluation_run_id, classification);

CREATE TABLE tool_invocations (
	id INTEGER NOT NULL, 
	execution_id INTEGER NOT NULL, 
	tool_name VARCHAR(128) NOT NULL, 
	arguments_json TEXT NOT NULL, 
	attempted_by_model BOOLEAN NOT NULL, 
	authorized BOOLEAN NOT NULL, 
	blocked_reason TEXT, 
	result_summary TEXT, 
	invoked_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(execution_id) REFERENCES test_executions (id) ON DELETE CASCADE
);

CREATE INDEX ix_tool_exec ON tool_invocations (execution_id);

CREATE TABLE evaluation_criteria (
	id INTEGER NOT NULL, 
	safety_evaluation_id INTEGER NOT NULL, 
	criterion_name VARCHAR(128) NOT NULL, 
	passed BOOLEAN NOT NULL, 
	evidence TEXT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(safety_evaluation_id) REFERENCES safety_evaluations (id) ON DELETE CASCADE
);

CREATE INDEX ix_crit_eval ON evaluation_criteria (safety_evaluation_id);

CREATE TABLE reviewer_annotations (
	id INTEGER NOT NULL, 
	safety_evaluation_id INTEGER NOT NULL, 
	automated_classification VARCHAR(64) NOT NULL, 
	human_classification VARCHAR(64) NOT NULL, 
	reviewer_id VARCHAR(64) NOT NULL, 
	reviewer_notes TEXT NOT NULL, 
	rule_version VARCHAR(32) NOT NULL, 
	reviewed_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(safety_evaluation_id) REFERENCES safety_evaluations (id) ON DELETE CASCADE
);
