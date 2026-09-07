"""Shared, agent-independent helpers for the myfocus skill."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional


_WINDOW_RE = re.compile(r"^(\d+)([smhd])$")
_UNIT_MAP = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}


class WindowParseError(ValueError):
    """Raised when a window argument cannot be parsed."""


def parse_window(s: str) -> timedelta:
    """Parse a single-unit window string like '5h' into a timedelta.

    Combined units (e.g. '5h30m') are rejected — pass the larger unit.
    """
    m = _WINDOW_RE.match(s or "")
    if not m:
        raise WindowParseError(
            f"invalid window {s!r}: expected single-unit form like '30m', '5h', '2d' "
            f"(combined forms such as '5h30m' are not supported)"
        )
    n, unit = int(m.group(1)), m.group(2)
    return timedelta(**{_UNIT_MAP[unit]: n})


def cwd_matches(cwd: Optional[str], filter_prefix: Optional[str]) -> bool:
    """Return True if `cwd` is equal to or a descendant of `filter_prefix`.

    `filter_prefix=None` accepts any cwd including null. A non-null filter
    rejects null cwds. Match uses '/' as a boundary so '/x/y' does not match
    '/x/yankee'.
    """
    if filter_prefix is None:
        return True
    if cwd is None:
        return False
    prefix = filter_prefix.rstrip("/")
    return cwd == prefix or cwd.startswith(prefix + "/")


@dataclass
class SessionDigest:
    agent: str
    session_id: str
    path: str
    cwd: Optional[str]
    mtime: datetime
    user_excerpts: List[str] = field(default_factory=list)
    assistant_excerpts: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "agent": self.agent,
            "session_id": self.session_id,
            "path": self.path,
            "cwd": self.cwd,
            "mtime": self.mtime.isoformat(),
            "user_excerpts": list(self.user_excerpts),
            "assistant_excerpts": list(self.assistant_excerpts),
        }
