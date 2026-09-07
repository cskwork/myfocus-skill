<p align="center"><img src="logo.png" width="120" alt="logo" /></p>

# myfocus-skill

> `/myfocus` — Surface the highest-priority next task across recent coding-agent sessions. An antidote to parallel-work decision fatigue.

[![tests](https://img.shields.io/badge/tests-stdlib%20unittest-blue)](#testing)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## What

`/myfocus` scans your local session logs from any registered coding agent (Claude Code, Codex, Gemini, plus anything you add via the plugin interface), clusters by project, applies a priority heuristic, and prints **one task to focus on** plus 2–4 deferred candidates. The skill never executes the task — it only points.

## Install

Requires Python 3.10+ (stdlib only, no pip deps).

```bash
git clone https://github.com/cskwork/myfocus-skill ~/myfocus-skill
ln -s ~/myfocus-skill ~/.claude/skills/myfocus
```

Restart Claude Code (or reload skills). `/myfocus` is now registered.

## Usage

```
/myfocus                              # last 5h, all registered agents
/myfocus --window 24h                 # widen window
/myfocus --cwd $(pwd)                 # only sessions in current directory tree
/myfocus --agents claude_code,codex   # restrict to subset
/myfocus --list-agents                # show registered scanners + default paths
/myfocus --save                       # snapshot to ~/.claude/myfocus/<timestamp>.md
/myfocus --json                       # raw scanner JSON, skip LLM synthesis
```

You can also call the scanner directly without Claude:

```bash
cd ~/myfocus-skill
python3 -m scripts.collect --window 5h
```

## Supported agents

| Agent | Module | Default session path |
|---|---|---|
| Claude Code | `scripts/scanners/claude_code.py` | `~/.claude/projects/<encoded-cwd>/*.jsonl` |
| Codex CLI | `scripts/scanners/codex.py` | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` |
| Gemini CLI | `scripts/scanners/gemini.py` | `~/.gemini/tmp/<alias>/logs.json` |

Override any base path via environment variables: `MYFOCUS_BASE_CLAUDE_CODE`, `MYFOCUS_BASE_CODEX`, `MYFOCUS_BASE_GEMINI`. The skill auto-discovers any other scanner registered under `scripts/scanners/` — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Architecture

```
            collect.py (CLI)
                 │
                 ▼
         scanners/ registry  ←──── add scanners/<name>.py to extend
        ┌────────┼────────┐
        ▼        ▼        ▼
  claude_code  codex   gemini  (+ community-added)
                 │
                 ▼
           SessionDigest[] → JSON → stdout
                 │
                 ▼
            SKILL.md (LLM)  ← clusters, prioritizes, renders
                 │
                 ▼
       TOP PRIORITY  /  DEFERRED  /  CONTEXT
```

Deterministic work (file I/O, time filtering, JSON extraction) lives in Python. Subjective work (topic clustering, priority weighting) lives in the LLM via the instructions in `SKILL.md`.

## Testing

```bash
python3 -m unittest discover -s tests -v
```

All tests use stdlib + temp-dir fixtures. No real session content is committed to the repo.

## Documentation

- **[docs/SPEC.md](docs/SPEC.md)** — full design (problem, architecture, plugin interface, heuristics, security)
- **[docs/PLAN.md](docs/PLAN.md)** — implementation plan with TDD task breakdown
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — how to add a scanner

## Non-goals

- Persistent task databases or ML ranking — heuristic + LLM synthesis is enough.
- Real-time monitoring or background daemons — explicit invocation only.
- Direct Jira / Linear / GitHub Issues integration — compose other skills for that.
- Cross-machine session aggregation — single-laptop assumption.
- Web-only chat histories without local export.

## License

MIT — see [LICENSE](LICENSE).

## Maintained skill sources

Edit `skills/myfocus/` for maintained instructions/helpers and root `scripts/` for shared resources. Run `python3 scripts/sync-distributions.py`, then `python3 scripts/sync-distributions.py --check`. Resource copies under the skill and the existing Cursor directory are generated; keep them committed for independent installation.
