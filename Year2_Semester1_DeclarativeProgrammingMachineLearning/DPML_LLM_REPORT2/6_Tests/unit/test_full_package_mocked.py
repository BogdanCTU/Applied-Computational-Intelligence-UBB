"""Offline end-to-end smoke test of FullEvaluationPackageGenerator on synthetic paired data."""

from __future__ import annotations

import json
from pathlib import Path

from source.analytics.full_evaluation_pipeline import FullEvaluationPackageGenerator
from source.config.settings import AppConfig
from source.penetration.taxonomy import CATEGORIES
from source.storage.database import DatabaseManager
from source.storage.models import Experiment, ModelResponse, TestCaseRecord, TestCategory, TestExecution


def test_full_evaluation_package_synthetic_e2e(tmp_path: Path) -> None:
    cfg = AppConfig()
    db = DatabaseManager(tmp_path / "full_smoke.db")
    db.init_db(export_schema=False)

    with db.session() as sess:
        for cat in CATEGORIES:
            sess.add(TestCategory(id=cat.category_id, name=cat.display_name, description="d", risk_domain="r", target_count=2))
        sess.flush()

        for exp_id, phase, model_id in (
            ("exp_b_smoke", "baseline", "qwen3.5:4b"),
            ("exp_m_smoke", "mitigated", "qwen3.5:4b-safety"),
        ):
            sess.add(Experiment(id=exp_id, name=exp_id, phase=phase, config_json="{}", dataset_version="v1.0", status="completed"))
        sess.flush()

        for idx, cat in enumerate(CATEGORIES):
            for suffix, expected in (("0001", "refuse_and_redirect"), ("0099", "safe_completion")):
                tid = f"{cat.prefix}_{suffix}"
                if sess.query(TestCaseRecord).filter(TestCaseRecord.test_id == tid).one_or_none() is None:
                    sess.add(
                        TestCaseRecord(
                            test_id=tid,
                            category_id=cat.category_id,
                            subcategory=cat.subcategories[0],
                            severity="high" if expected == "refuse_and_redirect" else "low",
                            risk_type=f"{cat.category_id}_risk",
                            attack_pattern="direct_request" if expected == "refuse_and_redirect" else "benign_educational_boundary",
                            expected_behavior=expected,
                            expected_risk="high" if expected == "refuse_and_redirect" else "low",
                            split="held_out_eval",
                            template_family=f"{cat.category_id}_fam_15",
                            dataset_version="v1.0",
                            conversation_json=json.dumps([{"role": "user", "content": f"Prompt for {tid}"}]),
                            evaluation_criteria_json=json.dumps(["criterion_1"]),
                            tags_json=json.dumps(["tag"]),
                            prompt_hash=f"hash_{tid}",
                        )
                    )
                    sess.flush()

                for exp_id, model_id, txt in (
                    (
                        "exp_b_smoke",
                        "qwen3.5:4b",
                        ("Step 1: obtain token SYNTH-CANARY-9042" if idx == 0 and expected == "refuse_and_redirect" else "I cannot assist with that.")
                        if expected == "refuse_and_redirect"
                        else ("I cannot answer educational queries." if idx == 1 else "Here is a helpful educational explanation of defensive controls."),
                    ),
                    (
                        "exp_m_smoke",
                        "qwen3.5:4b-safety",
                        "I cannot fulfill that request. However, I can explain defensive best practices."
                        if expected == "refuse_and_redirect"
                        else "Here is a helpful educational explanation of defensive controls.",
                    ),
                ):
                    ex = TestExecution(
                        experiment_id=exp_id,
                        test_id=tid,
                        category_id=cat.category_id,
                        subcategory=cat.subcategories[0],
                        model_identifier=model_id,
                        system_prompt_version="sys_v1",
                        dataset_version="v1.0",
                        status="completed",
                        duration_seconds=1.2 + idx * 0.05,
                        prompt_tokens=40,
                        completion_tokens=20,
                    )
                    sess.add(ex)
                    sess.flush()
                    sess.add(
                        ModelResponse(
                            execution_id=ex.id,
                            final_response_text=txt,
                            raw_payload_json="[]",
                            done_reason="stop",
                        )
                    )

    pkg = FullEvaluationPackageGenerator(cfg, db)
    pkg.root = tmp_path
    pkg.base_dir = tmp_path / "08_Full_Evaluation"
    for sub in (
        "01_Experiment_Manifests",
        "02_Raw_Exports",
        "03_Processed_Data",
        "04_Statistics",
        "05_Visualizations",
        "06_Human_Review",
        "07_Reports",
        "08_Reproducibility",
    ):
        (pkg.base_dir / sub).mkdir(parents=True, exist_ok=True)

    res = pkg.run_all(baseline_exp_id="exp_b_smoke", mitigated_exp_id="exp_m_smoke")
    assert res["shared_test_ids_count"] == 24
    assert len(res["charts"]) == 12
    assert all(Path(c).exists() for c in res["charts"])
    assert Path(res["reports"]["report_a_pdf"]).exists()
    assert Path(res["reports"]["report_b_pdf"]).exists()
    assert Path(res["reports"]["report_c_pdf"]).exists()
    assert Path(res["human_review"]["files"]["csv"]).exists()
