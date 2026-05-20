---
spec: myfocus-skill
status: draft
date: 2026-05-20
license-intent: MIT
distribution: public GitHub (private first, then public)
---

# `/myfocus` Skill — Highest-Priority Next-Task Surfacer

## 1. Problem

Working in parallel across multiple coding agents (Claude Code, Codex, Gemini, and others — Aider, Cursor, Continue, etc.) generates many half-finished threads. After context-switching, the user must spend cognitive effort reconstructing "which of these matters most right now." This decision fatigue is the bottleneck the skill targets.

The skill is **domain-agnostic** — no assumptions about repos, languages, ticketing systems, or workflows. It works for anyone whose coding agents persist session logs locally.

## 2. Goal

A single command `/myfocus` (and equivalent natural-language triggers) that:

1. Scans the last N hours (default 5h) of session logs from any registered coding agent.
2. Synthesizes a **single top-priority task** with a one-step entry-point.
3. Lists 2–4 deferred candidates with one-liner reasons.

The skill **never executes the task itself**. It only points the user (or the next skill invocation) to where to start.

**Extensibility is a first-class requirement.** New agents (Aider, Cursor, Continue, Goose, etc.) join by adding one Python file in `scanners/`, no core changes.

## 3. Non-Goals

- Persistent task database.
- ML / embedding-based ranking.
- Real-time monitoring or push notifications.
- Direct integration with Jira / Linear / GitHub Issues (those belong to separate skills users compose).
- Web-only chat histories without local export (e.g., Pi web).
- Cross-machine session aggregation.
- Built-in support for every agent on day one — bundled scanners cover Claude Code, Codex, Gemini; community contributes the rest via the plugin interface.

## 4. Architecture

Two layers separating deterministic vs. judgment-bound work:

```
"/myfocus" / "what next" / "다음 작업" / "next task"
        │
        ▼
[scripts/collect.py]            ← deterministic FS+time work
  scans configured agent dirs,
  filters by mtime ≤ window,
  extracts compact "session digest" per file,
  emits one JSON blob to stdout
        │
        ▼
[SKILL.md body instructions]    ← LLM (the calling Claude) does synthesis
  · cluster by topic / repo
  · apply priority heuristics
  · render markdown report
  · optional snapshot save
```

**Why split:** deterministic work (FS scan, mtime filter, JSON extraction) is unreliable when delegated to an LLM and cheap when delegated to a script. Judgment work (priority weighting given a user's context) is the opposite. The split keeps tokens low and accuracy high.

## 4a. Repository Layout (publish-ready)

```
myfocus-skill/                     ← standalone repo root (future GitHub public)
├── LICENSE                      ← MIT
├── .gitignore                   ← Python + macOS
├── README.md                    ← public-facing (install, usage, contribute)
├── CONTRIBUTING.md              ← how to add a scanner
├── SKILL.md                     ← Claude Code skill entry point
├── docs/
│   ├── SPEC.md                  ← this file
│   └── PLAN.md                  ← implementation plan
├── scripts/
│   ├── __init__.py
│   ├── collect.py               ← CLI entry; thin orchestrator
│   ├── core.py                  ← shared types (parse_window, SessionDigest, …)
│   └── scanners/
│       ├── __init__.py          ← @register decorator + REGISTRY dict
│       ├── claude_code.py       ← bundled
│       ├── codex.py             ← bundled
│       └── gemini.py            ← bundled
├── tests/
│   ├── __init__.py
│   ├── test_core.py
│   ├── test_cli.py
│   └── test_scanners/
│       ├── __init__.py
│       ├── test_claude_code.py
│       ├── test_codex.py
│       └── test_gemini.py
└── .github/
    └── workflows/
        └── test.yml             ← runs `python -m unittest discover` on push/PR
```

The repo is self-contained — anyone can `git clone` and either symlink `SKILL.md` (and `scripts/`) into `~/.claude/skills/myfocus/` or use a one-line installer documented in README.

## 5. Components

### 5.1 `SKILL.md`

YAML frontmatter:

```yaml
---
name: myfocus
description: Use when the user asks what to work on next after context-switching across coding agents. Scans recent Claude Code / Codex / Gemini sessions and surfaces the single highest-priority next task with one concrete entry-point. Triggers on "/myfocus", "myfocus", "what next", "next task", "다음 작업", "다음에 뭐 할까", "prioritize".
---
```

Body:
- Argument parsing instructions (window, cwd, agents, save, json).
- Invocation of `scripts/collect.py` with parsed args.
- Synthesis rules (priority heuristic, output format).
- Save behavior.
- Error handling expectations.

### 5.2 `scripts/collect.py` + `scripts/core.py` + `scripts/scanners/`

Python 3, **stdlib only** (no pip dependencies — keeps install frictionless on any Mac/Linux/Windows-with-py3 box).

**`core.py`** holds shared, agent-independent code:
- `parse_window(s: str) -> timedelta` + `WindowParseError`
- `SessionDigest` dataclass + `.to_dict()`
- helper `make_cwd_filter(prefix)` for consistent prefix matching across scanners

**`scanners/__init__.py`** exposes the registry:

```python
REGISTRY: dict[str, ScannerFn] = {}

def register(name: str, *, default_base: Path):
    def decorator(fn):
        REGISTRY[name] = ScannerSpec(name=name, fn=fn, default_base=default_base)
        return fn
    return decorator
```

Each scanner module (e.g. `scanners/claude_code.py`) registers itself at import time. `collect.py` discovers all members of `REGISTRY` and exposes them through `--agents`.

**`collect.py` inputs (argv):**

| Flag | Default | Notes |
|---|---|---|
| `--window` | `5h` | Parsed by exact regex `^(\d+)([smhd])$`. Combined units like `5h30m` rejected with explicit error pointing to single-unit form. |
| `--cwd PATH` | none | If set, only sessions whose recorded cwd is `PATH` or descends from it (prefix match with `/` boundary). |
| `--agents LIST` | all registered | Comma-separated. Unknown agent → recorded in `errors[]`, scan continues with the rest. |
| `--list-agents` | — | Prints registered agent names and default base paths, exits 0. |
| `--max-files-per-agent` | `40` | Safety cap. |
| `--max-chars-per-session` | `4000` | Trim digest. |

**Bundled scanners** (live in `scripts/scanners/`, each registered via the decorator):

| Agent | Discovery path | cwd recovery | Digest extraction |
|---|---|---|---|
| Claude Code | `~/.claude/projects/*/*.jsonl` (top-level only; v1 ignores `subagents/` subdir to avoid double-counting) | Decode from parent directory name: leading `-` → `/`, remaining `-` → `/`. Reverse only the directory-name encoding, not message content. | JSONL line-by-line. Each line is a typed event (`user`, `assistant`, `file-history-snapshot`, etc.). For `user`/`assistant`, look at `.message.content` (array of `{type,text}` blocks) and concatenate `text` fields. Keep last 5 user + last 3 assistant. |
| Codex | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` | Read line 1 only: `payload.cwd` from `{"type":"session_meta","payload":{"cwd":"..."}}`. If absent, mark cwd as `null`. | Same digest rule: last 5 user, last 3 assistant. Codex line types use `payload.message` or `payload.content`; collect text values. |
| Gemini | `~/.gemini/tmp/<dir>/logs.json` (ignore `chats/` subdir in v1 — `logs.json` is the flat, reliable format) | Load `~/.gemini/projects.json` once; build `alias → fullpath` map (alias = value, fullpath = key). If `<dir>` matches an alias, use the path; otherwise `null`. | `logs.json` is a JSON array of `{sessionId, type, message, timestamp}` objects. Group by `sessionId`, keep last 5 `type=="user"` and last 3 `type=="model"` (or `assistant`). If JSON parse fails, append `errors[]` entry and skip. |

**Output JSON shape:**

```json
{
  "generated_at": "2026-05-20T14:45:00Z",
  "window": "5h",
  "agents_scanned": ["claude", "codex", "gemini"],
  "sessions": [
    {
      "agent": "claude",
      "session_id": "21ab6597-...",
      "path": "/Users/.../21ab6597-....jsonl",
      "cwd": "/Users/.../item-docs",
      "mtime": "2026-05-20T14:40:00Z",
      "user_excerpts": ["...", "..."],
      "assistant_excerpts": ["...", "..."]
    }
  ],
  "errors": []
}
```

### 5.3 Synthesis instructions (in `SKILL.md`)

Given the JSON, the calling Claude must:

1. Group sessions by `cwd` (project) and infer topic per cluster.
2. Apply priority heuristic table (see §6).
3. Choose **exactly one** TOP task.
4. List 2–4 deferred items (skip if fewer than 2 distinct deferrable topics).
5. Render markdown in the §7 format.
6. If `--save`, write the rendered markdown to `~/.claude/myfocus/YYYY-MM-DD-HHMM.md` and print the path.

## 6. Priority Heuristic

| Signal | Source pattern | Weight |
|---|---|---|
| Blocker | `blocked`, `stuck`, `fails`, `error 5xx`, `cannot`, `막힘`, `안 됨` in last assistant turn | +3 |
| Time-sensitive | `today`, `tomorrow`, ISO date within next 3 days, `deadline`, `ASAP`, `오늘`, `내일` | +3 |
| In-flight (incomplete) | Last assistant turn ends with TODO / "다음 단계" / unresolved question | +2 |
| Repeat theme | Same topic touched in ≥3 sessions across window | +2 |
| Cross-agent confirmation | Same topic in 2+ different agents | +1 |
| Already-closed signal | Recent commit / PR merge / "done" in last assistant turn | −3 |
| Single short session | Only 1 session, <500 chars total | −1 |

Tie-break: prefer (a) most recent mtime, (b) the agent the user is currently in (Claude Code if invoked here).

## 7. Output Format

Plain markdown to stdout. Single, opinionated layout — no theming.

```
TOP PRIORITY
  <one-sentence task title>
  Why  <one sentence: which signals made this win>
  First step  <one concrete action — file path, command, or first sub-decision>
  Context  <session-id, source agent, repo, ticket ref if any>

DEFERRED
  · <one-liner>
  · <one-liner>
  · <one-liner>

CONTEXT
  Window: last 5h
  Sessions scanned: claude=N, codex=M, gemini=K
  Cross-cutting theme: <if any>
```

If `--json` flag is set, the helper script's raw JSON is printed and synthesis is skipped.

## 8. Plugin Interface (Extensibility)

A new agent scanner is one file in `scripts/scanners/`. Required interface:

```python
# scripts/scanners/aider.py
from pathlib import Path
from datetime import timedelta
from typing import List, Optional
from ..core import SessionDigest
from . import register

@register("aider", default_base=Path("~/.aider").expanduser())
def scan_aider(
    base_path: Path,
    window: timedelta,
    cwd_filter: Optional[str],
    max_files: int,
    max_chars: int,
) -> List[SessionDigest]:
    """Return SessionDigest list for sessions modified within window."""
    ...
```

Rules:
1. Signature must match exactly (positional + keyword acceptable; tests verify shape).
2. Return type is always `List[SessionDigest]`.
3. Missing `base_path` → return `[]` silently (don't raise).
4. Unparseable individual files → skip silently or append to a module-level error list (collected by `collect.py`).
5. Network calls are forbidden — `core.py` runs a smoke check during tests that imports each scanner with `socket` access denied.

A snippet template lives in `CONTRIBUTING.md`. New scanners need:
- The module file under `scripts/scanners/`
- A test file under `tests/test_scanners/test_<name>.py` using temp-dir fixtures
- One line in README's "Supported agents" table

Snapshots: `~/.claude/myfocus/YYYY-MM-DD-HHMM.md` (created on `--save`).

## 9. Failure Modes & Handling

| Failure | Behavior |
|---|---|
| Agent dir missing (e.g., Codex never installed) | Skip silently, note in `agents_scanned` exclusion. |
| Single file unparseable | Add entry to `errors[]`, continue. |
| Zero sessions in window | Output: "No activity in last <window>. Try `/myfocus --window 24h`." |
| All sessions filtered out by `--cwd` | Output: "No sessions matching cwd. Available cwds: <list top 5>." |
| Python 3 missing | SKILL.md instructs Claude to surface clear error and abort. |
| Gemini scanner crashes | Caught; agent marked `partial` in JSON. |

## 10. Testing Plan

Manual integration test (no automated framework — skill is local-only):

1. **Empty window:** `/myfocus --window 1m` → "No activity" message.
2. **Claude-only:** `/myfocus --agents claude` → ignores codex/gemini paths even if present.
3. **cwd filter:** `/myfocus --cwd $(pwd)` → only sessions tied to current dir.
4. **JSON pass-through:** `/myfocus --json` → emits valid JSON, no synthesis text.
5. **Save:** `/myfocus --save` → file written to `~/.claude/myfocus/`, content matches stdout.
6. **Real run:** invoke without args while having recent activity → output is sensible (subjective check).

No unit tests required for v1; the synthesis layer is LLM-evaluated and the scanner layer is small enough to inspect.

## 11. Security & Privacy

- Session logs contain user prompts + assistant outputs which may include secrets pasted by the user. The skill **does not** transmit data anywhere; all processing is local. Snapshots (if `--save`) inherit the same privacy properties as the source `.jsonl` files.
- No content from `~/.claude/auth.json` or similar credential files is read.

## 12. Open Questions (resolved before plan)

None — all design choices are locked. Adding a new agent later = new function in `collect.py` and new entry in the `--agents` allowlist.

## 13. YAGNI Explicit Rejections

- ❌ Cross-machine sync (single-laptop assumption).
- ❌ Web UI / TUI dashboard.
- ❌ Configurable priority weights (defaults are opinionated; users adjust by editing the skill).
- ❌ Auto-trigger on context switch (explicit invocation only).
- ❌ Per-project skill overrides.
- ❌ Slack / Teams output formatter.

## 14. Future Extensions (NOT v1 scope)

- Community scanners: Aider, Cursor, Continue, Goose, Windsurf — added via plugin interface, not bundled.
- "Resume" flag that auto-loads the TOP task into a fresh session.
- Confidence score per ranked task.
- TOML config file at `~/.config/myfocus-skill/config.toml` for user-tunable heuristic weights and language keyword sets.

## 15. Publishing & Distribution

The repo will live at `github.com/<owner>/myfocus-skill` (private until v1 stabilizes, then public).

**License:** MIT — permissive, standard for tools, compatible with users redistributing inside their own dotfiles.

**Install paths documented in README:**

1. **Symlink (recommended for hackers):** clone the repo, then `ln -s <repo>/SKILL.md <repo>/scripts ~/.claude/skills/myfocus/`.
2. **Copy (recommended for non-Git users):** download the release tarball and copy into `~/.claude/skills/myfocus/`.
3. **Plugin (future):** once Claude Code's plugin marketplace stabilizes, publish via the official channel.

**CI (`.github/workflows/test.yml`):**

```yaml
on: [push, pull_request]
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest]
        python: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: ${{ matrix.python }} }
      - run: python -m unittest discover -s tests -v
```

**No PyPI release planned.** The skill is a shell script + markdown — `git clone` is the install. Avoiding PyPI keeps the dependency surface zero.

**Contributor expectations** (CONTRIBUTING.md outline):
- One scanner per PR, with tests
- No new runtime dependencies (stdlib only)
- Sample anonymized fixtures in tests (never commit real session content)
- Update README "Supported agents" table
