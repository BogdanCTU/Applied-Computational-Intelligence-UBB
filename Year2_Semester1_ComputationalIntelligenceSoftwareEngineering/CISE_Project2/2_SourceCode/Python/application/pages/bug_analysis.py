"""Bug Analysis Page: Bug-Fix Detection, SZZ Localization, and Method-Level Label Auditing."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core.settings import AppSettings
from database.repository import RepositoryDB
from services.mining.bug_fix_detector import BugFixDetector
from services.mining.szz_analyzer import SZZAnalyzer
from services.labeling.label_manager import LabelManager


def render_bug_analysis(db: RepositoryDB, settings: AppSettings) -> None:
    st.title("Bug Analysis and SZZ")
    st.caption("Identify bug-fixing commits, trace candidate bug-inducing commits via SZZ, and audit method labels.")

    repos = db.list_repositories()
    cloned_repos = [r for r in repos if r["is_cloned"] and r.get("local_path")]

    if not cloned_repos:
        st.warning("No cloned repositories available. Clone a repository in Repository Collection first.")
        return

    repo_options = {f"{r['full_name']} (ID: {r['id']})": r for r in cloned_repos}
    selected_label = st.selectbox("Target Repository", list(repo_options.keys()))
    selected_repo = repo_options[selected_label]
    repo_id = selected_repo["id"]
    local_path = selected_repo["local_path"]

    bug_detector = BugFixDetector(db=db)
    szz_analyzer = SZZAnalyzer(db=db)
    label_mgr = LabelManager(db=db)

    tab1, tab2, tab3 = st.tabs([
        "Bug-Fixing Commits",
        "SZZ Defect Localization",
        "Method Observations",
    ])

    # TAB 1: Bug-Fixing Commits Detection & Review
    with tab1:
        st.subheader("Bug-Fixing Commit Detection")

        col_d1, col_d2, col_d3 = st.columns([2, 1, 1])
        with col_d1:
            threshold = st.slider("Confidence threshold", 0.30, 0.90, 0.50, 0.05)
        with col_d2:
            force_reanalysis = st.checkbox("Re-analyze all commits", value=False)
        with col_d3:
            if st.button("Run Bug-Fix Detector", width="stretch"):
                with st.spinner("Analyzing repository commits..."):
                    bug_detector.detect_in_repository(repo_id, threshold=threshold, force=force_reanalysis)
                    st.rerun()

        filter_col1, filter_col2 = st.columns([1, 2])
        with filter_col1:
            filter_mode = st.radio("Display filter", ["All Commits", "Bug Fixes Only"])
        with filter_col2:
            search_kw = st.text_input("Filter commit message", placeholder="null, crash, #123")

        bug_only = filter_mode == "Bug Fixes Only"
        commits = db.list_commits(repository_id=repo_id, bug_fix_only=bug_only, limit=300)

        if search_kw:
            commits = [c for c in commits if search_kw.lower() in (c["message"] or "").lower()]

        if commits:
            st.caption(f"Matching commits: {len(commits)} (showing top 20 expandable records)")
            commits_summary = pd.DataFrame(commits[:50])[
                ["commit_sha", "committed_date", "author_name", "is_bug_fix", "bug_fix_confidence", "review_status", "message"]
            ]
            st.dataframe(commits_summary, hide_index=True, width="stretch")

            for c in commits[:20]:
                cid = c["id"]
                sha = c["commit_sha"]
                is_fix = c["is_bug_fix"] == 1
                tag = "BUG FIX" if is_fix else "REGULAR"
                conf = c.get("bug_fix_confidence", 0.0)
                review = c.get("review_status", "unreviewed")

                with st.expander(f"[{tag}] {sha[:8]} (Confidence: {conf:.2f} | Status: {review}) — {(c['message'] or '').splitlines()[0][:80]}"):
                    st.code(c["message"] or "", language="text")
                    st.caption(f"Author: {c['author_name']} | Date: {c['committed_date']} | Evidence: {c.get('bug_fix_evidence') or 'N/A'}")

                    c_b1, c_b2, c_b3 = st.columns(3)
                    with c_b1:
                        if st.button("Confirm Bug Fix", key=f"conf_fix_{cid}", width="stretch"):
                            db.update_commit_review_status(cid, "confirmed", is_bug_fix=True)
                            st.rerun()
                    with c_b2:
                        if st.button("Reject Bug Fix", key=f"rej_fix_{cid}", width="stretch"):
                            db.update_commit_review_status(cid, "rejected", is_bug_fix=False)
                            st.rerun()
                    with c_b3:
                        if st.button("Reset Review", key=f"rst_fix_{cid}", width="stretch"):
                            db.update_commit_review_status(cid, "unreviewed", is_bug_fix=None)
                            st.rerun()
        else:
            st.caption("No commits match current filter criteria.")

    # TAB 2: SZZ Analysis (BICs)
    with tab2:
        st.subheader("SZZ Line-Blame Tracing")
        st.caption("Traces deleted or modified production C# lines in fixing commits via git blame (-w -M -C).")

        if st.button("Run SZZ Algorithm", width="stretch"):
            p_bar = st.progress(0.1, text="Running SZZ blame analysis...")

            def on_szz_prog(msg: str, pct: float) -> None:
                p_bar.progress(pct, text=msg)

            try:
                szz_analyzer.run_repository_szz(
                    repository_id=repo_id,
                    local_path=local_path,
                    progress_callback=on_szz_prog,
                )
                st.rerun()
            except Exception as e:
                st.error(f"SZZ analysis failed: {e}")

        traces = db.list_szz_results(repository_id=repo_id)
        if traces:
            st.caption(f"Total SZZ traces: {len(traces)}")
            df_traces = pd.DataFrame(traces)[
                ["fixing_commit_sha", "inducing_commit_sha", "file_path", "deleted_line_number", "deleted_line_content", "confidence"]
            ]
            st.dataframe(df_traces, hide_index=True, width="stretch")
        else:
            st.caption("No SZZ traces recorded for this repository.")

    # TAB 3: Method Observations & Label Audit
    with tab3:
        st.subheader("Method-Level Observation Extraction")
        st.caption("Map SZZ traces to enclosing pre-fix C# methods (Label 1) and sample candidate-clean HEAD methods (Label 0).")

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            if st.button("Extract Defect-Prone Methods (Label 1)", width="stretch"):
                with st.spinner("Extracting pre-fix methods..."):
                    label_mgr.create_observations_from_szz(repo_id, local_path)
                    st.rerun()

        with col_m2:
            clean_count = st.number_input("Candidate-clean sample count (Label 0)", min_value=10, max_value=500, value=50, step=10)
            if st.button("Sample Candidate-Clean Methods (Label 0)", width="stretch"):
                with st.spinner("Sampling candidate-clean methods from HEAD..."):
                    label_mgr.sample_candidate_clean_methods(repo_id, local_path, target_count=clean_count)
                    st.rerun()

        st.subheader("Observation Audit")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            label_filter = st.selectbox("Filter by label", ["All", "Defect-Prone (1)", "Candidate-Clean (0)", "Uncertain (-1)"])
        with col_f2:
            method_search = st.text_input("Filter by method name", placeholder="Parse, Calculate")

        target_label = None
        if label_filter == "Defect-Prone (1)":
            target_label = 1
        elif label_filter == "Candidate-Clean (0)":
            target_label = 0
        elif label_filter == "Uncertain (-1)":
            target_label = -1

        observations = db.list_observations(repository_id=repo_id, label=target_label)
        if method_search:
            observations = [o for o in observations if method_search.lower() in o["method_name"].lower()]

        if observations:
            st.caption(f"Observations: {len(observations)} (showing first 15 expandable code records)")
            obs_summary = pd.DataFrame(observations)[
                ["id", "class_name", "method_name", "file_path", "label", "evidence_category", "label_confidence"]
            ]
            st.dataframe(obs_summary, hide_index=True, width="stretch")

            for obs in observations[:15]:
                oid = obs["id"]
                lbl = obs["label"]
                tag = "DEFECT-PRONE (1)" if lbl == 1 else ("CANDIDATE-CLEAN (0)" if lbl == 0 else "UNCERTAIN (-1)")

                with st.expander(f"[{tag}] {obs['class_name']}.{obs['method_name']} — {obs['file_path']}"):
                    st.caption(
                        f"Signature: {obs['method_signature']} | Evidence: {obs['evidence_category']} | "
                        f"Confidence: {obs['label_confidence']:.2f}"
                    )

                    col_c1, col_c2 = st.columns(2)
                    with col_c1:
                        st.caption("Pre-fix or sampled source code:")
                        st.code(obs["source_code"], language="csharp")
                    with col_c2:
                        st.caption("Post-fix source code:")
                        if obs.get("corrected_code"):
                            st.code(obs["corrected_code"], language="csharp")
                        else:
                            st.caption("Not applicable.")

                    c_act1, c_act2, c_act3 = st.columns(3)
                    with c_act1:
                        if st.button("Set Label 1 (Defect-Prone)", key=f"obs_bug_{oid}", width="stretch"):
                            db.update_observation_label(oid, 1, "manual_override_buggy")
                            st.rerun()
                    with c_act2:
                        if st.button("Set Label 0 (Candidate-Clean)", key=f"obs_clean_{oid}", width="stretch"):
                            db.update_observation_label(oid, 0, "manual_override_clean")
                            st.rerun()
                    with c_act3:
                        if st.button("Set Label -1 (Uncertain)", key=f"obs_uncert_{oid}", width="stretch"):
                            label_mgr.mark_observation_uncertain(oid, "manual_override_uncertain")
                            st.rerun()
        else:
            st.caption("No observations match current filter criteria.")
