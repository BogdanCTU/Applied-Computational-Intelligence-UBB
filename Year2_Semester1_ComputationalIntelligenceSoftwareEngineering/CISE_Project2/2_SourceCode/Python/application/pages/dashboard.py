"""Dashboard Page: System Overview, Class-Level Corpus Metrics, Active Model, and Constraints."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core.settings import AppSettings
from database.repository import RepositoryDB
from ml.model_manager import ModelManager


def render_dashboard(db: RepositoryDB, settings: AppSettings) -> None:
    st.title("Machine Learning-Based Bug Detection in C# Source Code")
    st.caption(
        "Static class- and file-level C# bug detection combining Roslyn AST metrics, "
        "SZZ defect history provenance, and repository-grouped cross-validation."
    )

    stats = db.get_summary_statistics()
    total_classes = stats.get("class_observations_total", 0)
    class_feats = stats.get("class_features_extracted", 0)
    total_methods = stats.get("observations_total", 0)

    # 1. Key Metrics
    st.subheader("Corpus Overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Processed Repositories", stats.get("repositories_processed", 0))
    c2.metric("Registered Repositories", stats.get("repositories_total", 0))
    c3.metric("Class Observations", total_classes)
    c4.metric("SZZ Bug-Inducing Traces", stats.get("szz_bics_total", 0))

    # 2. Label Distribution & Authoritative Active Model
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Class Label Distribution")
        if total_classes > 0:
            labels_df = pd.DataFrame(
                [
                    {
                        "Class": "Defect-Prone Class (1)",
                        "Count": stats.get("class_observations_buggy", 0),
                        "Share": f"{stats.get('class_observations_buggy', 0) / total_classes * 100:.1f}%",
                    },
                    {
                        "Class": "Candidate-Clean Class (0)",
                        "Count": stats.get("class_observations_non_buggy", 0),
                        "Share": f"{stats.get('class_observations_non_buggy', 0) / total_classes * 100:.1f}%",
                    },
                    {
                        "Class": "Uncertain (-1)",
                        "Count": stats.get("class_observations_uncertain", 0),
                        "Share": f"{stats.get('class_observations_uncertain', 0) / total_classes * 100:.1f}%",
                    },
                    {
                        "Class": "Class Features Extracted (40 metrics)",
                        "Count": class_feats,
                        "Share": f"{class_feats / total_classes * 100:.1f}%",
                    },
                    {
                        "Class": "File Observations Tracked",
                        "Count": stats.get("file_observations_total", 0),
                        "Share": "—",
                    },
                    {
                        "Class": "Historical Method Archive",
                        "Count": total_methods,
                        "Share": "Preserved",
                    },
                ]
            )
            st.table(labels_df)
        else:
            st.caption("No class-level observations recorded yet. Run repository collection first.")

    with col_right:
        st.subheader("Active Champion Model (Unified Registry)")
        model_mgr = ModelManager(settings.storage.models_dir, db=db)
        models = model_mgr.list_saved_models()
        if models:
            active = models[0]
            metrics = active.get("metrics", {}) or {}
            roc_val = metrics.get("roc_auc")
            pr_val = metrics.get("average_precision")
            prec_val = metrics.get("precision")
            rec_val = metrics.get("recall")
            f1_val = metrics.get("f1")

            model_summary = pd.DataFrame(
                [
                    {"Property": "Model Name", "Value": str(active.get("name", "N/A"))},
                    {"Property": "Algorithm", "Value": str(active.get("algorithm", "N/A"))},
                    {"Property": "Granularity / Dataset", "Value": f"{active.get('granularity', 'method')} (v{active.get('dataset_version') or active.get('version', '1.0.0')})"},
                    {"Property": "Stored Decision Threshold", "Value": f"{float(active.get('decision_threshold', 0.50)):.2f}"},
                    {"Property": "Holdout Precision / Recall", "Value": f"{prec_val:.3f} / {rec_val:.3f}" if prec_val is not None and rec_val is not None else "N/A"},
                    {"Property": "Holdout F1 / ROC-AUC / PR-AUC", "Value": f"{f1_val:.3f} / {roc_val:.3f} / {pr_val:.3f}" if (f1_val is not None and roc_val is not None and pr_val is not None) else "N/A"},
                    {"Property": "Total Registered Models", "Value": str(len(models))},
                ]
            )
            st.table(model_summary)
        else:
            st.caption("No trained model recorded.")

    # 3. Pipeline Architecture
    st.subheader("Class/File Bug Detection Pipeline")
    cols = st.columns(5)
    steps = [
        ("1. Discovery", ["Paginated GitHub search", "Composite quality ranking", "100+ C# repositories"]),
        ("2. SZZ Mining", ["Strict bug-fix heuristics", "Line blame (-w -M -C)", "Enclosing class attribution"]),
        ("3. Roslyn AST", ["40 class metrics", "Nested type isolation", "Multi-class file parsing"]),
        ("4. Nested ML", ["Outer/Inner GroupKFold", "7 model families", "Inner precision tuning"]),
        ("5. Detection", ["Class & .cs file input", "Stored bundle threshold", "File summary aggregation"]),
    ]
    for col, (title, items) in zip(cols, steps):
        with col:
            st.markdown(f"**{title}**")
            for item in items:
                st.write(f"- {item}")

    # 4. Scientific Boundaries
    st.subheader("Methodological Principles and Constraints")
    principles = [
        ("Prediction scope", "ML-based static indication of potential defects supported by SZZ history, not formal defect proof."),
        ("Repository isolation", "Training, nested CV, and holdout test partitions never share classes from the same repository."),
        ("Nested class isolation", "Roslyn computes class metrics strictly on direct members without double-counting nested types."),
        ("Candidate-clean labels", "Absence of mined bug-fix traces indicates candidate-clean code under the Open-World Assumption."),
        ("Local execution", "Static parsing and inference run locally; network access is only required for GitHub collection."),
    ]
    st.table({"Principle": [p[0] for p in principles], "Description": [p[1] for p in principles]})
