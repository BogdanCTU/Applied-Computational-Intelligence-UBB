"""Model Training page: train Random Forest models, run A-I experiments, compare, and activate."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import streamlit as st

from bug_detector.config import EXPERIMENT_DEFINITIONS
from bug_detector.ml import (
    ExperimentSuiteRunner,
    build_repository_splits,
    compute_classification_metrics,
    save_model_bundle,
    train_random_forest_with_cv,
)
from bug_detector.ml.trainer import load_dataset_records_from_db
from gui.components import get_app_context, safe_json_loads


def render() -> None:
    st.header("Model Training")
    cfg, repo = get_app_context()
    datasets = repo.list_dataset_versions()
    if not datasets:
        st.info("No datasets available. Build a dataset before training.")
        return

    ds_versions = [d["dataset_version"] for d in datasets]

    col_left, col_right = st.columns([2, 3])
    with col_left:
        st.subheader("Train Random Forest Model")
        sel_ds = st.selectbox("Dataset Version", ds_versions)
        exp_code = st.selectbox(
            "Feature Configuration (Experiment)",
            list(EXPERIMENT_DEFINITIONS.keys()),
            index=list(EXPERIMENT_DEFINITIONS.keys()).index(cfg.features.experiment_code),
            format_func=lambda c: f"{c}: {', '.join(EXPERIMENT_DEFINITIONS[c])}",
        )
        n_est = int(st.number_input("n_estimators", min_value=50, max_value=1000, value=cfg.random_forest.n_estimators, step=50))
        max_d = int(st.number_input("max_depth (0 = unlimited)", min_value=0, max_value=100, value=cfg.random_forest.max_depth or 20, step=2))
        min_leaf = int(st.number_input("min_samples_leaf", min_value=1, max_value=20, value=cfg.random_forest.min_samples_leaf))
        outer_folds = int(st.number_input("Outer Grouped-CV Folds", min_value=2, max_value=10, value=cfg.validation.outer_folds))
        tune_hpo = st.checkbox("Run Inner-CV Hyperparameter & Calibration Search", value=False)
        activate_after = st.checkbox("Activate Model After Training", value=True)

        if st.button("Start Training", type="primary"):
            prog = st.progress(0.1, text="Loading dataset records...")
            records, ds_meta = load_dataset_records_from_db(sel_ds, cfg)
            splits = build_repository_splits(
                records,
                independent_test_fraction=cfg.validation.independent_test_repo_fraction,
                temporal_test_fraction=cfg.validation.temporal_test_fraction,
                random_state=cfg.validation.random_state,
            )
            cfg.random_forest.n_estimators = n_est
            cfg.random_forest.max_depth = None if max_d == 0 else max_d
            cfg.random_forest.min_samples_leaf = min_leaf
            cfg.validation.outer_folds = outer_folds

            prog.progress(0.4, text="Fitting Random Forest with repository-grouped CV...")
            bundle = train_random_forest_with_cv(
                dev_records=splits["dev"],
                dataset_version=sel_ds,
                dataset_sha256=ds_meta.get("dataset_sha256"),
                experiment_code=exp_code,
                feature_groups=EXPERIMENT_DEFINITIONS[exp_code],
                config=cfg,
                tune_hyperparameters=tune_hpo,
                tune_calibration=tune_hpo,
            )
            prog.progress(0.8, text="Evaluating on untouched independent test set...")
            X_test, _ = bundle["feature_pipeline"].transform(splits["independent_test"])
            y_test = np.array([int(r["label"]) for r in splits["independent_test"]], dtype=int)
            probs_test = bundle["estimator"].predict_proba(X_test)[:, 1]
            test_m = compute_classification_metrics(
                y_test,
                probs_test,
                bundle["threshold_low"],
                bundle["threshold_center"],
                bundle["threshold_high"],
                repository_ids=[str(r["repository_id"]) for r in splits["independent_test"]],
            )
            mver = f"rf_{exp_code}_{sel_ds}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            bundle["model_version"] = mver
            bundle["experiment_id"] = f"ui_train_{uuid.uuid4().hex[:8]}"
            bundle["independent_test_metrics"] = test_m
            save_model_bundle(mver, bundle, config=cfg, activate=activate_after)
            repo.save_evaluation_result(mver, "dev_nested_cv_oof", bundle["cv_metrics"])
            repo.save_evaluation_result(mver, "independent_test", test_m)
            prog.progress(1.0, text="Completed.")
            st.success(f"Trained {mver} | Independent Test F1={test_m.get('f1')}, PR-AUC={test_m.get('pr_auc')}")

        if st.button("Run Full Experiment Suite (A-I)"):
            with st.spinner("Running Experiments A-I, ablation, and baselines..."):
                summary = ExperimentSuiteRunner(cfg).run_all(dataset_version=sel_ds)
            st.success(f"Suite complete. Champion activated: {summary['champion_model_version']}")

    with col_right:
        st.subheader("Experiment Comparison")
        exps = repo.list_experiments(sel_ds)
        if exps:
            edf = pd.DataFrame(
                [
                    {
                        "Exp": e["experiment_code"],
                        "Groups": ", ".join(safe_json_loads(e["feature_groups_json"], [])),
                        "CV F1": safe_json_loads(e["cv_metrics_json"], {}).get("f1"),
                        "Test F1": safe_json_loads(e["test_metrics_json"], {}).get("f1"),
                        "Test Prec": safe_json_loads(e["test_metrics_json"], {}).get("precision"),
                        "Test Rec": safe_json_loads(e["test_metrics_json"], {}).get("recall"),
                        "Test PR-AUC": safe_json_loads(e["test_metrics_json"], {}).get("pr_auc"),
                        "Test ROC-AUC": safe_json_loads(e["test_metrics_json"], {}).get("roc_auc"),
                        "Test FPR": safe_json_loads(e["test_metrics_json"], {}).get("fpr"),
                        "Time (s)": round(e["duration_seconds"], 1),
                    }
                    for e in exps
                ]
            )
            st.dataframe(edf, width="stretch", hide_index=True)
        else:
            st.info("No experiments recorded yet for this dataset version.")

        st.subheader("Activate Registered Model")
        models = repo.list_models()
        if models:
            model_names = [m["model_version"] for m in models]
            pick = st.selectbox("Model Version", model_names)
            if st.button("Set Active Model"):
                repo.set_active_model(pick)
                chosen = next(m for m in models if m["model_version"] == pick)
                cfg.inference.active_model_version = pick
                cfg.inference.active_model_path = chosen["artifact_path"]
                cfg.thresholds.threshold_low = float(chosen["threshold_low"])
                cfg.thresholds.threshold_center = float(chosen["threshold_center"])
                cfg.thresholds.threshold_high = float(chosen["threshold_high"])
                from bug_detector.config import save_config

                save_config(cfg)
                st.success(f"Activated {pick}")


if __name__ == "__main__":
    render()
