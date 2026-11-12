"""Unit and integration tests for LabelManager."""
import pytest
import git
from pathlib import Path

from src.database.connection import Database
from src.database.repository import RepositoryDB
from src.labeling.label_manager import LabelManager
from src.mining.szz_analyzer import SZZAnalyzer


@pytest.fixture
def repo_with_szz(tmp_path):
    """Set up a git repository with an SZZ defect trace."""
    repo_dir = tmp_path / "label_test_repo"
    repo_dir.mkdir()
    repo = git.Repo.init(repo_dir)

    cs_path = repo_dir / "MathUtils.cs"
    code_v1 = """public class MathUtils
{
    public int Multiply(int a, int b) => a * b;

    public int Subtract(int a, int b)
    {
        return a + b; // Defect: added instead of subtracted
    }
}
"""
    cs_path.write_text(code_v1, encoding="utf-8")
    repo.index.add(["MathUtils.cs"])
    bic = repo.index.commit("Initial MathUtils with defect in Subtract")

    code_v2 = """public class MathUtils
{
    public int Multiply(int a, int b) => a * b;

    public int Subtract(int a, int b)
    {
        return a - b; // Fixed
    }
}
"""
    cs_path.write_text(code_v2, encoding="utf-8")
    repo.index.add(["MathUtils.cs"])
    fix = repo.index.commit("Fix Subtract operator")

    db = Database(tmp_path / "label_test.db")
    repo_db = RepositoryDB(db)
    repo_id = repo_db.upsert_repository({
        "full_name": "org/math",
        "name": "math",
        "owner": "org",
        "url": str(repo_dir),
    })

    # Run SZZ to produce traces
    analyzer = SZZAnalyzer(db=repo_db)
    analyzer.analyze_commit(repo, fix.hexsha, repo_id)

    return repo_dir, repo_db, repo_id, bic, fix


def test_create_label_1_observations_from_szz(repo_with_szz):
    repo_dir, repo_db, repo_id, bic, fix = repo_with_szz
    label_mgr = LabelManager(repo_db)

    observations = label_mgr.create_observations_from_szz(repo_id, repo_dir)
    assert len(observations) == 1

    obs = observations[0]
    assert obs["label"] == 1
    assert obs["method_name"] == "Subtract"
    assert obs["class_name"] == "MathUtils"
    assert obs["evidence_category"] == "szz_bic"
    assert "return a + b;" in obs["source_code"]
    assert "return a - b;" in obs["corrected_code"]
    assert obs["bug_fix_commit_sha"] == fix.hexsha

    # Verify persisted in database
    db_obs = repo_db.list_observations(repository_id=repo_id, label=1)
    assert len(db_obs) == 1
    assert db_obs[0]["method_name"] == "Subtract"


def test_sample_candidate_clean_methods(repo_with_szz):
    repo_dir, repo_db, repo_id, _, _ = repo_with_szz
    label_mgr = LabelManager(repo_db)

    # First generate buggy observations so 'Subtract' is known buggy
    label_mgr.create_observations_from_szz(repo_id, repo_dir)

    # Sample candidate clean methods from HEAD
    clean_obs = label_mgr.sample_candidate_clean_methods(repo_id, repo_dir, target_count=5)
    assert len(clean_obs) >= 1

    # 'Multiply' was never touched by a bug fix, so it should be candidate clean
    multiply_obs = next((o for o in clean_obs if o["method_name"] == "Multiply"), None)
    assert multiply_obs is not None
    assert multiply_obs["label"] == 0
    assert multiply_obs["evidence_category"] == "stable_version"

    # 'Subtract' MUST NOT be in clean observations
    subtract_clean = next((o for o in clean_obs if o["method_name"] == "Subtract"), None)
    assert subtract_clean is None


def test_mark_observation_uncertain(repo_with_szz):
    repo_dir, repo_db, repo_id, _, _ = repo_with_szz
    label_mgr = LabelManager(repo_db)
    observations = label_mgr.create_observations_from_szz(repo_id, repo_dir)
    obs_id = observations[0]["id"]

    label_mgr.mark_observation_uncertain(obs_id, reason="ambiguous_commit")
    updated = repo_db.list_observations(repository_id=repo_id, label=-1)
    assert len(updated) == 1
    assert updated[0]["id"] == obs_id
    assert updated[0]["label"] == -1
    assert updated[0]["evidence_category"] == "ambiguous_commit"

