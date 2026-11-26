"""Model Evaluation Page: Repository-Aware Class & Legacy Model Benchmarks, Curves, and Feature Importance."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.express as px
import streamlit as st

from core.settings import AppSettings, PROJECT_ROOT
from database.repository import RepositoryDB
from services.dataset.dataset_builder import DatasetBuilder
from ml.evaluator import ModelEvaluator
from ml.model_manager import ModelManager, ModelManagerError
from ml.preprocessing import split_by_repository


def render_model_evaluation(db: RepositoryDB, settings: AppSettings) -> None:
    st.title("Model Evaluation")
    st.caption(
        "Inspect repository-grouped nested cross-validation and untouched holdout results across "
        "all retained model families."
    )

    # Display Top-200 class-level benchmark comparison (falling back to v3 if v4 not generated yet)
    top200_comp = PROJECT_ROOT / "3_TestResults" / "Top200ClassifierOptimization" / "top200_model_comparison.csv"
    top200_ho = PROJECT_ROOT / "3_TestResults" / "Top200ClassifierOptimization" / "top200_holdout_results.csv"
    top200_loc = PROJECT_ROOT / "3_TestResults" / "Top200ClassifierOptimization" / "method_localizer_evaluation.json"
    comp_csv = top200_comp if top200_comp.exists() else (PROJECT_ROOT / "3_TestResults" / "ClassModelOptimization" / "class_model_comparison.csv")
    ho_csv = top200_ho if top200_ho.exists() else (PROJECT_ROOT / "3_TestResults" / "ClassModelOptimization" / "class_holdout_results.csv")
    if comp_csv.exists():
        with st.expander("Multi-Model Bug Classifier Benchmark (Nested GroupKFold & Untouched Holdout)", expanded=True):
            st.caption("Nested cross-validation OOF results across all evaluated model families:")
            df_comp = pd.read_csv(comp_csv)
            show_cols = [
                c for c in [
                    "config_id", "family", "recommended_threshold",
                    "oof_precision", "oof_recall", "oof_f1", "oof_fpr", "oof_fnr",
                    "oof_roc_auc", "oof_pr_auc", "oof_brier",
                ] if c in df_comp.columns
            ]
            st.dataframe(df_comp[show_cols], hide_index=True, width="stretch")
            if ho_csv.exists():
                st.caption("One-shot Independent Untouched Holdout Repository Evaluation (with FPR & FNR):")
                st.dataframe(pd.read_csv(ho_csv), hide_index=True, width="stretch")
            if top200_loc.exists():
                loc_eval = json.loads(top200_loc.read_text(encoding="utf-8"))
                hm = loc_eval.get("holdout_metrics", {})
                st.caption(
                    f"Separately Validated Method Localizer Holdout — Precision: {hm.get('precision', 0):.3f}, "
                    f"Recall: {hm.get('recall', 0):.3f}, F1: {hm.get('f1', 0):.3f}, ROC-AUC: {hm.get('roc_auc', 0):.3f}, "
                    f"Top-1 BUG Class Hit: {loc_eval.get('holdout_top1_class_hit_rate', 0):.1%}, "
                    f"Top-3 Hit: {loc_eval.get('holdout_top3_class_hit_rate', 0):.1%}"
                )

    model_mgr = ModelManager(settings.storage.models_dir, db=db)
    models = model_mgr.list_saved_models()

    if not models:
        st.caption("No trained models recorded. Train a model on the Model Training page first.")
        return

    model_labels = {
        f"{m.get('name', 'unnamed')} ({m.get('granularity', 'method')} | {m.get('algorithm', 'Model')} | tau={float(m.get('decision_threshold', 0.50)):.2f})": m
        for m in models
    }
    selected_label = st.selectbox("Model (Unified Registry)", list(model_labels.keys()))
    selected_meta = model_labels[selected_label]

    model_path = selected_meta.get("model_file_path")
    bundle: Optional[Dict[str, Any]] = None
    if model_path and Path(model_path).exists():
        try:
            bundle = model_mgr.load_model(model_path)
        except ModelManagerError as e:
            st.error(f"Could not load model bundle from '{model_path}': {e}")

    metrics: Dict[str, Any] = {}
    parameters: Dict[str, Any] = {}
    feature_names: List[str] = []
    split_summary: Dict[str, Any] = {}
    dataset_id: Optional[int] = selected_meta.get("dataset_id")

    if bundle:
        metrics = bundle.get("metrics", {})
        parameters = bundle.get("parameters", {})
        feature_names = bundle.get("feature_names", [])
        split_summary = bundle.get("split_summary", {})
        dataset_id = bundle.get("dataset_id", dataset_id)
    else:
        raw_m = selected_meta.get("metrics_json") or selected_meta.get("metrics", {})
        metrics = json.loads(raw_m) if isinstance(raw_m, str) else raw_m
        raw_p = selected_meta.get("parameters_json") or selected_meta.get("parameters", {})
        parameters = json.loads(raw_p) if isinstance(raw_p, str) else raw_p
        raw_f = selected_meta.get("feature_names_json") or selected_meta.get("feature_names", [])
        feature_names = json.loads(raw_f) if isinstance(raw_f, str) else raw_f

    decision_thresh = float(
        (bundle.get("decision_threshold") if bundle else None)
        or selected_meta.get("decision_threshold")
        or metrics.get("decision_threshold")
        or 0.50
    )

    st.caption(
        f"Algorithm: {selected_meta.get('algorithm', 'Model')} | "
        f"Granularity: {selected_meta.get('granularity', 'method')} | "
        f"Dataset ID: {dataset_id if dataset_id else 'N/A'} | "
        f"Stored Threshold: {decision_thresh:.2f} | "
        f"Features: {len(feature_names)}"
    )

    if not metrics:
        st.warning("No evaluation metrics recorded for this model.")
        return

    # 1. Generalization Metrics
    st.subheader("Holdout / Evaluation Metrics")
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric("Precision", f"{metrics.get('precision', 0.0):.3f}")
    c2.metric("Recall", f"{metrics.get('recall', 0.0):.3f}")
    c3.metric("F1-Score", f"{metrics.get('f1', 0.0):.3f}")
    c4.metric("Accuracy", f"{metrics.get('accuracy', 0.0):.3f}")
    roc_val = metrics.get("roc_auc")
    c5.metric("ROC-AUC", f"{roc_val:.3f}" if roc_val is not None else "N/A")
    ap_val = metrics.get("average_precision")
    c6.metric("PR-AUC", f"{ap_val:.3f}" if ap_val is not None else "N/A")
    brier_val = metrics.get("brier_score")
    c7.metric("Brier", f"{brier_val:.3f}" if brier_val is not None else "N/A")

    eval_tab1, eval_tab2, eval_tab3, eval_tab4 = st.tabs([
        "Confusion Matrix & Nested CV",
        "Discrimination Curves",
        "Feature Importance",
        "Hyperparameters & Provenance",
    ])

    with eval_tab1:
        col_cm, col_rep = st.columns(2)
        cm_data = metrics.get("confusion_matrix")
        with col_cm:
            st.subheader("Confusion Matrix")
            if cm_data and len(cm_data) == 2:
                st.plotly_chart(ModelEvaluator.create_confusion_matrix_figure(cm_data), width="stretch")
            else:
                st.caption("No confusion matrix recorded.")

        with col_rep:
            st.subheader("Nested CV vs. Holdout Summary")
            nested_oof = metrics.get("nested_cv_oof")
            if nested_oof:
                summary_rows = [
                    {
                        "Metric": k.upper(),
                        "Nested CV Pooled OOF": f"{nested_oof.get(k, 0.0):.4f}" if isinstance(nested_oof.get(k), (int, float)) else str(nested_oof.get(k)),
                        "Untouched Holdout": f"{metrics.get(k if k != 'pr_auc' else 'average_precision', 0.0):.4f}",
                    }
                    for k in ["precision", "recall", "f1", "accuracy", "roc_auc", "pr_auc", "brier_score"]
                    if k in nested_oof
                ]
                st.table(pd.DataFrame(summary_rows))
            else:
                report = metrics.get("classification_report", {})
                if report:
                    report_rows = [
                        {
                            "Class": label_display,
                            "Precision": round(report[label_key].get("precision", 0.0), 3),
                            "Recall": round(report[label_key].get("recall", 0.0), 3),
                            "F1-Score": round(report[label_key].get("f1-score", 0.0), 3),
                            "Support": report[label_key].get("support", 0),
                        }
                        for label_key, label_display in [("0", "Candidate-Clean (0)"), ("1", "Defect-Prone (1)")]
                        if label_key in report
                    ]
                    st.table(pd.DataFrame(report_rows))

    with eval_tab2:
        st.subheader("ROC and Precision-Recall Curves")
        rendered = False
        if bundle and dataset_id:
            try:
                builder = DatasetBuilder(db)
                X_full, y_full, meta_full = builder.get_features_and_labels(dataset_id)
                if split_summary and split_summary.get("test_repositories"):
                    test_repo_set = set(split_summary["test_repositories"])
                    te_mask = meta_full["repository_id"].isin(test_repo_set)
                    X_te, y_te = X_full[te_mask], y_full[te_mask]
                else:
                    _, X_te, _, y_te, _, _, _ = split_by_repository(
                        X_full, y_full, meta_full, test_size=0.25, random_state=parameters.get("random_state", 42)
                    )
                preprocessor = bundle["preprocessor"]
                model = bundle["model"]
                X_te_proc = preprocessor.transform(X_te)
                for col in feature_names:
                    if col not in X_te_proc.columns:
                        X_te_proc[col] = 0.0
                X_te_proc = X_te_proc[feature_names]

                col_roc, col_pr = st.columns(2)
                with col_roc:
                    roc_fig = ModelEvaluator.create_roc_curve_figure(model, X_te_proc, y_te)
                    if roc_fig:
                        st.plotly_chart(roc_fig, width="stretch")
                with col_pr:
                    pr_fig = ModelEvaluator.create_pr_curve_figure(model, X_te_proc, y_te)
                    if pr_fig:
                        st.plotly_chart(pr_fig, width="stretch")
                rendered = True
            except Exception as e:
                st.caption(f"Holdout curve reconstruction unavailable: {e}")

        if not rendered:
            st.table(pd.DataFrame([
                {"Metric": "ROC-AUC", "Value": str(metrics.get("roc_auc", "N/A"))},
                {"Metric": "PR-AUC (Average Precision)", "Value": str(metrics.get("average_precision", "N/A"))},
            ]))

    with eval_tab3:
        st.subheader("Feature Importance Rankings")
        mdi_list = metrics.get("mdi_feature_importances", [])
        perm_list = metrics.get("permutation_feature_importances", [])
        col_mdi, col_perm = st.columns(2)
        with col_mdi:
            if mdi_list:
                top_mdi = pd.DataFrame(mdi_list).head(15).iloc[::-1]
                fig_m = px.bar(top_mdi, x="importance", y="feature", orientation="h", title="Top 15 Features (MDI)")
                fig_m.update_layout(yaxis=dict(autorange="reversed"), showlegend=False)
                st.plotly_chart(fig_m, width="stretch")
            else:
                st.caption("No MDI importances available for this estimator.")
        with col_perm:
            if perm_list:
                top_perm = pd.DataFrame(perm_list).head(15).iloc[::-1]
                fig_p = px.bar(
                    top_perm, x="importance_mean", y="feature",
                    error_x="importance_std" if "importance_std" in top_perm.columns else None,
                    orientation="h", title="Top 15 Features (Holdout Permutation)",
                )
                fig_p.update_layout(yaxis=dict(autorange="reversed"), showlegend=False)
                st.plotly_chart(fig_p, width="stretch")
            else:
                st.caption("No permutation importances recorded.")

    with eval_tab4:
        p_col1, p_col2 = st.columns(2)
        with p_col1:
            st.subheader("Hyperparameters")
            if parameters:
                st.table(pd.DataFrame([{"Parameter": k, "Value": str(v)} for k, v in parameters.items()]))
        with p_col2:
            st.subheader("Repository Split Provenance")
            if split_summary:
                unit_lbl = "Classes" if selected_meta.get("granularity") == "class" else "Methods"
                st.table(pd.DataFrame([
                    {"Property": "Training Repositories", "Value": str(split_summary.get("train_repo_count", "N/A"))},
                    {"Property": "Holdout Repositories", "Value": str(split_summary.get("test_repo_count", "N/A"))},
                    {"Property": f"Training {unit_lbl}", "Value": str(split_summary.get("train_samples", "N/A"))},
                    {"Property": f"Holdout {unit_lbl}", "Value": str(split_summary.get("test_samples", "N/A"))},
                ]))
        st.subheader("Artifact Metadata")
        meta_rows = [
            {"Property": "Artifact Path", "Value": str(model_path)},
            {"Property": "Stored Decision Threshold", "Value": f"{decision_thresh:.4f}"},
        ]
        if bundle:
            meta_rows.append({"Property": "Python Version", "Value": bundle.get("python_version", "N/A").splitlines()[0]})
            meta_rows.append({"Property": "scikit-learn Version", "Value": str(bundle.get("sklearn_version", "N/A"))})
        st.table(pd.DataFrame(meta_rows))
