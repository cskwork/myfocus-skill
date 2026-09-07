"""Scanner for Claude Code session logs at ~/.claude/projects/<encoded-cwd>/*.jsonl."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from ..core import SessionDigest, cwd_matches
from . import register


def _decode_cwd(dirname: str) -> Optional[str]:
    """Reverse Claude Code's projects/ directory encoding.

    The encoding strips the leading '/' and replaces remaining '/' with '-'.
    Folders containing literal dashes are not perfectly recoverable; the
    decoded path is used only for grouping and prefix matching.
    """
    if not dirname or not dirname.startswith("-"):
        return None
    return "/" + dirname[1:].replace("-", "/")


def _encode_cwd(path: str) -> str:
    """Forward-encode an absolute path to the Claude Code dirname form.

    Used to match a user-supplied --cwd filter against the actual encoded
    directory name when decoding round-trip is lossy (e.g. dashes in the
    real path).
    """
    return "-" + path.lstrip("/").replace("/", "-")


def _filter_matches_dir(dirname: str, decoded_cwd: Optional[str], filter_prefix: Optional[str]) -> bool:
    """True if either the decoded path or the encoded dirname matches the filter."""
    if filter_prefix is None:
        return True
    if cwd_matches(decoded_cwd, filter_prefix):
        return True
    # Fallback: filter encoded → match against dirname with boundary safety.
    encoded = _encode_cwd(filter_prefix.rstrip("/"))
    return dirname == encoded or dirname.startswith(encoded + "-")


def _text_blocks(message_obj) -> List[str]:
    """Extract text strings from a Claude-style content array."""
    if not isinstance(message_obj, dict):
        return []
    content = message_obj.get("content")
    if isinstance(content, str):
        return [content]
    if not isinstance(content, list):
        return []
    out: List[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text")
            if isinstance(text, str) and text.strip():
                out.append(text)
    return out


@register("claude_code", default_base=Path(os.path.expanduser("~/.claude/projects")))
def scan_claude_code(
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
    for proj_dir in sorted(base_path.iterdir()):
        if not proj_dir.is_dir():
            continue
        cwd = _decode_cwd(proj_dir.name)
        if not _filter_matches_dir(proj_dir.name, cwd, cwd_filter):
            continue
        for session_file in sorted(proj_dir.glob("*.jsonl")):
            try:
                mtime = session_file.stat().st_mtime
            except OSError:
                continue
            if mtime < cutoff:
                continue
            users: List[str] = []
            assists: List[str] = []
            try:
                with session_file.open("r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            obj = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        t = obj.get("type")
                        if t == "user":
                            users.extend(_text_blocks(obj.get("message")))
                        elif t == "assistant":
                            assists.extend(_text_blocks(obj.get("message")))
            except OSError:
                continue
            digests.append(SessionDigest(
                agent="claude_code",
                session_id=session_file.stem,
                path=str(session_file),
                cwd=cwd,
                mtime=datetime.fromtimestamp(mtime, tz=timezone.utc),
                user_excerpts=[u[:max_chars] for u in users[-5:]],
                assistant_excerpts=[a[:max_chars] for a in assists[-3:]],
            ))
            if len(digests) >= max_files:
                return digests
    return digests
