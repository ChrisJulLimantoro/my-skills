---
name: pr-review
description: Review a real GitHub PR end-to-end. Fetches the PR diff with gh, runs a 4-aspect parallel review (correctness, security, performance, hygiene) internally, reads prior comments/reviews to reconcile whether earlier requested changes were addressed, then posts inline per-file comments plus an overall review whose verdict maps to APPROVE / COMMENT / REQUEST_CHANGES. Confirms before posting. Trigger - /pr-review
trigger: /pr-review
---

# /pr-review

Review a GitHub pull request and publish the review back to GitHub. You are the orchestrator
AND the final merger: 4 sub-agents gather findings in parallel; you de-duplicate, re-rank,
compute the verdict, reconcile against any prior review, and post a single GitHub review with
inline per-file comments.

This skill is **self-contained** — it inlines the review engine and **must not** invoke
`/codereview` (that is the local-only internal tool). All GitHub I/O goes through the
authenticated `gh` CLI.

## Inputs

Invoked as: `/pr-review [PR number | URL]`

- If a PR number/URL is given, use it.
- Otherwise default to the PR for the **current branch** (`gh pr view` with no number).

## Prerequisites

- `gh` CLI installed and authenticated (`gh auth status`). No token is stored in this skill.
- Run from inside the target git repo (so `gh` resolves owner/repo), or pass a full PR URL.

## Scratchpad

Put all temp artifacts in the session scratchpad dir (the one named in the environment's
"Scratchpad Directory" reminder), e.g. `<SCRATCH>/pr.diff`, `<SCRATCH>/pr-files.txt`,
`<SCRATCH>/pr-review-out/`, `<SCRATCH>/review-payload.json`. Write the human-readable
`review-report.md` to the **current working directory** for visibility. Never pollute the repo
with the JSON/diff temp files.

## Step 1 — Resolve the PR and gather context (all via `gh`)

Collect and stash these. `<n>` = PR number, `<owner>/<repo>` = repo slug.

1. Repo slug: `gh repo view --json nameWithOwner -q .nameWithOwner`.
2. PR metadata: `gh pr view [<n>] --json number,headRefOid,headRefName,baseRefName,title,state,author`.
   - `number` → `<n>`; `headRefOid` → the `commit_id` required by the reviews API.
3. Diff → `<SCRATCH>/pr.diff`:  `gh pr diff <n>`.
4. Changed files → `<SCRATCH>/pr-files.txt`:  `gh pr diff <n> --name-only`.
5. Prior **reviews**:  `gh api repos/<owner>/<repo>/pulls/<n>/reviews`
   (fields: `state`, `body`, `user.login`, `submitted_at`).
6. Prior **inline review comments**:  `gh api repos/<owner>/<repo>/pulls/<n>/comments --paginate`
   (fields: `path`, `line`, `original_line`, `body`, `user.login`, `created_at`, `in_reply_to_id`).
7. Prior **issue (general) comments**:  `gh pr view <n> --json comments`.
8. **Thread resolution** (open/closed state of earlier requested changes) via GraphQL:
   ```
   gh api graphql -f query='
   query($owner:String!,$repo:String!,$num:Int!){
     repository(owner:$owner,name:$repo){
       pullRequest(number:$num){
         reviewThreads(first:100){ nodes{
           isResolved isOutdated path line
           comments(first:1){ nodes{ body author{login} } }
         } }
       }
     }
   }' -F owner=<owner> -F repo=<repo> -F num=<n>
   ```

If there are **no prior reviews/comments**, skip the reconciliation step (Step 4) entirely.

## Step 2 — Run the 4-aspect engine internally (parallel)

Dispatch **all four Agent calls in one message** so they run concurrently. Use
`subagent_type: "general-purpose"` for each (Explore is read-only and cannot write the JSON).
First create `<SCRATCH>/pr-review-out/`.

Model per aspect:
- `model: "sonnet"` → **correctness**, **security**, **performance**
- `model: "haiku"` → **hygiene**

Give every sub-agent this shared contract, substituting the scratchpad paths and the
aspect-specific rubric:

> You are a code reviewer focused **only** on the **<ASPECT>** aspect of a code change.
>
> Inputs:
> - Unified diff: `<SCRATCH>/pr.diff`
> - Changed files list: `<SCRATCH>/pr-files.txt`
>
> Do this:
> 1. Read the diff in full. For any file named in the changed-files list that exists on disk,
>    you may open it to get surrounding context beyond the diff hunks (improves accuracy). Paths
>    in the diff are repo-root-relative. Do not review files outside the diff.
> 2. Find issues that fall under **<ASPECT>** using this rubric: **<RUBRIC>**.
> 3. Assign each finding a severity:
>    - **Critical** — must fix before merge: data loss, security hole, crash, incorrect core behavior.
>    - **Major** — should fix: real bug in an edge case, significant maintainability/perf problem.
>    - **Minor** — worth fixing: localized issue, smaller correctness/clarity concern.
>    - **Nit** — optional polish: style, naming, micro-optimization.
> 4. Be precise — cite `file:line`, explain *why*, and give a concrete suggestion/snippet. Do not
>    invent issues; if you find nothing, return an empty list. Stay strictly within your aspect.
> 5. **CRITICAL for inline comments:** report `line` as the **new-file line number on the RIGHT
>    side of the diff** (the line number in the post-change file, as shown after the `+` side of
>    the relevant `@@ -a,b +c,d @@` hunk). If the finding is about a deleted line only present on
>    the LEFT side, set `"side":"LEFT"` and use the old-file line number; otherwise omit `side`.
> 6. **Write** your result to `<SCRATCH>/pr-review-out/<ASPECT>.json` with exactly this shape:
>    ```json
>    {"aspect":"<ASPECT>","findings":[
>      {"severity":"Critical|Major|Minor|Nit","file":"path","line":123,"side":"RIGHT",
>       "title":"short title","detail":"why it's a problem","suggestion":"concrete fix / snippet"}]}
>    ```
> 7. Return a one-line summary (count by severity) as your final message.

Aspect rubrics:
- **correctness** — logic errors, edge cases, null/undefined, off-by-one, race conditions, broken control flow, incorrect error handling, regressions vs. apparent intent.
- **hygiene** — naming, readability, dead/duplicated code, structure, consistency with surrounding style, comment quality, obvious missing test coverage.
- **security** — injection, auth/authz gaps, hardcoded secrets/credentials, unsafe deserialization, missing input validation, path traversal, risky or outdated dependencies.
- **performance** — N+1 / redundant queries, unnecessary allocations or loops, algorithmic complexity, blocking I/O on hot paths, and whether the change effectively achieves its goal.

## Step 3 — Merge + verdict (you, Opus)

1. Read all four `<SCRATCH>/pr-review-out/*.json`. If a file is missing/unparseable, note the
   aspect; if **more than half** failed, stop and ask the user to re-run.
2. **De-duplicate**: when multiple aspects flag the same line/issue, keep the clearest write-up
   and tag it with every relevant aspect (e.g. `[correctness, security]`).
3. **Re-rank holistically** against the severity definitions.
4. **Compute the verdict** from the final counts:
   - `Critical > 0 || Major > 0` → **Rejected with changes** → event `REQUEST_CHANGES`
   - else if `Minor > 0 || Nit > 0` → **Approve with changes** → event `COMMENT`
   - else → **Approved** → event `APPROVE`

## Step 4 — Reconcile prior review (only if prior reviews/comments/threads exist)

For each prior finding (from Step 1's reviews, inline comments, and GraphQL threads), decide
whether it has been **addressed**:
- Parse `pr.diff` hunk headers (`@@ -a,b +c,d @@`) to know which regions changed in the current head.
- Mark **Resolved** if the GraphQL thread for it has `isResolved: true` or `isOutdated: true`, OR
  the referenced code no longer matches the complained-about pattern in the current diff/file.
- Otherwise mark **Still Open**.

Emit a reconciliation table (used in the report and the GitHub review body):

```
## Prior review status
| # | Reviewer | File:Line | Prior concern | Status |
|---|----------|-----------|---------------|--------|
| 1 | @alice (2026-06-20) | src/x.ts:17 | NaN passthrough | Resolved |
| 2 | @bob (2026-06-21)   | src/y.ts:88 | missing null check | Still Open |
```

(`Resolved` = the requested change was apprehended / thread closed/outdated; `Still Open` =
unaddressed.)

## Step 5 — Build the GitHub review payload

1. **Line-validity check.** For each finding, confirm its `file:line` corresponds to an added or
   context line within a diff hunk on the stated side (parse the `@@ -a,b +c,d @@` headers in
   `pr.diff`; RIGHT-side valid lines run over the `+c,d` range counting `+`/context lines).
   - **Valid** → emit an inline comment object.
   - **Invalid** (line not in the diff) → drop the finding into the overall body under a per-file
     `### <path>` subsection (so nothing is silently lost and the API won't reject it).
2. **Inline comment objects:**
   ```json
   {"path":"<repo-root-relative path>","line":<n>,"side":"RIGHT",
    "body":"**<Severity> [<aspects>]** <title>\n\n<detail>\n\n**Suggestion:** <fix>"}
   ```
   (Use `side":"LEFT"` only for LEFT-side findings; for a multi-line span add `start_line` +
   `start_side`.)
3. **Overall body** (Markdown) =
   - `**Verdict:** <…>  (event: <…>)`
   - `## Summary` line with counts + one-paragraph assessment
   - `## Findings` table (same columns/shape as `/codereview`: `# | Severity | Aspect(s) | File | Line | Issue | Suggestion`, sorted Critical→Nit, files contiguous)
   - `## Prior review status` table from Step 4 (omit if none)
   - per-file `### <path>` fallback findings from 5.1 (omit if none)
4. **Event** from the verdict: `APPROVE` / `COMMENT` / `REQUEST_CHANGES`.
5. Write `<SCRATCH>/review-payload.json`:
   ```json
   { "commit_id": "<headRefOid>", "body": "<overall body md>", "event": "<EVENT>",
     "comments": [ ...inline objects... ] }
   ```

## Step 6 — Confirm, then submit

1. Write the same human-readable content to `./review-report.md` and **print the Verdict +
   Summary + tables in chat**.
2. **Ask the user to confirm before posting** (this is an outward-facing action). Show the
   verdict/event and how many inline comments will be posted. Do **not** post on your own.
   - Note: GitHub rejects `APPROVE`/`REQUEST_CHANGES` on the user's **own** PR. If the PR author
     is the authenticated user and the event isn't `COMMENT`, warn that GitHub will reject it and
     offer to submit as `COMMENT` instead.
3. On confirmation, submit **one** review (inline comments + verdict atomically):
   ```
   gh api repos/<owner>/<repo>/pulls/<n>/reviews -X POST --input <SCRATCH>/review-payload.json
   ```
4. **Failure handling:** if the API rejects a comment whose line isn't in the diff
   (`"... is not part of the pull request"`), remove that comment from `comments[]`, append its
   finding to the per-file body fallback, and re-submit. Report the created review URL when done.
