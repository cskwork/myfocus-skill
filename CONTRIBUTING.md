# Contributing

Thanks for considering a contribution. The most common kind is **a new scanner** for an additional coding agent.

## Add a scanner in three files

### 1. `scripts/scanners/<your_agent>.py`

```python
"""Scanner for <agent name>."""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from ..core import SessionDigest, cwd_matches
from . import register


@register("<your_agent>", default_base=Path(os.path.expanduser("~/.your-agent")))
def scan_your_agent(
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
    # ... walk session files, extract user/assistant text, populate digests ...
    return digests
```

### 2. `tests/test_scanners/test_<your_agent>.py`

Use `tempfile.TemporaryDirectory()` and write small JSON/JSONL fixtures inline. **Never commit real session content** — write the smallest synthetic samples that exercise the parsing logic. Pattern your tests after `test_claude_code.py`, `test_codex.py`, `test_gemini.py`.

### 3. Import in `scripts/collect.py`

Add:

```python
from .scanners import your_agent as _your_agent  # noqa: F401
```

This ensures the scanner registers when `collect.py` is run as a module.

### 4. README "Supported agents" table

Add one row.

## Rules

1. **stdlib only.** No new pip dependencies. The skill must work on a fresh Python 3.10+ install.
2. **No network calls.** Scanners read local filesystem only. Network access is forbidden.
3. **Fail soft.** A missing base path returns `[]`. An unparseable file is skipped, not raised.
4. **Anonymized fixtures.** Tests must never include real session content.
5. **One PR per scanner.** Don't bundle multiple agents in one PR.
6. **Heuristic changes go through discussion.** Keyword lists, weights, and tie-breakers in `SKILL.md` are open to refinement, but propose them via issue first.

## Running tests

```bash
python3 -m unittest discover -s tests -v
```

GitHub Actions runs the same command on every push and PR.

## Coding style

- Type hints encouraged but not required.
- Docstrings: one line for private helpers; a short paragraph for public functions.
- Imports: stdlib first, then `..core`, then `from . import register`.
- File length: keep scanner modules under ~150 lines. If one needs more, that's a signal to split helpers out.

## Reporting bugs

Open an issue with:
- OS + Python version
- The output of `/myfocus --list-agents`
- A minimal reproduction (anonymized!)
- Expected vs. actual behavior
