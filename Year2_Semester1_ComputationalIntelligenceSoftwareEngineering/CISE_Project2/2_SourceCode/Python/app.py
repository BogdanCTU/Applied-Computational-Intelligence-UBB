"""Streamlit Main Application Entrypoint.
Provides navigation layout, unified model registry summary, and session state management.
"""
from __future__ import annotations

import sys
from pathlib import Path

_current_dir = Path(__file__).resolve().parent
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))

import pandas as pd
import streamlit as st
from core.settings import get_settings
from database.connection import Database
from database.repository import RepositoryDB
from ml.model_manager import ModelManager

st.set_page_config(
    page_title="C# Defect Predictor | Class & File Bug Detection",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "settings" not in st.session_state:
    st.session_state.settings = get_settings()

if "db" not in st.session_state:
    db = Database(st.session_state.settings.storage.database_path)
    st.session_state.db = db
    st.session_state.repo_db = RepositoryDB(db)


def main() -> None:
    settings = st.session_state.settings
    repo_db = st.session_state.repo_db

    with st.sidebar:
        st.subheader("C# Bug Detection")
        st.caption("Machine Learning-Based Bug Detection in C# Source Code (Class & File Level)")

        page_options = [
            "Dashboard",
            "Repository Collection",
            "Bug Analysis & SZZ",
            "Dataset Management",
            "Model Training",
            "Model Evaluation",
            "Real-World Bug Detection",
            "Settings",
        ]

        if "current_page" not in st.session_state:
            st.session_state.current_page = page_options[0]

        selected_page = st.radio(
            "Navigation",
            options=page_options,
            index=page_options.index(st.session_state.current_page) if st.session_state.current_page in page_options else 0,
        )
        st.session_state.current_page = selected_page

        try:
            stats = repo_db.get_summary_statistics()
            registered_models = ModelManager(settings.storage.models_dir, db=repo_db).list_saved_models()
            st.subheader("Workspace Summary")
            summary_df = pd.DataFrame(
                [
                    {"Item": "Repositories", "Count": f"{stats['repositories_processed']} processed / {stats['repositories_total']}"},
                    {"Item": "Commits", "Count": f"{stats['commits_total']} ({stats['commits_bug_fix']} fixes)"},
                    {"Item": "Class Observations", "Count": str(stats.get("class_observations_total", 0))},
                    {"Item": "Defect-Prone Classes", "Count": str(stats.get("class_observations_buggy", 0))},
                    {"Item": "Candidate-Clean Classes", "Count": str(stats.get("class_observations_non_buggy", 0))},
                    {"Item": "Legacy Methods", "Count": str(stats["observations_total"])},
                    {"Item": "Datasets / Models", "Count": f"{stats['datasets_count']} / {len(registered_models)}"},
                ]
            )
            st.dataframe(summary_df, hide_index=True, width="stretch")
        except Exception:
            pass

        st.caption("CISE Project 2 | Babes-Bolyai University")

    if selected_page == "Dashboard":
        from application.pages.dashboard import render_dashboard
        render_dashboard(repo_db, settings)
    elif selected_page == "Repository Collection":
        from application.pages.repository_collection import render_repository_collection
        render_repository_collection(repo_db, settings)
    elif selected_page == "Bug Analysis & SZZ":
        from application.pages.bug_analysis import render_bug_analysis
        render_bug_analysis(repo_db, settings)
    elif selected_page == "Dataset Management":
        from application.pages.dataset_management import render_dataset_management
        render_dataset_management(repo_db, settings)
    elif selected_page == "Model Training":
        from application.pages.model_training import render_model_training
        render_model_training(repo_db, settings)
    elif selected_page == "Model Evaluation":
        from application.pages.model_evaluation import render_model_evaluation
        render_model_evaluation(repo_db, settings)
    elif selected_page == "Real-World Bug Detection":
        from application.pages.bug_prediction import render_bug_prediction
        render_bug_prediction(repo_db, settings)
    elif selected_page == "Settings":
        from application.pages.settings import render_settings
        render_settings(repo_db, settings)


if __name__ == "__main__":
    main()
