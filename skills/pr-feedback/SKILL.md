---
name: pr-feedback
description: This skill should be used when the user asks to "review the feedback on my PR", "fetch the reviews on my PR", "what do the reviewers want", "validate the PR comments", "triage my PR review", "help me respond to review comments", or wants to understand and decide how to act on reviews left on their own pull request. Fetches every review/comment on a GitHub PR, validates each point against the actual code, renders a verdict table plus per-point explanation, then asks how to proceed for each point. Does NOT post replies or push changes on its own. Trigger - /pr-feedback
trigger: /pr-feedback
---

# /pr-feedback

Triage the feedback **left on the user's own pull request**. Fetch every review, inline
comment, and general comment; validate each distinct review point against the current code;
judge whether it is valid; present a verdict table and a per-point explanation; then ask the
user how they want to proceed for each point.

This is the mirror image of `/pr-review`: that skill *authors* a review of someone else's PR;
this skill *consumes* the reviews on the user's PR and helps decide what to do about them. It
**reads** from GitHub via `gh` and **does not** post replies, resolve threads, commit, or push
unless the user later asks — the proceed step only records the user's decision.

## Inputs

Invoked as: `/pr-feedback [PR number | URL]`

- If a PR number/URL is given, use it.
- Otherwise default to the PR for the **current branch** (`gh pr view` with no number).

## Prerequisites

- `gh` CLI installed and authenticated (`gh auth status`). No token is stored in this skill.
- Run from inside the target git repo (so `gh` resolves owner/repo), or pass a full PR URL.

## Scratchpad

Put all temp artifacts in the session scratchpad dir (named in the environment's "Scratchpad
Directory" reminder), e.g. `<SCRATCH>/pr.diff`, `<SCRATCH>/reviews.json`,
`<SCRATCH>/comments.json`, `<SCRATCH>/threads.json`. Never pollute the repo with temp files.

## Step 1 — Resolve the PR and gather all feedback (via `gh`)

`<n>` = PR number, `<owner>/<repo>` = repo slug.

1. Repo slug: `gh repo view --json nameWithOwner -q .nameWithOwner`.
2. PR metadata: `gh pr view [<n>] --json number,headRefOid,headRefName,baseRefName,title,state,author,changedFiles,additions,deletions`.
3. Current diff → `<SCRATCH>/pr.diff`: `gh pr diff <n>`. This is the source of truth for what
   the code looks like **now** — used to check whether each review point is still applicable.
   - If `gh pr diff` returns empty/odd output, fetch from the API:
     `gh api repos/<owner>/<repo>/pulls/<n> -H "Accept: application/vnd.github.v3.diff" > <SCRATCH>/pr.diff`.
4. **Reviews** → `<SCRATCH>/reviews.json`: `gh api repos/<owner>/<repo>/pulls/<n>/reviews`
   (fields: `state`, `body`, `user.login`, `submitted_at`).
5. **Inline review comments** → `<SCRATCH>/comments.json`:
   `gh api repos/<owner>/<repo>/pulls/<n>/comments --paginate`
   (fields: `path`, `line`, `original_line`, `body`, `user.login`, `created_at`, `in_reply_to_id`, `diff_hunk`).
6. **General (issue) comments**: `gh pr view <n> --json comments`.
7. **Thread resolution state** via GraphQL (know which points are already resolved/outdated):
   ```
   gh api graphql -f query='
   query($owner:String!,$repo:String!,$num:Int!){
     repository(owner:$owner,name:$repo){
       pullRequest(number:$num){
         reviewThreads(first:100){ nodes{
           isResolved isOutdated path line
           comments(first:10){ nodes{ body author{login} createdAt } }
         } }
       }
     }
   }' -F owner=<owner> -F repo=<repo> -F num=<n>
   ```

If there is **no feedback at all** (no reviews, inline comments, or actionable general
comments), say so plainly and stop — there is nothing to triage.

## Step 2 — Extract distinct review points

Consolidate the raw feedback into a list of **distinct, actionable review points**:

- One point per substantive concern. Merge duplicates (the same issue raised inline and again
  in a review body) and merge a comment thread into the single point it discusses.
- Ignore pure chatter (approvals with no ask, "LGTM", "thanks", emoji reactions, replies that
  only acknowledge). Keep anything that requests a change, questions the code, or flags a risk.
- For each point capture: reviewer login, `file:line` (if inline), the ask in the reviewer's own
  intent, the surrounding `diff_hunk`, and the thread's resolved/outdated state from Step 1.7.

Number the points `1..N` in a stable order (group by file, then by line).

## Step 3 — Validate each point against the current code

For every point, decide whether it still holds against the **current** diff and the files on
disk. This is a real check, not a restatement of the comment.

1. Open the referenced `file:line` in the working tree (paths are repo-root-relative) and read
   enough surrounding context to judge the claim. Cross-reference `<SCRATCH>/pr.diff` to see the
   current state of that region.
2. Assign a **verdict** to the point:
   - **Valid** — the concern is correct and the code still has the issue; worth acting on.
   - **Partially valid** — a real underlying point, but overstated, or only part applies.
   - **Invalid** — incorrect: based on a misread, a false premise, or contradicted by the code.
   - **Already addressed** — was valid but the current code already fixes it, or the thread is
     `isResolved`/`isOutdated`.
   - **Non-actionable** — a question, preference, or opinion with no concrete required change.
3. Assign a **severity** to Valid/Partially-valid points using the same scale as `/pr-review`:
   **Critical** (must fix: data loss, security, crash, broken core behavior), **Major** (should
   fix: real edge-case bug, significant maintainability/perf problem), **Minor** (localized,
   worth fixing), **Nit** (optional polish). Non-Valid points get severity `—`.

For a large PR with many points, the validation of independent points MAY be fanned out to
parallel `general-purpose` sub-agents (one batch of points each), but the merge, verdicts, and
the user-facing table are always produced here. For a handful of points, do it inline.

## Step 4 — Present the verdict table

Print this table in chat (sorted Critical→Nit, then non-actionable/invalid last), and also write
the full report to `./pr-feedback-report.md` in the current working directory:

```
## PR feedback triage — #<n> "<title>"
| # | Reviewer | File:Line | Review point | Verdict | Severity |
|---|----------|-----------|--------------|---------|----------|
| 1 | @alice | src/x.ts:17 | NaN passes through validation | Valid | Major |
| 2 | @bob   | src/y.ts:88 | rename `tmp` for clarity | Partially valid | Nit |
| 3 | @alice | api/z.go:40 | thinks the mutex is missing | Invalid | — |
```

Keep the `Review point` cell to a short phrase — the full explanation goes in Step 5, not the
table.

## Step 5 — Explain each verdict (one paragraph per point)

Below the table, add a `## Details` section with one short paragraph per point, keyed by its `#`:

- **What the reviewer means** — restate the ask in plain terms.
- **Why the verdict** — the concrete evidence from the code: cite `file:line` and what the
  current code actually does, justifying Valid / Partially valid / Invalid / Already addressed /
  Non-actionable.
- **Suggestion** — the recommended response: for Valid/Partially-valid, the concrete fix (a
  snippet where useful); for Invalid, the reasoning to reply with; for Already-addressed, note
  it can be resolved; for Non-actionable, a one-line answer to the reviewer's question.

Format each as: `**<#>.** <what they mean>. **Verdict:** <why>. **Suggestion:** <recommended response>.`

## Step 6 — Ask how to proceed, per point

After presenting the table and details, ask the user how to proceed for **each** actionable
point. Use the `AskUserQuestion` tool — one question per point (batch up to 4 per call; iterate
if there are more), with the point's `#` and short phrase in the header. Offer these options,
ordered most-recommended first based on the verdict:

- **Fix it** — apply the change now (recommended for Valid points). Records intent to edit the
  code; the actual edit happens after the user confirms the plan.
- **Reply / push back** — draft a reply explaining why (recommended for Invalid points) without
  changing code.
- **Acknowledge & resolve** — for Already-addressed points, mark the thread resolved.
- **Defer** — leave for later / out of scope, optionally as a follow-up note.

Collect the decisions into a short action plan and print it. **Do not** edit code, post replies,
resolve threads, commit, or push as part of this skill — those are separate, explicitly
user-approved actions. If the user chooses "Fix it" for one or more points, hand off cleanly:
summarize exactly what would change and let the user greenlight the edits (or a subsequent
`/pr-review`-style follow-up) before any file is touched.
