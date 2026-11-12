"""Dashboard Page: System Overview, Health Metrics, Lifecycle Pipeline, and Latest Model Performance."""
from __future__ import annotations

import json
from typing import Any, Dict
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config.settings import AppSettings
from src.database.repository import RepositoryDB


def render_dashboard(db: RepositoryDB, settings: AppSettings) -> None:
    st.header("📊 System Overview & Experiment Dashboard")
    st.markdown("""
    Welcome to the **C# Defect Predictor**! This application implements an end-to-end academic machine learning pipeline
    for identifying defect-prone C# methods using Git mining, SZZ-based bug localization, Roslyn AST static code metric extraction,
    and Random Forest classification.
    """)

    stats = db.get_summary_statistics()

    # -------------------------------------------------------------
    # 1. Primary Metrics Row
    # -------------------------------------------------------------
    st.markdown("### 1. Repository Collection & Mining Statistics")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Managed Repositories", stats["repositories_total"], f"{stats['repositories_cloned']} Cloned Locally")
    with c2:
        st.metric("Analyzed Commits", stats["commits_total"], f"{stats['commits_bug_fix']} Bug-Fixing Commits")
    with c3:
        st.metric("SZZ Inducing Commits (BICs)", stats["szz_bics_total"], "Candidate Root Causes")
    with c4:
        st.metric("Trained Models", stats["models_count"], f"{stats['datasets_count']} Dataset Snapshots")

    st.markdown("---")

    # -------------------------------------------------------------
    # 2. Observations & Feature Extraction Breakdown
    # -------------------------------------------------------------
    st.markdown("### 2. Method Observations & Static Code Metrics")
    total_obs = stats["observations_total"]
    feat_count = stats["features_extracted"]
    feat_pct = (feat_count / total_obs * 100.0) if total_obs > 0 else 0.0

    c_o1, c_o2, c_o3, c_o4 = st.columns(4)
    with c_o1:
        st.metric("Total Observations", total_obs)
    with c_o2:
        st.metric("Buggy Methods (Label 1)", stats["observations_buggy"])
    with c_o3:
        st.metric("Candidate Clean (Label 0)", stats["observations_non_buggy"])
    with c_o4:
        st.metric("Feature Extraction", f"{feat_count} / {total_obs}", f"{feat_pct:.1f}% Complete")

    # Visual distribution chart
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        if total_obs > 0:
            labels_df = pd.DataFrame([
                {"Label": "Buggy (1)", "Count": stats["observations_buggy"]},
                {"Label": "Candidate Clean (0)", "Count": stats["observations_non_buggy"]},
                {"Label": "Uncertain (-1)", "Count": stats["observations_uncertain"]},
            ])
            fig_labels = px.pie(
                labels_df,
                values="Count",
                names="Label",
                title="Observation Class Distribution",
                color="Label",
                color_discrete_map={"Buggy (1)": "#e74c3c", "Candidate Clean (0)": "#2ecc71", "Uncertain (-1)": "#95a5a6"},
                hole=0.4,
            )
            st.plotly_chart(fig_labels, use_container_width=True)
        else:
            st.info("No method observations mined yet. Start by discovering repositories in **Repository Collection**.")

    with col_chart2:
        models = db.list_models()
        if models:
            latest_model = models[0]
            st.markdown(f"#### Latest Model: `{latest_model['name']}`")
            st.caption(f"Algorithm: `{latest_model['algorithm']}` | Created: `{latest_model['created_at']}`")

            raw_m = latest_model.get("metrics_json", "{}")
            metrics = json.loads(raw_m) if isinstance(raw_m, str) else raw_m

            m_col1, m_col2, m_col3 = st.columns(3)
            m_col1.metric("Holdout F1", f"{metrics.get('f1', 0.0):.3f}")
            m_col2.metric("Holdout Acc", f"{metrics.get('accuracy', 0.0):.3f}")
            roc_val = metrics.get("roc_auc")
            m_col3.metric("ROC-AUC", f"{roc_val:.3f}" if roc_val is not None else "N/A")

            # Show Top 3 MDI features if present
            mdi_feats = metrics.get("mdi_feature_importances", [])
            if mdi_feats:
                st.markdown("**Top Defect-Inducing Code Metrics (MDI):**")
                for item in mdi_feats[:3]:
                    st.write(f"- `{item['feature']}`: importance = `{item['importance']:.3f}`")
        else:
            st.info("No trained machine learning model recorded yet. Train one in **Model Training**.")

    st.markdown("---")

    # -------------------------------------------------------------
    # 3. Machine Learning Lifecycle Pipeline Map
    # -------------------------------------------------------------
    st.subheader("🔄 Machine Learning Lifecycle Pipeline")
    cols = st.columns(5)
    with cols[0]:
        st.info("### 1. Discovery\n- GitHub REST API\n- Full Git history clone\n- File diff extraction")
    with cols[1]:
        st.info("### 2. SZZ Mining\n- Bug-fixing heuristics\n- Git blame BIC tracing\n- Method locator")
    with cols[2]:
        st.info("### 3. Roslyn Metrics\n- 24 Code metrics\n- AST & OOP analysis\n- Snapshot generation")
    with cols[3]:
        st.info("### 4. RF Modeling\n- GroupKFold by repo\n- Leakage prevention\n- Permutation importance")
    with cols[4]:
        st.info("### 5. Prediction\n- Real-time inference\n- Multi-method files\n- Influential metrics")

    st.markdown("---")
    st.subheader("📚 Academic Principles & Traceability Guarantees")
    st.markdown("""
    - **Defect Risk Indicator, Not Proof**: Predictions are continuous risk propensities indicating structural complexity, not formal proofs of defect presence or absence.
    - **Zero Cross-Repository Leakage**: All cross-validation and holdout testing partition strictly by `repository_id` (`GroupShuffleSplit` / `GroupKFold`).
    - **SZZ Traceability**: Every buggy observation links deterministically to the bug-introducing commit, fixing commit, and diff context.
    - **Privacy Preserving**: Operates strictly on the local machine with zero telemetry and optional local history logging.
    """)
