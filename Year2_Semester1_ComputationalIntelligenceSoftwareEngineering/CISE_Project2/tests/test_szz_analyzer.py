"""Unit and integration tests for SZZ Algorithm using local synthetic Git repositories."""
import pytest
import git
from pathlib import Path

from src.database.connection import Database
from src.database.repository import RepositoryDB
from src.mining.szz_analyzer import SZZAnalyzer


@pytest.fixture
def synthetic_szz_repo(tmp_path):
    """Create a local Git repository with a controlled Bug-Introducing Commit (BIC) and Bug Fix."""
    repo_dir = tmp_path / "szz_synthetic_repo"
    repo_dir.mkdir()
    repo = git.Repo.init(repo_dir)

    # 1. Commit 1: Introduce buggy method (BIC)
    cs_path = repo_dir / "Calculator.cs"
    code_v1 = """public class Calculator
{
    public int Divide(int a, int b)
    {
        if (b < 0) return 0;
        return a / b;
    }
}
"""
    cs_path.write_text(code_v1, encoding="utf-8")
    repo.index.add(["Calculator.cs"])
    bic_commit = repo.index.commit("Introduce Calculator.Divide with bug")

    # 2. Commit 2: Unrelated change (Docs)
    doc_path = repo_dir / "README.md"
    doc_path.write_text("# Math Lib", encoding="utf-8")
    repo.index.add(["README.md"])
    repo.index.commit("Add README docs")

    # 3. Commit 3: Bug fix modifying the defective line
    code_v2 = """public class Calculator
{
    public int Divide(int a, int b)
    {
        if (b == 0) throw new System.DivideByZeroException();
        return a / b;
    }
}
"""
    cs_path.write_text(code_v2, encoding="utf-8")
    repo.index.add(["Calculator.cs"])
    fix_commit = repo.index.commit("Fix Divide zero check")

    return repo_dir, repo, bic_commit, fix_commit


def test_szz_identifies_true_bic(synthetic_szz_repo, tmp_path):
    repo_dir, repo, bic_commit, fix_commit = synthetic_szz_repo
    db = Database(tmp_path / "szz_test.db")
    repo_db = RepositoryDB(db)

    repo_id = repo_db.upsert_repository({
        "full_name": "test/szz_repo",
        "name": "szz_repo",
        "owner": "test",
        "url": str(repo_dir),
    })

    analyzer = SZZAnalyzer(db=repo_db)
    bic_traces = analyzer.analyze_commit(repo, fix_commit.hexsha, repo_id)

    assert len(bic_traces) >= 1
    # Verify that the blamed inducing commit is exactly Commit 1 (the BIC)!
    assert bic_traces[0]["inducing_commit_sha"] == bic_commit.hexsha
    assert bic_traces[0]["fixing_commit_sha"] == fix_commit.hexsha
    assert bic_traces[0]["file_path"] == "Calculator.cs"
    assert "if (b < 0) return 0;" in bic_traces[0]["deleted_line_content"]

    # Verify persisted in szz_results table
    persisted = repo_db.list_szz_results(repo_id)
    assert len(persisted) >= 1
    assert persisted[0]["inducing_commit_sha"] == bic_commit.hexsha


def test_szz_filters_whitespace_and_comments(tmp_path):
    repo_dir = tmp_path / "szz_filter_repo"
    repo_dir.mkdir()
    repo = git.Repo.init(repo_dir)

    cs_path = repo_dir / "Service.cs"
    cs_path.write_text("public class Service {\n    // Original comment\n    public void Run() {}\n}\n", encoding="utf-8")
    repo.index.add(["Service.cs"])
    repo.index.commit("Initial commit")

    # Make cosmetic change: change comment and adjust indentation only
    cs_path.write_text("public class Service {\n        // Updated comment\n    public void Run() {}\n}\n", encoding="utf-8")
    repo.index.add(["Service.cs"])
    cosmetic_commit = repo.index.commit("Cosmetic comment and whitespace")

    analyzer = SZZAnalyzer()
    traces = analyzer.analyze_commit(repo, cosmetic_commit.hexsha, repository_id=1)
    # Pure comment/cosmetic change should produce 0 BIC traces
    assert len(traces) == 0


def test_szz_merge_commit_handling(tmp_path):
    repo_dir = tmp_path / "szz_merge_repo"
    repo_dir.mkdir()
    repo = git.Repo.init(repo_dir)

    cs_path = repo_dir / "Logic.cs"
    cs_path.write_text("public class Logic { public int Calc() => 10; }", encoding="utf-8")
    repo.index.add(["Logic.cs"])
    c1 = repo.index.commit("Initial Logic")

    # Create feature branch that fixes the logic
    feat = repo.create_head("fix-logic")
    feat.checkout()
    cs_path.write_text("public class Logic { public int Calc() => 20; }", encoding="utf-8")
    repo.index.add(["Logic.cs"])
    c_fix = repo.index.commit("Fix Logic.Calc return value")

    # Switch back to master and merge
    main_branch = repo.heads.master if "master" in repo.heads else repo.heads.main
    main_branch.checkout()
    repo.git.merge("fix-logic", "-m", "Merge fix-logic into mainline")
    c_merge = repo.head.commit

    analyzer = SZZAnalyzer()
    # Analyzing merge commit should diff against parents[0] (mainline) and blame back to c1
    traces = analyzer.analyze_commit(repo, c_merge.hexsha, repository_id=1)
    assert len(traces) >= 1
    assert traces[0]["inducing_commit_sha"] == c1.hexsha

