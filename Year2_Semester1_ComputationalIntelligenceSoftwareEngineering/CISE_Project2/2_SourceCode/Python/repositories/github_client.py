"""GitHub REST API Client for C# repository discovery, ranking, and metadata collection."""
from __future__ import annotations

from datetime import datetime, timezone
import math
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
import requests
from requests.exceptions import RequestException

from utils.logger import setup_logger

logger = setup_logger("github_client")


class GitHubAPIError(Exception):
    """Base exception for GitHub API errors."""
    pass


class RateLimitExceededError(GitHubAPIError):
    """Raised when GitHub API rate limit is exceeded."""
    def __init__(self, message: str, reset_timestamp: Optional[int] = None) -> None:
        super().__init__(message)
        self.reset_timestamp = reset_timestamp


def evaluate_repository_candidate(
    repo_item: Dict[str, Any],
    min_stars: int = 50,
    min_size_kb: int = 100,
    max_size_kb: int = 60000,
    exclude_forks: bool = True,
    exclude_archived: bool = True,
) -> Tuple[bool, float, str, Optional[str]]:
    """Evaluate a repository against inclusion criteria and compute a reproducible composite score.

    Returns:
        (is_selected, selection_score, selection_reason, exclusion_reason)
    """
    stars = int(repo_item.get("stars", 0) or 0)
    forks = int(repo_item.get("forks", 0) or 0)
    size_kb = int(repo_item.get("size_kb", 0) or 0)
    is_fork = bool(repo_item.get("is_fork", False))
    is_archived = bool(repo_item.get("is_archived", False))
    language = (repo_item.get("language") or "C#").strip()
    pushed_at = repo_item.get("pushed_at")

    if exclude_forks and is_fork:
        return False, 0.0, "", "excluded_fork"
    if exclude_archived and is_archived:
        return False, 0.0, "", "excluded_archived"
    if language and language.lower() not in ("c#", "csharp"):
        return False, 0.0, "", f"excluded_primary_language:{language}"
    if size_kb <= 0:
        return False, 0.0, "", "excluded_empty_repository"
    if size_kb < min_size_kb:
        return False, 0.0, "", f"excluded_insufficient_size_kb:{size_kb}<{min_size_kb}"
    if size_kb > max_size_kb:
        return False, 0.0, "", f"excluded_excessive_size_kb:{size_kb}>{max_size_kb}"
    if stars < min_stars:
        return False, 0.0, "", f"excluded_insufficient_stars:{stars}<{min_stars}"

    # Popularity component (log-scaled up to ~30k stars)
    star_score = min(1.0, math.log10(max(1, stars) + 1) / 4.5)

    # Recency component from pushed_at ISO timestamp
    recency_score = 0.4
    if pushed_at:
        try:
            pushed_dt = datetime.fromisoformat(str(pushed_at).replace("Z", "+00:00"))
            age_days = max(0.0, (datetime.now(timezone.utc) - pushed_dt).total_seconds() / 86400.0)
            # Half-life decay over ~730 days
            recency_score = max(0.05, math.exp(-age_days / 730.0))
        except Exception:
            recency_score = 0.4

    # Size suitability: prefer mid-to-large production C# libraries (300 KB - 25 MB)
    if 300 <= size_kb <= 25000:
        size_score = 1.0
    elif size_kb < 300:
        size_score = size_kb / 300.0
    else:
        size_score = max(0.3, 1.0 - (size_kb - 25000) / max(1, max_size_kb - 25000) * 0.7)

    # Community engagement (forks / stars ratio capped cleanly)
    fork_score = min(1.0, math.log10(max(1, forks) + 1) / 3.5)

    composite = round(0.35 * star_score + 0.30 * recency_score + 0.25 * size_score + 0.10 * fork_score, 4)
    reason = (
        f"Selected (score={composite:.4f}; stars={stars}, size_kb={size_kb}, "
        f"recency={recency_score:.2f}, forks={forks})"
    )
    return True, composite, reason, None


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
            "User-Agent": "CSharpBugDetection-AcademicClient/2.0",
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

                remaining = response.headers.get("X-RateLimit-Remaining")
                reset_time = response.headers.get("X-RateLimit-Reset")
                if remaining is not None and int(remaining) == 0:
                    reset_ts = int(reset_time) if reset_time else None
                    wait_seconds = max(1, reset_ts - int(time.time())) if reset_ts else 60
                    logger.warning(f"GitHub API rate limit exhausted. Resets in {wait_seconds}s.")
                    if retries < self.max_retries and wait_seconds <= 65:
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
                    wait_seconds = max(1, reset_ts - int(time.time())) if reset_ts else 60
                    if retries < self.max_retries and wait_seconds <= 65:
                        logger.warning(f"GitHub HTTP {response.status_code} rate limit. Waiting {wait_seconds + 1}s...")
                        time.sleep(wait_seconds + 1)
                        retries += 1
                        continue
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
        max_size_kb: Optional[int] = None,
        max_stars: Optional[int] = None,
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
        if max_stars is not None and min_stars > 0:
            query_parts.append(f"stars:{min_stars}..{max_stars}")
        elif min_stars > 0:
            query_parts.append(f"stars:>={min_stars}")
        if max_size_kb is not None and min_size_kb > 0:
            query_parts.append(f"size:{min_size_kb}..{max_size_kb}")
        elif min_size_kb > 0:
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

    def discover_csharp_repositories(
        self,
        target_count: int = 150,
        min_stars: int = 50,
        min_size_kb: int = 120,
        max_size_kb: int = 35000,
        updated_since: str = "2020-01-01",
        exclude_forks: bool = True,
        exclude_archived: bool = True,
        max_pages_per_query: int = 3,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> Dict[str, Any]:
        """Paginate across stratified GitHub C# search bands, evaluate inclusion, and rank candidates."""
        star_bands: List[Tuple[int, Optional[int]]] = [
            (3000, None),
            (800, 2999),
            (250, 799),
            (max(min_stars, 50), 249),
        ]

        discovered_by_name: Dict[str, Dict[str, Any]] = {}
        queries_executed = 0
        rate_limited = False

        for band_min, band_max in star_bands:
            if len(discovered_by_name) >= target_count:
                break
            for page in range(1, max_pages_per_query + 1):
                if len(discovered_by_name) >= target_count:
                    break
                try:
                    res = self.search_repositories(
                        min_stars=band_min,
                        max_stars=band_max,
                        min_size_kb=min_size_kb,
                        max_size_kb=max_size_kb,
                        updated_since=updated_since,
                        exclude_forks=exclude_forks,
                        exclude_archived=exclude_archived,
                        page=page,
                        per_page=100,
                        sort="stars",
                        order="desc",
                    )
                    queries_executed += 1
                    items = res.get("items", [])
                    if not items:
                        break
                    for item in items:
                        slug = (item.get("full_name") or "").lower()
                        if slug and slug not in discovered_by_name:
                            is_sel, score, sel_reason, excl_reason = evaluate_repository_candidate(
                                item,
                                min_stars=min_stars,
                                min_size_kb=min_size_kb,
                                max_size_kb=max_size_kb,
                                exclude_forks=exclude_forks,
                                exclude_archived=exclude_archived,
                            )
                            item["is_selected"] = is_sel
                            item["selection_score"] = score
                            item["selection_reason"] = sel_reason
                            item["exclusion_reason"] = excl_reason
                            discovered_by_name[slug] = item

                    if progress_callback:
                        progress_callback(f"Discovered {len(discovered_by_name)} unique C# repositories", len(discovered_by_name))

                    if len(items) < 100:
                        break
                    # Respect unauthenticated search API rate limit (10 req/min)
                    if not self.token:
                        time.sleep(6.2)
                except RateLimitExceededError:
                    rate_limited = True
                    logger.warning(f"GitHub search rate limit reached after {len(discovered_by_name)} candidates.")
                    break
                except GitHubAPIError as e:
                    logger.warning(f"Search query failed on band {band_min}..{band_max} page {page}: {e}")
                    break

        all_candidates = list(discovered_by_name.values())
        selected = [c for c in all_candidates if c.get("is_selected")]
        excluded = [c for c in all_candidates if not c.get("is_selected")]
        selected.sort(key=lambda c: (c.get("selection_score", 0.0), c.get("stars", 0)), reverse=True)
        for rank, item in enumerate(selected, 1):
            item["selection_rank"] = rank

        return {
            "discovered_total": len(all_candidates),
            "selected_total": len(selected),
            "excluded_total": len(excluded),
            "queries_executed": queries_executed,
            "rate_limited": rate_limited,
            "selected": selected,
            "excluded": excluded,
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
            "language": raw.get("language") or "C#",
            "stars": raw.get("stargazers_count", 0),
            "forks": raw.get("forks_count", 0),
            "size_kb": raw.get("size", 0),
            "default_branch": raw.get("default_branch", "main"),
            "license": license_str,
            "is_fork": raw.get("fork", False),
            "is_archived": raw.get("archived", False),
            "created_at": raw.get("created_at"),
            "created_at_gh": raw.get("created_at"),
            "updated_at": raw.get("updated_at"),
            "pushed_at": raw.get("pushed_at"),
        }
