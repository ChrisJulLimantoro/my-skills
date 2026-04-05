# My Skills

A portable collection of Claude Code skills for daily development workflows. Clone this repo once, run the setup script, and these skills become available in every project on your machine.

## What is a "skill"?

A skill is a reusable prompt template that Claude Code can invoke by name. When you type a trigger phrase (e.g. "review a PR" or "design the architecture"), Claude recognizes it and runs the corresponding skill's instructions automatically. Skills keep complex, multi-step workflows consistent across projects without copy-pasting prompts.

## Quick Start

```bash
# 1. Clone the repo
git clone <repo-url> ~/my-skills
cd ~/my-skills

# 2. Make skills available in every project on this machine
make install-global
```

That's it. A symlink is created at `~/.claude/skills` pointing to this repo. Claude Code picks it up automatically in any project.

**Per-project only:**

```bash
make install
```

This sets up the skills locally in the current repo and creates the `.openclaw/skills` symlink for OpenClaw compatibility.

## Setup Commands

All setup operations are available via `make` (or directly via `bash scripts/setup.sh`):

| Command | What it does |
|---|---|
| `make install` | Set up skills for this project only |
| `make install-global` | Install globally — skills available in every project |
| `make uninstall` | Remove the `~/.claude/skills` global symlink |
| `make list` | List all installed skills with version and trigger |
| `make new SKILL_NAME=my-skill` | Scaffold a new skill with a stub `SKILL.md` |
| `make update` | Pull latest changes and re-validate |

The same flags work directly on the script if you prefer:

```bash
bash scripts/setup.sh                  # install (project-local)
bash scripts/setup.sh --global         # install globally
bash scripts/setup.sh --uninstall      # remove global symlink
bash scripts/setup.sh --list           # list skills
bash scripts/setup.sh --new my-skill   # scaffold a new skill
```

## Available Skills

| Skill | What it does | How to trigger |
|---|---|---|
| [`pr-architect`](#pr-architect) | Writes intent-based PR descriptions and CHANGELOG entries from `git diff` | "review a PR", "write a PR description", "document this pull request" |
| [`deep-research`](#deep-research) | Multi-source research with conflict synthesis, outputs `EXPLORATION_REPORT.md` | "explore", "do a deep dive", "research in depth", "investigate" |
| [`architect-pro`](#architect-pro) | Generates C4 or Mermaid diagrams before any implementation starts | "design the architecture", "draw a diagram", "plan before we build" |
| [`skill-creator`](#skill-creator) | Interviews you and writes a new `SKILL.md` file | "create a skill", "build a skill", "I need a skill that" |
| [`code-reviewer`](#code-reviewer) | Soft post-write review: logic, edge cases, naming, conventions, security | "review this code", "check my code", "soft review" |
| [`creative-ui`](#creative-ui) | Visual design decisions: color palettes, typography, spacing, micro-interactions | "design a UI", "make this look better", "pick a color palette" |
| [`ux-strategist`](#ux-strategist) | User flows, friction audits, information architecture, onboarding design | "map the user flow", "reduce friction", "audit UX" |

---

## Skill Details

### pr-architect

Runs `git diff main...HEAD`, classifies each change by impact type and severity, then outputs a structured PR description (What / Why / Impact / Breaking Changes / Testing) and a Keep a Changelog snippet. Documents intent, not line counts.

### deep-research

Searches a minimum of 8 sources across at least 4 categories (docs, academic, community, practitioner, contrarian, etc.), synthesizes conflicts between sources, and writes a structured `EXPLORATION_REPORT.md` to the working directory.

### architect-pro

Selects the right diagram type (C4 Context, C4 Container, flowchart, sequence, ER, state), generates it, adds a written summary of decisions and trade-offs, then **stops and asks for confirmation** before any implementation begins.

### skill-creator

Runs a three-round interview to understand purpose, workflow, and constraints, drafts a `SKILL.md`, iterates based on feedback, then writes the file to `.claude/skills/<name>/SKILL.md`.

### code-reviewer

A lightweight advisory review (max 10 observations) covering: logic correctness, edge cases, error handling, naming clarity, project conventions, and obvious security flags. Never blocks — always advisory.

### creative-ui

Starts by identifying emotional tone, audience, and one visual anchor. Produces CSS design tokens for color, a typography scale, spacing system, motion spec, and implemented code. Focuses on craft and making designs memorable, not just functional.

### ux-strategist

Starts by articulating the user's mental model and job-to-be-done. Maps current and proposed flows as Mermaid diagrams, audits against Nielsen's 10 heuristics, identifies unnecessary friction, and proposes concrete changes with success metrics.

---

## Repository Structure

```
.claude/skills/<skill-name>/SKILL.md   — skill definitions (auto-discovered by Claude Code)
.openclaw/skills                        — symlink to .claude/skills (OpenClaw compatibility)
scripts/setup.sh                        — bootstrapper and symlink manager
Makefile                                — convenience targets for setup operations
CLAUDE.md                               — project instructions for Claude Code
```

## Adding a New Skill

**Option A — scaffold with the setup script:**

```bash
make new SKILL_NAME=my-skill
# or: bash scripts/setup.sh --new my-skill
```

This creates `.claude/skills/my-skill/SKILL.md` with the correct frontmatter and section stubs. Open the file and fill in the description and body.

**Option B — use the skill-creator skill:**

Open any project in Claude Code and type: `create a new skill`

Claude will interview you and write the file.

**Option C — write it manually:**

1. Create `.claude/skills/<your-skill-name>/SKILL.md`
2. Add YAML frontmatter:

```yaml
---
name: your-skill-name
description: This skill should be used when the user asks to "...", "...", or "...". One sentence on what it does.
version: 0.1.0
---
```

3. Write the skill body in imperative form ("Run the diff." not "You should run the diff.")
4. Run `bash scripts/setup.sh` to validate

**Frontmatter rules:**
- `name`: kebab-case, must match the directory name
- `description`: third-person, opens with "This skill should be used when the user asks to", includes quoted trigger phrases
- `version`: start at `0.1.0`

**Body rules:**
- Imperative/infinitive verb form throughout
- No second person ("you")
- Keep under 2,000 words; move large reference material to a `references/` subdirectory

## Global vs. Per-Project Installation

| Mode | Command | Effect |
|---|---|---|
| Global (recommended) | `make install-global` | `~/.claude/skills` → this repo — works in every project |
| Per-project | `make install` | Skills available only in this repo |
| Remove global | `make uninstall` | Removes the `~/.claude/skills` symlink |

If `~/.claude/skills` already exists as a real directory (not a symlink), the script will warn you rather than overwrite it. To migrate: copy its contents into `.claude/skills/` in this repo, delete the original directory, then re-run.

## Compatibility

- **Claude Code** — skills are auto-discovered from `~/.claude/skills` (global) or `.claude/skills` (project-local)
- **OpenClaw** — the `.openclaw/skills` symlink provides compatibility with the OpenClaw skill loader
