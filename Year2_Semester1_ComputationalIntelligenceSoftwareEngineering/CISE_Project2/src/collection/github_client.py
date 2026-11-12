"""GitHub REST API Client for C# repository discovery and metadata collection."""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
import requests
from requests.exceptions import RequestException

from src.utils.logger import setup_logger

logger = setup_logger("github_client")


class GitHubAPIError(Exception):
    """Base exception for GitHub API errors."""
    pass


class RateLimitExceededError(GitHubAPIError):
    """Raised when GitHub API rate limit is exceeded."""
    def __init__(self, message: str, reset_timestamp: Optional[int] = None) -> None:
        super().__init__(message)
        self.reset_timestamp = reset_timestamp


class GitHubClient:
    """Client for querying the GitHub REST API v3."""

    BASE_URL = "https://api.github.com"

    def __init__(
        self,
        token: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 30,
        backoff_factor: float = 1.5,
    ) -> None:
        self.token = token
        self.max_retries = max_retries
        self.timeout = timeout
        self.backoff_factor = backoff_factor
        self.session = requests.Session()
        self._configure_headers()

    def _configure_headers(self) -> None:
        self.session.headers.update({
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "CSharpBugDetection-AcademicClient/1.0",
        })
        if self.token:
            self.session.headers["Authorization"] = f"token {self.token}"

    def _request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Perform HTTP GET with exponential backoff and rate limit handling."""
        url = f"{self.BASE_URL}{endpoint}" if endpoint.startswith("/") else f"{self.BASE_URL}/{endpoint}"
        retries = 0

        while True:
            try:
                logger.debug(f"GitHub GET: {url} params={params}")
                response = self.session.get(url, params=params, timeout=self.timeout)

                # Check rate limit headers
                remaining = response.headers.get("X-RateLimit-Remaining")
                reset_time = response.headers.get("X-RateLimit-Reset")
                if remaining is not None and int(remaining) == 0:
                    reset_ts = int(reset_time) if reset_time else None
                    wait_seconds = max(1, reset_ts - int(time.time())) if reset_ts else 60
                    logger.warning(f"GitHub API rate limit exhausted. Resets in {wait_seconds}s.")
                    if retries < self.max_retries and wait_seconds <= 60:
                        time.sleep(wait_seconds + 1)
                        retries += 1
                        continue
                    raise RateLimitExceededError(
                        f"GitHub rate limit exceeded. Reset at {reset_ts}.",
                        reset_timestamp=reset_ts,
                    )

                if response.status_code == 200:
                    return response.json()

                if response.status_code in (403, 429) and "rate limit" in response.text.lower():
                    reset_ts = int(reset_time) if reset_time else None
                    raise RateLimitExceededError(f"GitHub rate limit reached: {response.text}", reset_ts)

                if response.status_code in (500, 502, 503, 504) and retries < self.max_retries:
                    sleep_time = self.backoff_factor ** retries
                    logger.warning(f"GitHub server error {response.status_code}. Retrying in {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                    retries += 1
                    continue

                response.raise_for_status()
                return response.json()

            except RequestException as e:
                if retries < self.max_retries:
                    sleep_time = self.backoff_factor ** retries
                    logger.warning(f"Network error: {e}. Retrying in {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                    retries += 1
                    continue
                logger.error(f"GitHub request failed permanently: {e}")
                raise GitHubAPIError(f"Request failed: {e}") from e

    def search_repositories(
        self,
        keywords: Optional[str] = None,
        min_stars: int = 100,
        min_size_kb: int = 0,
        updated_since: Optional[str] = None,
        exclude_forks: bool = True,
        exclude_archived: bool = True,
        page: int = 1,
        per_page: int = 30,
        sort: str = "stars",
        order: str = "desc",
    ) -> Dict[str, Any]:
        """Search GitHub for public C# repositories matching criteria."""
        query_parts = ["language:csharp"]
        if keywords and keywords.strip():
            query_parts.append(keywords.strip())
        if min_stars > 0:
            query_parts.append(f"stars:>={min_stars}")
        if min_size_kb > 0:
            query_parts.append(f"size:>={min_size_kb}")
        if updated_since:
            query_parts.append(f"pushed:>={updated_since}")
        if exclude_forks:
            query_parts.append("fork:false")
        if exclude_archived:
            query_parts.append("archived:false")

        q = " ".join(query_parts)
        params = {
            "q": q,
            "sort": sort,
            "order": order,
            "page": page,
            "per_page": min(100, max(1, per_page)),
        }
        logger.info(f"Searching repositories with query: '{q}' (page {page}, per_page {per_page})")
        data = self._request("/search/repositories", params=params)

        items = [self._normalize_repo(item) for item in data.get("items", [])]
        return {
            "total_count": data.get("total_count", 0),
            "incomplete_results": data.get("incomplete_results", False),
            "items": items,
            "page": page,
            "per_page": per_page,
        }

    def get_repository(self, owner: str, name: str) -> Dict[str, Any]:
        """Fetch complete repository metadata for a specific owner/name."""
        logger.info(f"Fetching metadata for repository: {owner}/{name}")
        raw_data = self._request(f"/repos/{owner}/{name}")
        return self._normalize_repo(raw_data)

    def _normalize_repo(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize raw GitHub repository JSON into application metadata dictionary."""
        license_info = raw.get("license") or {}
        license_str = license_info.get("spdx_id") or license_info.get("name") or "Unknown"

        return {
            "github_id": raw.get("id"),
            "full_name": raw.get("full_name"),
            "name": raw.get("name"),
            "owner": raw.get("owner", {}).get("login", ""),
            "url": raw.get("html_url"),
            "clone_url": raw.get("clone_url"),
            "description": raw.get("description"),
            "stars": raw.get("stargazers_count", 0),
            "forks": raw.get("forks_count", 0),
            "size_kb": raw.get("size", 0),
            "default_branch": raw.get("default_branch", "main"),
            "license": license_str,
            "is_fork": raw.get("fork", False),
            "is_archived": raw.get("archived", False),
            "created_at": raw.get("created_at"),
            "updated_at": raw.get("updated_at"),
            "pushed_at": raw.get("pushed_at"),
        }

