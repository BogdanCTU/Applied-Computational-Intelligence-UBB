"""Unit tests for Bug-Fixing Commit Detector."""
import pytest
from src.database.connection import Database
from src.database.repository import RepositoryDB
from src.mining.bug_fix_detector import BugFixDetector


def test_positive_and_negative_commit_messages():
    detector = BugFixDetector(default_threshold=0.50)

    # Strong positives
    is_fix, conf, evidence, issues = detector.analyze_commit("Fix null reference exception in Parser.cs")
    assert is_fix is True
    assert conf >= 0.50
    assert "fix" in evidence.lower() or "exception" in evidence.lower()

    is_fix, conf, evidence, issues = detector.analyze_commit("Fixes #1042: crash on empty array input")
    assert is_fix is True
    assert conf >= 0.70
    assert "1042" in issues

    is_fix, conf, evidence, issues = detector.analyze_commit("Resolve race condition and deadlock in ConnectionPool")
    assert is_fix is True
    assert conf >= 0.60

    # False positives that should be rejected or penalized
    is_fix, conf, evidence, issues = detector.analyze_commit("Fix typo in README.md documentation", modifies_csharp=False)
    assert is_fix is False
    assert conf < 0.50

    is_fix, conf, evidence, issues = detector.analyze_commit("StyleCop reformatting and whitespace clean up")
    assert is_fix is False

    is_fix, conf, evidence, issues = detector.analyze_commit("Add new unit test fixture for AuthController")
    assert is_fix is False


def test_issue_pr_reference_extraction():
    detector = BugFixDetector()
    _, _, _, issues = detector.analyze_commit("Resolve issue #89 and fix GH-123")
    assert "89" in issues
    assert "123" in issues


def test_repository_batch_detection_and_manual_override(tmp_path):
    db = Database(tmp_path / "test_detector.db")
    repo_db = RepositoryDB(db)
    detector = BugFixDetector(db=repo_db, default_threshold=0.50)

    repo_id = repo_db.upsert_repository({
        "full_name": "org/repo",
        "name": "repo",
        "owner": "org",
        "url": "https://github.com/org/repo",
    })

    # Add 2 commits: 1 bug fix, 1 regular feature
    cid1 = repo_db.upsert_commit({
        "repository_id": repo_id,
        "commit_sha": "1111111",
        "message": "Fix buffer overflow defect in Decoder",
        "modifies_csharp": 1,
    })
    cid2 = repo_db.upsert_commit({
        "repository_id": repo_id,
        "commit_sha": "2222222",
        "message": "Add initial project configuration",
        "modifies_csharp": 1,
    })

    # Run batch detection
    res = detector.detect_in_repository(repo_id)
    assert res["classified_bug_fixes"] == 1

    commits = repo_db.list_commits(repository_id=repo_id, limit=5)
    c1 = next(c for c in commits if c["commit_sha"] == "1111111")
    assert c1["is_bug_fix"] == 1
    assert c1["bug_fix_confidence"] >= 0.50

    # Test manual override: reject c1
    repo_db.update_commit_review_status(cid1, review_status="rejected", is_bug_fix=False)
    # Re-run detection: should respect manual rejection
    res2 = detector.detect_in_repository(repo_id, force=True)
    assert res2["classified_bug_fixes"] == 0
