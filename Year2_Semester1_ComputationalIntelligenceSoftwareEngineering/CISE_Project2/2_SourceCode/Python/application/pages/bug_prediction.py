"""Real-World Bug Prediction Page: Single-Method, Full-File Batch Inference, and Validation."""
from __future__ import annotations

import io
from pathlib import Path
from typing import List
import pandas as pd
import streamlit as st

from core.settings import AppSettings
from database.repository import RepositoryDB
from ml.model_manager import ModelManager
from ml.predictor import (
    BugPredictor,
    MethodPrediction,
    PredictorError,
    NoMethodsFoundError,
    ModelCompatibilityError,
)


def render_risk_badge(risk_category: str, risk_score: float) -> str:
    """Return concise text label for risk presentation."""
    return f"{risk_category} ({risk_score:.3f})"


def render_bug_prediction(db: RepositoryDB, settings: AppSettings) -> None:
    st.title("Defect Prediction")
    st.caption(
        "Extract 26 Roslyn AST static code metrics and estimate method defect risk. "
        "Scores reflect structural defect propensity, not proof of defect presence."
    )

    model_mgr = ModelManager(settings.storage.models_dir, db=db)
    models = model_mgr.list_saved_models()

    if not models:
        st.warning("No trained models found. Train a Random Forest classifier in Model Training first.")
        return

    col_m1, col_m2 = st.columns([2, 1])
    with col_m1:
        model_options = {
            f"{m.get('name', 'unnamed')} (ID: {m.get('id', 'N/A')} | {m.get('algorithm', 'RF')})": m
            for m in models
        }
        selected_label = st.selectbox("Model", list(model_options.keys()))
        selected_model = model_options[selected_label]
    with col_m2:
        st.caption(f"Artifact: `{Path(selected_model.get('model_file_path', '')).name}`")
        st.caption(f"Dataset ID: #{selected_model.get('dataset_id', 'N/A')}")

    try:
        predictor = BugPredictor.from_model_identifier(
            model_identifier=selected_model["model_file_path"],
            models_dir=settings.storage.models_dir,
            model_id=selected_model.get("id"),
            db=db,
            low_threshold=settings.prediction.low_risk_threshold,
            medium_threshold=settings.prediction.medium_risk_threshold,
            persist_history=settings.prediction.persist_history,
            persist_source_code=settings.prediction.persist_source_code,
        )
    except ModelCompatibilityError as e:
        st.error(f"Model compatibility error: {e}")
        return
    except Exception as e:
        st.error(f"Failed to load model bundle: {e}")
        return

    tab_single, tab_file, tab_validation, tab_history = st.tabs([
        "Single Method",
        "C# File Analysis",
        "Repository Validation",
        "Prediction History",
    ])

    sample_method = """public int CalculateDiscount(int customerAge, int purchaseTotal, bool isMember)
{
    int discount = 0;
    if (customerAge > 65)
    {
        discount += 15;
    }
    if (purchaseTotal > 100)
    {
        if (isMember)
        {
            discount += 20;
        }
        else
        {
            discount += 5;
        }
    }
    return discount;
}"""

    # TAB 1: Single Method Analysis
    with tab_single:
        st.subheader("Single C# Method Analysis")

        col_inp, col_opts = st.columns([3, 1])
        with col_inp:
            method_code = st.text_area(
                "C# method source code",
                value=sample_method,
                height=240,
                key="txt_single_method",
            )
        with col_opts:
            st.table(pd.DataFrame([
                {"Risk Band": "Low", "Range": f"0.00 - {predictor.low_threshold:.2f}"},
                {"Risk Band": "Medium", "Range": f"{predictor.low_threshold + 0.01:.2f} - {predictor.medium_threshold:.2f}"},
                {"Risk Band": "High", "Range": f"{predictor.medium_threshold + 0.01:.2f} - 1.00"},
            ]))

        if st.button("Analyze Method", key="btn_single_predict", width="stretch"):
            with st.spinner("Extracting Roslyn metrics and running inference..."):
                try:
                    preds = predictor.predict_code(method_code)
                    if not preds:
                        st.warning("No methods extracted from snippet.")
                    else:
                        p = preds[0]

                        st.subheader("Prediction Result")
                        c_res1, c_res2, c_res3, c_res4 = st.columns(4)
                        c_res1.metric("Method", p.method_name)
                        c_res2.metric("Risk Score", f"{p.risk_score:.3f}")
                        c_res3.metric("Risk Category", p.risk_category)
                        c_res4.metric("Predicted Class", "Defect-Prone (1)" if p.predicted_label == 1 else "Candidate-Clean (0)")

                        st.subheader("Influential Metrics")
                        if p.influential_metrics:
                            inf_df = pd.DataFrame(p.influential_metrics).rename(columns={
                                "feature": "Metric",
                                "value": "Value",
                                "threshold": "Threshold",
                                "global_importance": "Global Importance",
                                "interpretation": "Context",
                            })
                            st.dataframe(inf_df, width="stretch", hide_index=True)
                        else:
                            st.caption("No heuristic complexity thresholds exceeded.")

                        with st.expander("All 26 Extracted Roslyn Metrics"):
                            m_df = pd.DataFrame([{"Metric": k, "Value": v} for k, v in p.metrics.items()])
                            st.dataframe(m_df, width="stretch", hide_index=True)

                except NoMethodsFoundError as nfe:
                    st.error(f"Method extraction error: {nfe}")
                except PredictorError as pe:
                    st.error(f"Prediction error: {pe}")
                except Exception as e:
                    st.error(f"Unexpected error: {e}")

    # TAB 2: Full C# File Analysis
    with tab_file:
        st.subheader("Batch File Analysis (.cs)")

        uploaded_cs = st.file_uploader("Upload C# source file", type=["cs"], key="uploader_cs_file")

        if uploaded_cs:
            file_content = uploaded_cs.read().decode("utf-8", errors="replace")
            st.caption(f"Loaded `{uploaded_cs.name}` ({len(file_content.splitlines())} lines).")

            if st.button("Analyze File Methods", key="btn_file_predict", width="stretch"):
                with st.spinner(f"Analyzing '{uploaded_cs.name}'..."):
                    try:
                        file_preds = predictor.predict_code(file_content, file_name=uploaded_cs.name)
                        st.session_state["file_preds"] = file_preds
                        st.session_state["file_name"] = uploaded_cs.name
                    except NoMethodsFoundError as nfe:
                        st.warning(f"No methods found in file: {nfe}")
                    except Exception as e:
                        st.error(f"File analysis failed: {e}")

        if "file_preds" in st.session_state and st.session_state.get("file_name"):
            file_preds: List[MethodPrediction] = st.session_state["file_preds"]
            st.subheader(f"Results: {st.session_state['file_name']}")

            high_count = sum(1 for p in file_preds if p.risk_category == "High risk")
            med_count = sum(1 for p in file_preds if p.risk_category == "Medium risk")
            low_count = sum(1 for p in file_preds if p.risk_category == "Low risk")

            c_f1, c_f2, c_f3, c_f4 = st.columns(4)
            c_f1.metric("Total Methods", len(file_preds))
            c_f2.metric("High Risk", high_count)
            c_f3.metric("Medium Risk", med_count)
            c_f4.metric("Low Risk", low_count)

            col_flt1, col_flt2 = st.columns(2)
            with col_flt1:
                filter_cat = st.multiselect(
                    "Filter by risk category",
                    ["High risk", "Medium risk", "Low risk"],
                    default=["High risk", "Medium risk", "Low risk"],
                )
            with col_flt2:
                sort_opt = st.selectbox("Sort by", ["Risk Score (Descending)", "Risk Score (Ascending)", "Method Name", "LOC"])

            filtered_preds = [p for p in file_preds if p.risk_category in filter_cat]

            if sort_opt == "Risk Score (Descending)":
                filtered_preds.sort(key=lambda x: x.risk_score, reverse=True)
            elif sort_opt == "Risk Score (Ascending)":
                filtered_preds.sort(key=lambda x: x.risk_score)
            elif sort_opt == "Method Name":
                filtered_preds.sort(key=lambda x: x.method_name)
            elif sort_opt == "LOC":
                filtered_preds.sort(key=lambda x: x.metrics.get("loc", 0), reverse=True)

            table_rows = []
            for p in filtered_preds:
                table_rows.append({
                    "Method": p.method_name,
                    "Class": p.class_name,
                    "Lines": f"L{p.start_line}-L{p.end_line}",
                    "Risk Category": p.risk_category,
                    "Risk Score": round(p.risk_score, 3),
                    "Predicted Class": "Defect-Prone (1)" if p.predicted_label == 1 else "Candidate-Clean (0)",
                    "CC": p.metrics.get("cyclomatic_complexity", 0),
                    "LOC": p.metrics.get("loc", 0),
                    "Nesting": p.metrics.get("max_nesting_depth", 0),
                })

            df_table = pd.DataFrame(table_rows)
            st.dataframe(df_table, width="stretch", hide_index=True)

            csv_buf = io.StringIO()
            df_table.to_csv(csv_buf, index=False)
            st.download_button(
                label="Download Predictions CSV",
                data=csv_buf.getvalue(),
                file_name=f"predictions_{st.session_state['file_name']}.csv",
                mime="text/csv",
                width="stretch",
            )

    # TAB 3: Repository Ground-Truth Validation
    with tab_validation:
        st.subheader("Validation on Mined Observations")
        st.caption("Evaluate the loaded model against SZZ-labeled and candidate-clean observations stored in SQLite.")

        train_repos = set(predictor.split_summary.get("train_repositories", []))
        test_repos = set(predictor.split_summary.get("test_repositories", []))

        col_vopt1, col_vopt2 = st.columns([2, 1])
        with col_vopt1:
            strict_holdout = st.checkbox(
                "Exclude training repositories",
                value=True if train_repos else False,
            )
        with col_vopt2:
            st.caption(f"Training repos: {len(train_repos)} | Holdout repos: {len(test_repos)}")

        obs_list = db.list_observations()
        eval_obs = [o for o in obs_list if o.get("label") in (0, 1)]
        if strict_holdout and train_repos:
            eval_obs = [o for o in eval_obs if o.get("repository_id") not in train_repos]

        if not eval_obs:
            st.caption("No eligible labeled observations match the current filter.")
        else:
            val_limit = st.slider(
                "Observations to evaluate",
                5,
                min(100, len(eval_obs)),
                min(20, len(eval_obs)),
                5,
            )

            if st.button("Run Validation Benchmark", width="stretch"):
                with st.spinner("Evaluating observations..."):
                    results = []
                    for obs in eval_obs[:val_limit]:
                        feat = db.get_features(obs["id"])
                        if not feat:
                            continue

                        raw_metrics = feat.get("raw_metrics", {})
                        if not raw_metrics:
                            raw_metrics = {
                                k: v
                                for k, v in feat.items()
                                if k not in ("id", "observation_id", "extracted_at", "raw_metrics_json", "raw_metrics")
                            }

                        pred = predictor.predict_from_metrics(
                            metrics=raw_metrics,
                            method_name=obs.get("method_name", "Method"),
                            class_name=obs.get("class_name", "Class"),
                            file_name=obs.get("file_path"),
                        )

                        actual_label = obs["label"]
                        predicted_label = pred.predicted_label
                        is_correct = actual_label == predicted_label
                        outcome = (
                            "True Positive"
                            if (actual_label == 1 and predicted_label == 1)
                            else (
                                "True Negative"
                                if (actual_label == 0 and predicted_label == 0)
                                else ("False Positive" if (actual_label == 0 and predicted_label == 1) else "False Negative")
                            )
                        )

                        r_id = obs["repository_id"]
                        part_name = "Holdout" if r_id in test_repos else ("Training" if r_id in train_repos else "External")

                        results.append({
                            "Observation ID": obs["id"],
                            "Repo ID": r_id,
                            "Partition": part_name,
                            "Method": obs["method_name"],
                            "Observed Label": "Defect-Prone (1)" if actual_label == 1 else "Candidate-Clean (0)",
                            "Predicted Class": "Defect-Prone (1)" if predicted_label == 1 else "Candidate-Clean (0)",
                            "Risk Score": round(pred.risk_score, 3),
                            "Outcome": outcome,
                            "Correct": "Yes" if is_correct else "No",
                        })

                    if results:
                        res_df = pd.DataFrame(results)
                        acc = sum(1 for r in results if r["Correct"] == "Yes") / len(results)
                        tp = sum(1 for r in results if r["Outcome"] == "True Positive")
                        fp = sum(1 for r in results if r["Outcome"] == "False Positive")
                        fn = sum(1 for r in results if r["Outcome"] == "False Negative")

                        c_v1, c_v2, c_v3, c_v4 = st.columns(4)
                        c_v1.metric("Accuracy", f"{acc:.1%}")
                        c_v2.metric("True Positives", tp)
                        c_v3.metric("False Positives", fp)
                        c_v4.metric("False Negatives", fn)

                        st.dataframe(res_df, width="stretch", hide_index=True)

                        err_df = res_df[res_df["Outcome"].isin(["False Positive", "False Negative"])]
                        if not err_df.empty:
                            with st.expander("Misclassified Observations (FP / FN)"):
                                st.dataframe(err_df, width="stretch", hide_index=True)

    # TAB 4: Prediction History & Privacy
    with tab_history:
        st.subheader("Prediction History and Privacy")
        st.caption("Source code analysis and inference execute locally.")

        history_rows = db.list_predictions(limit=100)
        c_h1, c_h2, c_h3 = st.columns(3)
        c_h1.metric("Stored Predictions", len(history_rows))
        c_h2.metric("History Logging", "Enabled" if settings.prediction.persist_history else "Disabled")
        c_h3.metric("Source Storage", "Enabled" if settings.prediction.persist_source_code else "Disabled")

        if st.button("Clear Prediction History", key="btn_clear_hist", width="stretch"):
            db.clear_predictions()
            st.rerun()

        if history_rows:
            h_df = pd.DataFrame(history_rows)
            display_cols = ["id", "method_name", "class_name", "file_name", "risk_score", "risk_category", "predicted_label", "created_at"]
            display_cols = [c for c in display_cols if c in h_df.columns]
            st.dataframe(h_df[display_cols], width="stretch", hide_index=True)
        else:
            st.caption("No prediction history recorded.")
