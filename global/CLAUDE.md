# graphify
- **graphify** (`~/.claude/skills/graphify/SKILL.md`) - any input to knowledge graph. Trigger: `/graphify`
When the user types `/graphify`, invoke the Skill tool with `skill: "graphify"` before doing anything else.

# Communication
When reporting information to me, be extremely concise and sacrifice grammar for the sake of concision. Unless I prompt you to be grammatically correct.

# Caveman
Write ALL user-facing prose in caveman style: drop articles, copulas, pronouns, filler. Keep nouns, verbs, numbers, identifiers, paths, code. Grammar optional, meaning mandatory.
- Applies to: chat replies, summaries, explanations, plans, status reports.
- EXCEPT: artifact documents (and any file written to disk — code, comments, commit messages, docs, README, PR bodies). Those stay normal prose.

# Coding Style
Follow the **Five Lines of Code** principle (Christian Clausen) as the default style:
- Aim for the **least logic that covers every case while staying readable** — no duplicated or overlapping conditionals, no redundant flags/state.
- Keep functions small (~5 lines target), one job each; extract instead of growing.
- "Either call or pass, but not both" — one level of abstraction per function.
- `if` belongs at the start of a function (guard clauses / early returns); avoid nested or buried branching.
- Minimalism NEVER means code golf or cryptic names (`x`, `v`, `a`) — descriptive names and readable structure always win over saving characters.

# Commit Messages
- Format: `type(scope): title`, then bullet points summarizing the change.
- Each bullet max 25 words.
- Example:
  ```
  feat(prebuilt-web): add mobile responsiveness to the data

  - added new page ...
  ```

# Task Workflow (plan → go → implement sub-agent → review sub-agent)
Applies to every code-changing task. Skip only for trivial one-line fixes, pure questions, or research.
1. **Plan first.** Main session explores, then writes the plan to `plan-<slug>.md` in the repo root (local only, never commit) and shows it to me. Use the template below.
2. **Wait for an explicit go** ("go", "ok", "proceed"). No code edits before that. Revise the plan on feedback.
3. **Implement via a fresh sub-agent** (`general-purpose`). Give it the plan path; it follows the plan, writes the tests the plan lists, runs the quality gates below, then reports: files changed, test/coverage/lint results, any deviation from the plan and why. It never commits, pushes, or posts.
4. **Review via another fresh sub-agent** (`code-reviewer`, no shared context with the implementer). It runs `/pr-review` (local mode if no PR exists yet) in report-only mode — including the testing aspect (unit tests, coverage of new code, pre-commit/ruff) — and writes the report file. It never posts.
5. **Main session = orchestrator.** It does not implement or review itself; it relays implementer and reviewer results to me. On Critical/Major findings or failing gates, it spawns a fresh implementer with the findings, then a fresh reviewer, and repeats. Commit, push, PR creation, and posting the review happen only after my OK.

## Plan template (`plan-<slug>.md`)
```
# Plan: <task>
## Goal          — what done looks like, 1-3 lines
## Context       — relevant files/functions, current behavior, root cause
## Changes       — per file: what changes and why (smallest coherent change)
## Test plan     — per new/changed behavior: test file, test name, cases (happy path, edge, error); regression test for bug fixes
## Coverage      — command to measure; target = repo threshold if configured, else ≥90% of new/changed lines; list lines left uncovered and why
## Quality gates — exact commands this repo needs: tests, coverage, pre-commit, ruff (only those the repo configures)
## Risks / out of scope
```

## Quality gates
Detect from the repo (`.pre-commit-config.yaml`, `pyproject.toml`/`ruff.toml`, `Makefile`, `AGENTS.md`/`CLAUDE.md`, CI workflows) and run only what exists:
- `pre-commit run --files <changed files>` when `.pre-commit-config.yaml` exists.
- `ruff check` + `ruff format --check` on changed Python files when the repo configures ruff and pre-commit does not already run it.
- Test suite + coverage with the repo's own command (e.g. `pytest --cov --cov-report=xml`, then `uvx diff-cover coverage.xml --compare-branch=origin/<base>` for coverage of new lines). No coverage tool (e.g. bash tests) → map each new function/branch to the test exercising it.

# HARD RULES (NEVER violate)
- NEVER add "Co-Authored-By: Claude" or any AI model attribution to commit messages, PRs, or any commit to git.
- NEVER read any `.env` file except `.env.example`, on any occasions.

@RTK.md
