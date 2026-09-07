"""Scanner for Codex CLI rollout logs at ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from ..core import SessionDigest, cwd_matches
from . import register


def _payload_text(payload) -> List[str]:
    """Extract text strings from a Codex payload.

    Codex `response_item` payloads carry `content` as a list of `{type, text}`
    blocks (e.g. type='input_text' for user, 'output_text' for assistant).
    Older or alternative payload shapes use a bare `message` string.
    """
    if not isinstance(payload, dict):
        return []
    out: List[str] = []
    for key in ("message", "content"):
        v = payload.get(key)
        if isinstance(v, str) and v.strip():
            out.append(v)
        elif isinstance(v, list):
            for block in v:
                if isinstance(block, dict):
                    text = block.get("text") or block.get("content")
                    if isinstance(text, str) and text.strip():
                        out.append(text)
    return out


@register("codex", default_base=Path(os.path.expanduser("~/.codex/sessions")))
def scan_codex(
    base_path: Path,
    window: timedelta,
    cwd_filter: Optional[str],
    max_files: int,
    max_chars: int,
) -> List[SessionDigest]:
    if not base_path.exists():
        return []
    cutoff = time.time() - window.total_seconds()
    digests: List[SessionDigest] = []
    for session_file in sorted(base_path.rglob("rollout-*.jsonl")):
        try:
            mtime = session_file.stat().st_mtime
        except OSError:
            continue
        if mtime < cutoff:
            continue
        cwd: Optional[str] = None
        session_id = session_file.stem
        users: List[str] = []
        assists: List[str] = []
        try:
            with session_file.open("r", encoding="utf-8") as f:
                for i, line in enumerate(f):
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    t = obj.get("type")
                    if i == 0 and t == "session_meta":
                        payload = obj.get("payload") or {}
                        cwd = payload.get("cwd") or cwd
                        sid = payload.get("id")
                        if isinstance(sid, str):
                            session_id = sid
                    elif t == "response_item":
                        payload = obj.get("payload") or {}
                        role = payload.get("role")
                        if role == "user":
                            users.extend(_payload_text(payload))
                        elif role == "assistant":
                            assists.extend(_payload_text(payload))
                    elif t == "user":
                        users.extend(_payload_text(obj.get("payload")))
                    elif t == "assistant":
                        assists.extend(_payload_text(obj.get("payload")))
        except OSError:
            continue
        if not cwd_matches(cwd, cwd_filter):
            continue
        digests.append(SessionDigest(
            agent="codex",
            session_id=session_id,
            path=str(session_file),
            cwd=cwd,
            mtime=datetime.fromtimestamp(mtime, tz=timezone.utc),
            user_excerpts=[u[:max_chars] for u in users[-5:]],
            assistant_excerpts=[a[:max_chars] for a in assists[-3:]],
        ))
        if len(digests) >= max_files:
            return digests
    return digests
