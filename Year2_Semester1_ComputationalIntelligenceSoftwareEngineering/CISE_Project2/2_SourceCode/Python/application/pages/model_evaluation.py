"""Model Evaluation Page: Performance Metrics, Discrimination Curves, and Feature Importance."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.express as px
import streamlit as st

from core.settings import AppSettings
from database.repository import RepositoryDB
from services.dataset.dataset_builder import DatasetBuilder
from ml.evaluator import ModelEvaluator
from ml.model_manager import ModelManager, ModelManagerError
from ml.preprocessing import split_by_repository


def render_model_evaluation(db: RepositoryDB, settings: AppSettings) -> None:
    st.title("Model Evaluation")
    st.caption("Evaluate trained Random Forest models on held-out repositories, discrimination curves, and feature importances.")

    model_mgr = ModelManager(settings.storage.models_dir, db=db)
    models = model_mgr.list_saved_models()

    if not models:
        st.caption("No trained models recorded. Train a model on the Model Training page first.")
        return

    model_labels = {
        f"{m.get('name', 'unnamed')} (ID: {m.get('id', 'N/A')} | {m.get('algorithm', 'RF')} | {m.get('created_at', 'recent')})": m
        for m in models
    }
    selected_label = st.selectbox("Model", list(model_labels.keys()))
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

    st.caption(
        f"Algorithm: {selected_meta.get('algorithm', 'RandomForestClassifier')} | "
        f"Dataset ID: {dataset_id if dataset_id else 'N/A'} | "
        f"Features: {len(feature_names)}"
    )

    if not metrics:
        st.warning("No evaluation metrics recorded for this model.")
        return

    # 1. Performance Metrics
    st.subheader("Generalization Metrics")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Accuracy", f"{metrics.get('accuracy', 0.0):.3f}")
    c2.metric("Precision", f"{metrics.get('precision', 0.0):.3f}")
    c3.metric("Recall", f"{metrics.get('recall', 0.0):.3f}")
    c4.metric("F1-Score", f"{metrics.get('f1', 0.0):.3f}")

    roc_val = metrics.get("roc_auc")
    c5.metric("ROC-AUC", f"{roc_val:.3f}" if roc_val is not None else "N/A")

    ap_val = metrics.get("average_precision")
    c6.metric("PR-AUC", f"{ap_val:.3f}" if ap_val is not None else "N/A")

    # 2. Detailed Tabs
    eval_tab1, eval_tab2, eval_tab3, eval_tab4 = st.tabs([
        "Confusion Matrix and Report",
        "Discrimination Curves",
        "Feature Importance",
        "Hyperparameters and Provenance",
    ])

    # TAB 1: Confusion Matrix & Report
    with eval_tab1:
        col_cm, col_rep = st.columns(2)

        cm_data = metrics.get("confusion_matrix")
        with col_cm:
            st.subheader("Confusion Matrix")
            if cm_data and len(cm_data) == 2:
                fig_cm = ModelEvaluator.create_confusion_matrix_figure(cm_data)
                st.plotly_chart(fig_cm, width="stretch")
            else:
                st.caption("No confusion matrix recorded.")

        with col_rep:
            st.subheader("Classification Report")
            report = metrics.get("classification_report", {})
            if report:
                report_rows = []
                for label_key, label_display in [("0", "Candidate-Clean (0)"), ("1", "Defect-Prone (1)")]:
                    if label_key in report:
                        sub = report[label_key]
                        report_rows.append({
                            "Class / Average": label_display,
                            "Precision": round(sub.get("precision", 0.0), 3),
                            "Recall": round(sub.get("recall", 0.0), 3),
                            "F1-Score": round(sub.get("f1-score", 0.0), 3),
                            "Support": sub.get("support", 0),
                        })
                for avg_key, avg_display in [("macro avg", "Macro Average"), ("weighted avg", "Weighted Average")]:
                    if avg_key in report:
                        sub = report[avg_key]
                        report_rows.append({
                            "Class / Average": avg_display,
                            "Precision": round(sub.get("precision", 0.0), 3),
                            "Recall": round(sub.get("recall", 0.0), 3),
                            "F1-Score": round(sub.get("f1-score", 0.0), 3),
                            "Support": sub.get("support", 0),
                        })
                if report_rows:
                    st.table(pd.DataFrame(report_rows))
            else:
                st.caption("No classification report stored.")

    # TAB 2: ROC and PR Curves
    with eval_tab2:
        st.subheader("ROC and Precision-Recall Curves")

        rendered_curves = False
        if bundle and dataset_id:
            try:
                builder = DatasetBuilder(db)
                X_full, y_full, meta_full = builder.get_features_and_labels(dataset_id)
                rand_s = parameters.get("random_state", 42)
                _, X_te, _, y_te, _, _, _ = split_by_repository(
                    X_full, y_full, meta_full, test_size=0.25, random_state=rand_s
                )

                preprocessor = bundle["preprocessor"]
                model = bundle["model"]
                X_te_proc = preprocessor.transform(X_te)

                col_roc, col_pr = st.columns(2)
                with col_roc:
                    roc_fig = ModelEvaluator.create_roc_curve_figure(model, X_te_proc, y_te)
                    if roc_fig:
                        st.plotly_chart(roc_fig, width="stretch")
                with col_pr:
                    pr_fig = ModelEvaluator.create_pr_curve_figure(model, X_te_proc, y_te)
                    if pr_fig:
                        st.plotly_chart(pr_fig, width="stretch")
                rendered_curves = True
            except Exception as e:
                st.caption(f"Test partition curve reconstruction unavailable: {e}")

        if not rendered_curves:
            st.table(pd.DataFrame([
                {"Metric": "ROC-AUC", "Value": str(metrics.get("roc_auc", "N/A"))},
                {"Metric": "PR-AUC (Average Precision)", "Value": str(metrics.get("average_precision", "N/A"))},
            ]))

    # TAB 3: Feature Importances
    with eval_tab3:
        st.subheader("Feature Importance Rankings")
        st.caption("Mean Decrease in Impurity (MDI) vs. out-of-sample Permutation Importance.")

        mdi_list = metrics.get("mdi_feature_importances", [])
        perm_list = metrics.get("permutation_feature_importances", [])

        col_mdi, col_perm = st.columns(2)

        with col_mdi:
            if mdi_list:
                df_mdi = pd.DataFrame(mdi_list)
                top_mdi = df_mdi.head(15).iloc[::-1]
                fig_m = px.bar(
                    top_mdi,
                    x="importance",
                    y="feature",
                    orientation="h",
                    title="Top 15 Features (MDI / Gini)",
                    labels={"importance": "MDI Score", "feature": "Metric"},
                )
                fig_m.update_layout(yaxis=dict(autorange="reversed"), showlegend=False)
                st.plotly_chart(fig_m, width="stretch")
            else:
                st.caption("No MDI importances available.")

        with col_perm:
            if perm_list:
                df_perm = pd.DataFrame(perm_list)
                top_perm = df_perm.head(15).iloc[::-1]
                fig_p = px.bar(
                    top_perm,
                    x="importance_mean",
                    y="feature",
                    error_x="importance_std" if "importance_std" in top_perm.columns else None,
                    orientation="h",
                    title="Top 15 Features (Permutation)",
                    labels={"importance_mean": "Mean Decrease in F1", "feature": "Metric"},
                )
                fig_p.update_layout(yaxis=dict(autorange="reversed"), showlegend=False)
                st.plotly_chart(fig_p, width="stretch")
            else:
                st.caption("No permutation importances recorded.")

        with st.expander("Full Feature Ranking Table"):
            if mdi_list:
                df_all = pd.DataFrame(mdi_list).rename(columns={"importance": "MDI Importance"})
                if perm_list:
                    df_p = pd.DataFrame(perm_list).rename(columns={"importance_mean": "Permutation Mean", "importance_std": "Permutation Std"})
                    df_all = df_all.merge(df_p, on="feature", how="left")
                st.dataframe(df_all, width="stretch", hide_index=True)

    # TAB 4: Hyperparameters & Provenance
    with eval_tab4:
        p_col1, p_col2 = st.columns(2)

        with p_col1:
            st.subheader("Hyperparameters")
            if parameters:
                param_rows = [{"Parameter": k, "Value": str(v)} for k, v in parameters.items()]
                st.table(pd.DataFrame(param_rows))
            else:
                st.caption("No parameters recorded.")

        with p_col2:
            st.subheader("Repository Split Provenance")
            if split_summary:
                prov_rows = [
                    {"Property": "Training Repositories", "Value": str(split_summary.get("train_repo_count", "N/A"))},
                    {"Property": "Holdout Repositories", "Value": str(split_summary.get("test_repo_count", "N/A"))},
                    {"Property": "Training Methods", "Value": str(split_summary.get("train_samples", "N/A"))},
                    {"Property": "Holdout Methods", "Value": str(split_summary.get("test_samples", "N/A"))},
                ]
                st.table(pd.DataFrame(prov_rows))

                with st.expander("Repository Lists"):
                    st.write("Training:", split_summary.get("train_repos", []))
                    st.write("Holdout:", split_summary.get("test_repos", []))
            else:
                st.caption("Split provenance not recorded.")

        st.subheader("Artifact Metadata")
        meta_rows = [{"Property": "Artifact Path", "Value": str(model_path)}]
        if bundle:
            meta_rows.append({"Property": "Python Version", "Value": bundle.get("python_version", "N/A").splitlines()[0]})
            meta_rows.append({"Property": "scikit-learn Version", "Value": str(bundle.get("sklearn_version", "N/A"))})
        st.table(pd.DataFrame(meta_rows))
