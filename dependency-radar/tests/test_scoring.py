"""Tests for radar.scoring — pure health-scoring functions."""

from datetime import datetime, timedelta, timezone

import pytest

from radar import GitHubData, NpmData, PackageInfo
from radar.scoring import (
    LABEL_AT_RISK,
    LABEL_HEALTHY,
    LABEL_UNKNOWN,
    LABEL_WATCH,
    calculate_health,
    score_active_maintainers,
    score_days_since,
    score_deprecated_archived,
    score_issue_responsiveness,
)

NOW = datetime(2026, 10, 10, tzinfo=timezone.utc)


# ── score_days_since ─────────────────────────────────────────────────────────


class TestScoreDaysSince:
    """Tests for score_days_since."""

    def test_zero_days(self) -> None:
        """Just released → perfect score."""
        assert score_days_since(0) == 100.0

    def test_max_days(self) -> None:
        """At the ceiling → zero."""
        assert score_days_since(730) == 0.0

    def test_beyond_max(self) -> None:
        """Past the ceiling → still zero."""
        assert score_days_since(1000) == 0.0

    def test_half_max(self) -> None:
        """Halfway → ~50."""
        assert score_days_since(365) == pytest.approx(50.0, abs=0.1)

    def test_none_days(self) -> None:
        """Unknown date → zero."""
        assert score_days_since(None) == 0.0

    def test_negative_days(self) -> None:
        """Negative (future date) → full score."""
        assert score_days_since(-5) == 100.0

    def test_custom_max(self) -> None:
        """Works with a custom max_days ceiling."""
        assert score_days_since(50, max_days=100) == pytest.approx(50.0, abs=0.1)


# ── score_issue_responsiveness ───────────────────────────────────────────────


class TestScoreIssueResponsiveness:
    """Tests for score_issue_responsiveness."""

    def test_all_closed(self) -> None:
        """All issues closed → 100."""
        assert score_issue_responsiveness(10, 0) == 100.0

    def test_none_closed(self) -> None:
        """No issues closed → 0."""
        assert score_issue_responsiveness(0, 10) == 0.0

    def test_half_closed(self) -> None:
        """50/50 → 50."""
        assert score_issue_responsiveness(5, 5) == 50.0

    def test_no_issues(self) -> None:
        """Zero total → neutral 50."""
        assert score_issue_responsiveness(0, 0) == 50.0


# ── score_active_maintainers ────────────────────────────────────────────────


class TestScoreActiveMaintainers:
    """Tests for score_active_maintainers."""

    def test_zero(self) -> None:
        assert score_active_maintainers(0) == 0.0

    def test_one(self) -> None:
        assert score_active_maintainers(1) == 30.0

    def test_two(self) -> None:
        assert score_active_maintainers(2) == 60.0

    def test_three(self) -> None:
        assert score_active_maintainers(3) == 80.0

    def test_four(self) -> None:
        assert score_active_maintainers(4) == 80.0

    def test_five_plus(self) -> None:
        assert score_active_maintainers(5) == 100.0
        assert score_active_maintainers(20) == 100.0


# ── score_deprecated_archived ────────────────────────────────────────────────


class TestScoreDeprecatedArchived:
    """Tests for score_deprecated_archived."""

    def test_neither(self) -> None:
        assert score_deprecated_archived(False, False) == 100.0

    def test_deprecated_only(self) -> None:
        assert score_deprecated_archived(True, False) == 0.0

    def test_archived_only(self) -> None:
        assert score_deprecated_archived(False, True) == 0.0

    def test_both(self) -> None:
        assert score_deprecated_archived(True, True) == 0.0


# ── calculate_health ─────────────────────────────────────────────────────────


class TestCalculateHealth:
    """Integration tests for the full scoring pipeline."""

    def test_healthy_package(self) -> None:
        """A well-maintained package should score >= 70."""
        pkg = PackageInfo(name="healthy-pkg", version="1.0.0")
        npm = NpmData(
            last_release_date=NOW - timedelta(days=30),
            deprecated=False,
            repository_url="owner/repo",
        )
        github = GitHubData(
            last_commit_date=NOW - timedelta(days=7),
            archived=False,
            open_issues=10,
            closed_issues_90d=20,
            active_contributors_12m=5,
        )

        health = calculate_health(pkg, npm, github, now=NOW)

        assert health.score >= 70
        assert health.label == LABEL_HEALTHY

    def test_at_risk_deprecated_package(self) -> None:
        """A deprecated + archived package should score < 40."""
        pkg = PackageInfo(name="old-pkg", version="0.1.0")
        npm = NpmData(
            last_release_date=NOW - timedelta(days=800),
            deprecated=True,
        )
        github = GitHubData(
            last_commit_date=NOW - timedelta(days=900),
            archived=True,
            open_issues=50,
            closed_issues_90d=0,
            active_contributors_12m=0,
        )

        health = calculate_health(pkg, npm, github, now=NOW)

        assert health.score < 40
        assert health.label == LABEL_AT_RISK
        assert "deprecated" in health.main_reason.lower()

    def test_unknown_when_no_data(self) -> None:
        """No metadata at all → Unknown label."""
        pkg = PackageInfo(name="mystery-pkg", version="1.0.0")

        health = calculate_health(pkg, None, None, now=NOW)

        assert health.label == LABEL_UNKNOWN
        assert health.main_reason == "No metadata available"

    def test_watch_package(self) -> None:
        """A moderately stale package should land in the Watch band."""
        pkg = PackageInfo(name="aging-pkg", version="2.0.0")
        npm = NpmData(
            last_release_date=NOW - timedelta(days=400),
            deprecated=False,
        )
        github = GitHubData(
            last_commit_date=NOW - timedelta(days=300),
            archived=False,
            open_issues=20,
            closed_issues_90d=5,
            active_contributors_12m=1,
        )

        health = calculate_health(pkg, npm, github, now=NOW)

        assert 40 <= health.score < 70
        assert health.label == LABEL_WATCH

    def test_score_clamped_0_to_100(self) -> None:
        """Score is always in [0, 100] regardless of inputs."""
        pkg = PackageInfo(name="test-pkg", version="1.0.0")
        npm = NpmData(last_release_date=NOW)
        github = GitHubData(
            last_commit_date=NOW,
            active_contributors_12m=100,
            closed_issues_90d=100,
            open_issues=0,
        )

        health = calculate_health(pkg, npm, github, now=NOW)

        assert 0 <= health.score <= 100

    def test_main_reason_for_stale_release(self) -> None:
        """When the release is the weakest signal, the reason says so."""
        pkg = PackageInfo(name="stale-release-pkg", version="1.0.0")
        npm = NpmData(
            last_release_date=NOW - timedelta(days=700),
            deprecated=False,
        )
        github = GitHubData(
            last_commit_date=NOW - timedelta(days=10),
            archived=False,
            open_issues=5,
            closed_issues_90d=10,
            active_contributors_12m=5,
        )

        health = calculate_health(pkg, npm, github, now=NOW)

        assert "release" in health.main_reason.lower()

    def test_archived_reason_takes_priority(self) -> None:
        """Archived flag should be reported even if other scores are decent."""
        pkg = PackageInfo(name="archived-pkg", version="1.0.0")
        npm = NpmData(
            last_release_date=NOW - timedelta(days=10),
            deprecated=False,
        )
        github = GitHubData(
            last_commit_date=NOW - timedelta(days=10),
            archived=True,
            open_issues=5,
            closed_issues_90d=10,
            active_contributors_12m=5,
        )

        health = calculate_health(pkg, npm, github, now=NOW)

        assert "archived" in health.main_reason.lower()
