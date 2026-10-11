"""Local JSON cache with 24-hour expiry for API responses."""

import hashlib
import json
import time
from pathlib import Path
from typing import Any

CACHE_DIR = Path.home() / ".dependency-radar" / "cache"
CACHE_EXPIRY_SECONDS: int = 24 * 60 * 60  # 24 hours


def _get_cache_path() -> Path:
    """Return the path to the on-disk cache file.

    Returns:
        Absolute path to ``api_cache.json``.
    """
    return CACHE_DIR / "api_cache.json"


def _load_cache() -> dict[str, Any]:
    """Load the entire cache dictionary from disk.

    Returns:
        The parsed cache dict, or an empty dict on any error.
    """
    cache_path = _get_cache_path()
    if not cache_path.exists():
        return {}
    try:
        with open(cache_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache: dict[str, Any]) -> None:
    """Persist the cache dictionary to disk.

    Args:
        cache: The full cache dictionary to write.
    """
    cache_path = _get_cache_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, indent=2)


def _make_key(namespace: str, identifier: str) -> str:
    """Create a deterministic cache key from *namespace* and *identifier*.

    Args:
        namespace: Cache namespace (e.g. ``"npm"``, ``"github"``).
        identifier: Unique identifier within the namespace.

    Returns:
        A hex-encoded SHA-256 hash string.
    """
    raw = f"{namespace}:{identifier}"
    return hashlib.sha256(raw.encode()).hexdigest()


def get_cached(namespace: str, identifier: str) -> Any | None:
    """Retrieve a cached value if it exists and has not expired.

    Args:
        namespace: Cache namespace (e.g. ``"npm"``, ``"github"``).
        identifier: Unique identifier within the namespace.

    Returns:
        The cached data, or ``None`` if missing / expired.
    """
    cache = _load_cache()
    key = _make_key(namespace, identifier)
    entry = cache.get(key)

    if entry is None:
        return None

    if time.time() - entry.get("timestamp", 0) > CACHE_EXPIRY_SECONDS:
        return None

    return entry.get("data")


def set_cached(namespace: str, identifier: str, data: Any) -> None:
    """Store a value in the cache (must be JSON-serialisable).

    Args:
        namespace: Cache namespace.
        identifier: Unique identifier within the namespace.
        data: Payload to cache.
    """
    cache = _load_cache()
    key = _make_key(namespace, identifier)
    cache[key] = {
        "timestamp": time.time(),
        "namespace": namespace,
        "identifier": identifier,
        "data": data,
    }
    _save_cache(cache)


def clear_cache() -> None:
    """Delete the cache file from disk."""
    cache_path = _get_cache_path()
    if cache_path.exists():
        cache_path.unlink()
