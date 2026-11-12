"""Label Manager for extracting method-level observations and assigning defect ground truth."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import git

from src.analyzer.roslyn_client import RoslynClient
from src.database.repository import RepositoryDB
from src.utils.logger import setup_logger

logger = setup_logger("label_manager")


class LabelManager:
    """Extracts method-level observations from Git revisions and manages defect labels."""

    def __init__(self, db: RepositoryDB, roslyn_client: Optional[RoslynClient] = None) -> None:
        self.db = db
        self.roslyn = roslyn_client or RoslynClient()

    def get_file_content_at_commit(self, repo: git.Repo, commit_sha: str, file_path: str) -> Optional[str]:
        """Retrieve source code of a file at a specific historical commit."""
        try:
            norm_path = file_path.replace("\\", "/")
            commit = repo.commit(commit_sha)
            blob = commit.tree / norm_path
            raw = blob.data_stream.read().decode("utf-8", errors="replace")
            return raw.replace("\r\n", "\n").replace("\r", "\n")
        except Exception as e:
            logger.debug(f"Could not read {file_path} at commit {commit_sha[:8]}: {e}")
            return None

    def create_observations_from_szz(
        self,
        repository_id: int,
        local_path: Path | str,
    ) -> List[Dict[str, Any]]:
        """Map SZZ line-level traces to enclosing C# methods and create Label 1 (Buggy) observations."""
        repo = git.Repo(local_path)
        szz_traces = self.db.list_szz_results(repository_id)

        created_observations: List[Dict[str, Any]] = []
        processed_keys: Set[str] = set()

        for trace in szz_traces:
            fix_sha = trace["fixing_commit_sha"]
            bic_sha = trace["inducing_commit_sha"]
            file_path = trace["file_path"]
            deleted_line = trace["deleted_line_number"]

            if not deleted_line:
                continue

            fix_commit = repo.commit(fix_sha)
            if not fix_commit.parents:
                continue
            parent_sha = fix_commit.parents[0].hexsha

            # 1. Fetch pre-fix code from parent of fix commit
            pre_fix_code = self.get_file_content_at_commit(repo, parent_sha, file_path)
            if not pre_fix_code:
                continue

            # 2. Locate enclosing method using Roslyn AST
            pre_method = self.roslyn.find_enclosing_method(pre_fix_code, deleted_line)
            if not pre_method:
                # The deleted line was outside any method (e.g. field/class declaration or import)
                continue

            dedup_key = f"{parent_sha}:{file_path}:{pre_method['method_signature']}"
            if dedup_key in processed_keys:
                continue
            processed_keys.add(dedup_key)

            # 3. Retrieve corrected method from fixing commit if available
            post_fix_code = self.get_file_content_at_commit(repo, fix_sha, file_path)
            corrected_source: Optional[str] = None
            if post_fix_code:
                post_methods = self.roslyn.extract_methods(code=post_fix_code)
                for pm in post_methods:
                    if pm["method_name"] == pre_method["method_name"] and pm["class_name"] == pre_method["class_name"]:
                        corrected_source = pm["source_code"]
                        break

            # 4. Insert observation (Label 1: Confirmed / Candidate Buggy Method)
            obs_data = {
                "repository_id": repository_id,
                "commit_sha": parent_sha,
                "parent_sha": bic_sha,
                "bug_fix_commit_sha": fix_sha,
                "file_path": file_path,
                "class_name": pre_method["class_name"],
                "method_name": pre_method["method_name"],
                "method_signature": pre_method["method_signature"],
                "source_code": pre_method["source_code"],
                "corrected_code": corrected_source,
                "label": 1,
                "label_confidence": trace.get("confidence", 0.85),
                "evidence_category": "szz_bic",
                "bug_fixing_commit_message": fix_commit.message.strip(),
                "issue_or_pr_url": None,
            }
            obs_id = self.db.insert_observation(obs_data)
            obs_data["id"] = obs_id
            created_observations.append(obs_data)

        logger.info(f"Created {len(created_observations)} Label 1 observations from SZZ traces for repo #{repository_id}.")
        return created_observations

    def sample_candidate_clean_methods(
        self,
        repository_id: int,
        local_path: Path | str,
        target_count: int = 50,
    ) -> List[Dict[str, Any]]:
        """Sample candidate non-buggy (Label 0) methods from stable repository revisions."""
        repo = git.Repo(local_path)
        head_commit = repo.head.commit.hexsha

        # Gather all methods currently known to have bugs
        known_buggy_signatures = {
            f"{o['file_path']}:{o['method_signature']}"
            for o in self.db.list_observations(repository_id=repository_id, label=1)
        }

        # Find all .cs files in repository tree at HEAD
        cs_files = [f for f in repo.git.ls_files().splitlines() if f.lower().endswith(".cs") and not any(p.search(f) for p in [re.compile(r"test|obj|bin", re.I)])]

        clean_observations: List[Dict[str, Any]] = []

        for fpath in cs_files:
            if len(clean_observations) >= target_count:
                break

            content = self.get_file_content_at_commit(repo, head_commit, fpath)
            if not content:
                continue

            methods = self.roslyn.extract_methods(code=content)
            for m in methods:
                sig_key = f"{fpath}:{m['method_signature']}"
                if sig_key in known_buggy_signatures:
                    continue  # Known buggy method; do not label clean

                obs_data = {
                    "repository_id": repository_id,
                    "commit_sha": head_commit,
                    "parent_sha": None,
                    "bug_fix_commit_sha": None,
                    "file_path": fpath,
                    "class_name": m["class_name"],
                    "method_name": m["method_name"],
                    "method_signature": m["method_signature"],
                    "source_code": m["source_code"],
                    "corrected_code": None,
                    "label": 0,
                    "label_confidence": 0.80,
                    "evidence_category": "stable_version",
                    "bug_fixing_commit_message": "Sampled from stable HEAD without known defect traces.",
                    "issue_or_pr_url": None,
                }
                obs_id = self.db.insert_observation(obs_data)
                obs_data["id"] = obs_id
                clean_observations.append(obs_data)

                if len(clean_observations) >= target_count:
                    break

        logger.info(f"Sampled {len(clean_observations)} candidate clean (Label 0) methods for repo #{repository_id}.")
        return clean_observations

    def mark_observation_uncertain(self, observation_id: int, reason: str = "ambiguous_evidence") -> None:
        """Mark an observation as uncertain (-1) so it is excluded from training."""
        self.db.update_observation_label(observation_id, new_label=-1, reason=reason)
