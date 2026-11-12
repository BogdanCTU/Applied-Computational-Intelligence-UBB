"""Bug Analysis Page: Bug-Fix Detection, SZZ Localization, and Method-Level Label Auditing."""
from __future__ import annotations

from pathlib import Path
import pandas as pd
import streamlit as st

from config.settings import AppSettings
from src.database.repository import RepositoryDB
from src.mining.bug_fix_detector import BugFixDetector
from src.mining.szz_analyzer import SZZAnalyzer
from src.labeling.label_manager import LabelManager


def render_bug_analysis(db: RepositoryDB, settings: AppSettings) -> None:
    st.header("🔍 Bug Analysis, SZZ Defect Localization & Ground-Truth Labeling")
    st.markdown("""
    Automatically detect bug-fixing commits using natural language heuristics and issue linkages,
    run the **SZZ algorithm** with line-level AST diff tracing to identify Bug-Inducing Commits (BICs),
    and extract method-level observations labeled as **Buggy (1)**, **Candidate Clean (0)**, or **Uncertain (-1)**.
    """)

    repos = db.list_repositories()
    cloned_repos = [r for r in repos if r["is_cloned"] and r.get("local_path")]

    if not cloned_repos:
        st.warning("No cloned repositories available. Please clone a repository first in 'Repository Collection'.")
        return

    repo_options = {f"{r['full_name']} (ID: {r['id']})": r for r in cloned_repos}
    selected_label = st.selectbox("Select Target Repository", list(repo_options.keys()))
    selected_repo = repo_options[selected_label]
    repo_id = selected_repo["id"]
    local_path = selected_repo["local_path"]

    bug_detector = BugFixDetector(db=db)
    szz_analyzer = SZZAnalyzer(db=db)
    label_mgr = LabelManager(db=db)

    tab1, tab2, tab3 = st.tabs([
        "🐞 Bug-Fixing Commits",
        "🔬 SZZ Defect Localization (BICs)",
        "🏷️ Method Observations & Label Audit",
    ])

    # -------------------------------------------------------------
    # TAB 1: Bug-Fixing Commits Detection & Review
    # -------------------------------------------------------------
    with tab1:
        st.subheader("1. Detect Potential Bug-Fixing Commits")
        st.caption("Scans commit messages, issue keywords, and modified files to calculate defect confidence.")

        col_d1, col_d2, col_d3 = st.columns([2, 1, 1])
        with col_d1:
            threshold = st.slider("Classification Confidence Threshold", 0.30, 0.90, 0.50, 0.05)
        with col_d2:
            force_reanalysis = st.checkbox("Force Re-Analyze All", value=False)
        with col_d3:
            st.write("")
            if st.button("⚡ Run Bug-Fix Detector", use_container_width=True):
                with st.spinner("Analyzing repository commits..."):
                    res = bug_detector.detect_in_repository(repo_id, threshold=threshold, force=force_reanalysis)
                    st.success(f"Classified {res['classified_bug_fixes']} bug-fixing commits out of {res['total_commits']} total commits.")
                    st.rerun()

        # Display commit list with filter
        filter_col1, filter_col2 = st.columns([1, 3])
        with filter_col1:
            filter_mode = st.radio("Display Filter", ["All Commits", "Bug Fixes Only (Confirmed/Candidate)"])
        with filter_col2:
            search_kw = st.text_input("Filter message by keyword", placeholder="e.g. null, crash, #123")

        bug_only = filter_mode == "Bug Fixes Only (Confirmed/Candidate)"
        commits = db.list_commits(repository_id=repo_id, bug_fix_only=bug_only, limit=300)

        if search_kw:
            commits = [c for c in commits if search_kw.lower() in (c["message"] or "").lower()]

        if commits:
            st.write(f"Showing **{len(commits)}** commits:")
            for c in commits[:20]:
                cid = c["id"]
                sha = c["commit_sha"]
                is_fix = c["is_bug_fix"] == 1
                badge = "🔴 BUG FIX" if is_fix else "⚪ REGULAR"
                conf = c.get("bug_fix_confidence", 0.0)
                review = c.get("review_status", "unreviewed")

                with st.expander(f"{badge} [{conf:.2f}] `{sha[:8]}` — {(c['message'] or '').splitlines()[0][:80]}"):
                    st.write(f"**Full Commit Message:**\n```text\n{c['message']}\n```")
                    st.write(f"**Author:** {c['author_name']} | **Date:** {c['committed_date']}")
                    st.write(f"**Confidence:** `{conf:.2f}` | **Evidence:** {c.get('bug_fix_evidence') or 'N/A'}")
                    st.write(f"**Review Status:** `{review.upper()}`")

                    # Review override buttons
                    c_b1, c_b2, c_b3 = st.columns(3)
                    with c_b1:
                        if st.button("✅ Confirm Bug Fix", key=f"conf_fix_{cid}"):
                            db.update_commit_review_status(cid, "confirmed", is_bug_fix=True)
                            st.rerun()
                    with c_b2:
                        if st.button("❌ Reject Bug Fix", key=f"rej_fix_{cid}"):
                            db.update_commit_review_status(cid, "rejected", is_bug_fix=False)
                            st.rerun()
                    with c_b3:
                        if st.button("🔄 Reset Review", key=f"rst_fix_{cid}"):
                            db.update_commit_review_status(cid, "unreviewed", is_bug_fix=None)
                            st.rerun()
        else:
            st.info("No commits match current filter criteria. Run the Bug-Fix Detector above.")

    # -------------------------------------------------------------
    # TAB 2: SZZ Analysis (BICs)
    # -------------------------------------------------------------
    with tab2:
        st.subheader("2. SZZ Bug-Inducing Commit Localization")
        st.markdown("""
        Walks backward through `git blame -w -M -C` on pre-fix parent states to identify
        which historical commits originally introduced the lines that required defect correction.
        """)

        col_szz1, col_szz2 = st.columns([1, 2])
        with col_szz1:
            if st.button("🚀 Run SZZ Algorithm on Bug Fixes", use_container_width=True):
                p_bar = st.progress(0.1, text="Running SZZ line-level blame analysis...")
                def on_szz_prog(msg: str, pct: float) -> None:
                    p_bar.progress(pct, text=msg)

                try:
                    szz_stats = szz_analyzer.run_repository_szz(
                        repository_id=repo_id,
                        local_path=local_path,
                        progress_callback=on_szz_prog,
                    )
                    st.success(
                        f"SZZ Completed: Analyzed {szz_stats['total_fixing_commits']} fixes, "
                        f"discovered {szz_stats['total_bic_traces']} line traces across "
                        f"{szz_stats['unique_bug_inducing_commits']} candidate BICs!"
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"SZZ analysis failed: {e}")

        # Display discovered SZZ traces
        traces = db.list_szz_results(repository_id=repo_id)
        if traces:
            st.markdown(f"### Discovered SZZ Bug Traces ({len(traces)} total)")
            df_traces = pd.DataFrame(traces)[["fixing_commit_sha", "inducing_commit_sha", "file_path", "deleted_line_number", "deleted_line_content", "confidence"]]
            st.dataframe(df_traces, use_container_width=True)
        else:
            st.info("No SZZ traces generated yet. Click 'Run SZZ Algorithm' to analyze confirmed fixes.")

    # -------------------------------------------------------------
    # TAB 3: Method Observations & Ground-Truth Label Audit
    # -------------------------------------------------------------
    with tab3:
        st.subheader("3. Method-Level Dataset Observation Builder")
        st.markdown("""
        Using Roslyn AST, map SZZ line-level traces to enclosing C# method definitions,
        extract original (pre-fix buggy) code as **Label 1**, sample stable methods as **Label 0**,
        and manage audit status.
        """)

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            if st.button("🔨 Extract Label 1 (Buggy) Methods from SZZ", use_container_width=True):
                with st.spinner("Parsing AST and extracting pre-fix methods..."):
                    created = label_mgr.create_observations_from_szz(repo_id, local_path)
                    st.success(f"Extracted {len(created)} method observations with Label 1 (Buggy)!")
                    st.rerun()

        with col_m2:
            clean_count = st.number_input("Clean Methods to Sample (Label 0)", min_value=10, max_value=500, value=50, step=10)
            if st.button("🌿 Sample Candidate Clean Methods (Label 0)", use_container_width=True):
                with st.spinner("Sampling stable C# methods from HEAD..."):
                    sampled = label_mgr.sample_candidate_clean_methods(repo_id, local_path, target_count=clean_count)
                    st.success(f"Sampled {len(sampled)} candidate clean methods (Label 0)!")
                    st.rerun()

        # Observation inspection and manual review
        st.markdown("---")
        st.subheader("Method Observations Audit Table")

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            label_filter = st.selectbox("Filter by Label", ["All", "Buggy (1)", "Candidate Clean (0)", "Uncertain (-1)"])
        with col_f2:
            method_search = st.text_input("Filter by method name", placeholder="e.g. Parse, Calculate")

        target_label = None
        if label_filter == "Buggy (1)":
            target_label = 1
        elif label_filter == "Candidate Clean (0)":
            target_label = 0
        elif label_filter == "Uncertain (-1)":
            target_label = -1

        observations = db.list_observations(repository_id=repo_id, label=target_label)
        if method_search:
            observations = [o for o in observations if method_search.lower() in o["method_name"].lower()]

        if observations:
            st.write(f"Displaying **{len(observations)}** observations:")
            for obs in observations[:15]:
                oid = obs["id"]
                lbl = obs["label"]
                badge = "🔴 BUGGY (1)" if lbl == 1 else ("🟢 CLEAN (0)" if lbl == 0 else "🟡 UNCERTAIN (-1)")

                with st.expander(f"{badge} **{obs['class_name']}.{obs['method_name']}** — `{obs['file_path']}`"):
                    st.write(f"**Signature:** `{obs['method_signature']}`")
                    st.write(f"**Evidence Category:** `{obs['evidence_category']}` | **Confidence:** `{obs['label_confidence']:.2f}`")
                    if obs.get("bug_fix_commit_sha"):
                        st.write(f"**Fixing Commit:** `{obs['bug_fix_commit_sha'][:8]}` | **BIC:** `{obs['parent_sha'][:8] if obs.get('parent_sha') else 'N/A'}`")

                    col_c1, col_c2 = st.columns(2)
                    with col_c1:
                        st.markdown("**Original Pre-Fix Method Code:**")
                        st.code(obs["source_code"], language="csharp")
                    with col_c2:
                        st.markdown("**Corrected Post-Fix Method Code (if recorded):**")
                        if obs.get("corrected_code"):
                            st.code(obs["corrected_code"], language="csharp")
                        else:
                            st.caption("No post-fix diff recorded (clean sample or deleted method).")

                    # Label audit actions
                    c_act1, c_act2, c_act3 = st.columns(3)
                    with c_act1:
                        if st.button("Mark as Buggy (1)", key=f"obs_bug_{oid}"):
                            db.update_observation_label(oid, 1, "manual_override_buggy")
                            st.rerun()
                    with c_act2:
                        if st.button("Mark as Clean (0)", key=f"obs_clean_{oid}"):
                            db.update_observation_label(oid, 0, "manual_override_clean")
                            st.rerun()
                    with c_act3:
                        if st.button("Mark as Uncertain (-1)", key=f"obs_uncert_{oid}"):
                            label_mgr.mark_observation_uncertain(oid, "manual_override_uncertain")
                            st.rerun()
        else:
            st.info("No observations found for current filter. Extract observations using buttons above.")
