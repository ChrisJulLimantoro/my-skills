---
name: pr-architect
description: This skill should be used when the user asks to "review a PR", "write a PR description", "create PR documentation", "analyze the diff", "generate a CHANGELOG entry", or "document this pull request". Produces intent-based PR documentation by running git diff and explaining impact rather than line counts.
version: 0.1.0
---

# PR Architect

Produce intent-based PR documentation and CHANGELOG snippets from git diff analysis.

## Core Philosophy

Document the *why* and *impact*, not the *what*. The diff already shows what changed. Every section answers a question a future reviewer or maintainer would ask.

## Step 1 — Gather Diff

```bash
# Full diff with context
git diff main...HEAD

# File-level summary
git diff main...HEAD --stat

# Commit log for this branch
git log main...HEAD --oneline
```

If `main` is not the base branch, try `master`, `develop`, or ask the user.

## Step 2 — Classify Each Change

For each changed file, assign an impact type:

| Impact Type | Indicators |
|---|---|
| Breaking change | Removed public API, changed function signature, deleted export |
| New capability | New public function/class/endpoint, new feature flag |
| Bug fix | Corrects wrong behavior, handles previously-unhandled case |
| Performance | Algorithmic change, caching, query optimization |
| Refactor | Behavior preserved, internal structure changed |
| Test | Only test files changed |
| Config / infra | CI, build scripts, dependencies, environment |
| Documentation | Only docs or comments changed |

Assign severity — **High** / **Medium** / **Low** — based on blast radius (how many callers or users affected).

Auto-flag as High severity:
- Any diff touching authentication, authorization, or cryptography
- Any removed or renamed exported symbol (potential breaking change)
- Any database migration file

## Step 3 — Generate PR Description

```markdown
## What this PR does

<1–3 sentences describing the intent and outcome, not the implementation>

## Why

<The motivation: bug report, user feedback, performance data, architectural goal>

## Impact

| Area | Change Type | Severity |
|---|---|---|
| <component or file area> | <type> | High / Medium / Low |

## Breaking Changes

<List any breaking changes with migration steps, or "None">

## Testing

<Specific test command, manual steps, or CI link>

## Notes for Reviewers

<Anything needing special attention, known trade-offs, or follow-up work>
```

## Step 4 — Generate CHANGELOG Entry

Propose a snippet in Keep a Changelog format. Only include sections that apply:

```markdown
## [Unreleased]

### Added
- <new user-facing capability>

### Changed
- <behavior change that is not breaking>

### Deprecated
- <feature being phased out>

### Removed
- <removed feature>

### Fixed
- <bug fix>

### Security
- <security fix>
```

Keep each entry to one line. Do not include internal refactors that have no user-visible effect unless the PR description calls them out as intentional cleanup.

## Quality Rules

- Do not treat line count as a proxy for impact
- If the diff touches database migrations, note rollback safety explicitly
- If the diff removes test coverage, call it out under Notes for Reviewers
- If the branch has only one commit, the commit message is a useful source for the "Why" section
