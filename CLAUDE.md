# AI Skills Repository

A portable collection of Claude Code skills for daily development workflows.

## Structure

```
.claude/skills/<skill-name>/SKILL.md   — skill definitions (auto-discovered)
.openclaw/skills                        — symlink to .claude/skills (OpenClaw compat)
scripts/setup.sh                        — bootstrapper and symlink manager
```

## Skills Included

| Skill | Purpose |
|---|---|
| `pr-architect` | Intent-based PR descriptions and CHANGELOG snippets from `git diff` |
| `deep-research` | Multi-source research with conflict synthesis and EXPLORATION_REPORT.md |
| `architect-pro` | C4/Mermaid diagram generation before any implementation |
| `skill-creator` | Interview-driven skill authoring assistant |
| `code-reviewer` | Soft post-write code review: logic, edge cases, conventions, naming |

## Skill File Conventions

**Frontmatter** (required):
```yaml
---
name: skill-name           # kebab-case, matches directory name
description: This skill should be used when the user asks to "..."   # third-person, with trigger phrases
version: 0.1.0
---
```

**Body rules**:
- Imperative/infinitive form: "Run the diff. Classify each change." — not "You should run..."
- Keep SKILL.md under 2,000 words; move large reference material to `references/` subdirectory
- No second person ("you") in skill body text

## Adding a New Skill

1. Create `.claude/skills/<your-skill-name>/SKILL.md`
2. Write YAML frontmatter with `name`, `description` (trigger phrases), `version`
3. Write the body in imperative form
4. Run `bash scripts/setup.sh` to validate

Or use the `skill-creator` skill — it interviews you and generates the file.

## Global Installation

Make skills available across all projects on this machine:

```bash
bash scripts/setup.sh --global
# Creates: ~/.claude/skills -> /path/to/this/repo/.claude/skills
```
