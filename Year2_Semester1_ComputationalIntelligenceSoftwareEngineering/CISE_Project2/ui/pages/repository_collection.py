"""Repository Collection Page with GitHub Discovery, Manual Registration, Full-History Cloning, and Commit Extraction."""
from __future__ import annotations

import re
from pathlib import Path
import pandas as pd
import streamlit as st

from config.settings import AppSettings
from src.collection.github_client import GitHubClient, GitHubAPIError, RateLimitExceededError
from src.collection.repository_manager import RepositoryManager, RepositoryManagerError
from src.collection.commit_collector import CommitCollector, CommitCollectorError
from src.database.repository import RepositoryDB


def parse_github_url(url: str) -> tuple[str, str]:
    """Extract owner and repo name from github URL or owner/repo string."""
    cleaned = url.strip().rstrip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]

    pattern = r"(?:https?://github\.com/)?([^/\s]+)/([^/\s]+)$"
    match = re.search(pattern, cleaned)
    if not match:
        raise ValueError(f"Invalid repository specification: '{url}'. Expected format: 'owner/repo' or 'https://github.com/owner/repo'")
    return match.group(1), match.group(2)


def render_repository_collection(db: RepositoryDB, settings: AppSettings) -> None:
    st.header("📥 GitHub C# Repository Collection Engine")
    st.markdown("""
    Discover public C# repositories via the GitHub REST API or register repositories manually.
    Repositories are cloned locally with their **complete Git history** to enable historical SZZ bug-origin localization.
    """)

    gh_client = GitHubClient(token=settings.github.token)
    repo_mgr = RepositoryManager(settings.storage.repositories_dir, db=db)
    commit_collector = CommitCollector(db)

    tab1, tab2, tab3 = st.tabs(["🔎 GitHub Discovery", "➕ Manual Repository Import", "📦 Managed Local Repositories"])

    # -------------------------------------------------------------
    # TAB 1: GitHub Discovery
    # -------------------------------------------------------------
    with tab1:
        st.subheader("Search Public GitHub C# Repositories")
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        with col1:
            keywords = st.text_input("Keywords / Topic (optional)", placeholder="e.g. parser, serialization, roslyn")
        with col2:
            min_stars = st.number_input("Min Stars", min_value=0, value=100, step=50)
        with col3:
            min_size_kb = st.number_input("Min Size (KB)", min_value=0, value=100, step=100)
        with col4:
            limit = st.slider("Results Limit", min_value=5, max_value=50, value=15, step=5)

        col_opts1, col_opts2 = st.columns(2)
        with col_opts1:
            exclude_forks = st.checkbox("Exclude Forks", value=True)
        with col_opts2:
            exclude_archived = st.checkbox("Exclude Archived Repositories", value=True)

        if st.button("🔍 Search GitHub Repositories", use_container_width=True):
            with st.spinner("Querying GitHub Search API..."):
                try:
                    search_results = gh_client.search_repositories(
                        keywords=keywords,
                        min_stars=min_stars,
                        min_size_kb=min_size_kb,
                        exclude_forks=exclude_forks,
                        exclude_archived=exclude_archived,
                        per_page=limit,
                    )
                    st.session_state["search_results"] = search_results["items"]
                    st.success(f"Discovered {search_results['total_count']} repositories (showing top {len(search_results['items'])}).")
                except RateLimitExceededError as e:
                    st.error(f"GitHub API Rate Limit Reached: {e}. Provide a GitHub PAT in Settings to raise limits.")
                except GitHubAPIError as e:
                    st.error(f"GitHub Search Error: {e}")

        # Display discovered results
        items = st.session_state.get("search_results", [])
        if items:
            st.markdown("### Discovered Repositories")
            for repo_item in items:
                with st.expander(f"⭐ {repo_item['stars']} | **{repo_item['full_name']}** — {repo_item['license']}"):
                    st.write(f"**Description:** {repo_item['description'] or 'No description provided.'}")
                    st.write(f"**Default Branch:** `{repo_item['default_branch']}` | **Size:** {repo_item['size_kb']} KB")
                    st.write(f"**GitHub URL:** [{repo_item['url']}]({repo_item['url']})")

                    col_b1, col_b2 = st.columns([1, 3])
                    with col_b1:
                        if st.button("Register & Clone", key=f"btn_clone_{repo_item['full_name']}"):
                            # 1. Upsert into database
                            repo_id = db.upsert_repository({
                                "full_name": repo_item["full_name"],
                                "name": repo_item["name"],
                                "owner": repo_item["owner"],
                                "url": repo_item["url"],
                                "description": repo_item["description"],
                                "license": repo_item["license"],
                                "default_branch": repo_item["default_branch"],
                                "stars": repo_item["stars"],
                                "forks": repo_item["forks"],
                                "size_kb": repo_item["size_kb"],
                            })
                            # 2. Clone full history
                            progress_bar = st.progress(0.1, text=f"Cloning {repo_item['full_name']}...")
                            def on_progress(msg: str, pct: float) -> None:
                                progress_bar.progress(pct, text=msg)

                            try:
                                res = repo_mgr.clone_or_update(
                                    url=repo_item["clone_url"],
                                    owner=repo_item["owner"],
                                    name=repo_item["name"],
                                    default_branch=repo_item["default_branch"],
                                    progress_callback=on_progress,
                                )
                                st.success(f"Successfully cloned {repo_item['full_name']} to `{res['local_path']}` (HEAD: {res['head_commit'][:8]})!")
                                st.rerun()
                            except RepositoryManagerError as err:
                                st.error(f"Clone failed: {err}")

    # -------------------------------------------------------------
    # TAB 2: Manual Import
    # -------------------------------------------------------------
    with tab2:
        st.subheader("Manually Register & Clone a C# Repository")
        st.markdown("Enter any public Git or GitHub URL (e.g., `https://github.com/dotnet/roslyn` or `owner/repo`).")
        manual_url = st.text_input("Repository URL or Slug", placeholder="https://github.com/owner/repository")
        clone_immediately = st.checkbox("Clone full history immediately upon registration", value=True)

        if st.button("➕ Register & Import Repository", use_container_width=True):
            if not manual_url:
                st.warning("Please provide a repository URL.")
            else:
                try:
                    owner, name = parse_github_url(manual_url)
                    full_name = f"{owner}/{name}"

                    # Attempt fetching live metadata if available
                    meta: dict = {}
                    try:
                        meta = gh_client.get_repository(owner, name)
                    except Exception:
                        meta = {
                            "description": "Manually registered repository",
                            "license": "Custom/Unknown",
                            "default_branch": "main",
                            "stars": 0,
                            "forks": 0,
                            "size_kb": 0,
                            "clone_url": f"https://github.com/{full_name}.git",
                        }

                    repo_id = db.upsert_repository({
                        "full_name": full_name,
                        "name": name,
                        "owner": owner,
                        "url": f"https://github.com/{full_name}",
                        "description": meta.get("description"),
                        "license": meta.get("license", "Unknown"),
                        "default_branch": meta.get("default_branch", "main"),
                        "stars": meta.get("stars", 0),
                        "forks": meta.get("forks", 0),
                        "size_kb": meta.get("size_kb", 0),
                    })
                    st.success(f"Registered repository '{full_name}' in database (ID: {repo_id}).")

                    if clone_immediately:
                        progress_bar = st.progress(0.1, text=f"Cloning {full_name}...")
                        def on_progress(msg: str, pct: float) -> None:
                            progress_bar.progress(pct, text=msg)

                        res = repo_mgr.clone_or_update(
                            url=meta.get("clone_url", f"https://github.com/{full_name}.git"),
                            owner=owner,
                            name=name,
                            default_branch=meta.get("default_branch", "main"),
                            progress_callback=on_progress,
                        )
                        st.success(f"Cloned successfully into `{res['local_path']}`!")
                        st.rerun()

                except ValueError as ve:
                    st.error(str(ve))
                except RepositoryManagerError as rme:
                    st.error(f"Clone operation failed: {rme}")

    # -------------------------------------------------------------
    # TAB 3: Managed Repositories
    # -------------------------------------------------------------
    with tab3:
        st.subheader("Locally Managed Repositories")
        repos = db.list_repositories()
        if not repos:
            st.info("No repositories in database. Use Tab 1 or Tab 2 to register repositories.")
            return

        for repo in repos:
            repo_id = repo["id"]
            commits_count = db.get_commits_count(repo_id)
            status_color = "green" if repo["is_cloned"] else "orange"

            with st.container(border=True):
                col_h1, col_h2 = st.columns([3, 1])
                with col_h1:
                    st.markdown(f"### **{repo['full_name']}**")
                    st.caption(f"Status: :{status_color}[**{repo['status'].upper()}**] | Stars: ⭐ {repo['stars']} | Commits in DB: `{commits_count}`")
                    st.write(f"**License:** {repo['license']} | **Default Branch:** `{repo['default_branch']}`")
                    if repo['local_path']:
                        st.code(repo['local_path'], language="text")
                with col_h2:
                    st.caption(f"Last Synced:\n{repo.get('last_sync_at') or 'Never'}")

                # Actions row
                c_act1, c_act2, c_act3, c_act4 = st.columns(4)

                with c_act1:
                    clone_btn_label = "🔄 Pull / Update" if repo["is_cloned"] else "📥 Clone Repo"
                    if st.button(clone_btn_label, key=f"btn_sync_{repo_id}", use_container_width=True):
                        p_bar = st.progress(0.1, text="Syncing repository...")
                        def on_prog(msg: str, pct: float) -> None:
                            p_bar.progress(pct, text=msg)

                        try:
                            res = repo_mgr.clone_or_update(
                                url=repo["url"] if repo["url"].endswith(".git") else f"{repo['url']}.git",
                                owner=repo["owner"],
                                name=repo["name"],
                                default_branch=repo["default_branch"],
                                progress_callback=on_prog,
                            )
                            st.success(f"Finished: {res['status']} (HEAD: {res['head_commit'][:8]})")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Sync failed: {e}")

                with c_act2:
                    if st.button("📜 Extract Commits", key=f"btn_commits_{repo_id}", disabled=not repo["is_cloned"], use_container_width=True):
                        if not repo["local_path"] or not Path(repo["local_path"]).exists():
                            st.error("Repository local directory is missing or not cloned.")
                        else:
                            p_bar = st.progress(0.1, text="Extracting commits...")
                            def on_commit_prog(msg: str, pct: float) -> None:
                                p_bar.progress(pct, text=msg)

                            try:
                                stats = commit_collector.extract_and_persist(
                                    repository_id=repo_id,
                                    local_path=repo["local_path"],
                                    progress_callback=on_commit_prog,
                                )
                                st.success(f"Extracted {stats['new_extracted']} new commits (Total in repo: {stats['total_in_repo']})!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Commit extraction error: {e}")

                with c_act3:
                    with st.popover("👁️ View Commits"):
                        recent_commits = db.list_commits(repository_id=repo_id, limit=20)
                        if recent_commits:
                            df_c = pd.DataFrame(recent_commits)[["commit_sha", "committed_date", "author_name", "modifies_csharp", "message"]]
                            st.dataframe(df_c, use_container_width=True)
                        else:
                            st.write("No commits extracted yet.")

                with c_act4:
                    if st.button("🗑️ Unlink from DB", key=f"btn_del_{repo_id}", use_container_width=True, help="Removes repository record from database. Local files are NOT deleted."):
                        db.delete_repository(repo_id)
                        st.warning(f"Unlinked {repo['full_name']} from database (local files preserved).")
                        st.rerun()
