"""Manual Detection page: analyze pasted C# code or uploaded .cs files at method level."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
import streamlit as st

from bug_detector.ml import BugDetectorPredictor
from gui.components import get_app_context, render_source_excerpt


def render() -> None:
    st.header("Manual Detection")
    cfg, repo = get_app_context()
    active = repo.get_active_model()

    if not active:
        st.error("No active trained model is registered. Train or activate a model first.")
        return

    st.caption(
        f"Active model: {active['model_version']} | Thresholds: "
        f"CLEAN < {cfg.thresholds.threshold_low:.3f} <= UNCERTAIN <= {cfg.thresholds.threshold_high:.3f} < BUG"
    )

    mode = st.radio("Input Mode", ["Paste C# Source", "Upload .cs File(s)"], horizontal=True)
    files_to_analyze: list[tuple[str, str, str]] = []

    if mode == "Paste C# Source":
        fname = st.text_input("File Name", value="Snippet.cs")
        src = st.text_area(
            "C# Source Code",
            height=260,
            placeholder="Paste a complete C# class, struct, record, or file...",
        )
        if st.button("Analyze Source", type="primary"):
            if not src.strip():
                st.warning("Provide non-empty C# source code.")
            else:
                files_to_analyze.append((fname.strip() or "Snippet.cs", src, "paste"))
    else:
        uploaded = st.file_uploader("Upload one or more .cs files", type=["cs"], accept_multiple_files=True)
        if st.button("Analyze Uploaded Files", type="primary"):
            if not uploaded:
                st.warning("Upload at least one .cs file.")
            else:
                for uf in uploaded:
                    text = uf.getvalue().decode("utf-8", errors="replace")
                    files_to_analyze.append((uf.name, text, "upload"))

    if files_to_analyze:
        predictor = BugDetectorPredictor(config=cfg)
        outputs: list[dict[str, Any]] = []
        for fname, src_text, imode in files_to_analyze:
            res = predictor.predict_source(
                source_code=src_text,
                file_name=fname,
                input_mode=imode,
                persist_run=True,
            )
            res["_raw_source"] = src_text
            outputs.append(res)
        st.session_state["last_detection_outputs"] = outputs

    outputs = st.session_state.get("last_detection_outputs") or []
    if not outputs:
        return

    export_payload = [{k: v for k, v in o.items() if k != "_raw_source"} for o in outputs]
    st.download_button(
        "Export JSON Results",
        data=json.dumps(export_payload, indent=2),
        file_name="bug_detection_results.json",
        mime="application/json",
    )

    for out in outputs:
        st.divider()
        st.subheader(f"File: {out['file_name']} (Run {out['run_id']})")
        status = out["analysis_status"]
        if status == "ANALYSIS_ERROR":
            st.error(f"ANALYSIS_ERROR: {out.get('error_message')}")
            if out.get("syntax_errors"):
                st.dataframe(pd.DataFrame(out["syntax_errors"]), width="stretch", hide_index=True)
            render_source_excerpt(out.get("_raw_source", ""))
            continue
        if status == "NO_METHODS":
            st.warning(out.get("error_message") or "No supported C# methods found.")
            continue

        methods = out["methods"]
        table_df = pd.DataFrame(
            [
                {
                    "Rank": m["suspicious_rank"],
                    "Class": m["class_name"],
                    "Method": m["method_name"],
                    "Lines": f"{m['start_line']}-{m['end_line']}",
                    "Classification": m["classification"],
                    "Probability": m["probability"],
                    "Uncertainty": m["uncertainty_status"],
                    "Feature Status": m["feature_extraction_status"],
                }
                for m in methods
            ]
        )
        st.dataframe(table_df, width="stretch", hide_index=True)
        st.download_button(
            f"Export CSV ({out['file_name']})",
            data=table_df.to_csv(index=False),
            file_name=f"{out['file_name']}_predictions.csv",
            mime="text/csv",
            key=f"csv_{out['run_id']}",
        )

        labels = [
            f"[{m['classification']}] {m['class_name']}.{m['method_name']} (L{m['start_line']}-{m['end_line']}, p={m['probability']})"
            for m in methods
        ]
        sel_idx = st.selectbox(
            f"Inspect Method ({out['file_name']})",
            range(len(methods)),
            format_func=lambda i: labels[i],
            key=f"sel_{out['run_id']}",
        )
        sel = methods[sel_idx]

        col_code, col_ev = st.columns([3, 2])
        with col_code:
            st.caption(f"Signature: `{sel['method_signature']}` | Lines {sel['start_line']}-{sel['end_line']}")
            render_source_excerpt(out.get("_raw_source", ""), sel["start_line"], sel["end_line"])
        with col_ev:
            st.markdown(f"**Verdict:** `{sel['classification']}` (p = `{sel['probability']}`)")
            st.caption(
                f"Thresholds: low={sel['threshold_low']}, center={sel['threshold_center']}, high={sel['threshold_high']}"
            )
            if sel.get("clean_disclaimer"):
                st.info(sel["clean_disclaimer"])

            ev = sel.get("local_evidence") or {}
            st.markdown("**Feature-Group Contributions (Tree Path)**")
            g_contribs = ev.get("group_contributions") or {}
            if g_contribs:
                st.dataframe(
                    pd.DataFrame(
                        [{"Group": g, "Contribution": v} for g, v in g_contribs.items()]
                    ),
                    width="stretch",
                    hide_index=True,
                )
            top_feats = ev.get("top_feature_contributions") or []
            if top_feats:
                st.markdown("**Top Local Feature Contributions**")
                st.dataframe(pd.DataFrame(top_feats), width="stretch", hide_index=True)
            if ev.get("disclaimer"):
                st.caption(ev["disclaimer"])

            if sel.get("historical_provenance"):
                st.markdown("**Historical Provenance Match (Exact Hash)**")
                st.dataframe(pd.DataFrame(sel["historical_provenance"]), width="stretch", hide_index=True)


if __name__ == "__main__":
    render()
