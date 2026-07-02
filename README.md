# My Skills

A portable, version-controlled collection of agent **skills** — one canonical source of truth
that installs into five different AI coding agents. Clone once, run the setup script, and every
skill becomes available in Claude Code, Hermes, Codex, OpenCode, and Cursor across every project
on your machine.

## What is a "skill"?

A skill is a reusable, multi-step prompt workflow defined in a single `SKILL.md` file. When you
type a trigger phrase (e.g. "do a deep dive") or invoke it as a slash command (e.g.
`/deep-research`), the agent runs the skill's instructions automatically — no copy-pasting
prompts between projects or tools.

## The architecture: one source, five tools

The key insight: **four of the five supported tools read `SKILL.md` natively** (the exact same
format). Only Cursor needs a transform. So there is exactly **one** copy of each skill —
everything else is a symlink or a generated file.

```
skills/<name>/SKILL.md          ← canonical source of truth (edit here, only here)
        │
        ├─ symlink ──▶ Claude Code   (~/.claude/skills,        .claude/skills)
        ├─ symlink ──▶ Hermes        (~/.hermes/skills,        skills/)
        ├─ symlink ──▶ Codex         (~/.codex/skills,         .agents/skills)
        ├─ symlink ──▶ OpenCode      (~/.config/opencode/skills, .opencode/skills)
        └─ generate ▶ Cursor         (~/.cursor/commands/*.md, .cursor/commands)
```

| Tool | Reads `SKILL.md`? | Global directory | Project directory |
|---|---|---|---|
| Claude Code | ✅ native | `~/.claude/skills/` | `.claude/skills/` |
| Hermes (Nous) | ✅ native | `~/.hermes/skills/` | `skills/` |
| Codex (OpenAI) | ✅ native | `~/.codex/skills/` | `.agents/skills/` |
| OpenCode | ✅ native | `~/.config/opencode/skills/` | `.opencode/skills/` |
| Cursor | ❌ uses `.md` commands | `~/.cursor/commands/` | `.cursor/commands/` |

Because the four native tools are symlinked to the same `skills/` directory, editing a `SKILL.md`
updates all of them at once. Cursor commands are regenerated from the same source by
`scripts/build-cursor.sh`.

## Quick Start

```bash
# 1. Clone the repo
git clone <repo-url> ~/my-skills
cd ~/my-skills

# 2. Install for every tool on this machine
make install-global
```

That wires `~/.claude/skills`, `~/.hermes/skills`, `~/.codex/skills`,
`~/.config/opencode/skills` to this repo's `skills/` directory, links generated Cursor
commands into `~/.cursor/commands/`, and symlinks `~/.claude/CLAUDE.md` →
`global/CLAUDE.md` (global Claude Code memory, see below).

**Per-project only** (no changes to your home directory):

```bash
make install
```

This creates in-repo symlinks (`.claude/skills`, `.opencode/skills`, `.agents/skills`,
`.cursor/commands`) so the skills work when an agent is launched from inside this repo.

## Setup Commands

| Command | What it does |
|---|---|
| `make install` | Wire skills for this project only |
| `make install-global` | Install for all five tools, every project on this machine |
| `make build` | Regenerate Cursor commands from `skills/*/SKILL.md` |
| `make uninstall` | Remove all global symlinks + generated Cursor command links |
| `make list` | List all skills with their trigger description |
| `make new SKILL_NAME=my-skill` | Scaffold a new skill |
| `make update` | Pull latest changes and re-wire |

The same flags work on the script directly: `bash scripts/setup.sh [--global | --uninstall |
--list | --new <name>]`.

## Global CLAUDE.md (personal preferences, every project)

`global/CLAUDE.md` is the version-controlled copy of `~/.claude/CLAUDE.md` — Claude Code's
**user-level memory**, loaded into every session in every project. It carries:

- **Communication** — extreme concision, grammar sacrificed for brevity
- **Coding Style** — the *Five Lines of Code* principle (Clausen): least logic that covers
  every case while staying readable; ~5-line functions; guard clauses first; one abstraction
  level per function; never code golf or cryptic names
- **Hard rules** — no AI attribution in commits, never read `.env` files
- Skill trigger wiring (e.g. `/graphify`)

**Setup:** `make install-global` symlinks `~/.claude/CLAUDE.md` → `global/CLAUDE.md`
automatically. If a real (non-symlink) `~/.claude/CLAUDE.md` already exists it is **skipped**,
not clobbered — merge its content into `global/CLAUDE.md` first, delete the original, then
re-run. Edit preferences in `global/CLAUDE.md` only; every session picks the change up
instantly through the symlink. `make uninstall` removes the symlink.

## Available Skills (16)

| Skill | What it does |
|---|---|
| `codereview` | 5-parallel-reviewer local diff review (correctness, hygiene, security, performance, efficiency) → ranked report + verdict |
| `command-development` | Guidance for authoring Claude Code slash commands |
| `creative-ui` | Visual design: color palettes, typography, spacing, motion |
| `deep-research` | Multi-source research → `EXPLORATION_REPORT.md` with conflict synthesis |
| `find-skills` | Discover and install agent skills by intent |
| `frontend-design` | Distinctive, production-grade frontend interfaces |
| `graphify` | Any input → knowledge graph → clustered communities + HTML/JSON/report |
| `hook-development` | Author Claude Code plugin hooks (PreToolUse/PostToolUse/etc.) |
| `plugin-settings` | The `.local.md` pattern for configurable plugin settings |
| `plugin-structure` | Scaffold and organize a Claude Code plugin |
| `pr-comment` | Draft a PR description (`PR-COMMENT.md`) from the branch diff + repo template |
| `pr-feedback` | Fetch + validate reviews on your own PR, verdict table, decide responses |
| `pr-review` | End-to-end 5-aspect GitHub PR review with inline comments via `gh` |
| `skill-creator` | Interview-driven authoring of a new `SKILL.md` |
| `skill-development` | Guidance and best practices for writing skills |
| `weekly-report` | GitHub + Calendar + Gmail → weekly report synced to Google Docs |

Run `make list` for the live list and descriptions.

## Repository Structure

```
skills/<skill-name>/SKILL.md   — canonical skill definitions (the only place to edit)
dist/cursor/commands/<name>.md — generated Cursor commands (gitignored, rebuilt on demand)
scripts/setup.sh               — installer / symlink manager for all five tools
scripts/build-cursor.sh        — SKILL.md → Cursor command generator
Makefile                       — convenience targets
CLAUDE.md                      — project instructions for Claude Code
global/CLAUDE.md               — global Claude Code memory (~/.claude/CLAUDE.md symlink target)
```

The in-repo tool symlinks (`.claude/skills`, `.opencode/skills`, `.agents/skills`,
`.cursor/commands`) and `dist/` are gitignored — they are recreated by `make install`.

## Adding a New Skill

**Option A — scaffold:**

```bash
make new SKILL_NAME=my-skill   # creates skills/my-skill/SKILL.md
make build                     # regenerate the Cursor command
```

**Option B — use the `skill-creator` skill:** open any project and ask to "create a new skill".

**Option C — write it manually:** create `skills/<name>/SKILL.md` with frontmatter:

```yaml
---
name: your-skill-name        # kebab-case, matches the directory name
description: This skill should be used when the user asks to "...", "...". One sentence on what it does.
---
```

`name` and `description` are the only required fields (Codex and Cursor rely on them). Existing
`trigger:` / `version:` fields are harmless extras and are preserved. Write the body in
imperative form ("Run the diff." not "You should run the diff."), keep it under ~2,000 words, and
move large reference material into a `references/` subdirectory.

After adding or editing a skill, run `make build` (or `make install`) to refresh the generated
Cursor commands. The four native tools pick up changes automatically through their symlinks.
