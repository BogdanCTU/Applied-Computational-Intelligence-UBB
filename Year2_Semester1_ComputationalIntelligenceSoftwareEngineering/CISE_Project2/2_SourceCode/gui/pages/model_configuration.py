"""Model Configuration page: inspect, validate, and save active model, feature, threshold, and inference settings."""

from __future__ import annotations

import streamlit as st
from pydantic import ValidationError

from bug_detector.config import EXPERIMENT_DEFINITIONS, AppConfig, save_config
from gui.components import get_app_context


def render() -> None:
    st.header("Model Configuration")
    cfg, repo = get_app_context()
    models = repo.list_models()

    model_names = [m["model_version"] for m in models] if models else [cfg.inference.active_model_version or "none"]
    current_idx = model_names.index(cfg.inference.active_model_version) if cfg.inference.active_model_version in model_names else 0

    with st.form("config_form"):
        st.subheader("Active Model & Feature Configuration")
        sel_model = st.selectbox("Active Model Version", model_names, index=current_idx)
        exp_keys = list(EXPERIMENT_DEFINITIONS.keys())
        sel_exp = st.selectbox(
            "Default Experiment Code",
            exp_keys,
            index=exp_keys.index(cfg.features.experiment_code),
        )

        st.subheader("Classification Thresholds & Uncertainty Band")
        c1, c2, c3 = st.columns(3)
        t_low = float(c1.number_input("Threshold Low (CLEAN < low)", min_value=0.01, max_value=0.95, value=float(cfg.thresholds.threshold_low), step=0.01))
        t_center = float(c2.number_input("Threshold Center (Binary)", min_value=0.02, max_value=0.96, value=float(cfg.thresholds.threshold_center), step=0.01))
        t_high = float(c3.number_input("Threshold High (BUG > high)", min_value=0.03, max_value=0.99, value=float(cfg.thresholds.threshold_high), step=0.01))

        st.subheader("Training & Inference Settings")
        t1, t2, t3 = st.columns(3)
        n_est = int(t1.number_input("RF n_estimators", min_value=10, max_value=2000, value=int(cfg.random_forest.n_estimators), step=25))
        max_depth = int(t2.number_input("RF max_depth (0 = None)", min_value=0, max_value=100, value=int(cfg.random_forest.max_depth or 0), step=2))
        require_clean_syntax = t3.checkbox("Require Clean C# Syntax", value=bool(cfg.inference.require_clean_syntax))
        top_ev = int(st.number_input("Top Local Evidence Features", min_value=3, max_value=30, value=int(cfg.inference.top_local_evidence_count)))

        submitted = st.form_submit_button("Validate and Save Configuration", type="primary")

    if submitted:
        try:
            updated_dict = cfg.model_dump()
            updated_dict["features"]["experiment_code"] = sel_exp
            updated_dict["features"]["enabled_groups"] = list(EXPERIMENT_DEFINITIONS[sel_exp])
            updated_dict["thresholds"]["threshold_low"] = t_low
            updated_dict["thresholds"]["threshold_center"] = t_center
            updated_dict["thresholds"]["threshold_high"] = t_high
            updated_dict["random_forest"]["n_estimators"] = n_est
            updated_dict["random_forest"]["max_depth"] = None if max_depth == 0 else max_depth
            updated_dict["inference"]["require_clean_syntax"] = require_clean_syntax
            updated_dict["inference"]["top_local_evidence_count"] = top_ev
            if models and sel_model in [m["model_version"] for m in models]:
                chosen = next(m for m in models if m["model_version"] == sel_model)
                updated_dict["inference"]["active_model_version"] = sel_model
                updated_dict["inference"]["active_model_path"] = chosen["artifact_path"]
                repo.set_active_model(sel_model)

            validated = AppConfig.model_validate(updated_dict)
            saved_path = save_config(validated)
            st.success(f"Configuration validated and saved to {saved_path}")
        except (ValidationError, ValueError) as exc:
            st.error(f"Validation failed: {exc}")

    st.subheader("Current Active JSON Configuration")
    st.json(cfg.model_dump())


if __name__ == "__main__":
    render()
