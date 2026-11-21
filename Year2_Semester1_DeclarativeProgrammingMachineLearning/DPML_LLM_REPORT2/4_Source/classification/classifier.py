"""Response classification runner, processed result serializer, and manual academic review manager."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import jsonlines

from source.config.settings import AppConfig
from source.safety_evaluation.evaluator import EvaluationResult, MultiDimensionalSafetyEvaluator
from source.storage.database import DatabaseManager
from source.storage.models import (
    EvaluationCriterion,
    EvaluationRun,
    ModelResponse,
    ReviewerAnnotation,
    SafetyEvaluation,
    TestCaseRecord,
    TestExecution,
    ToolInvocation,
)


class ResponseClassifier:
    """Runs multi-dimensional classification over persisted executions and supports manual review."""

    def __init__(self, config: AppConfig, db: DatabaseManager):
        self.config = config
        self.db = db
        self.evaluator = MultiDimensionalSafetyEvaluator(rule_version=config.evaluation.rule_version)

    def classify_experiment(
        self,
        experiment_id: str,
        output_dir: Optional[Path] = None,
    ) -> tuple[str, List[Dict[str, Any]]]:
        """Classify all executions in an experiment and persist to SQLite and processed JSON/JSONL."""
        eval_run_id = f"eval_{experiment_id}_{uuid.uuid4().hex[:8]}"
        records: List[Dict[str, Any]] = []

        with self.db.session() as sess:
            execs = (
                sess.query(TestExecution)
                .filter(TestExecution.experiment_id == experiment_id)
                .order_by(TestExecution.test_id)
                .all()
            )
            if not execs:
                raise ValueError(f"No executions found for experiment '{experiment_id}'.")

            model_identifier = execs[0].model_identifier
            eval_run = EvaluationRun(
                id=eval_run_id,
                experiment_id=experiment_id,
                model_identifier=model_identifier,
                rule_version=self.config.evaluation.rule_version,
                total_evaluated=len(execs),
                metrics_json="{}",
            )
            sess.add(eval_run)
            sess.flush()

            for ex in execs:
                tc = sess.query(TestCaseRecord).filter(TestCaseRecord.test_id == ex.test_id).one()
                mr = sess.query(ModelResponse).filter(ModelResponse.execution_id == ex.id).one_or_none()
                tools = sess.query(ToolInvocation).filter(ToolInvocation.execution_id == ex.id).all()

                tc_dict = {
                    "test_id": tc.test_id,
                    "category": tc.category_id,
                    "subcategory": tc.subcategory,
                    "severity": tc.severity,
                    "attack_pattern": tc.attack_pattern,
                    "expected_behavior": tc.expected_behavior,
                    "evaluation_criteria": json.loads(tc.evaluation_criteria_json),
                    "split": tc.split,
                    "template_family": tc.template_family,
                }
                tool_dicts = [
                    {
                        "tool_name": t.tool_name,
                        "arguments": json.loads(t.arguments_json),
                        "authorized": t.authorized,
                        "blocked_reason": t.blocked_reason,
                    }
                    for t in tools
                ]
                resp_text = mr.final_response_text if mr else ""
                res: EvaluationResult = self.evaluator.evaluate(
                    test_case=tc_dict,
                    response_text=resp_text,
                    tool_invocations=tool_dicts,
                    status=ex.status,
                    error_message=ex.error_message,
                )

                se = SafetyEvaluation(
                    evaluation_run_id=eval_run_id,
                    execution_id=ex.id,
                    test_id=res.test_id,
                    category_id=res.category,
                    severity=res.severity,
                    expected_behavior=res.expected_behavior,
                    classification=res.classification,
                    is_safe=res.is_safe,
                    is_unsafe_failure=res.is_unsafe_failure,
                    is_over_refusal=res.is_over_refusal,
                    provides_operational_harm=res.provides_operational_harm,
                    discloses_protected_info=res.discloses_protected_info,
                    follows_malicious_instructions=res.follows_malicious_instructions,
                    violates_instruction_hierarchy=res.violates_instruction_hierarchy,
                    unauthorized_tool_action=res.unauthorized_tool_action,
                    provides_safe_alternative=res.provides_safe_alternative,
                    appropriate_sensitive_handling=res.appropriate_sensitive_handling,
                    confidence=res.confidence,
                    rationale=res.rationale,
                    rule_version=self.config.evaluation.rule_version,
                )
                sess.add(se)
                sess.flush()

                for cs in res.criteria_scores:
                    sess.add(
                        EvaluationCriterion(
                            safety_evaluation_id=se.id,
                            criterion_name=cs.name,
                            passed=cs.passed,
                            evidence=cs.evidence,
                        )
                    )

                rec = {
                    **asdict(res),
                    "safety_evaluation_id": se.id,
                    "execution_id": ex.id,
                    "experiment_id": experiment_id,
                    "model_identifier": ex.model_identifier,
                    "subcategory": tc.subcategory,
                    "attack_pattern": tc.attack_pattern,
                    "split": tc.split,
                    "template_family": tc.template_family,
                    "duration_seconds": ex.duration_seconds,
                    "prompt_tokens": ex.prompt_tokens,
                    "completion_tokens": ex.completion_tokens,
                    "response_excerpt": resp_text[:300],
                    "tool_invocations": tool_dicts,
                }
                rec["criteria_scores"] = [asdict(cs) for cs in res.criteria_scores]
                records.append(rec)

        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / f"{experiment_id}_classified.json").write_text(
                json.dumps(records, indent=2), encoding="utf-8"
            )
            with jsonlines.open(output_dir / f"{experiment_id}_classified.jsonl", mode="w") as w:
                w.write_all(records)

        return eval_run_id, records

    def add_manual_review(
        self,
        safety_evaluation_id: int,
        human_classification: str,
        reviewer_id: str,
        reviewer_notes: str,
    ) -> int:
        """Record a manual academic review annotation alongside the original automated classification."""
        with self.db.session() as sess:
            se = sess.query(SafetyEvaluation).filter(SafetyEvaluation.id == safety_evaluation_id).one()
            ann = ReviewerAnnotation(
                safety_evaluation_id=safety_evaluation_id,
                automated_classification=se.classification,
                human_classification=human_classification,
                reviewer_id=reviewer_id,
                reviewer_notes=reviewer_notes,
                rule_version=se.rule_version,
            )
            sess.add(ann)
            sess.flush()
            return ann.id
