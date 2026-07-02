# AI Skills Repository

A portable, version-controlled collection of agent skills shared across five AI coding agents:
Claude Code, Hermes, Codex, OpenCode, and Cursor.

## Architecture

One canonical source of truth, distributed to every tool:

```
skills/<skill-name>/SKILL.md   — canonical skill definitions (edit ONLY here)
dist/cursor/commands/<name>.md — generated Cursor commands (gitignored, via build-cursor.sh)
scripts/setup.sh               — installs into all five tools (symlinks + generated files)
scripts/build-cursor.sh        — SKILL.md → Cursor command generator
global/CLAUDE.md               — global Claude Code memory; `--global` symlinks ~/.claude/CLAUDE.md here
```

Four tools (Claude Code, Hermes, Codex, OpenCode) read `SKILL.md` natively and are wired by
**symlinking** their skills directory to `skills/`. Cursor cannot read `SKILL.md`, so commands
are **generated** into `dist/cursor/commands/` and linked into Cursor's command directory.

Editing a `SKILL.md` updates the four native tools instantly (shared symlink target). After any
skill change, run `bash scripts/setup.sh` (or `make build`) to refresh the Cursor commands.

The in-repo tool symlinks (`.claude/skills`, `.opencode/skills`, `.agents/skills`,
`.cursor/commands`) and `dist/` are gitignored — `make install` recreates them.

## Skills Included (16)

`codereview`, `command-development`, `creative-ui`, `deep-research`, `find-skills`,
`frontend-design`, `graphify`, `hook-development`, `plugin-settings`, `plugin-structure`,
`pr-comment`, `pr-feedback`, `pr-review`, `skill-creator`, `skill-development`,
`weekly-report`.

Run `make list` for descriptions.

## Skill File Conventions

**Frontmatter** (required):
```yaml
---
name: skill-name           # kebab-case, matches directory name
description: This skill should be used when the user asks to "..."   # third-person, with trigger phrases
---
```

`name` and `description` are the only required fields (Codex and Cursor depend on them).
Existing `trigger:` / `version:` fields are harmless extras and are preserved.

**Body rules**:
- Imperative/infinitive form: "Run the diff. Classify each change." — not "You should run..."
- Keep SKILL.md under ~2,000 words; move large reference material to a `references/` subdirectory
- No second person ("you") in skill body text

## Adding a New Skill

1. Create `skills/<your-skill-name>/SKILL.md` (or run `make new SKILL_NAME=<name>`)
2. Write YAML frontmatter with `name` and `description` (trigger phrases)
3. Write the body in imperative form
4. Run `bash scripts/setup.sh` (or `make build`) to validate and regenerate Cursor commands

Or use the `skill-creator` skill — it interviews you and generates the file.

## Installation

```bash
make install         # this project only — in-repo symlinks
make install-global  # all five tools, machine-wide
make uninstall       # remove global symlinks + generated Cursor links
```

`make install-global` symlinks `~/.claude/skills`, `~/.hermes/skills`, `~/.codex/skills`,
`~/.config/opencode/skills` → this repo's `skills/`, and links generated commands into
`~/.cursor/commands/`.
