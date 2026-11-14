"""Collection package."""
from repositories.github_client import GitHubClient, GitHubAPIError, RateLimitExceededError
from repositories.repository_manager import RepositoryManager, RepositoryManagerError
from repositories.commit_collector import CommitCollector, CommitCollectorError

__all__ = [
    "GitHubClient",
    "GitHubAPIError",
    "RateLimitExceededError",
    "RepositoryManager",
    "RepositoryManagerError",
    "CommitCollector",
    "CommitCollectorError",
]

