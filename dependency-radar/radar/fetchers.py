"""Fetch package metadata from the npm registry and GitHub API."""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import requests

from radar import GitHubData, NpmData, PackageInfo
from radar.cache import get_cached, set_cached

logger = logging.getLogger(__name__)

NPM_REGISTRY_URL = "https://registry.npmjs.org"
GITHUB_API_URL = "https://api.github.com"
REQUEST_TIMEOUT = 15


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_github_headers() -> dict[str, str]:
    """Build HTTP headers for GitHub API requests.

    Uses the ``GITHUB_TOKEN`` environment variable when available.

    Returns:
        A dict of HTTP headers.
    """
    headers: dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def _parse_date(date_str: str) -> datetime | None:
    """Parse an ISO-8601 date string into a timezone-aware datetime.

    Args:
        date_str: An ISO-8601 formatted string.

    Returns:
        A UTC-aware datetime, or ``None`` on failure.
    """
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError):
        return None


def _normalize_github_url(url: str) -> str | None:
    """Extract a ``owner/repo`` slug from various GitHub URL formats.

    Args:
        url: A repository URL (may use ``git+``, ``ssh://``, etc.).

    Returns:
        A normalised ``"owner/repo"`` string, or ``None`` if not a GitHub URL.
    """
    if not url:
        return None

    url = (
        url.replace("git+", "")
        .replace("git://", "https://")
        .replace(".git", "")
        .replace("ssh://git@github.com/", "https://github.com/")
        .replace("git@github.com:", "https://github.com/")
    )

    if "github.com" not in url:
        return None

    parts = url.split("github.com/")
    if len(parts) < 2:
        return None

    path = parts[-1].strip("/")
    segments = path.split("/")
    if len(segments) >= 2:
        return f"{segments[0]}/{segments[1]}"

    return None


# ── npm registry ─────────────────────────────────────────────────────────────


def fetch_npm_data(package_name: str, use_cache: bool = True) -> NpmData:
    """Fetch package metadata from the npm registry.

    Args:
        package_name: The npm package name (e.g. ``"express"``).
        use_cache: Whether to consult the local cache first.

    Returns:
        An :class:`NpmData` instance (never raises).
    """
    if use_cache:
        cached = get_cached("npm", package_name)
        if cached is not None:
            return NpmData(
                last_release_date=(
                    datetime.fromisoformat(cached["last_release_date"])
                    if cached.get("last_release_date")
                    else None
                ),
                deprecated=cached.get("deprecated", False),
                repository_url=cached.get("repository_url"),
            )

    npm_data = NpmData()

    try:
        url = f"{NPM_REGISTRY_URL}/{package_name}"
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        # ── Last release date ────────────────────────────────────────────
        time_info: dict[str, str] = data.get("time", {})
        if time_info:
            latest_version = data.get("dist-tags", {}).get("latest")
            if latest_version and latest_version in time_info:
                npm_data.last_release_date = _parse_date(time_info[latest_version])
            elif "modified" in time_info:
                npm_data.last_release_date = _parse_date(time_info["modified"])

        # ── Deprecated flag ──────────────────────────────────────────────
        latest_version = data.get("dist-tags", {}).get("latest")
        if latest_version:
            version_data = data.get("versions", {}).get(latest_version, {})
            if version_data.get("deprecated"):
                npm_data.deprecated = True

        # ── Repository URL ───────────────────────────────────────────────
        repo = data.get("repository", {})
        if isinstance(repo, dict):
            repo_url = repo.get("url", "")
        elif isinstance(repo, str):
            repo_url = repo
        else:
            repo_url = ""

        npm_data.repository_url = _normalize_github_url(repo_url)

    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.warning("Failed to fetch npm data for %s: %s", package_name, exc)

    if use_cache:
        set_cached(
            "npm",
            package_name,
            {
                "last_release_date": (
                    npm_data.last_release_date.isoformat()
                    if npm_data.last_release_date
                    else None
                ),
                "deprecated": npm_data.deprecated,
                "repository_url": npm_data.repository_url,
            },
        )

    return npm_data


# ── GitHub API ───────────────────────────────────────────────────────────────


def fetch_github_data(repo_slug: str, use_cache: bool = True) -> GitHubData:
    """Fetch repository metadata from the GitHub API.

    Args:
        repo_slug: GitHub ``"owner/repo"`` slug.
        use_cache: Whether to consult the local cache first.

    Returns:
        A :class:`GitHubData` instance (never raises).
    """
    if use_cache:
        cached = get_cached("github", repo_slug)
        if cached is not None:
            return GitHubData(
                last_commit_date=(
                    datetime.fromisoformat(cached["last_commit_date"])
                    if cached.get("last_commit_date")
                    else None
                ),
                archived=cached.get("archived", False),
                open_issues=cached.get("open_issues", 0),
                closed_issues_90d=cached.get("closed_issues_90d", 0),
                active_contributors_12m=cached.get("active_contributors_12m", 0),
            )

    github_data = GitHubData()
    headers = _get_github_headers()

    try:
        # ── Repository info ──────────────────────────────────────────────
        repo_resp = requests.get(
            f"{GITHUB_API_URL}/repos/{repo_slug}",
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        repo_resp.raise_for_status()
        repo_info: dict = repo_resp.json()

        github_data.archived = repo_info.get("archived", False)
        github_data.open_issues = repo_info.get("open_issues_count", 0)

        # ── Last commit on default branch ────────────────────────────────
        default_branch = repo_info.get("default_branch", "main")
        commits_resp = requests.get(
            f"{GITHUB_API_URL}/repos/{repo_slug}/commits",
            headers=headers,
            params={"sha": default_branch, "per_page": 1},
            timeout=REQUEST_TIMEOUT,
        )
        if commits_resp.status_code == 200:
            commits = commits_resp.json()
            if commits:
                date_str = (
                    commits[0]
                    .get("commit", {})
                    .get("committer", {})
                    .get("date")
                )
                if date_str:
                    github_data.last_commit_date = _parse_date(date_str)

        # ── Issues closed in last 90 days ────────────────────────────────
        since_90d = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
        closed_resp = requests.get(
            f"{GITHUB_API_URL}/repos/{repo_slug}/issues",
            headers=headers,
            params={"state": "closed", "since": since_90d, "per_page": 100},
            timeout=REQUEST_TIMEOUT,
        )
        if closed_resp.status_code == 200:
            github_data.closed_issues_90d = len(
                [i for i in closed_resp.json() if not i.get("pull_request")]
            )

        # ── Active contributors (last 12 months) ────────────────────────
        since_12m = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
        contrib_resp = requests.get(
            f"{GITHUB_API_URL}/repos/{repo_slug}/commits",
            headers=headers,
            params={"since": since_12m, "per_page": 100},
            timeout=REQUEST_TIMEOUT,
        )
        if contrib_resp.status_code == 200:
            authors: set[str] = set()
            for commit in contrib_resp.json():
                author = commit.get("author")
                if author and author.get("login"):
                    authors.add(author["login"])
            github_data.active_contributors_12m = len(authors)

    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.warning("Failed to fetch GitHub data for %s: %s", repo_slug, exc)

    if use_cache:
        set_cached(
            "github",
            repo_slug,
            {
                "last_commit_date": (
                    github_data.last_commit_date.isoformat()
                    if github_data.last_commit_date
                    else None
                ),
                "archived": github_data.archived,
                "open_issues": github_data.open_issues,
                "closed_issues_90d": github_data.closed_issues_90d,
                "active_contributors_12m": github_data.active_contributors_12m,
            },
        )

    return github_data


# ── Concurrent orchestrator ──────────────────────────────────────────────────


def fetch_all_package_data(
    packages: list[PackageInfo],
    use_cache: bool = True,
    max_workers: int = 8,
) -> list[tuple[PackageInfo, NpmData, GitHubData | None]]:
    """Fetch npm and GitHub data for every package concurrently.

    Args:
        packages: List of packages to look up.
        use_cache: Whether to use the local cache.
        max_workers: Thread-pool size.

    Returns:
        A list of ``(PackageInfo, NpmData, GitHubData | None)`` tuples.
    """
    results: list[tuple[PackageInfo, NpmData, GitHubData | None]] = []

    def _fetch_single(
        pkg: PackageInfo,
    ) -> tuple[PackageInfo, NpmData, GitHubData | None]:
        """Fetch all data for a single package (runs in a worker thread)."""
        npm_data = fetch_npm_data(pkg.name, use_cache=use_cache)
        github_data: GitHubData | None = None
        if npm_data.repository_url:
            github_data = fetch_github_data(
                npm_data.repository_url, use_cache=use_cache
            )
        return (pkg, npm_data, github_data)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch_single, pkg): pkg for pkg in packages}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:
                pkg = futures[future]
                logger.error("Error fetching data for %s: %s", pkg.name, exc)
                results.append((pkg, NpmData(), None))

    return results
