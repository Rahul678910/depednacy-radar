"""Tests for radar.parsers — package.json parsing."""

import json
from pathlib import Path

import pytest

from radar.parsers import _clean_version, parse_package_json


# ── _clean_version ───────────────────────────────────────────────────────────


class TestCleanVersion:
    """Tests for the _clean_version helper."""

    def test_caret_prefix(self) -> None:
        """Strips a leading ``^``."""
        assert _clean_version("^1.2.3") == "1.2.3"

    def test_tilde_prefix(self) -> None:
        """Strips a leading ``~``."""
        assert _clean_version("~1.2.3") == "1.2.3"

    def test_gte_prefix(self) -> None:
        """Strips ``>=``."""
        assert _clean_version(">=1.0.0") == "1.0.0"

    def test_no_prefix(self) -> None:
        """Leaves a bare version unchanged."""
        assert _clean_version("1.0.0") == "1.0.0"

    def test_complex_prefix(self) -> None:
        """Strips a combination of range characters."""
        assert _clean_version("^>=2.0.0") == "2.0.0"

    def test_spaces(self) -> None:
        """Strips leading spaces."""
        assert _clean_version("  3.0.0") == "3.0.0"


# ── parse_package_json ───────────────────────────────────────────────────────


class TestParsePackageJson:
    """Tests for parse_package_json."""

    def test_parse_dependencies(self, tmp_path: Path) -> None:
        """Extracts names and cleaned versions from ``dependencies``."""
        pkg = {
            "name": "test-project",
            "dependencies": {
                "express": "^4.18.0",
                "lodash": "~4.17.21",
            },
        }
        pkg_file = tmp_path / "package.json"
        pkg_file.write_text(json.dumps(pkg))

        result = parse_package_json(pkg_file)

        assert len(result) == 2
        assert result[0].name == "express"
        assert result[0].version == "4.18.0"
        assert result[1].name == "lodash"
        assert result[1].version == "4.17.21"

    def test_parse_dev_dependencies(self, tmp_path: Path) -> None:
        """Reads ``devDependencies`` section."""
        pkg = {
            "name": "test-project",
            "devDependencies": {"jest": "^29.0.0"},
        }
        pkg_file = tmp_path / "package.json"
        pkg_file.write_text(json.dumps(pkg))

        result = parse_package_json(pkg_file)

        assert len(result) == 1
        assert result[0].name == "jest"

    def test_parse_both_sections(self, tmp_path: Path) -> None:
        """Reads both ``dependencies`` and ``devDependencies``."""
        pkg = {
            "name": "test-project",
            "dependencies": {"react": "^18.0.0"},
            "devDependencies": {"typescript": "^5.0.0"},
        }
        pkg_file = tmp_path / "package.json"
        pkg_file.write_text(json.dumps(pkg))

        result = parse_package_json(pkg_file)

        assert len(result) == 2
        names = [p.name for p in result]
        assert "react" in names
        assert "typescript" in names

    def test_empty_dependencies(self, tmp_path: Path) -> None:
        """Returns an empty list when no dependency sections exist."""
        pkg = {"name": "test-project"}
        pkg_file = tmp_path / "package.json"
        pkg_file.write_text(json.dumps(pkg))

        result = parse_package_json(pkg_file)

        assert result == []

    def test_file_not_found(self) -> None:
        """Raises FileNotFoundError for a missing file."""
        with pytest.raises(FileNotFoundError):
            parse_package_json("/nonexistent/package.json")

    def test_invalid_json(self, tmp_path: Path) -> None:
        """Raises JSONDecodeError for malformed JSON."""
        pkg_file = tmp_path / "package.json"
        pkg_file.write_text("not json {{{")

        with pytest.raises(json.JSONDecodeError):
            parse_package_json(pkg_file)

    def test_invalid_structure(self, tmp_path: Path) -> None:
        """Raises ValueError when the top-level value is not an object."""
        pkg_file = tmp_path / "package.json"
        pkg_file.write_text('"just a string"')

        with pytest.raises(ValueError, match="expected object"):
            parse_package_json(pkg_file)

    def test_non_dict_dependencies_ignored(self, tmp_path: Path) -> None:
        """Skips a ``dependencies`` value that is not a dict."""
        pkg = {
            "name": "test-project",
            "dependencies": "invalid",
            "devDependencies": {"chalk": "^5.0.0"},
        }
        pkg_file = tmp_path / "package.json"
        pkg_file.write_text(json.dumps(pkg))

        result = parse_package_json(pkg_file)

        assert len(result) == 1
        assert result[0].name == "chalk"
