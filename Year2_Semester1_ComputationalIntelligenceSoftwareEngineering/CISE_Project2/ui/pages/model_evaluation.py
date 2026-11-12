"""Model Evaluation Page: Performance Metrics, Discrimination Curves, and Feature Importance."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config.settings import AppSettings
from src.database.repository import RepositoryDB
from src.dataset.dataset_builder import DatasetBuilder
from src.ml.evaluator import ModelEvaluator
from src.ml.model_manager import ModelManager, ModelManagerError
from src.ml.preprocessing import split_by_repository


def render_model_evaluation(db: RepositoryDB, settings: AppSettings) -> None:
    st.header("📈 Model Evaluation & Feature Importance Analysis")
    st.markdown("""
    Evaluate trained Supervised Random Forest models against held-out repositories.
    Inspect generalization performance, confusion matrix distributions, discrimination curves (ROC / PR),
    and analyze structural code metrics via **MDI (Gini)** and **Permutation** feature importances.
    """)

    model_mgr = ModelManager(settings.storage.models_dir, db=db)
    models = model_mgr.list_saved_models()

    if not models:
        st.info("No trained models recorded yet. Please train a Random Forest model on the **Model Training** page first.")
        return

    # Model Selection Dropdown
    model_labels = {
        f"{m.get('name', 'unnamed')} (ID: {m.get('id', 'N/A')} | {m.get('algorithm', 'RF')} | {m.get('created_at', 'recent')})": m
        for m in models
    }
    selected_label = st.selectbox("Select Model to Evaluate", list(model_labels.keys()))
    selected_meta = model_labels[selected_label]

    model_path = selected_meta.get("model_file_path")
    bundle: Optional[Dict[str, Any]] = None
    if model_path and Path(model_path).exists():
        try:
            bundle = model_mgr.load_model(model_path)
        except ModelManagerError as e:
            st.error(f"Could not load model bundle from '{model_path}': {e}")

    # Fallback to DB JSON fields if bundle loading failed
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

    # Overview header
    st.subheader(f"Model: {selected_meta.get('name')}")
    col_hdr1, col_hdr2, col_hdr3 = st.columns(3)
    col_hdr1.caption(f"**Algorithm:** {selected_meta.get('algorithm', 'RandomForestClassifier')}")
    col_hdr2.caption(f"**Dataset ID:** #{dataset_id if dataset_id else 'N/A'}")
    col_hdr3.caption(f"**Active Features:** {len(feature_names)} metrics")

    if not metrics:
        st.warning("No evaluation metrics recorded for this model.")
        return

    # -------------------------------------------------------------
    # 1. High-Level Performance Metrics Cards
    # -------------------------------------------------------------
    st.markdown("### 1. Generalization Performance on Held-Out Repositories")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Accuracy", f"{metrics.get('accuracy', 0.0):.3f}")
    c2.metric("Precision (Buggy)", f"{metrics.get('precision', 0.0):.3f}")
    c3.metric("Recall (Buggy)", f"{metrics.get('recall', 0.0):.3f}")
    c4.metric("F1-Score", f"{metrics.get('f1', 0.0):.3f}")

    roc_val = metrics.get("roc_auc")
    c5.metric("ROC-AUC", f"{roc_val:.3f}" if roc_val is not None else "N/A")

    ap_val = metrics.get("average_precision")
    c6.metric("PR-AUC (AP)", f"{ap_val:.3f}" if ap_val is not None else "N/A")

    st.markdown("---")

    # -------------------------------------------------------------
    # 2. Detailed Tabs
    # -------------------------------------------------------------
    eval_tab1, eval_tab2, eval_tab3, eval_tab4 = st.tabs([
        "🎯 Confusion Matrix & Classification Report",
        "📈 Discrimination Curves (ROC & PR)",
        "📊 Feature Importance (MDI vs Permutation)",
        "📋 Hyperparameters & Provenance",
    ])

    # TAB 1: Confusion Matrix & Report
    with eval_tab1:
        st.subheader("Confusion Matrix on Test Repositories")
        col_cm, col_rep = st.columns([1, 1])

        cm_data = metrics.get("confusion_matrix")
        with col_cm:
            if cm_data and len(cm_data) == 2:
                fig_cm = ModelEvaluator.create_confusion_matrix_figure(cm_data)
                st.plotly_chart(fig_cm, use_container_width=True)
            else:
                st.info("No confusion matrix recorded.")

        with col_rep:
            st.markdown("#### Classification Report Details")
            report = metrics.get("classification_report", {})
            if report:
                report_rows = []
                for label_key, label_display in [("0", "Clean Methods (0)"), ("1", "Buggy Methods (1)")]:
                    if label_key in report:
                        sub = report[label_key]
                        report_rows.append({
                            "Class": label_display,
                            "Precision": round(sub.get("precision", 0.0), 3),
                            "Recall": round(sub.get("recall", 0.0), 3),
                            "F1-Score": round(sub.get("f1-score", 0.0), 3),
                            "Support": sub.get("support", 0),
                        })
                if report_rows:
                    st.dataframe(pd.DataFrame(report_rows), use_container_width=True, hide_index=True)

                st.markdown("##### Global Averages")
                macro = report.get("macro avg", {})
                weighted = report.get("weighted avg", {})
                avg_df = pd.DataFrame([
                    {
                        "Average": "Macro Average",
                        "Precision": round(macro.get("precision", 0.0), 3),
                        "Recall": round(macro.get("recall", 0.0), 3),
                        "F1-Score": round(macro.get("f1-score", 0.0), 3),
                        "Support": macro.get("support", 0),
                    },
                    {
                        "Average": "Weighted Average",
                        "Precision": round(weighted.get("precision", 0.0), 3),
                        "Recall": round(weighted.get("recall", 0.0), 3),
                        "F1-Score": round(weighted.get("f1-score", 0.0), 3),
                        "Support": weighted.get("support", 0),
                    },
                ])
                st.dataframe(avg_df, use_container_width=True, hide_index=True)
            else:
                st.info("No detailed classification report stored.")

    # TAB 2: ROC and PR Curves
    with eval_tab2:
        st.subheader("Discrimination Curves")
        st.markdown("""
        - **ROC Curve**: True Positive Rate (Recall) vs False Positive Rate ($1 - \\text{Specificity}$).
        - **Precision-Recall Curve**: Evaluates performance under class imbalance (Buggy methods are typically minority).
        """)

        # Attempt to reconstruct holdout test split for curve rendering if dataset snapshot exists
        rendered_curves = False
        if bundle and dataset_id:
            try:
                builder = DatasetBuilder(db)
                X_full, y_full, meta_full = builder.get_features_and_labels(dataset_id)
                test_size = 0.25
                rand_s = parameters.get("random_state", 42)
                _, X_te, _, y_te, _, _, _ = split_by_repository(
                    X_full, y_full, meta_full, test_size=test_size, random_state=rand_s
                )

                preprocessor = bundle["preprocessor"]
                model = bundle["model"]
                X_te_proc = preprocessor.transform(X_te)

                col_roc, col_pr = st.columns(2)
                with col_roc:
                    roc_fig = ModelEvaluator.create_roc_curve_figure(model, X_te_proc, y_te)
                    if roc_fig:
                        st.plotly_chart(roc_fig, use_container_width=True)
                with col_pr:
                    pr_fig = ModelEvaluator.create_pr_curve_figure(model, X_te_proc, y_te)
                    if pr_fig:
                        st.plotly_chart(pr_fig, use_container_width=True)
                rendered_curves = True
            except Exception as e:
                st.caption(f"Could not reconstruct test partition for live curves: {e}")

        if not rendered_curves:
            st.info(
                f"Static Curve Metric Values: ROC-AUC = `{metrics.get('roc_auc', 'N/A')}` | "
                f"PR-AUC (Average Precision) = `{metrics.get('average_precision', 'N/A')}`"
            )

    # TAB 3: Feature Importances
    with eval_tab3:
        st.subheader("Feature Importance Rankings")
        st.markdown("""
        - **MDI (Gini Importance)**: Measures how much each metric decreased node impurity across all trees in the forest.
        - **Permutation Importance**: Measures drop in model performance on held-out repositories when values of a metric are randomly permuted.
        """)

        mdi_list = metrics.get("mdi_feature_importances", [])
        perm_list = metrics.get("permutation_feature_importances", [])

        col_mdi, col_perm = st.columns(2)

        with col_mdi:
            st.markdown("#### Mean Decrease in Impurity (MDI)")
            if mdi_list:
                df_mdi = pd.DataFrame(mdi_list)
                top_mdi = df_mdi.head(15).iloc[::-1] # Reverse for bottom-up horizontal bar
                fig_m = px.bar(
                    top_mdi,
                    x="importance",
                    y="feature",
                    orientation="h",
                    title="Top 15 Features by Gini Importance",
                    labels={"importance": "MDI Score", "feature": "Metric"},
                    color="importance",
                    color_continuous_scale="Viridis",
                )
                fig_m.update_layout(yaxis=dict(autorange="reversed"), showlegend=False)
                st.plotly_chart(fig_m, use_container_width=True)
            else:
                st.info("No MDI importances available.")

        with col_perm:
            st.markdown("#### Permutation Importance (Holdout Test)")
            if perm_list:
                df_perm = pd.DataFrame(perm_list)
                top_perm = df_perm.head(15).iloc[::-1]
                fig_p = px.bar(
                    top_perm,
                    x="importance_mean",
                    y="feature",
                    error_x="importance_std" if "importance_std" in top_perm.columns else None,
                    orientation="h",
                    title="Top 15 Features by Permutation Importance",
                    labels={"importance_mean": "Mean Decrease in F1", "feature": "Metric"},
                    color="importance_mean",
                    color_continuous_scale="Cividis",
                )
                fig_p.update_layout(yaxis=dict(autorange="reversed"), showlegend=False)
                st.plotly_chart(fig_p, use_container_width=True)
            else:
                st.info("No Permutation importances recorded.")

        # Full Table of Features
        with st.expander("🔍 View Full Feature Ranking Table"):
            if mdi_list:
                df_all = pd.DataFrame(mdi_list).rename(columns={"importance": "MDI Importance"})
                if perm_list:
                    df_p = pd.DataFrame(perm_list).rename(columns={"importance_mean": "Permutation Mean", "importance_std": "Permutation Std"})
                    df_all = df_all.merge(df_p, on="feature", how="left")
                st.dataframe(df_all, use_container_width=True, hide_index=True)

    # TAB 4: Hyperparameters & Provenance
    with eval_tab4:
        st.subheader("Model Configuration & Training Provenance")
        p_col1, p_col2 = st.columns(2)

        with p_col1:
            st.markdown("#### Hyperparameters")
            if parameters:
                param_rows = [{"Hyperparameter": k, "Configured Value": str(v)} for k, v in parameters.items()]
                st.dataframe(pd.DataFrame(param_rows), use_container_width=True, hide_index=True)
            else:
                st.info("No parameters recorded.")

        with p_col2:
            st.markdown("#### Repository Split Provenance")
            if split_summary:
                st.write(f"- **Training Repositories:** {split_summary.get('train_repo_count', 'N/A')}")
                st.write(f"- **Holdout Test Repositories:** {split_summary.get('test_repo_count', 'N/A')}")
                st.write(f"- **Training Samples:** {split_summary.get('train_samples', 'N/A')}")
                st.write(f"- **Holdout Test Samples:** {split_summary.get('test_samples', 'N/A')}")

                with st.expander("View Training Repositories"):
                    st.write(split_summary.get("train_repos", []))
                with st.expander("View Holdout Test Repositories"):
                    st.write(split_summary.get("test_repos", []))
            else:
                st.info("Split summary not recorded for this model.")

        st.markdown("#### Storage Artifacts")
        st.write(f"- **Artifact File Path:** `{model_path}`")
        if bundle:
            st.write(f"- **Python Version:** `{bundle.get('python_version', 'N/A').splitlines()[0]}`")
            st.write(f"- **scikit-learn Version:** `{bundle.get('sklearn_version', 'N/A')}`")
