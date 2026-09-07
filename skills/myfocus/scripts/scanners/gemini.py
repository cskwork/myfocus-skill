"""Scanner for Gemini CLI session logs at ~/.gemini/tmp/<alias>/logs.json."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from ..core import SessionDigest, cwd_matches
from . import register


def _alias_map(projects_json: Path) -> dict:
    try:
        data = json.loads(projects_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    projects = data.get("projects") if isinstance(data, dict) else None
    if not isinstance(projects, dict):
        return {}
    return {alias: full for full, alias in projects.items() if isinstance(alias, str)}


@register("gemini", default_base=Path(os.path.expanduser("~/.gemini")))
def scan_gemini(
    base_path: Path,
    window: timedelta,
    cwd_filter: Optional[str],
    max_files: int,
    max_chars: int,
) -> List[SessionDigest]:
    tmp_dir = base_path / "tmp"
    if not tmp_dir.exists():
        return []
    aliases = _alias_map(base_path / "projects.json")
    cutoff = time.time() - window.total_seconds()
    digests: List[SessionDigest] = []

    for sub in sorted(tmp_dir.iterdir()):
        if not sub.is_dir():
            continue
        logs = sub / "logs.json"
        if not logs.exists():
            continue
        try:
            mtime = logs.stat().st_mtime
        except OSError:
            continue
        if mtime < cutoff:
            continue
        cwd = aliases.get(sub.name)
        if not cwd_matches(cwd, cwd_filter):
            continue
        try:
            data = json.loads(logs.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, list):
            continue

        users: List[str] = []
        assists: List[str] = []
        for entry in data:
            if not isinstance(entry, dict):
                continue
            kind = entry.get("type")
            msg = entry.get("message")
            if not isinstance(msg, str) or not msg.strip():
                continue
            if kind == "user":
                users.append(msg)
            elif kind in ("model", "assistant"):
                assists.append(msg)
        digests.append(SessionDigest(
            agent="gemini",
            session_id=sub.name,
            path=str(logs),
            cwd=cwd,
            mtime=datetime.fromtimestamp(mtime, tz=timezone.utc),
            user_excerpts=[u[:max_chars] for u in users[-5:]],
            assistant_excerpts=[a[:max_chars] for a in assists[-3:]],
        ))
        if len(digests) >= max_files:
            return digests
    return digests
