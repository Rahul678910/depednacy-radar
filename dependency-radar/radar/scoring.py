"""Health-scoring logic for dependency packages.

Every function in this module is *pure* (no I/O, no side-effects) so that
unit-testing is straightforward.
"""

from datetime import datetime, timezone

from radar import GitHubData, NpmData, PackageHealth, PackageInfo

# ── Scoring weights ──────────────────────────────────────────────────────────

WEIGHT_DAYS_SINCE_RELEASE: float = 0.30
WEIGHT_DAYS_SINCE_COMMIT: float = 0.20
WEIGHT_ISSUE_RESPONSIVENESS: float = 0.20
WEIGHT_ACTIVE_MAINTAINERS: float = 0.15
WEIGHT_DEPRECATED_ARCHIVED: float = 0.15

# ── Label thresholds ─────────────────────────────────────────────────────────

LABEL_HEALTHY: str = "Healthy"
LABEL_WATCH: str = "Watch"
LABEL_AT_RISK: str = "At Risk"
LABEL_UNKNOWN: str = "Unknown"


# ── Sub-score helpers ────────────────────────────────────────────────────────


def score_days_since(days: int | None, max_days: int = 730) -> float:
    """Score based on recency — 100 for today, linearly down to 0 at *max_days*.

    Args:
        days: Number of days since the event, or ``None`` if unknown.
        max_days: The ceiling beyond which the score is 0.

    Returns:
        A float in ``[0.0, 100.0]``.
    """
    if days is None:
        return 0.0
    if days <= 0:
        return 100.0
    if days >= max_days:
        return 0.0
    return max(0.0, 100.0 * (1.0 - days / max_days))


def score_issue_responsiveness(closed_90d: int, open_issues: int) -> float:
    """Score based on the ratio of recently-closed issues to open issues.

    A higher ratio indicates more responsive maintenance.

    Args:
        closed_90d: Issues closed in the last 90 days.
        open_issues: Currently open issues.

    Returns:
        A float in ``[0.0, 100.0]``.  Returns 50 when there are zero issues.
    """
    total = closed_90d + open_issues
    if total == 0:
        return 50.0  # no issues at all — neutral
    ratio = closed_90d / total
    return min(100.0, ratio * 100.0)


def score_active_maintainers(count: int) -> float:
    """Score based on the number of contributors active in the last 12 months.

    Thresholds: 0 → 0, 1 → 30, 2 → 60, 3-4 → 80, 5+ → 100.

    Args:
        count: Number of distinct commit authors.

    Returns:
        A float in ``[0.0, 100.0]``.
    """
    if count <= 0:
        return 0.0
    if count == 1:
        return 30.0
    if count == 2:
        return 60.0
    if count <= 4:
        return 80.0
    return 100.0


def score_deprecated_archived(deprecated: bool, archived: bool) -> float:
    """Return 0 if the package is deprecated *or* archived, else 100.

    Args:
        deprecated: ``True`` if npm reports the package as deprecated.
        archived: ``True`` if the GitHub repo is archived.

    Returns:
        ``0.0`` or ``100.0``.
    """
    if deprecated or archived:
        return 0.0
    return 100.0


# ── Internal helpers ─────────────────────────────────────────────────────────


def _days_since(dt: datetime | None, now: datetime | None = None) -> int | None:
    """Return the number of whole days between *dt* and *now*.

    Args:
        dt: The reference datetime.
        now: Current datetime (defaults to ``datetime.now(UTC)``).

    Returns:
        Non-negative day count, or ``None`` when *dt* is ``None``.
    """
    if dt is None:
        return None
    if now is None:
        now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0, (now - dt).days)


def _determine_main_reason(
    npm_data: NpmData | None,
    github_data: GitHubData | None,
    release_score: float,
    commit_score: float,
    issue_score: float,
    maintainer_score: float,
    dep_arch_score: float,
) -> str:
    """Pick the single most impactful reason for a low health score.

    Args:
        npm_data: Registry metadata (may be ``None``).
        github_data: Repository metadata (may be ``None``).
        release_score: Sub-score for release freshness.
        commit_score: Sub-score for commit freshness.
        issue_score: Sub-score for issue responsiveness.
        maintainer_score: Sub-score for active maintainers.
        dep_arch_score: Sub-score for deprecated / archived flags.

    Returns:
        A short human-readable explanation.
    """
    if npm_data is not None and npm_data.deprecated:
        return "Package is deprecated"
    if github_data is not None and github_data.archived:
        return "Repository is archived"

    if npm_data is None and github_data is None:
        return "No metadata available"

    weighted: dict[str, float] = {
        "Stale releases": release_score * WEIGHT_DAYS_SINCE_RELEASE,
        "Stale commits": commit_score * WEIGHT_DAYS_SINCE_COMMIT,
        "Poor issue responsiveness": issue_score * WEIGHT_ISSUE_RESPONSIVENESS,
        "Few active maintainers": maintainer_score * WEIGHT_ACTIVE_MAINTAINERS,
    }

    return min(weighted, key=lambda k: weighted[k])


# ── Main entry point ─────────────────────────────────────────────────────────


def calculate_health(
    package: PackageInfo,
    npm_data: NpmData | None,
    github_data: GitHubData | None,
    now: datetime | None = None,
) -> PackageHealth:
    """Calculate the overall health score for a single package.

    Args:
        package: Parsed package name / version.
        npm_data: Data from the npm registry (or ``None``).
        github_data: Data from the GitHub API (or ``None``).
        now: Reference "current time" (defaults to UTC now).

    Returns:
        A fully-populated :class:`PackageHealth` instance.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # Extract values safely
    last_release = npm_data.last_release_date if npm_data else None
    deprecated = npm_data.deprecated if npm_data else False

    last_commit = github_data.last_commit_date if github_data else None
    archived = github_data.archived if github_data else False
    open_issues = github_data.open_issues if github_data else 0
    closed_90d = github_data.closed_issues_90d if github_data else 0
    contributors = github_data.active_contributors_12m if github_data else 0

    # Individual sub-scores
    release_score = score_days_since(_days_since(last_release, now))
    commit_score = score_days_since(_days_since(last_commit, now))
    issue_score = score_issue_responsiveness(closed_90d, open_issues)
    maintainer_score = score_active_maintainers(contributors)
    dep_arch_score = score_deprecated_archived(deprecated, archived)

    # Weighted total
    total = (
        release_score * WEIGHT_DAYS_SINCE_RELEASE
        + commit_score * WEIGHT_DAYS_SINCE_COMMIT
        + issue_score * WEIGHT_ISSUE_RESPONSIVENESS
        + maintainer_score * WEIGHT_ACTIVE_MAINTAINERS
        + dep_arch_score * WEIGHT_DEPRECATED_ARCHIVED
    )

    score = max(0, min(100, round(total)))

    # Label
    if npm_data is None and github_data is None:
        label = LABEL_UNKNOWN
    elif score >= 70:
        label = LABEL_HEALTHY
    elif score >= 40:
        label = LABEL_WATCH
    else:
        label = LABEL_AT_RISK

    main_reason = _determine_main_reason(
        npm_data,
        github_data,
        release_score,
        commit_score,
        issue_score,
        maintainer_score,
        dep_arch_score,
    )

    return PackageHealth(
        name=package.name,
        version=package.version,
        score=score,
        label=label,
        last_release=last_release,
        last_commit=last_commit,
        main_reason=main_reason,
        npm_data=npm_data,
        github_data=github_data,
    )
