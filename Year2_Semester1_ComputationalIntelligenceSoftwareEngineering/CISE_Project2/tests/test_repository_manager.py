"""Unit tests for RepositoryManager using local git fixtures."""
import pytest
import git
from pathlib import Path

from src.collection.repository_manager import RepositoryManager, RepositoryManagerError
from src.database.connection import Database
from src.database.repository import RepositoryDB


@pytest.fixture
def test_git_repo(tmp_path):
    """Create a real local git repository with multiple commits."""
    origin_dir = tmp_path / "origin_repo"
    origin_dir.mkdir()
    repo = git.Repo.init(origin_dir)

    # Initial commit
    file1 = origin_dir / "Calculator.cs"
    file1.write_text("public class Calculator { public int Add(int a, int b) => a + b; }", encoding="utf-8")
    repo.index.add(["Calculator.cs"])
    c1 = repo.index.commit("Initial commit: add Calculator.cs")

    # Second commit
    file2 = origin_dir / "README.md"
    file2.write_text("# Calculator Project", encoding="utf-8")
    repo.index.add(["README.md"])
    c2 = repo.index.commit("Docs: add README.md")

    return origin_dir, [c1.hexsha, c2.hexsha]


def test_sanitize_path_component():
    mgr = RepositoryManager(Path("tmp"))
    assert mgr.sanitize_path_component("dotnet") == "dotnet"
    assert mgr.sanitize_path_component("roslyn-analyzer.v1") == "roslyn-analyzer.v1"

    with pytest.raises(RepositoryManagerError):
        mgr.sanitize_path_component("../sneaky")

    with pytest.raises(RepositoryManagerError):
        mgr.sanitize_path_component("foo/bar")

    with pytest.raises(RepositoryManagerError):
        mgr.sanitize_path_component("")


def test_clone_full_history_and_idempotency(tmp_path, test_git_repo):
    origin_dir, commit_shas = test_git_repo
    storage_dir = tmp_path / "cloned_storage"
    db = Database(tmp_path / "test.db")
    repo_db = RepositoryDB(db)

    repo_id = repo_db.upsert_repository({
        "full_name": "test_owner/sample_repo",
        "name": "sample_repo",
        "owner": "test_owner",
        "url": str(origin_dir),
        "license": "MIT",
        "default_branch": "master",
    })

    mgr = RepositoryManager(storage_dir, db=repo_db)

    # Clone
    result = mgr.clone_or_update(
        url=str(origin_dir),
        owner="test_owner",
        name="sample_repo",
        default_branch="master",
    )
    assert result["status"] == "cloned"
    cloned_path = Path(result["local_path"])
    assert cloned_path.exists()
    assert (cloned_path / "Calculator.cs").exists()

    # Verify full history is preserved (not shallow)
    cloned_repo = git.Repo(cloned_path)
    cloned_commits = [c.hexsha for c in cloned_repo.iter_commits()]
    assert len(cloned_commits) == 2
    assert set(cloned_commits) == set(commit_shas)

    # Verify DB update
    record = repo_db.get_repository_by_id(repo_id)
    assert record["is_cloned"] == 1
    assert record["status"] == "cloned"

    # Second run should be idempotent update, not fail
    update_res = mgr.clone_or_update(
        url=str(origin_dir),
        owner="test_owner",
        name="sample_repo",
        default_branch="master",
    )
    assert update_res["status"] == "updated"


def test_dirty_repo_protection(tmp_path, test_git_repo):
    origin_dir, _ = test_git_repo
    storage_dir = tmp_path / "cloned_storage"
    mgr = RepositoryManager(storage_dir)

    result = mgr.clone_or_update(
        url=str(origin_dir),
        owner="test_owner",
        name="sample_repo",
        default_branch="master",
    )
    cloned_path = Path(result["local_path"])

    # Make uncommitted modification
    (cloned_path / "Calculator.cs").write_text("// Modified locally", encoding="utf-8")

    # Updating dirty repo must raise error to protect local work
    with pytest.raises(RepositoryManagerError, match="uncommitted local changes"):
        mgr.update_repository(cloned_path, default_branch="master")

