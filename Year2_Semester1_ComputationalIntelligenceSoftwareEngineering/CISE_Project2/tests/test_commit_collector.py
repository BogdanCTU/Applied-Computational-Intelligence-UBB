"""Unit tests for CommitCollector using local git fixtures."""
import pytest
import git
from pathlib import Path

from src.collection.commit_collector import CommitCollector
from src.database.connection import Database
from src.database.repository import RepositoryDB


@pytest.fixture
def complex_git_repo(tmp_path):
    """Create a local git repository with commits, branches, and a merge commit."""
    repo_dir = tmp_path / "csharp_history_repo"
    repo_dir.mkdir()
    repo = git.Repo.init(repo_dir)

    # 1. First commit: C# file
    f1 = repo_dir / "Service.cs"
    f1.write_text("public class Service { public void Run() {} }", encoding="utf-8")
    repo.index.add(["Service.cs"])
    c1 = repo.index.commit("Add Service.cs")

    # 2. Branch: feature branch with non-C# file
    feat_branch = repo.create_head("feature-docs")
    feat_branch.checkout()
    f2 = repo_dir / "docs.txt"
    f2.write_text("Service documentation", encoding="utf-8")
    repo.index.add(["docs.txt"])
    c2 = repo.index.commit("Add docs")

    # 3. Main branch commit
    main_branch = repo.heads.master if "master" in repo.heads else repo.heads.main
    main_branch.checkout()
    f3 = repo_dir / "Service.cs"
    f3.write_text("public class Service { public void Run() { System.Console.WriteLine(\"Running\"); } }", encoding="utf-8")
    repo.index.add(["Service.cs"])
    c3 = repo.index.commit("Update Service.cs implementation")

    # 4. Merge commit
    repo.git.merge("feature-docs", "-m", "Merge branch feature-docs")
    c4 = repo.head.commit

    return repo_dir, [c1, c2, c3, c4]


def test_commit_collection_and_merge_handling(tmp_path, complex_git_repo):
    repo_dir, expected_commits = complex_git_repo
    db = Database(tmp_path / "test_commits.db")
    repo_db = RepositoryDB(db)

    repo_id = repo_db.upsert_repository({
        "full_name": "org/csharp_repo",
        "name": "csharp_repo",
        "owner": "org",
        "url": str(repo_dir),
        "license": "MIT",
    })

    collector = CommitCollector(repo_db)
    result = collector.extract_and_persist(repo_id, repo_dir)

    assert result["new_extracted"] == 4
    assert result["already_present"] == 0

    # Verify commits stored in DB
    commits = repo_db.list_commits(repository_id=repo_id, limit=50)
    assert len(commits) == 4

    # Verify merge commit has multiple parent SHAs
    merge_commit = next(c for c in commits if "Merge" in c["message"])
    assert merge_commit is not None
    assert "," in merge_commit["parent_shas"]
    parents = merge_commit["parent_shas"].split(",")
    assert len(parents) == 2

    # Verify C# modification flag
    csharp_commits = [c for c in commits if c["modifies_csharp"] == 1]
    non_csharp_commits = [c for c in commits if c["modifies_csharp"] == 0]
    assert len(csharp_commits) >= 2
    assert len(non_csharp_commits) >= 1

    # Verify commit_files table entries
    first_commit = next(c for c in commits if "Add Service.cs" in c["message"])
    files = repo_db.get_commit_files(first_commit["id"])
    assert len(files) == 1
    assert files[0]["file_path"] == "Service.cs"
    assert files[0]["is_csharp"] == 1


def test_incremental_commit_collection(tmp_path, complex_git_repo):
    repo_dir, _ = complex_git_repo
    db = Database(tmp_path / "test_commits_incremental.db")
    repo_db = RepositoryDB(db)

    repo_id = repo_db.upsert_repository({
        "full_name": "org/csharp_repo",
        "name": "csharp_repo",
        "owner": "org",
        "url": str(repo_dir),
        "license": "MIT",
    })

    collector = CommitCollector(repo_db)
    # First sync
    res1 = collector.extract_and_persist(repo_id, repo_dir)
    assert res1["new_extracted"] == 4

    # Re-run immediately: should detect 0 new commits
    res2 = collector.extract_and_persist(repo_id, repo_dir)
    assert res2["new_extracted"] == 0
    assert res2["already_present"] == 4

    # Add 1 new commit to the local git repo
    repo = git.Repo(repo_dir)
    new_file = repo_dir / "NewClass.cs"
    new_file.write_text("public class NewClass {}", encoding="utf-8")
    repo.index.add(["NewClass.cs"])
    repo.index.commit("Add NewClass.cs")

    # Third sync: should incrementally extract ONLY 1 new commit
    res3 = collector.extract_and_persist(repo_id, repo_dir)
    assert res3["new_extracted"] == 1
    assert res3["already_present"] == 4

    total_commits = repo_db.get_commits_count(repo_id)
    assert total_commits == 5

