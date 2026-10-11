"""Parse package.json files to extract dependency information."""

import json
from pathlib import Path

from radar import PackageInfo


def parse_package_json(path: str | Path) -> list[PackageInfo]:
    """Parse a package.json file and return a list of PackageInfo objects.

    Reads both ``dependencies`` and ``devDependencies`` sections.

    Args:
        path: Path to the package.json file.

    Returns:
        A list of :class:`PackageInfo` objects, one per dependency.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
        ValueError: If the top-level value is not a JSON object.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    if not isinstance(data, dict):
        raise ValueError(
            f"Invalid package.json: expected object, got {type(data).__name__}"
        )

    packages: list[PackageInfo] = []

    for section in ("dependencies", "devDependencies"):
        deps = data.get(section, {})
        if not isinstance(deps, dict):
            continue
        for name, version in deps.items():
            packages.append(PackageInfo(name=name, version=_clean_version(version)))

    return packages


def _clean_version(version: str) -> str:
    """Strip common semver range prefixes (``^``, ``~``, ``>=``, etc.).

    Args:
        version: Raw version string from package.json.

    Returns:
        The cleaned version string.
    """
    return version.lstrip("^~>=<! ")
