"""Real-World Bug Detection Page: BUG / CLEAN Class Classifier, Multi-Class .cs Analysis & Localization."""
from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd
import streamlit as st

from core.settings import AppSettings
from database.repository import RepositoryDB
from ml.model_manager import ModelManager
from ml.predictor import (
    BugPredictor,
    ClassPrediction,
    FilePredictionResult,
    ModelCompatibilityError,
    NoClassesFoundError,
    NoMethodsFoundError,
    PredictorError,
)


def _highlight_class_rows(row: pd.Series) -> List[str]:
    cls_val = str(row.get("Classification", row.get("Predicted Classification", "")))
    if cls_val in ("BUG", "BUG DETECTED", "Defect-Prone (1)") or row.get("Risk Category") == "High risk":
        return ["background-color: rgba(192, 57, 43, 0.16)"] * len(row)
    return [""] * len(row)


def format_class_verdict(cp: ClassPrediction) -> Dict[str, Any]:
    """Build deterministic GUI presentation payload for a single classified C# class."""
    is_bug = (cp.predicted_label == 1) or (cp.classification == "BUG")
    verdict = "BUG DETECTED" if is_bug else "CLEAN"
    severity = "error" if is_bug else "success"
    return {
        "verdict": verdict,
        "severity": severity,
        "classification": "BUG" if is_bug else "CLEAN",
        "confidence_pct": round(float(cp.confidence) * 100.0, 1),
        "bug_probability": round(float(cp.defect_probability), 4),
        "threshold": round(float(cp.decision_threshold), 4),
        "explanation": cp.explanation_summary,
        "limitation": cp.limitation_note,
    }


def format_file_verdict(fres: FilePredictionResult) -> Dict[str, Any]:
    """Build deterministic GUI presentation payload for a multi-class .cs source file."""
    fc = fres.file_classification
    if fc == "BUG":
        verdict = "BUG DETECTED"
        severity = "error"
        banner_detail = f"{fres.classes_bug_count} of {fres.classes_analyzed_count} class(es) classified as BUG."
    elif fc == "BUG (PARTIAL ANALYSIS)":
        verdict = "BUG DETECTED (PARTIAL ANALYSIS)"
        severity = "error"
        banner_detail = (
            f"{fres.classes_bug_count} class(es) classified as BUG, but {fres.classes_failed_count} class(es) "
            f"failed analysis and {fres.syntax_error_count} syntax error(s) were reported."
        )
    elif fc == "CLEAN":
        verdict = "CLEAN"
        severity = "success"
        banner_detail = f"All {fres.classes_analyzed_count} analyzed class(es) classified as CLEAN."
    else:
        verdict = "ANALYSIS INCOMPLETE — CANNOT CLASSIFY AS CLEAN"
        severity = "warning"
        banner_detail = (
            f"No BUG detected among {fres.classes_analyzed_count} analyzed class(es), but "
            f"{fres.classes_failed_count} class(es) could not be analyzed cleanly and "
            f"{fres.syntax_error_count} Roslyn syntax error(s) occurred."
        )
    return {
        "verdict": verdict,
        "severity": severity,
        "banner_detail": banner_detail,
        "analysis_complete": fres.analysis_complete,
        "classes_bug_count": fres.classes_bug_count,
        "classes_clean_count": fres.classes_clean_count,
        "classes_failed_count": fres.classes_failed_count,
        "syntax_error_count": fres.syntax_error_count,
    }


def _render_verdict_banner(severity: str, message: str) -> None:
    if severity == "error":
        st.error(message)
    elif severity == "success":
        st.success(message)
    else:
        st.warning(message)


def _render_localization_panel(cp: ClassPrediction) -> None:
    st.subheader("Bug Localization & Evidence")
    loc = cp.localization
    if loc is None or cp.predicted_label == 0:
        st.info("No bug localization needed for a CLEAN classification.")
        return

    st.caption(loc.summary_note)
    if loc.verified_historical_locations:
        st.markdown("**Verified Historical SZZ Evidence (Observed in Mined Git History)**")
        hist_rows = [
            {
                "Repository": h.repository_name,
                "Method": h.method_name or "__class_scope__",
                "Affected Lines": ", ".join(str(x) for x in h.affected_lines) if h.affected_lines else "N/A",
                "Line Ranges": ", ".join(f"L{r['start']}-L{r['end']}" for r in h.affected_line_ranges) if h.affected_line_ranges else "N/A",
                "Fix Commit": (h.bug_fix_commit_sha or "")[:8],
                "SZZ Confidence": h.szz_confidence,
            }
            for h in loc.verified_historical_locations
        ]
        st.dataframe(pd.DataFrame(hist_rows), hide_index=True, width="stretch")
    else:
        st.info("Exact source line localization: **Unavailable** (no matching verified historical SZZ defect trace).")

    if loc.ml_suspicious_methods:
        st.markdown("**Separately Validated ML Method Localizer (Suspicious Member Methods — Not Exact Line Proof)**")
        ml_rows = [
            {
                "Method": m.method_name,
                "Lines": f"L{m.start_line}-L{m.end_line}",
                "ML Verdict": "SUSPICIOUS" if m.is_suspicious else "CLEAN METHOD",
                "Method Bug Probability": round(m.probability, 4),
                "Cyclomatic Complexity": m.cyclomatic_complexity,
                "LOC": m.loc,
            }
            for m in loc.ml_suspicious_methods
        ]
        st.dataframe(pd.DataFrame(ml_rows), hide_index=True, width="stretch")
    st.caption(loc.limitation_note)


def render_bug_prediction(db: RepositoryDB, settings: AppSettings) -> None:
    st.title("Real-World C# Bug Detection Classifier")
    st.caption(
        "Static ML bug detection classifier distinguishing BUG vs CLEAN across complete C# classes and multi-class .cs files. "
        "Classifications reflect patterns learned from historical SZZ defect evidence, not formal verification."
    )

    model_mgr = ModelManager(settings.storage.models_dir, db=db)
    models = model_mgr.list_saved_models()

    if not models:
        st.warning("No trained models found. Train a model in Model Training first.")
        return

    col_m1, col_m2 = st.columns([2, 1])
    with col_m1:
        model_options = {
            f"{m.get('name', 'unnamed')} ({m.get('granularity', 'method')} | {m.get('algorithm', 'Model')} | tau={float(m.get('decision_threshold', 0.50)):.2f})": m
            for m in models
        }
        selected_label = st.selectbox("Classifier Bundle (Unified Registry)", list(model_options.keys()))
        selected_model = model_options[selected_label]
    with col_m2:
        st.caption(f"Artifact: `{Path(selected_model.get('model_file_path', '')).name}`")
        st.caption(
            f"Granularity: `{selected_model.get('granularity', 'method')}` | "
            f"Dataset v`{selected_model.get('dataset_version') or selected_model.get('dataset_id', 'N/A')}` | "
            f"Decision Threshold: `{float(selected_model.get('decision_threshold', 0.50)):.2f}`"
        )

    try:
        predictor = BugPredictor.from_model_identifier(
            model_identifier=selected_model["model_file_path"],
            models_dir=settings.storage.models_dir,
            model_id=selected_model.get("id"),
            db=db,
            persist_history=settings.prediction.persist_history,
            persist_source_code=settings.prediction.persist_source_code,
        )
    except ModelCompatibilityError as e:
        st.error(f"Model compatibility error: {e}")
        return
    except Exception as e:
        st.error(f"Failed to load classifier bundle: {e}")
        return

    tab_class, tab_file, tab_validation, tab_history = st.tabs([
        "C# Class Classifier (Paste Class)",
        "C# Source File Upload (.cs)",
        "Repository Holdout Check",
        "Prediction History & Diagnostics",
    ])

    sample_class = """namespace OrderProcessing
{
    public class DiscountService
    {
        private readonly decimal _maxRate = 0.40m;

        public decimal ComputeDiscount(decimal totalAmount, int itemCount, bool isVip, string? couponCode)
        {
            if (totalAmount <= 0)
            {
                throw new ArgumentOutOfRangeException(nameof(totalAmount));
            }

            decimal rate = isVip ? 0.15m : 0.05m;
            if (!string.IsNullOrWhiteSpace(couponCode))
            {
                for (int i = 0; i < itemCount; i++)
                {
                    if (couponCode.StartsWith("PROMO") && totalAmount > 100m)
                    {
                        rate += 0.02m;
                    }
                }
            }

            return rate > _maxRate ? totalAmount * _maxRate : totalAmount * rate;
        }
    }
}"""

    # TAB 1: Single C# Class Analysis
    with tab_class:
        st.subheader("Classify a Complete C# Class")
        class_code = st.text_area(
            "Paste a complete C# class, struct, or record",
            value=sample_class,
            height=290,
            key="txt_single_class",
        )

        if st.button("Classify C# Class", key="btn_class_predict", width="stretch"):
            if predictor.granularity != "class" and "class_loc" not in predictor.preprocessor.feature_names_in_:
                st.warning(
                    "Selected model is a preserved method-level bundle. Choose a class-level classifier "
                    "(e.g. `class_bug_classifier_top200_v4`) or use Legacy Method Diagnostics in Tab 4."
                )
            else:
                with st.spinner("Extracting 40 Roslyn class features and running classifier..."):
                    try:
                        file_res = predictor.predict_csharp_file(code=class_code, file_name="SubmittedClass.cs")
                        st.session_state["last_single_file_res"] = file_res
                        st.session_state["last_class_pred"] = file_res.class_predictions[0]
                    except NoClassesFoundError as nce:
                        st.error(f"Class extraction error: {nce}")
                    except PredictorError as pe:
                        st.error(f"Classification error: {pe}")
                    except Exception as e:
                        st.error(f"Unexpected error: {e}")

        if "last_class_pred" in st.session_state:
            cp: ClassPrediction = st.session_state["last_class_pred"]
            f_single: FilePredictionResult | None = st.session_state.get("last_single_file_res")
            if f_single and f_single.syntax_error_count > 0:
                st.warning(f"Roslyn reported {f_single.syntax_error_count} syntax diagnostic error(s) in the submitted snippet.")

            verdict_info = format_class_verdict(cp)
            _render_verdict_banner(verdict_info["severity"], f"**{verdict_info['verdict']}** — `{cp.qualified_class_name}` (L{cp.start_line}-L{cp.end_line})")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Classification", verdict_info["classification"])
            m2.metric("Model Confidence", f"{verdict_info['confidence_pct']:.1f}%")
            m3.metric("P(BUG) Score", f"{verdict_info['bug_probability']:.3f}")
            m4.metric("Threshold", f"{verdict_info['threshold']:.2f}")

            st.markdown(f"**Explanation:** {cp.explanation_summary}")
            st.caption(cp.limitation_note)

            _render_localization_panel(cp)

            with st.expander("Structural Indicators & 40 Roslyn Class Metrics"):
                if cp.influential_metrics:
                    st.dataframe(pd.DataFrame(cp.influential_metrics), hide_index=True, width="stretch")
                st.dataframe(pd.DataFrame([{"Metric": k, "Value": v} for k, v in cp.metrics.items()]), hide_index=True, width="stretch")

    # TAB 2: Multi-Class .cs Source File Upload
    with tab_file:
        st.subheader("Complete C# Source File Classification (.cs)")
        st.caption(
            "Analyzes every class, struct, and record inside the uploaded .cs file independently as BUG or CLEAN. "
            "If parsing errors or failed classes occur, the file will never be falsely reported as CLEAN."
        )

        uploaded_cs = st.file_uploader("Upload C# source file", type=["cs"], key="uploader_cs_file")
        if uploaded_cs:
            file_content = uploaded_cs.read().decode("utf-8", errors="replace")
            st.caption(f"Loaded `{uploaded_cs.name}` ({len(file_content.splitlines())} lines).")

            if st.button("Classify C# File", key="btn_file_predict", width="stretch"):
                if predictor.granularity != "class" and "class_loc" not in predictor.preprocessor.feature_names_in_:
                    st.warning("Please select a class-level classifier in the model selector above for .cs file analysis.")
                else:
                    with st.spinner(f"Classifying all classes in '{uploaded_cs.name}'..."):
                        try:
                            file_res = predictor.predict_csharp_file(code=file_content, file_name=uploaded_cs.name)
                            st.session_state["file_pred_result"] = file_res
                        except NoClassesFoundError as nce:
                            st.error(f"ANALYSIS INCOMPLETE — No analyzable C# classes found: {nce}")
                        except Exception as e:
                            st.error(f"File classification failed: {e}")

        if "file_pred_result" in st.session_state:
            fres: FilePredictionResult = st.session_state["file_pred_result"]
            fv = format_file_verdict(fres)
            _render_verdict_banner(fv["severity"], f"**{fv['verdict']}** — `{fres.file_name}`: {fv['banner_detail']}")
            st.caption(fres.disclaimer)

            c_f1, c_f2, c_f3, c_f4, c_f5 = st.columns(5)
            c_f1.metric("Classes Analyzed", fres.classes_analyzed_count)
            c_f2.metric("BUG Classes", fres.classes_bug_count)
            c_f3.metric("CLEAN Classes", fres.classes_clean_count)
            c_f4.metric("Failed / Skipped", fres.classes_failed_count)
            c_f5.metric("Syntax Errors", fres.syntax_error_count)

            if fres.failed_classes or fres.syntax_error_count > 0:
                with st.expander("Parsing & Partial-Analysis Failures", expanded=True):
                    if fres.syntax_error_count > 0:
                        st.dataframe(pd.DataFrame(fres.parsing_diagnostics), hide_index=True, width="stretch")
                    if fres.failed_classes:
                        st.dataframe(pd.DataFrame([fc.to_dict() for fc in fres.failed_classes]), hide_index=True, width="stretch")

            table_rows = [
                {
                    "Class": c.class_name,
                    "Namespace": c.namespace_name,
                    "Type": c.type_kind,
                    "Lines": f"L{c.start_line}-L{c.end_line}",
                    "Classification": c.classification,
                    "Confidence": f"{c.confidence * 100:.1f}%",
                    "P(BUG)": round(c.defect_probability, 4),
                    "Localization": c.localization.status if c.localization else "unavailable",
                    "Suspicious Methods": ", ".join(
                        m.method_name for m in (c.localization.ml_suspicious_methods if c.localization else []) if m.is_suspicious
                    ) or "None / Unavailable",
                }
                for c in sorted(fres.class_predictions, key=lambda x: (x.predicted_label, x.defect_probability), reverse=True)
            ]
            df_table = pd.DataFrame(table_rows)
            styled = df_table.style.apply(_highlight_class_rows, axis=1)
            st.dataframe(styled, width="stretch", hide_index=True)

            st.subheader("Individual Class Inspection")
            class_choices = {
                f"[{c.classification}] {c.qualified_class_name} (L{c.start_line}-L{c.end_line} | Conf: {c.confidence * 100:.1f}%)": c
                for c in fres.class_predictions
            }
            chosen_c_label = st.selectbox("Select analyzed class", list(class_choices.keys()))
            chosen_cls = class_choices[chosen_c_label]
            st.markdown(f"**Explanation:** {chosen_cls.explanation_summary}")
            _render_localization_panel(chosen_cls)

            csv_buf = io.StringIO()
            df_table.to_csv(csv_buf, index=False)
            st.download_button(
                label="Download Class Classifications CSV",
                data=csv_buf.getvalue(),
                file_name=f"bug_classifications_{fres.file_name}.csv",
                mime="text/csv",
                width="stretch",
            )

    # TAB 3: Repository Class Holdout Check
    with tab_validation:
        st.subheader("Evaluation on Historical Mined Classes")
        st.caption("Evaluate the loaded classifier strictly against held-out repositories not used during training.")

        train_repos = set(predictor.split_summary.get("train_repositories", []))
        test_repos = set(predictor.split_summary.get("test_repositories", []))
        strict_holdout = st.checkbox("Exclude training repositories (Holdout only)", value=bool(train_repos))
        st.caption(f"Training repos: {len(train_repos)} | Holdout repos: {len(test_repos)}")

        obs_list = db.list_class_observations_with_features(exclude_uncertain=True)
        if strict_holdout and train_repos:
            obs_list = [o for o in obs_list if o.get("repository_id") not in train_repos]

        if not obs_list:
            st.caption("No eligible class observations match current filter.")
        else:
            val_limit = st.slider("Holdout classes to classify", 10, min(500, len(obs_list)), min(50, len(obs_list)), 10)
            if st.button("Run Holdout Classification Check", width="stretch"):
                results = []
                for obs in obs_list[:val_limit]:
                    pred = predictor.predict_class_from_metrics(
                        metrics=obs,
                        class_name=obs["class_name"],
                        qualified_class_name=obs["qualified_class_name"],
                        namespace_name=obs.get("namespace_name", "Global"),
                        file_name=obs["file_path"],
                        persist_record=False,
                    )
                    actual = int(obs["label"])
                    plabel = pred.predicted_label
                    outcome = (
                        "True Positive" if (actual == 1 and plabel == 1)
                        else "True Negative" if (actual == 0 and plabel == 0)
                        else "False Positive" if (actual == 0 and plabel == 1)
                        else "False Negative"
                    )
                    results.append({
                        "Repository": obs["repository_name"],
                        "Class": obs["qualified_class_name"],
                        "Actual": "BUG" if actual == 1 else "CLEAN",
                        "Predicted": pred.classification,
                        "P(BUG)": pred.defect_probability,
                        "Outcome": outcome,
                    })
                res_df = pd.DataFrame(results)
                tp = sum(1 for r in results if r["Outcome"] == "True Positive")
                fp = sum(1 for r in results if r["Outcome"] == "False Positive")
                fn = sum(1 for r in results if r["Outcome"] == "False Negative")
                tn = sum(1 for r in results if r["Outcome"] == "True Negative")
                prec = tp / max(1, tp + fp)
                rec = tp / max(1, tp + fn)
                cv1, cv2, cv3, cv4 = st.columns(4)
                cv1.metric("Precision", f"{prec:.1%}")
                cv2.metric("Recall", f"{rec:.1%}")
                cv3.metric("TP / FP", f"{tp} / {fp}")
                cv4.metric("TN / FN", f"{tn} / {fn}")
                st.dataframe(res_df, hide_index=True, width="stretch")

    # TAB 4: Prediction History & Legacy Method Diagnostic Mode
    with tab_history:
        st.subheader("Classification History & Provenance")
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
            display_cols = [
                c for c in [
                    "id", "granularity", "model_name", "classification_label",
                    "decision_threshold", "class_name", "file_name", "risk_score", "created_at",
                ] if c in h_df.columns
            ]
            st.dataframe(h_df[display_cols], width="stretch", hide_index=True)
        else:
            st.caption("No prediction history recorded.")

        with st.expander("Legacy Single-Method Diagnostic Mode"):
            st.caption("Available when a preserved method-level bundle is selected.")
            method_snip = st.text_area("Method snippet", value="public int Add(int a, int b) => a + b;", height=120)
            if st.button("Run Method Diagnostic", key="btn_legacy_method"):
                try:
                    mpreds = predictor.predict_code(method_snip)
                    st.dataframe(
                        pd.DataFrame([
                            {
                                "Method": p.method_name,
                                "Classification": p.classification,
                                "Confidence": f"{p.confidence * 100:.1f}%",
                                "P(BUG)": p.risk_score,
                            }
                            for p in mpreds
                        ]),
                        hide_index=True,
                        width="stretch",
                    )
                except (NoMethodsFoundError, PredictorError) as e:
                    st.error(str(e))
