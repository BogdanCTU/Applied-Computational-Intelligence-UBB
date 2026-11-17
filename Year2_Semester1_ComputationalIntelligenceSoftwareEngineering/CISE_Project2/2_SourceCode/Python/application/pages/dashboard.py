"""Dashboard Page: System Overview, Summary Metrics, Pipeline, and Methodological Constraints."""
from __future__ import annotations

import json
import pandas as pd
import streamlit as st

from core.settings import AppSettings
from database.repository import RepositoryDB


def render_dashboard(db: RepositoryDB, settings: AppSettings) -> None:
    st.title("Dashboard")
    st.caption("System summary, observation breakdown, pipeline overview, and methodological constraints.")

    stats = db.get_summary_statistics()
    total_obs = stats["observations_total"]
    feat_count = stats["features_extracted"]

    # 1. Key Metrics
    st.subheader("System Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Repositories", stats["repositories_total"])
    c2.metric("Analyzed Commits", stats["commits_total"])
    c3.metric("SZZ Bug-Inducing Commits", stats["szz_bics_total"])
    c4.metric("Method Observations", total_obs)

    # 2. Observation Distribution & Latest Model
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Observation Distribution")
        if total_obs > 0:
            labels_df = pd.DataFrame(
                [
                    {
                        "Class": "Defect-Prone (1)",
                        "Count": stats["observations_buggy"],
                        "Share": f"{stats['observations_buggy'] / total_obs * 100:.1f}%",
                    },
                    {
                        "Class": "Candidate-Clean (0)",
                        "Count": stats["observations_non_buggy"],
                        "Share": f"{stats['observations_non_buggy'] / total_obs * 100:.1f}%",
                    },
                    {
                        "Class": "Uncertain (-1)",
                        "Count": stats["observations_uncertain"],
                        "Share": f"{stats['observations_uncertain'] / total_obs * 100:.1f}%",
                    },
                    {
                        "Class": "Features Extracted",
                        "Count": feat_count,
                        "Share": f"{feat_count / total_obs * 100:.1f}%",
                    },
                ]
            )
            st.table(labels_df)
        else:
            st.caption("No method observations recorded.")

    with col_right:
        st.subheader("Latest Registered Model")
        models = db.list_models()
        if models:
            latest_model = models[0]
            raw_m = latest_model.get("metrics_json", "{}")
            metrics = json.loads(raw_m) if isinstance(raw_m, str) else raw_m
            roc_val = metrics.get("roc_auc")

            model_summary = pd.DataFrame(
                [
                    {"Property": "Model Name", "Value": str(latest_model.get("name", "N/A"))},
                    {"Property": "Algorithm", "Value": str(latest_model.get("algorithm", "N/A"))},
                    {"Property": "Holdout F1", "Value": f"{metrics.get('f1', 0.0):.3f}"},
                    {"Property": "Holdout Accuracy", "Value": f"{metrics.get('accuracy', 0.0):.3f}"},
                    {"Property": "Holdout ROC-AUC", "Value": f"{roc_val:.3f}" if roc_val is not None else "N/A"},
                ]
            )
            st.table(model_summary)
        else:
            st.caption("No trained model recorded.")

    # 3. Machine Learning Lifecycle Pipeline
    st.subheader("Machine Learning Lifecycle Pipeline")

    cols = st.columns(5)

    steps = [
        ("1. Discovery", [
            "GitHub REST API",
            "Git history",
            "File diffs",
        ]),
        ("2. SZZ Mining", [
            "Fix commit detection",
            "Git tracing",
            "Method localization",
        ]),
        ("3. Roslyn Metrics", [
            "26 code metrics",
            "AST analysis",
            "OOP metrics",
        ]),
        ("4. RF Modeling", [
            "Repository GroupKFold",
            "Model evaluation",
            "Feature importance",
        ]),
        ("5. Prediction", [
            "Method-level inference",
            "Risk classification",
            "Metric contributions",
        ]),
    ]

    for col, (title, items) in zip(cols, steps):
        with col:
            st.markdown(f"**{title}**")
            for item in items:
                st.write(f"- {item}")

    # 4. Academic Principles and Methodological Constraints
    st.subheader("Academic Principles and Methodological Constraints")

    principles = [
        (
            "Prediction scope",
            "Defect-proneness indicator, not proof of defect presence.",
        ),
        (
            "Repository separation",
            "GroupKFold separates repositories between training and validation.",
        ),
        (
            "SZZ traceability",
            "Positive labels retain links to fixing commits and traced bug-inducing changes.",
        ),
        (
            "Candidate-clean labels",
            "Absence of recorded bug-fixing traces does not establish defect-free code.",
        ),
        (
            "Privacy",
            "Source analysis and prediction run locally. Repository collection requires network access.",
        ),
    ]

    st.table(
        {
            "Principle": [item[0] for item in principles],
            "Description": [item[1] for item in principles],
        }
    )
