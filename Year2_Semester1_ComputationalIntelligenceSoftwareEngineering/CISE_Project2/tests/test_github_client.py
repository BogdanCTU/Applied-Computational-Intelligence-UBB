"""Unit tests for GitHub REST API client."""
import pytest
from unittest.mock import MagicMock, patch
from requests.exceptions import RequestException

from src.collection.github_client import GitHubClient, GitHubAPIError, RateLimitExceededError


@pytest.fixture
def mock_repo_json():
    return {
        "id": 123456,
        "full_name": "dotnet/samples",
        "name": "samples",
        "owner": {"login": "dotnet"},
        "html_url": "https://github.com/dotnet/samples",
        "clone_url": "https://github.com/dotnet/samples.git",
        "description": "C# sample code",
        "stargazers_count": 550,
        "forks_count": 120,
        "size": 4096,
        "default_branch": "main",
        "license": {"spdx_id": "MIT", "name": "MIT License"},
        "fork": False,
        "archived": False,
        "created_at": "2020-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "pushed_at": "2026-01-01T12:00:00Z",
    }


def test_client_headers_unauthenticated():
    client = GitHubClient()
    assert "Authorization" not in client.session.headers
    assert "Accept" in client.session.headers


def test_client_headers_authenticated():
    client = GitHubClient(token="ghp_fake_token_12345")
    assert client.session.headers["Authorization"] == "token ghp_fake_token_12345"


@patch("requests.Session.get")
def test_search_repositories_query_building(mock_get, mock_repo_json):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"X-RateLimit-Remaining": "50"}
    mock_resp.json.return_value = {
        "total_count": 1,
        "incomplete_results": False,
        "items": [mock_repo_json],
    }
    mock_get.return_value = mock_resp

    client = GitHubClient()
    results = client.search_repositories(
        keywords="analyzer",
        min_stars=100,
        min_size_kb=50,
        exclude_forks=True,
        page=2,
        per_page=15,
    )

    mock_get.assert_called_once()
    _, kwargs = mock_get.call_args
    params = kwargs["params"]
    assert "language:csharp" in params["q"]
    assert "analyzer" in params["q"]
    assert "stars:>=100" in params["q"]
    assert "size:>=50" in params["q"]
    assert "fork:false" in params["q"]
    assert params["page"] == 2
    assert params["per_page"] == 15

    assert results["total_count"] == 1
    assert len(results["items"]) == 1
    item = results["items"][0]
    assert item["full_name"] == "dotnet/samples"
    assert item["license"] == "MIT"
    assert item["stars"] == 550


@patch("requests.Session.get")
def test_get_repository_metadata(mock_get, mock_repo_json):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"X-RateLimit-Remaining": "50"}
    mock_resp.json.return_value = mock_repo_json
    mock_get.return_value = mock_resp

    client = GitHubClient()
    repo = client.get_repository("dotnet", "samples")

    assert repo["full_name"] == "dotnet/samples"
    assert repo["owner"] == "dotnet"
    assert repo["default_branch"] == "main"
    assert repo["size_kb"] == 4096


@patch("requests.Session.get")
def test_rate_limit_handling(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.headers = {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1999999999"}
    mock_resp.text = "API rate limit exceeded"
    mock_get.return_value = mock_resp

    client = GitHubClient()
    with pytest.raises(RateLimitExceededError):
        client.get_repository("dotnet", "samples")


@patch("requests.Session.get")
def test_network_failure_retries_and_raises(mock_get):
    mock_get.side_effect = RequestException("DNS lookup failed")

    client = GitHubClient(max_retries=2, backoff_factor=0.01)
    with pytest.raises(GitHubAPIError):
        client.get_repository("owner", "repo")

    assert mock_get.call_count == 3

