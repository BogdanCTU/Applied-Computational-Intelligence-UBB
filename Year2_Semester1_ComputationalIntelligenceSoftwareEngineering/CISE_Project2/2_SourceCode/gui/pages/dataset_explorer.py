"""Dataset Explorer page: paginated corpus browser, provenance, verification, and audit reports."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from gui.components import get_app_context, render_source_excerpt, safe_json_loads


def render() -> None:
    st.header("Dataset Explorer")
    _, repo = get_app_context()
    versions = repo.list_dataset_versions()
    if not versions:
        st.info("No datasets found in the database. Run `build-dataset` first.")
        return

    ver_names = [v["dataset_version"] for v in versions]
    selected_ver = st.selectbox("Dataset Version", ver_names)
    ds_meta = next(v for v in versions if v["dataset_version"] == selected_ver)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Valid Samples", f"{ds_meta['valid_records']:,}")
    c2.metric("Excluded Records", f"{ds_meta['invalid_records']:,}")
    c3.metric("BUG / CLEAN", f"{ds_meta['bug_count']} / {ds_meta['clean_count']}")
    c4.metric("Repositories", ds_meta["repository_count"])

    breakdown = repo.get_dataset_breakdown(selected_ver)

    tab_browse, tab_dist, tab_audit = st.tabs(["Sample Browser", "Distributions & Exclusions", "Audit Report"])

    with tab_dist:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Label Source Distribution")
            st.dataframe(pd.DataFrame(breakdown["by_source"]), width="stretch", hide_index=True)
            st.subheader("Verification Status")
            st.dataframe(pd.DataFrame(breakdown["by_verification_status"]), width="stretch", hide_index=True)
        with col2:
            st.subheader("Defect Categories")
            st.dataframe(pd.DataFrame(breakdown["by_bug_type"]), width="stretch", hide_index=True)
            st.subheader("Exclusion Statistics")
            st.dataframe(pd.DataFrame(breakdown["exclusions"]), width="stretch", hide_index=True)
        st.subheader("Top Repositories")
        st.dataframe(pd.DataFrame(breakdown["by_repository"]), width="stretch", hide_index=True)

    with tab_audit:
        audit_path = ds_meta.get("audit_report_path")
        if audit_path and Path(audit_path).exists():
            st.json(safe_json_loads(Path(audit_path).read_text(encoding="utf-8"), {}))
        else:
            st.write("Audit report file not found on disk.")

    with tab_browse:
        f1, f2, f3, f4 = st.columns(4)
        lbl_opt = f1.selectbox("Label", ["ALL", "BUG (1)", "CLEAN (0)"])
        lbl_val = 1 if lbl_opt == "BUG (1)" else (0 if lbl_opt == "CLEAN (0)" else None)
        src_opts = ["ALL"] + sorted({r["label_source"] for r in breakdown["by_source"]})
        src_val = f2.selectbox("Label Source", src_opts)
        part_val = f3.selectbox("Split Partition", ["ALL", "dev", "independent_test", "hard_negative_test", "unassigned"])
        repo_q = f4.text_input("Repository Contains", value="")

        page_size = 25
        page_num = int(st.number_input("Page", min_value=1, value=1, step=1))
        offset = (page_num - 1) * page_size

        rows, total = repo.query_dataset_samples(
            dataset_version=selected_ver,
            label=lbl_val,
            label_source=src_val,
            split_partition=part_val,
            repository_id=repo_q.strip() or None,
            offset=offset,
            limit=page_size,
        )
        st.caption(f"Showing {len(rows)} of {total} matching samples (Page {page_num})")
        if rows:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Sample ID": r["sample_id"],
                            "Repository": r["repository_id"],
                            "Method": f"{r['class_name']}.{r['method_name']}",
                            "Label": "BUG" if r["label"] == 1 else "CLEAN",
                            "Source": r["label_source"],
                            "Verification": r["verification_status"],
                            "Bug Type": r["bug_type"],
                            "Partition": r["split_partition"],
                        }
                        for r in rows
                    ]
                ),
                width="stretch",
                hide_index=True,
            )
            idx = st.selectbox(
                "Inspect Sample Code",
                range(len(rows)),
                format_func=lambda i: f"{rows[i]['sample_id']} ({rows[i]['class_name']}.{rows[i]['method_name']})",
            )
            sel = rows[idx]
            st.caption(f"Commit: `{sel['commit_sha']}` | File: `{sel['file_path']}` | Ref: `{sel.get('bug_fix_reference')}`")
            render_source_excerpt(sel["raw_source"])


if __name__ == "__main__":
    render()
