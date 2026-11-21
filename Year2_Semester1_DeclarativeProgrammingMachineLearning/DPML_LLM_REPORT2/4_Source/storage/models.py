"""SQLAlchemy 2.0 ORM schema for the Local LLM Safety Research Platform."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base ORM class."""


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phase: Mapped[str] = mapped_column(String(64), nullable=False)  # baseline | mitigated | comparison
    description: Mapped[Optional[str]] = mapped_column(Text)
    config_json: Mapped[str] = mapped_column(Text, nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="created", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class ModelRecord(Base):
    __tablename__ = "models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    identifier: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    architecture: Mapped[Optional[str]] = mapped_column(String(64))
    parameter_count: Mapped[Optional[str]] = mapped_column(String(64))
    context_length: Mapped[Optional[int]] = mapped_column(Integer)
    quantization: Mapped[Optional[str]] = mapped_column(String(64))
    capabilities_json: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (UniqueConstraint("model_id", "version_tag", name="uq_model_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id", ondelete="CASCADE"), nullable=False)
    version_tag: Mapped[str] = mapped_column(String(128), nullable=False)
    digest: Mapped[Optional[str]] = mapped_column(String(128))
    adapter_path: Mapped[Optional[str]] = mapped_column(String(512))
    training_run_id: Mapped[Optional[str]] = mapped_column(String(64))
    metadata_json: Mapped[Optional[str]] = mapped_column(Text)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class TestCategory(Base):
    __tablename__ = "test_categories"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    risk_domain: Mapped[str] = mapped_column(String(64), nullable=False)
    target_count: Mapped[int] = mapped_column(Integer, default=100, nullable=False)


class TestCaseRecord(Base):
    __tablename__ = "test_cases"
    __table_args__ = (
        Index("ix_test_cases_category_split", "category_id", "split"),
        Index("ix_test_cases_template_family", "template_family"),
    )

    test_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    category_id: Mapped[str] = mapped_column(ForeignKey("test_categories.id", ondelete="CASCADE"), nullable=False)
    subcategory: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_type: Mapped[str] = mapped_column(String(128), nullable=False)
    attack_pattern: Mapped[str] = mapped_column(String(128), nullable=False)
    expected_behavior: Mapped[str] = mapped_column(String(64), nullable=False)
    expected_risk: Mapped[str] = mapped_column(String(32), nullable=False)
    split: Mapped[str] = mapped_column(String(32), nullable=False)
    template_family: Mapped[str] = mapped_column(String(128), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(32), nullable=False)
    conversation_json: Mapped[str] = mapped_column(Text, nullable=False)
    evaluation_criteria_json: Mapped[str] = mapped_column(Text, nullable=False)
    tags_json: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class TestExecution(Base):
    __tablename__ = "test_executions"
    __table_args__ = (
        UniqueConstraint("experiment_id", "test_id", name="uq_exp_test"),
        Index("ix_exec_experiment_cat", "experiment_id", "category_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False)
    test_id: Mapped[str] = mapped_column(ForeignKey("test_cases.test_id", ondelete="CASCADE"), nullable=False)
    category_id: Mapped[str] = mapped_column(String(64), nullable=False)
    subcategory: Mapped[str] = mapped_column(String(128), nullable=False)
    model_identifier: Mapped[str] = mapped_column(String(128), nullable=False)
    model_version_digest: Mapped[Optional[str]] = mapped_column(String(128))
    system_prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # completed | error
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (Index("ix_conv_exec_turn", "execution_id", "turn_index"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[int] = mapped_column(ForeignKey("test_executions.id", ondelete="CASCADE"), nullable=False)
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    raw_message_json: Mapped[str] = mapped_column(Text, nullable=False)


class ModelResponse(Base):
    __tablename__ = "model_responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[int] = mapped_column(ForeignKey("test_executions.id", ondelete="CASCADE"), unique=True, nullable=False)
    final_response_text: Mapped[str] = mapped_column(Text, nullable=False)
    thinking_text: Mapped[Optional[str]] = mapped_column(Text)
    raw_payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    done_reason: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ToolInvocation(Base):
    __tablename__ = "tool_invocations"
    __table_args__ = (Index("ix_tool_exec", "execution_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[int] = mapped_column(ForeignKey("test_executions.id", ondelete="CASCADE"), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    arguments_json: Mapped[str] = mapped_column(Text, nullable=False)
    attempted_by_model: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    authorized: Mapped[bool] = mapped_column(Boolean, nullable=False)
    blocked_reason: Mapped[Optional[str]] = mapped_column(Text)
    result_summary: Mapped[Optional[str]] = mapped_column(Text)
    invoked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class SafetyEvaluation(Base):
    __tablename__ = "safety_evaluations"
    __table_args__ = (Index("ix_eval_run_label", "evaluation_run_id", "classification"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evaluation_run_id: Mapped[str] = mapped_column(ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False)
    execution_id: Mapped[int] = mapped_column(ForeignKey("test_executions.id", ondelete="CASCADE"), nullable=False)
    test_id: Mapped[str] = mapped_column(String(64), nullable=False)
    category_id: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    expected_behavior: Mapped[str] = mapped_column(String(64), nullable=False)
    classification: Mapped[str] = mapped_column(String(64), nullable=False)
    is_safe: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_unsafe_failure: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_over_refusal: Mapped[bool] = mapped_column(Boolean, nullable=False)
    provides_operational_harm: Mapped[bool] = mapped_column(Boolean, nullable=False)
    discloses_protected_info: Mapped[bool] = mapped_column(Boolean, nullable=False)
    follows_malicious_instructions: Mapped[bool] = mapped_column(Boolean, nullable=False)
    violates_instruction_hierarchy: Mapped[bool] = mapped_column(Boolean, nullable=False)
    unauthorized_tool_action: Mapped[bool] = mapped_column(Boolean, nullable=False)
    provides_safe_alternative: Mapped[bool] = mapped_column(Boolean, nullable=False)
    appropriate_sensitive_handling: Mapped[bool] = mapped_column(Boolean, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class EvaluationCriterion(Base):
    __tablename__ = "evaluation_criteria"
    __table_args__ = (Index("ix_crit_eval", "safety_evaluation_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    safety_evaluation_id: Mapped[int] = mapped_column(ForeignKey("safety_evaluations.id", ondelete="CASCADE"), nullable=False)
    criterion_name: Mapped[str] = mapped_column(String(128), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)


class TrainingExample(Base):
    __tablename__ = "training_examples"
    __table_args__ = (Index("ix_train_ex_split_cat", "split", "risk_category"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_test_id: Mapped[Optional[str]] = mapped_column(String(64))
    template_family: Mapped[str] = mapped_column(String(128), nullable=False)
    risk_category: Mapped[str] = mapped_column(String(64), nullable=False)
    desired_behavior: Mapped[str] = mapped_column(String(64), nullable=False)
    training_source: Mapped[str] = mapped_column(String(64), nullable=False)
    split: Mapped[str] = mapped_column(String(32), nullable=False)  # train | valid | test
    validation_status: Mapped[str] = mapped_column(String(32), default="validated", nullable=False)
    messages_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class TrainingRun(Base):
    __tablename__ = "training_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    base_model: Mapped[str] = mapped_column(String(128), nullable=False)
    mlx_base_path: Mapped[str] = mapped_column(String(512), nullable=False)
    adapter_path: Mapped[str] = mapped_column(String(512), nullable=False)
    fused_model_path: Mapped[Optional[str]] = mapped_column(String(512))
    ollama_target_model: Mapped[Optional[str]] = mapped_column(String(128))
    method: Mapped[str] = mapped_column(String(32), nullable=False)
    hyperparameters_json: Mapped[str] = mapped_column(Text, nullable=False)
    train_examples_count: Mapped[int] = mapped_column(Integer, nullable=False)
    val_examples_count: Mapped[int] = mapped_column(Integer, nullable=False)
    initial_val_loss: Mapped[Optional[float]] = mapped_column(Float)
    final_val_loss: Mapped[Optional[float]] = mapped_column(Float)
    final_train_loss: Mapped[Optional[float]] = mapped_column(Float)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    conversion_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    log_path: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False)
    model_identifier: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False)
    total_evaluated: Mapped[int] = mapped_column(Integer, nullable=False)
    metrics_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ComparativeResult(Base):
    __tablename__ = "comparative_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    comparison_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    baseline_eval_run_id: Mapped[str] = mapped_column(ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False)
    mitigated_eval_run_id: Mapped[str] = mapped_column(ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False)
    category_id: Mapped[str] = mapped_column(String(64), nullable=False)
    n_paired: Mapped[int] = mapped_column(Integer, nullable=False)
    baseline_ucr: Mapped[float] = mapped_column(Float, nullable=False)
    mitigated_ucr: Mapped[float] = mapped_column(Float, nullable=False)
    absolute_improvement: Mapped[float] = mapped_column(Float, nullable=False)
    relative_improvement: Mapped[float] = mapped_column(Float, nullable=False)
    mcnemar_statistic: Mapped[Optional[float]] = mapped_column(Float)
    p_value_raw: Mapped[float] = mapped_column(Float, nullable=False)
    p_value_fdr: Mapped[float] = mapped_column(Float, nullable=False)
    p_value_holm: Mapped[float] = mapped_column(Float, nullable=False)
    statistically_significant: Mapped[bool] = mapped_column(Boolean, nullable=False)
    details_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ReviewerAnnotation(Base):
    __tablename__ = "reviewer_annotations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    safety_evaluation_id: Mapped[int] = mapped_column(ForeignKey("safety_evaluations.id", ondelete="CASCADE"), nullable=False)
    automated_classification: Mapped[str] = mapped_column(String(64), nullable=False)
    human_classification: Mapped[str] = mapped_column(String(64), nullable=False)
    reviewer_id: Mapped[str] = mapped_column(String(64), nullable=False)
    reviewer_notes: Mapped[str] = mapped_column(Text, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
