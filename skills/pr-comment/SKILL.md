---
name: pr-comment
description: This skill should be used when the user asks to "create a PR comment", "generate PR-COMMENT.md", "draft my PR description", "fill out the PR template", or "prepare the pull request body" before actually opening a PR. Diffs the current branch against a target branch and fills the repo's PR template. Does NOT create or open a GitHub PR. Trigger - /pr-comment
trigger: /pr-comment
model: sonnet
---

# /pr-comment

Generate a filled-out `PR-COMMENT.md` from the repo's pull request template, based on all
commits on the current branch versus a target branch. This only writes a local markdown file —
it never runs `gh pr create` and never pushes.

## Inputs

Invoked as: `/pr-comment [target-branch]`

- If `target-branch` is given, diff against it.
- Otherwise detect the repo's default branch (`git symbolic-ref refs/remotes/origin/HEAD` or
  `gh repo view --json defaultBranchRef`), falling back to `main` then `master`.

## Step 1 — Gather the diff and commit history

Run from the repo root:

```
git fetch origin <target-branch> --quiet   # if a remote exists
MERGE_BASE=$(git merge-base <target-branch> HEAD)
git log $MERGE_BASE..HEAD --oneline
git diff $MERGE_BASE..HEAD
```

Use the full commit range (all commits on the branch), not just the latest commit. This is the
only source of truth for Title, Summary, and Related Issues — don't ask the user to describe the
change up front.

## Step 2 — Locate the template

1. Look for `.github/pull_request_template.md` in the current repo. Use it if present.
2. Otherwise fall back to the bundled copy at `references/pull_request_template.md` in this
   skill directory.

Preserve the exact section structure and legends of whichever template is used — only fill in
the blanks, don't restructure it.

## Step 3 — Fill each section

**Title** — `<type>(<scope>): <description>`. Infer `type` from the diff (feat/fix/docs/style/
refactor/test/chore) and `scope` from the top-level changed path (e.g. `auth`, `api`, `BE`).
Prefer a conventional-commit-formatted commit subject already on the branch if one summarizes
the whole change; otherwise synthesize one from the diff. Delete the template's instructional
sub-bullets once filled, matching the `<!-- Delete this section -->` note.

**Summary** — 2-4 sentences: what changed and why, derived from the diff and commit messages.
Not a file-by-file listing.

**How to Test** — see Step 4; this section requires actually attempting local validation, not
just guessing steps.

**Related Issues** — grep commit messages and the branch name for issue references
(`#123`, `JIRA-123`, `closes/fixes/resolves #n`). If found, use `Closes #123`. If none found,
leave the placeholder comment in place rather than inventing an issue number.

**Author Checklist** — check only items verifiable from the diff/repo state:
- `Synced with latest main branch`: check it if `git merge-base <target-branch> HEAD` equals
  `<target-branch>`'s current tip (branch is not behind); otherwise leave unchecked.
- `PR title follows conventional commit format`: check it if the generated Title matches
  `type(scope): description`.
- `All tests pass locally`: check it only if Step 4 actually ran the test suite and it passed.
- `Meaningful commit messages used`: check it if commit subjects are non-generic (not all
  "wip"/"fix"/"update").
Leave everything else (code standards, self-review, docs, added tests) unchecked — those need a
human judgment call. Do not touch the `AI Feedback: Author`/`Reviewer` code blocks; leave them
exactly as in the template for the author/reviewer to fill in after merge.

**Additional Notes** — leave template links/content as-is unless the diff touches something
that warrants a callout (e.g. a screenshot placeholder for UI changes).

## Step 4 — Attempt local validation before writing "How to Test"

Try to actually validate the change locally rather than guessing:

1. Check for an existing project-specific way to run tests/build (e.g. a `run` skill, a
   `Makefile` target, `package.json` scripts, `pytest`/`go test`/`cargo test` conventions) based
   on the changed files.
2. Run the most relevant one.
3. If it runs and passes: write concrete, reproducible steps in "How to Test" (the actual
   command(s) run) and note "Validated locally — `<command>` passed."
4. If it fails, or no runnable test/build target can be determined (e.g. requires secrets,
   external services, or a UI to click through): do NOT claim it was tested. Write best-guess
   manual steps and prepend a visible flag, e.g.:
   `⚠️ Could not validate locally — please run/verify these steps yourself before opening the PR.`

Never mark "All tests pass locally" in the checklist unless step 3 actually happened.

## Step 5 — Write the file

Write the filled template to `PR-COMMENT.md` at the repo root (overwrite if it already exists).
Do not create a branch, commit, push, or open a PR. Tell the user the file path and remind them
to review it — especially the "How to Test" section if local validation wasn't possible — before
pasting it into an actual PR.
