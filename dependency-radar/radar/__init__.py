"""Dependency Radar — Score the health of your project's dependencies."""

from dataclasses import dataclass
from datetime import datetime

__version__ = "0.1.0"


@dataclass
class PackageInfo:
    """Basic package information parsed from package.json."""

    name: str
    version: str


@dataclass
class NpmData:
    """Data fetched from the npm registry for a single package."""

    last_release_date: datetime | None = None
    deprecated: bool = False
    repository_url: str | None = None


@dataclass
class GitHubData:
    """Data fetched from the GitHub API for a repository."""

    last_commit_date: datetime | None = None
    archived: bool = False
    open_issues: int = 0
    closed_issues_90d: int = 0
    active_contributors_12m: int = 0


@dataclass
class PackageHealth:
    """Complete health assessment for a single package."""

    name: str
    version: str
    score: int
    label: str
    last_release: datetime | None = None
    last_commit: datetime | None = None
    main_reason: str = ""
    npm_data: NpmData | None = None
    github_data: GitHubData | None = None
