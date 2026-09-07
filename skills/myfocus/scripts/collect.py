#!/usr/bin/env python3
"""myfocus skill — CLI scanner. Walks the scanner registry and emits JSON."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from .core import parse_window, WindowParseError, SessionDigest
from . import scanners as _scanners_pkg  # noqa: F401 - keeps the package importable

# Import bundled scanners so they register themselves.
from .scanners import claude_code as _claude_code  # noqa: F401
from .scanners import codex as _codex  # noqa: F401
from .scanners import gemini as _gemini  # noqa: F401
from .scanners import REGISTRY


def _resolve_base(name: str, default: Path) -> Path:
    env_key = f"MYFOCUS_BASE_{name.upper()}"
    override = os.environ.get(env_key)
    return Path(override) if override else default


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="myfocus-collect",
        description="Scan recent coding-agent session logs and emit a JSON digest.",
    )
    parser.add_argument("--window", default="5h", help="Time window, single-unit form like 5h, 30m, 2d.")
    parser.add_argument("--cwd", default=None, help="Filter sessions to this cwd (prefix match).")
    parser.add_argument("--agents", default=None, help="Comma-separated agent names. Default: all registered.")
    parser.add_argument("--list-agents", action="store_true", help="List registered scanners and exit.")
    parser.add_argument("--max-files-per-agent", type=int, default=40)
    parser.add_argument("--max-chars-per-session", type=int, default=4000)
    args = parser.parse_args(argv)

    if args.list_agents:
        for name in sorted(REGISTRY):
            spec = REGISTRY[name]
            sys.stdout.write(f"{name}\t{spec.default_base}\n")
        return 0

    try:
        window = parse_window(args.window)
    except WindowParseError as e:
        print(str(e), file=sys.stderr)
        return 2

    requested = (
        [a.strip() for a in args.agents.split(",") if a.strip()]
        if args.agents
        else sorted(REGISTRY.keys())
    )

    sessions: List[SessionDigest] = []
    errors: List[dict] = []
    scanned: List[str] = []

    for agent in requested:
        spec = REGISTRY.get(agent)
        if spec is None:
            errors.append({"agent": agent, "error": "unknown agent"})
            continue
        base = _resolve_base(agent, spec.default_base)
        try:
            digests = spec.fn(
                base,
                window,
                args.cwd,
                args.max_files_per_agent,
                args.max_chars_per_session,
            )
            sessions.extend(digests)
            scanned.append(agent)
        except Exception as e:
            errors.append({"agent": agent, "error": f"{type(e).__name__}: {e}"})

    sessions.sort(key=lambda d: d.mtime, reverse=True)
    out = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "window": args.window,
        "agents_scanned": scanned,
        "sessions": [d.to_dict() for d in sessions],
        "errors": errors,
    }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
