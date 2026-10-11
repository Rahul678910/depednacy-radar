<div align="center">

# 🛰️ Dependency Radar

### Don't let zombie packages haunt your codebase.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-42%20passed-brightgreen?style=for-the-badge&logo=pytest&logoColor=white)](tests/)
[![Built with Typer](https://img.shields.io/badge/CLI-Typer-009688?style=for-the-badge)](https://typer.tiangolo.com)

**One command. Every dependency. Health scores you can act on.**

Dependency Radar scans your `package.json`, queries the npm registry & GitHub API,
and gives each package a **0–100 health score** so you can spot the ones
that are quietly being abandoned — before they become a problem.

---

[Installation](#-installation) · [Quick Start](#-quick-start) · [Scoring](#-how-scoring-works) · [CI Integration](#-ci-integration) · [Configuration](#%EF%B8%8F-configuration)

</div>

<br>

## 📡 What It Looks Like

```
Dependency Radar v0.1.0
  Scanning: package.json

  Found 5 dependencies. Fetching metadata...

                               Dependency Radar
┌──────────────┬───────┬──────────┬──────────────┬─────────────┬──────────────────────────┐
│ Package      │ Score │ Label    │ Last Release │ Last Commit │ Main Concern             │
├──────────────┼───────┼──────────┼──────────────┼─────────────┼──────────────────────────┤
│ left-pad     │  12   │ At Risk  │ 2018-03-15   │ 2018-04-01  │ Stale releases           │
│ moment       │  35   │ At Risk  │ 2022-07-06   │ 2023-01-10  │ Few active maintainers   │
│ lodash       │  58   │ Watch    │ 2024-02-10   │ 2024-06-15  │ Stale releases           │
│ express      │  82   │ Healthy  │ 2025-09-01   │ 2025-09-28  │ Stale releases           │
│ react        │  91   │ Healthy  │ 2025-10-01   │ 2025-10-08  │ Stale releases           │
└──────────────┴───────┴──────────┴──────────────┴─────────────┴──────────────────────────┘

  + Healthy: 2  ! Watch: 1  x At Risk: 2  ? Unknown: 0
```

> Sorted worst-first so the scariest stuff is always at the top. 🎯

<br>

## 📦 Installation

```bash
# Clone it
git clone https://github.com/your-org/dependency-radar.git
cd dependency-radar

# Install (with uv — recommended)
uv venv && uv pip install -e ".[dev]"

# …or with plain pip
pip install -e ".[dev]"
```

That's it — the `radar` command is now available globally in your shell.

<br>

## 🚀 Quick Start

```bash
# Basic scan
radar scan package.json

# Fresh data, no cache
radar scan package.json --no-cache

# Save results for later
radar scan package.json --json report.json

# CI gate — explode if anything scores below 50
radar scan package.json --fail-under 50
```

<br>

## 🧠 How Scoring Works

Every dependency gets a **0–100** health score built from five real-world signals:

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│   ███████████████░░░░░░░░░░  30%  Release freshness │
│   ██████████░░░░░░░░░░░░░░░  20%  Commit freshness  │
│   ██████████░░░░░░░░░░░░░░░  20%  Issue response    │
│   ████████░░░░░░░░░░░░░░░░░  15%  Active devs       │
│   ████████░░░░░░░░░░░░░░░░░  15%  Not deprecated    │
│                                                     │
└─────────────────────────────────────────────────────┘
```

| Signal | Weight | Details |
|:---|:---:|:---|
| 📅 **Days since last release** | 30% | Linear decay: 100 → 0 over 2 years |
| 🔨 **Days since last commit** | 20% | Linear decay: 100 → 0 over 2 years |
| 🐛 **Issue responsiveness** | 20% | `closed_in_90d / (closed + open)` × 100 |
| 👥 **Active maintainers** | 15% | Committers in last 12 months (5+ = perfect) |
| ⚠️ **Deprecated / archived** | 15% | Instant zero if either flag is set |

### The Labels

| Score Range | Label | What it means |
|:---:|:---:|:---|
| **70 – 100** | 🟢 `Healthy` | Actively maintained, ship with confidence |
| **40 – 69** | 🟡 `Watch` | Showing signs of slowdown — keep an eye on it |
| **0 – 39** | 🔴 `At Risk` | Abandoned or deprecated — find an alternative |

<br>

## 🔌 CI Integration

Add Dependency Radar as a quality gate in your pipeline:

```yaml
# GitHub Actions example
- name: Dependency health check
  run: |
    pip install dependency-radar
    radar scan package.json --fail-under 50
```

The `--fail-under` flag exits with code **1** if *any* dependency scores below the threshold — perfect for blocking PRs that introduce risky deps.

```bash
# Combine with JSON export for artifact upload
radar scan package.json --fail-under 40 --json dep-report.json
```

<br>

## ⚙️ Configuration

### 🔑 GitHub Token

Without a token you're limited to **60 API requests/hour**. Set one to unlock 5,000/hr:

```bash
# Linux / macOS
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx

# Windows (PowerShell)
$env:GITHUB_TOKEN = "ghp_xxxxxxxxxxxxxxxxxxxx"
```

> **Tip:** Create a [fine-grained personal access token](https://github.com/settings/tokens?type=beta) with *no permissions* — public repo metadata is all Radar needs.

### 💾 Cache

API responses are cached for **24 hours** in `~/.dependency-radar/cache/` so repeated scans are instant. Use `--no-cache` to force fresh data.

<br>

## 📖 CLI Reference

```
USAGE
  radar scan <path-to-package.json> [OPTIONS]
  radar version

ARGUMENTS
  PATH                 Path to the package.json file  [required]

OPTIONS
  --json PATH          Export results to a JSON file
  --no-cache           Skip cache, fetch everything fresh
  --fail-under INT     Exit 1 if any package scores below this (CI mode)
  --help               Show this message and exit
```

<br>

## 🏗️ Architecture

```
dependency-radar/
├── radar/
│   ├── __init__.py        # Shared data models
│   ├── cli.py             # Typer CLI (scan + version)
│   ├── parsers.py         # package.json → [PackageInfo]
│   ├── fetchers.py        # npm + GitHub API (ThreadPoolExecutor)
│   ├── scoring.py         # Pure scoring functions (easy to test)
│   ├── cache.py           # JSON cache, 24h TTL
│   └── report.py          # Rich table + JSON export
├── tests/
│   ├── test_parsers.py    # 14 tests
│   └── test_scoring.py    # 28 tests
├── pyproject.toml
└── README.md              # You are here!
```

**Design decisions:**
- **Scoring is pure** — no I/O, no state, just `(data) → score`. Makes testing trivial.
- **Fetching is concurrent** — `ThreadPoolExecutor` keeps scans fast even with 50+ deps.
- **Caching is transparent** — same interface whether data comes from disk or the network.
- **No hardcoded secrets** — tokens come from environment variables, always.

<br>

## 🧪 Development & Testing

```bash
# Setup
git clone https://github.com/your-org/dependency-radar.git
cd dependency-radar
uv venv && uv pip install -e ".[dev]"

# Run all tests
pytest -v

# Run just scoring tests
pytest tests/test_scoring.py -v

# Run just parser tests
pytest tests/test_parsers.py -v
```

### Test Results — 42/42 Passing ✅

```
============================= test session starts =============================
platform win32 -- Python 3.14.8, pytest-9.1.1, pluggy-1.6.0

tests/test_parsers.py::TestCleanVersion::test_caret_prefix PASSED        [  2%]
tests/test_parsers.py::TestCleanVersion::test_tilde_prefix PASSED        [  4%]
tests/test_parsers.py::TestCleanVersion::test_gte_prefix PASSED          [  7%]
tests/test_parsers.py::TestCleanVersion::test_no_prefix PASSED           [  9%]
tests/test_parsers.py::TestCleanVersion::test_complex_prefix PASSED      [ 11%]
tests/test_parsers.py::TestCleanVersion::test_spaces PASSED              [ 14%]
tests/test_parsers.py::TestParsePackageJson::test_parse_dependencies PASSED [ 16%]
tests/test_parsers.py::TestParsePackageJson::test_parse_dev_dependencies PASSED [ 19%]
tests/test_parsers.py::TestParsePackageJson::test_parse_both_sections PASSED [ 21%]
tests/test_parsers.py::TestParsePackageJson::test_empty_dependencies PASSED [ 23%]
tests/test_parsers.py::TestParsePackageJson::test_file_not_found PASSED  [ 26%]
tests/test_parsers.py::TestParsePackageJson::test_invalid_json PASSED    [ 28%]
tests/test_parsers.py::TestParsePackageJson::test_invalid_structure PASSED [ 30%]
tests/test_parsers.py::TestParsePackageJson::test_non_dict_dependencies_ignored PASSED [ 33%]
tests/test_scoring.py::TestScoreDaysSince::test_zero_days PASSED         [ 35%]
tests/test_scoring.py::TestScoreDaysSince::test_max_days PASSED          [ 38%]
tests/test_scoring.py::TestScoreDaysSince::test_beyond_max PASSED        [ 40%]
tests/test_scoring.py::TestScoreDaysSince::test_half_max PASSED          [ 42%]
tests/test_scoring.py::TestScoreDaysSince::test_none_days PASSED         [ 45%]
tests/test_scoring.py::TestScoreDaysSince::test_negative_days PASSED     [ 47%]
tests/test_scoring.py::TestScoreDaysSince::test_custom_max PASSED        [ 50%]
tests/test_scoring.py::TestScoreIssueResponsiveness::test_all_closed PASSED [ 52%]
tests/test_scoring.py::TestScoreIssueResponsiveness::test_none_closed PASSED [ 54%]
tests/test_scoring.py::TestScoreIssueResponsiveness::test_half_closed PASSED [ 57%]
tests/test_scoring.py::TestScoreIssueResponsiveness::test_no_issues PASSED [ 59%]
tests/test_scoring.py::TestScoreActiveMaintainers::test_zero PASSED      [ 61%]
tests/test_scoring.py::TestScoreActiveMaintainers::test_one PASSED       [ 64%]
tests/test_scoring.py::TestScoreActiveMaintainers::test_two PASSED       [ 66%]
tests/test_scoring.py::TestScoreActiveMaintainers::test_three PASSED     [ 69%]
tests/test_scoring.py::TestScoreActiveMaintainers::test_four PASSED      [ 71%]
tests/test_scoring.py::TestScoreActiveMaintainers::test_five_plus PASSED [ 73%]
tests/test_scoring.py::TestScoreDeprecatedArchived::test_neither PASSED  [ 76%]
tests/test_scoring.py::TestScoreDeprecatedArchived::test_deprecated_only PASSED [ 78%]
tests/test_scoring.py::TestScoreDeprecatedArchived::test_archived_only PASSED [ 80%]
tests/test_scoring.py::TestScoreDeprecatedArchived::test_both PASSED     [ 83%]
tests/test_scoring.py::TestCalculateHealth::test_healthy_package PASSED  [ 85%]
tests/test_scoring.py::TestCalculateHealth::test_at_risk_deprecated_package PASSED [ 88%]
tests/test_scoring.py::TestCalculateHealth::test_unknown_when_no_data PASSED [ 90%]
tests/test_scoring.py::TestCalculateHealth::test_watch_package PASSED    [ 92%]
tests/test_scoring.py::TestCalculateHealth::test_score_clamped_0_to_100 PASSED [ 95%]
tests/test_scoring.py::TestCalculateHealth::test_main_reason_for_stale_release PASSED [ 97%]
tests/test_scoring.py::TestCalculateHealth::test_archived_reason_takes_priority PASSED [100%]

============================= 42 passed in 0.23s ==============================
```

### Test Breakdown

<details>
<summary><strong>📄 Parser Tests — 14 tests</strong> (<code>tests/test_parsers.py</code>)</summary>

| # | Test | What it verifies |
|:--:|:---|:---|
| 1 | `test_caret_prefix` | Strips `^` from `^1.2.3` |
| 2 | `test_tilde_prefix` | Strips `~` from `~1.2.3` |
| 3 | `test_gte_prefix` | Strips `>=` from `>=1.0.0` |
| 4 | `test_no_prefix` | Leaves bare `1.0.0` unchanged |
| 5 | `test_complex_prefix` | Strips combo `^>=` from `^>=2.0.0` |
| 6 | `test_spaces` | Strips leading spaces |
| 7 | `test_parse_dependencies` | Reads `dependencies` section correctly |
| 8 | `test_parse_dev_dependencies` | Reads `devDependencies` section |
| 9 | `test_parse_both_sections` | Merges both sections into one list |
| 10 | `test_empty_dependencies` | Returns `[]` when no deps exist |
| 11 | `test_file_not_found` | Raises `FileNotFoundError` |
| 12 | `test_invalid_json` | Raises `JSONDecodeError` for bad JSON |
| 13 | `test_invalid_structure` | Raises `ValueError` for non-object JSON |
| 14 | `test_non_dict_dependencies_ignored` | Skips malformed dependency values |

</details>

<details>
<summary><strong>🧮 Scoring Tests — 28 tests</strong> (<code>tests/test_scoring.py</code>)</summary>

| # | Test | What it verifies |
|:--:|:---|:---|
| 1 | `test_zero_days` | 0 days since release → score 100 |
| 2 | `test_max_days` | 730 days → score 0 |
| 3 | `test_beyond_max` | 1000 days → still 0 |
| 4 | `test_half_max` | 365 days → ~50 |
| 5 | `test_none_days` | Unknown date → score 0 |
| 6 | `test_negative_days` | Future date → score 100 |
| 7 | `test_custom_max` | Custom ceiling works |
| 8 | `test_all_closed` | 10 closed, 0 open → 100 |
| 9 | `test_none_closed` | 0 closed, 10 open → 0 |
| 10 | `test_half_closed` | 5/5 → 50 |
| 11 | `test_no_issues` | No issues at all → neutral 50 |
| 12 | `test_zero` | 0 maintainers → 0 |
| 13 | `test_one` | 1 maintainer → 30 |
| 14 | `test_two` | 2 maintainers → 60 |
| 15 | `test_three` | 3 maintainers → 80 |
| 16 | `test_four` | 4 maintainers → 80 |
| 17 | `test_five_plus` | 5+ maintainers → 100 |
| 18 | `test_neither` | Not deprecated, not archived → 100 |
| 19 | `test_deprecated_only` | Deprecated → 0 |
| 20 | `test_archived_only` | Archived → 0 |
| 21 | `test_both` | Both flags → 0 |
| 22 | `test_healthy_package` | Well-maintained pkg scores ≥ 70 |
| 23 | `test_at_risk_deprecated_package` | Old deprecated pkg scores < 40 |
| 24 | `test_unknown_when_no_data` | No metadata → "Unknown" label |
| 25 | `test_watch_package` | Moderately stale → "Watch" (40–69) |
| 26 | `test_score_clamped_0_to_100` | Score never exceeds bounds |
| 27 | `test_main_reason_for_stale_release` | Identifies release staleness |
| 28 | `test_archived_reason_takes_priority` | Archived flag overrides other reasons |

</details>

### Coverage Summary

| Module | Tests | Status |
|:---|:---:|:---:|
| `parsers.py` | 14 | ✅ All passing |
| `scoring.py` | 28 | ✅ All passing |
| **Total** | **42** | **✅** |

<br>

## 🗺️ Roadmap

- [ ] Support `pnpm-lock.yaml` and `yarn.lock`
- [ ] PyPI support (`requirements.txt`, `pyproject.toml`)
- [ ] HTML report generation
- [ ] GitHub Action (ready-to-use marketplace action)
- [ ] Configurable scoring weights via `.radarrc`
- [ ] Trend tracking (compare scores across scans)

<br>

---

<div align="center">

**Built with** 🐍 [Python](https://python.org) + ⌨️ [Typer](https://typer.tiangolo.com) + 🎨 [Rich](https://rich.readthedocs.io) + ❤️

MIT License — do whatever you want with it.

</div>
