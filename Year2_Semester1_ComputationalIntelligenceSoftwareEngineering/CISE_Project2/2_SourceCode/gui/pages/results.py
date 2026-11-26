"""Results page: filterable historical prediction inspector and export."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from gui.components import get_app_context, render_source_excerpt, safe_json_loads


def render() -> None:
    st.header("Results")
    _, repo = get_app_context()
    runs = repo.list_detection_runs(limit=100)

    c1, c2, c3, c4 = st.columns(4)
    cls_filter = c1.selectbox("Classification", ["ALL", "BUG", "CLEAN", "UNCERTAIN", "ANALYSIS_ERROR"])
    run_options = ["ALL"] + [r["run_id"] for r in runs]
    run_filter = c2.selectbox("Run ID", run_options)
    file_filter = c3.text_input("File Name Contains", value="")
    sort_by = c4.selectbox("Sort By", ["Newest", "Highest Probability", "Lowest Probability"])

    preds = repo.query_predictions(
        classification=cls_filter,
        run_id=run_filter,
        file_like=file_filter.strip() or None,
        limit=300,
    )
    if not preds:
        st.info("No prediction results match the selected filters.")
        return

    if sort_by == "Highest Probability":
        preds.sort(key=lambda p: p["probability"] if p["probability"] is not None else -1.0, reverse=True)
    elif sort_by == "Lowest Probability":
        preds.sort(key=lambda p: p["probability"] if p["probability"] is not None else 2.0)

    df = pd.DataFrame(
        [
            {
                "ID": p["prediction_id"],
                "Run": p["run_id"],
                "File": p["file_name"],
                "Class": p["class_name"],
                "Method": p["method_name"],
                "Lines": f"{p['start_line']}-{p['end_line']}",
                "Classification": p["classification"],
                "Probability": p["probability"],
                "Uncertainty": p["uncertainty_status"],
                "Rank": p["suspicious_rank"],
                "Model": p["model_version"],
            }
            for p in preds
        ]
    )
    st.dataframe(df, width="stretch", hide_index=True)
    st.download_button("Export Filtered CSV", data=df.to_csv(index=False), file_name="filtered_results.csv", mime="text/csv")

    sel_idx = st.selectbox(
        "Inspect Prediction Record",
        range(len(preds)),
        format_func=lambda i: f"#{preds[i]['prediction_id']} [{preds[i]['classification']}] {preds[i]['file_name']} :: {preds[i]['class_name']}.{preds[i]['method_name']}",
    )
    sel = preds[sel_idx]
    ev = safe_json_loads(sel.get("local_evidence_json"), {})
    prov = safe_json_loads(sel.get("historical_provenance_json"), None)

    with repo.db.connect() as conn:
        blob = conn.execute(
            "SELECT b.raw_source FROM detection_runs d JOIN source_blobs b ON b.source_hash = d.source_hash WHERE d.run_id = ?",
            (sel["run_id"],),
        ).fetchone()
    raw_src = blob["raw_source"] if blob else ""

    col_a, col_b = st.columns([3, 2])
    with col_a:
        render_source_excerpt(raw_src, sel["start_line"], sel["end_line"])
    with col_b:
        st.write(f"**Signature:** `{sel['method_signature']}`")
        st.write(f"**Classification:** `{sel['classification']}` | **Probability:** `{sel['probability']}`")
        st.write(f"**Feature Status:** `{sel['feature_extraction_status']}`")
        if ev and ev.get("top_feature_contributions"):
            st.markdown("**Local Evidence**")
            st.dataframe(pd.DataFrame(ev["top_feature_contributions"]), width="stretch", hide_index=True)
        if prov:
            st.markdown("**Historical Provenance**")
            st.dataframe(pd.DataFrame(prov), width="stretch", hide_index=True)


if __name__ == "__main__":
    render()
