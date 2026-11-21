"""Bug-Fixing Commit Detector using commit message heuristics, issue references, and diff filters."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from database.repository import RepositoryDB
from utils.logger import setup_logger

logger = setup_logger("bug_fix_detector")


class BugFixDetector:
    """Heuristic rule-based engine to discover and classify bug-fixing commits."""

    ACTION_PATTERNS = [
        re.compile(r"\b(?:fix(?:es|ed|ing)?|close[sd]?|resolve[sd]?)\s+(?:#|gh-)(\d+)\b", re.IGNORECASE),
        re.compile(r"\b(?:fix(?:es|ed|ing)?|resolve[sd]?)\s+(?:issue|bug)\s+(?:#)?(\d+)\b", re.IGNORECASE),
        re.compile(r"#(\d+)\b"),
    ]

    BUG_KEYWORDS = {
        "bug": 0.40,
        "fix": 0.35,
        "fixes": 0.35,
        "fixed": 0.35,
        "defect": 0.45,
        "regression": 0.50,
        "crash": 0.40,
        "exception": 0.30,
        "overflow": 0.30,
        "race condition": 0.50,
        "nullreference": 0.45,
        "null reference": 0.45,
        "deadlock": 0.45,
        "memory leak": 0.45,
        "incorrect": 0.25,
        "fault": 0.30,
        "hotfix": 0.45,
        "bugfix": 0.50,
    }

    FP_KEYWORDS = [
        re.compile(r"\b(?:typo|spelling|grammar|comment|docs?|documentation)\b", re.IGNORECASE),
        re.compile(r"\b(?:formatting|reformat|indentation|stylecop|whitespace)\b", re.IGNORECASE),
        re.compile(r"\b(?:license|readme|changelog|version bump)\b", re.IGNORECASE),
        re.compile(r"\b(?:unit\s*test\s*fixture|test\s*fixture)\b", re.IGNORECASE),
    ]

    STRICT_FP_KEYWORDS = [
        re.compile(r"\b(?:dependabot|renovate|bump|upgrade\s+package|update\s+dependencies)\b", re.IGNORECASE),
        re.compile(r"^(?:chore|docs|style|ci|build|test)\s*(?:\([^)]+\))?:", re.IGNORECASE),
        re.compile(r"\b(?:merge\s+branch|merge\s+pull\s+request|revert\s+\"chore)\b", re.IGNORECASE),
        re.compile(r"\b(?:refactor|cleanup|clean\s+up|rename|reorganize)\b", re.IGNORECASE),
    ]

    def __init__(self, db: Optional[RepositoryDB] = None, default_threshold: float = 0.50) -> None:
        self.db = db
        self.default_threshold = default_threshold

    def analyze_commit(
        self,
        message: str,
        modifies_csharp: bool = True,
        files_changed_count: int = 1,
        strict_mode: bool = False,
        threshold: Optional[float] = None,
    ) -> Tuple[bool, float, str, List[str]]:
        """Evaluate a commit message and metadata to determine bug-fixing status.

        Returns:
            (is_bug_fix, confidence_score, evidence_rationale, linked_issues)
        """
        if not message or not message.strip():
            return False, 0.0, "Empty commit message", []

        eff_threshold = threshold if threshold is not None else self.default_threshold
        clean_msg = message.strip()
        lower_msg = clean_msg.lower()

        linked_issues: List[str] = []
        for pat in self.ACTION_PATTERNS:
            for match in pat.finditer(clean_msg):
                issue_id = match.group(1)
                if issue_id and issue_id not in linked_issues:
                    linked_issues.append(issue_id)

        evidence_items: List[str] = []
        score = 0.0

        if any(pat.search(clean_msg) for pat in self.ACTION_PATTERNS[:2]):
            score += 0.55
            evidence_items.append(f"Linked closing issue/PR: #{', #'.join(linked_issues)}")
        elif linked_issues:
            score += 0.25
            evidence_items.append(f"Referenced issue/PR: #{', #'.join(linked_issues)}")

        matched_keywords: set[str] = set()
        for kw, weight in self.BUG_KEYWORDS.items():
            # Avoid double-counting 'fix' and 'fixed'/'fixes' on same stem
            stem = "fix" if kw in ("fix", "fixes", "fixed") else kw
            if stem in matched_keywords:
                continue
            if re.search(rf"\b{re.escape(kw)}\b", lower_msg):
                matched_keywords.add(stem)
                score += weight
                evidence_items.append(f"Keyword matched: '{kw}' (+{weight:.2f})")

        for fp_pat in self.FP_KEYWORDS:
            if fp_pat.search(clean_msg):
                penalty = 0.40
                score = max(0.0, score - penalty)
                evidence_items.append(f"Penalized for cosmetic/doc pattern '{fp_pat.pattern}' (-{penalty:.2f})")

        if strict_mode:
            for sfp_pat in self.STRICT_FP_KEYWORDS:
                if sfp_pat.search(clean_msg):
                    penalty = 0.35
                    score = max(0.0, score - penalty)
                    evidence_items.append(f"Strict FP penalty '{sfp_pat.pattern}' (-{penalty:.2f})")

        if not modifies_csharp:
            score = max(0.0, score - 0.35)
            evidence_items.append("Penalized: commit does not modify any C# files (-0.35)")
            if strict_mode:
                score = 0.0

        if files_changed_count > 30:
            score = max(0.0, score - 0.25)
            evidence_items.append(f"Penalized: high change breadth ({files_changed_count} files) (-0.25)")
        elif strict_mode and files_changed_count > 18:
            score = max(0.0, score - 0.20)
            evidence_items.append(f"Strict breadth penalty ({files_changed_count} files) (-0.20)")

        final_score = min(1.0, max(0.0, score))
        is_bug_fix = final_score >= eff_threshold

        rationale = "; ".join(evidence_items) if evidence_items else "No defect signals detected"
        return is_bug_fix, round(final_score, 3), rationale, linked_issues

    def detect_in_repository(
        self,
        repository_id: int,
        threshold: Optional[float] = None,
        force: bool = False,
        strict_mode: bool = False,
    ) -> Dict[str, Any]:
        """Scan stored commits in repository and update bug-fix classification in database."""
        if not self.db:
            raise ValueError("RepositoryDB instance required for database updates.")

        eff_threshold = threshold if threshold is not None else self.default_threshold
        commits = self.db.list_commits(repository_id=repository_id, limit=50000)

        total = len(commits)
        bug_fixes_found = 0
        updated = 0
        pending_updates: List[Dict[str, Any]] = []

        for c in commits:
            if not force and c.get("analyzed_at") is not None and c.get("is_bug_fix") is not None:
                if c["is_bug_fix"] == 1:
                    bug_fixes_found += 1
                continue

            is_fix, conf, evidence, _ = self.analyze_commit(
                message=c["message"] or "",
                modifies_csharp=bool(c.get("modifies_csharp", 1)),
                files_changed_count=c.get("files_changed_count", 1),
                strict_mode=strict_mode,
                threshold=eff_threshold,
            )

            if c.get("review_status") == "confirmed":
                is_fix = True
                conf = 1.0
                evidence = f"Manually confirmed. {evidence}"
            elif c.get("review_status") == "rejected":
                is_fix = False
                conf = 0.0
                evidence = f"Manually rejected. {evidence}"

            pending_updates.append({
                "id": c["id"],
                "is_bug_fix": 1 if is_fix else 0,
                "bug_fix_confidence": conf,
                "bug_fix_evidence": evidence,
            })

            if is_fix:
                bug_fixes_found += 1
            updated += 1

        if pending_updates:
            self.db.batch_update_commit_classifications(pending_updates)

        self.db.update_repository_metrics(repository_id, {"bug_fixes_count": bug_fixes_found})
        logger.info(f"Bug fix detection complete for repo #{repository_id}: {bug_fixes_found}/{total} commits classified as bug fixes.")
        return {
            "total_commits": total,
            "classified_bug_fixes": bug_fixes_found,
            "updated_records": updated,
            "threshold_used": eff_threshold,
        }
