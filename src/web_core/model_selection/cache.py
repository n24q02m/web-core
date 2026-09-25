"""File cache for per-source snapshots, TTL per ``Source.ttl_seconds``.

Layout: ``<root>/<source_name>.json`` = {"fetched_at": epoch, "payload": ...}.
Read errors / corrupt files -> miss. ``get(..., allow_stale=True)`` returns the
previous snapshot when a fetch fails — same fail-open philosophy as the
fetchers themselves: a dead board degrades to stale data, never to a crash.

Ported from knowledge_core.model_selection.cache with the default root moved
to web_core's own cache directory.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_ROOT = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "web_core" / "model_selection"


class FileCache:
    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root else _DEFAULT_ROOT

    def _path(self, source: str) -> Path:
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in source)
        return self.root / f"{safe}.json"

    def get(self, source: str, ttl_seconds: float, *, allow_stale: bool = False) -> Any | None:
        """Payload if within TTL; ``allow_stale`` accepts expired snapshots."""
        path = self._path(source)
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
            fetched_at = float(blob["fetched_at"])
        except (OSError, ValueError, KeyError, TypeError):
            return None
        if time.time() - fetched_at <= ttl_seconds or allow_stale:
            return blob.get("payload")
        return None

    def set(self, source: str, payload: Any) -> None:
        path = self._path(source)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps({"fetched_at": time.time(), "payload": payload}), encoding="utf-8")
            tmp.replace(path)
        except OSError as exc:
            logger.warning("model_selection cache write failed: source=%s error=%s", source, exc)
