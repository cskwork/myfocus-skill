---
name: myfocus
description: myfocus — top next task across agent sessions. Use when: "what next", "next task", "다음 작업", "prioritize".
---


# MyFocus Skill

Surface the single highest-priority next task across recent coding-agent sessions. The skill never *executes* the task — it just points you to the one thing that deserves your next 30 minutes.

## Trigger

- `/myfocus`
- "myfocus", "what next", "next task", "prioritize"
- "다음 작업", "다음에 뭐 할까"

## Usage

```
/myfocus                                       # last 5h, all agents, verbose beginner-friendly output
/myfocus --window 24h                          # widen window
/myfocus --cwd $(pwd)                          # only sessions in current directory tree
/myfocus --agents claude_code,codex            # restrict to subset
/myfocus --brief                               # one-screen terse output (legacy minimal layout)
/myfocus --sections top,first_step             # pick exactly which sections to render
/myfocus --list-agents                         # show what scanners are registered
/myfocus --save                                # snapshot to ~/.claude/myfocus/YYYY-MM-DD-HHMM.md
/myfocus --json                                # raw scanner JSON, skip LLM synthesis
```

## What this skill does

When invoked, the calling Claude performs these steps:

### 1. Run the scanner

Execute (adjust the path to wherever the skill is installed):

```bash
python3 -m scripts.collect --window <window> [--cwd <cwd>] [--agents <list>] [--max-files-per-agent N] [--max-chars-per-session N]
```

Forward whatever flags the user passed. If `--json` was passed, print the script's stdout verbatim and stop.

The scanner must be invoked from the skill's repo root (so the `scripts` package resolves). When the skill is installed via symlink at `~/.claude/skills/myfocus`, the working directory should be `~/.claude/skills/myfocus`.

### 2. Parse and cluster

Parse the scanner's JSON. Group `sessions[]` by `cwd` (treat `null` cwd as its own bucket). Within each cwd, infer the dominant topic from the most recent `user_excerpts` and `assistant_excerpts`.

### 3. Apply the priority heuristic

For each topic, compute a score:

| Signal | Where to look | Δ |
|---|---|---|
| Blocker keyword in latest assistant turn (`blocked`, `stuck`, `fails`, `cannot`, `error 5xx`, plus user-language equivalents the user themselves used in transcripts) | `assistant_excerpts[-1]` | +3 |
| Time-sensitive (`today`, `tomorrow`, ISO date within 3 days, `deadline`, `ASAP`, plus user-language equivalents) | any excerpt | +3 |
| Last assistant turn ends with TODO or unresolved question | `assistant_excerpts[-1]` | +2 |
| Same topic appears in ≥3 sessions in this window | session count per topic | +2 |
| Same topic appears across ≥2 different agents | agent diversity per topic | +1 |
| "Done"/commit/PR-merge signal in latest assistant turn | `assistant_excerpts[-1]` | −3 |
| Only 1 session, total length <500 chars | session count + char count | −1 |

Tie-break: most recent `mtime`, then the agent the skill is running inside.

### 4. Render — composable sections

The output is a sequence of **named sections**. Each section is independent: render any subset, in any order. This is the extension point — to add a new section, define its name and renderer here and accept it under `--sections`.

#### Section catalog (built-in)

| name | always-on for `/myfocus`? | content |
|---|---|---|
| `top_priority` | yes | One-sentence title of the chosen task |
| `description` | verbose default only | 2–4 sentence beginner-friendly explanation of what the task actually is, in plain language. Names the code/file/concept and why it exists. |
| `why_now` | yes | Numbered list of the heuristic signals that made this win, with each signal explained in one sentence |
| `first_step` | yes | Numbered, copy-pasteable concrete actions. Include `cd`, file paths, exact commands |
| `references` | verbose default only | Source session id, agent, repo path, ticket/issue refs, any IDs mentioned in transcripts |
| `deferred` | yes (omit if <2 candidates) | Bulleted list with one-liner reasons per item |
| `context` | yes | Window, session counts per agent, cross-cutting theme |
| `commands` | optional | Suggested follow-up commands the user might want next (e.g., `/myfocus --save`, `git log --since`) |

Add a new section by adding a row here, defining its renderer below, and accepting its name under `--sections`. Contributors should send PRs that update only this catalog + a single Markdown template; no Python code change is required to add a section.

#### Modes

- **Default (no flag)**: emits `top_priority`, `description`, `why_now`, `first_step`, `references`, `deferred`, `context` — the beginner-friendly verbose layout.
- **`--brief`**: emits `top_priority`, `why_now`, `first_step`, `deferred`, `context` — terse single-screen output for power users.
- **`--sections a,b,c`**: emits exactly those, in that order. Overrides `--brief` and the default.

#### Verbose default — beginner-friendly template

Render exactly this layout (no other framing, no emojis except section markers, plain Markdown):

```
🎯 TOP PRIORITY: <one-sentence task title>

📝 What this task is
   <2-4 sentences in plain language. Name the code/file/concept; say what
   problem it addresses. Avoid acronyms unless you immediately expand them.
   Write for someone seeing the codebase for the first time.>

🔍 Why this is the top priority right now
   1. <signal name>: <one sentence — what we observed and why it counted>
   2. <signal name>: <one sentence>
   3. <signal name>: <one sentence>
   (Include only the signals that actually fired. Skip those that didn't.)

🚶 First step you can take in the next 30 seconds
   1. <concrete action: cd path, command, or specific decision>
   2. <next action>
   3. <next action>
   (Use real shell commands the user can paste. Show file paths with line
   numbers when relevant.)

🔗 References
   · Session: <agent> / <session_id>
   · Repo: <cwd>
   · Ticket/issue: <if mentioned in transcripts>
   · IDs / artifacts: <any concrete identifiers from transcripts>

📦 Deferred candidates (do these later)
   · <topic title> — <one-liner: why it can wait>
   · <topic title> — <one-liner>
   · <topic title> — <one-liner>

📊 Context
   Window: last <window>
   Sessions scanned: <agent>=N, <agent>=M, ...
   Cross-cutting theme: <only if there is one — otherwise omit this line>
```

#### Brief template (`--brief`)

```
TOP PRIORITY
  <one-sentence task title>
  Why  <one sentence: which signals made this win>
  First step  <one concrete action — file path, command, or first sub-decision>

DEFERRED
  · <one-liner>
  · <one-liner>

CONTEXT
  Window: last <window>  ·  Sessions: <agent>=N, <agent>=M, ...
```

#### Edge cases

- If fewer than 2 distinct deferrable topics exist, omit the `deferred` section.
- If `top_priority` was forced (only one viable topic), still include `why_now` with a single line saying "Only one in-flight topic in this window — no comparison needed."
- If the scanner returned zero sessions, output:

```
No activity in last <window>. Try /myfocus --window 24h to widen the search.
```

### 5. Save snapshot (if `--save`)

Create `~/.claude/myfocus/` if missing. Write the rendered markdown to `~/.claude/myfocus/YYYY-MM-DD-HHMM.md`. Print the absolute path on a final line.

## Boundaries

- **Never execute the task itself.** The skill only points; the user (or the next skill invocation) acts.
- **Never write to source code** as part of `/myfocus`. The only write target is the optional snapshot file.
- **Single laptop only.** No remote fetching, no cross-machine aggregation.
- **No external services.** All processing is local — session content never leaves the machine.

## Failure modes

| Symptom | Action |
|---|---|
| `collect.py` exits non-zero | Print stderr verbatim, do not attempt synthesis. |
| Scanner JSON parse fails | Surface the parse error and the first 200 chars of stdout. |
| All agents return zero sessions | Use the "No activity" message above. |
| `--cwd` filter removes everything | Output: "No sessions in last <window> matching <cwd>. Available cwds: <top 5 from a no-filter scan>." |
| Unknown agent in `--agents` | The scanner records it in `errors[]`. Mention this once in the report's CONTEXT section. |
