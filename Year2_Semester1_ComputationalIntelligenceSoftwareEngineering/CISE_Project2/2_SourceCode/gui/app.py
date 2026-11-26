"""Streamlit application router for CISE Project v5.0.0."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_source_dir = Path(__file__).resolve().parents[1]
if str(_source_dir) not in sys.path:
    sys.path.insert(0, str(_source_dir))

from gui.pages import (  # noqa: E402
    dashboard,
    dataset_explorer,
    manual_detection,
    model_configuration,
    model_training,
    results,
)


def main() -> None:
    st.set_page_config(
        page_title="C# Source-Code Bug Detector v5.0.0",
        layout="wide",
    )
    pages = [
        st.Page(dashboard.render, title="Dashboard", url_path="dashboard", default=True),
        st.Page(manual_detection.render, title="Manual Detection", url_path="manual-detection"),
        st.Page(results.render, title="Results", url_path="results"),
        st.Page(dataset_explorer.render, title="Dataset Explorer", url_path="dataset-explorer"),
        st.Page(model_training.render, title="Model Training", url_path="model-training"),
        st.Page(model_configuration.render, title="Model Configuration", url_path="model-configuration"),
    ]
    nav = st.navigation(pages)
    nav.run()


if __name__ == "__main__":
    main()
