---
name: codereview
description: Internal engine — review a local code change (diff.txt + file_name_diff.txt) using 5 parallel reviewers (correctness, hygiene, security, performance, efficiency), merged by Opus into a table report with a verdict (Approved / Approve with changes / Rejected with changes). For reviewing a real GitHub PR, use /pr-review instead. Trigger - /codereview
trigger: /codereview
---

# codereview

Review a code change described by a unified **diff** and a **changed-file list**. Fan out to
five specialized sub-agent reviewers running in parallel (one per aspect), then merge their
findings yourself (Opus) into a single ranked Markdown report.

You are the orchestrator AND the final merger. The sub-agents only gather findings; the
de-duplication, re-ranking, and report writing are done by you.

## Inputs

Invoked as: `/codereview [diff_path] [filenames_path]`

- `diff_path` — unified diff. Default: `./diff.txt`
- `filenames_path` — list of changed files (e.g. `git diff --name-status`). Default: `./file_name_diff.txt`

## Step 1 — Resolve and validate inputs

1. Resolve `DIFF` and `NAMES` from the args, applying the defaults above.
2. Verify both files exist and are non-empty. If either is missing, **stop** and tell the user
   the exact paths you looked for and how to generate them:
   ```
   git diff > diff.txt
   git diff --name-status > file_name_diff.txt
   ```
3. Read `NAMES` to get the changed-file scope. Read enough of `DIFF` to gauge size (don't fully
   ingest a huge diff yourself — the sub-agents read it).
4. Create the output dir: `mkdir -p codereview-out`.

## Step 2 — Fan out the 5 reviewers IN A SINGLE MESSAGE (parallel)

Dispatch **all five Agent calls in one message** so they run concurrently. Use
`subagent_type: "general-purpose"` for each (Explore is read-only and cannot write the JSON).

Model per aspect:
- `model: "sonnet"` → **correctness**, **security**, **performance**, **efficiency**
- `model: "haiku"` → **hygiene** (pattern-matching, low-reasoning aspect)

Give every sub-agent this shared contract, substituting the real `DIFF`/`NAMES` paths and the
aspect-specific rubric:

> You are a code reviewer focused **only** on the **<ASPECT>** aspect of a code change.
>
> Inputs:
> - Unified diff: `<DIFF>`
> - Changed files list: `<NAMES>`
>
> Do this:
> 1. Read the diff in full. For any file named in the changed-files list that exists on disk,
>    you may open it to get surrounding context beyond the diff hunks (improves accuracy). Do
>    not review files outside the diff.
> 2. Find issues that fall under **<ASPECT>** using this rubric: **<RUBRIC>**.
> 3. Assign each finding a severity using these definitions:
>    - **Critical** — must fix before merge: data loss, security hole, crash, incorrect core behavior.
>    - **Major** — should fix: real bug in an edge case, significant maintainability/perf problem.
>    - **Minor** — worth fixing: localized issue, smaller correctness/clarity concern.
>    - **Nit** — optional polish: style, naming, micro-optimization.
> 4. Be precise and specific — cite `file:line`, explain *why* it's a problem, and give a
>    concrete suggestion or code snippet. Do not invent issues; if you find nothing, return an
>    empty findings list. Stay strictly within your aspect.
> 5. **Write** your result to `codereview-out/<ASPECT>.json` with exactly this shape:
>    ```json
>    {"aspect":"<ASPECT>","findings":[
>      {"severity":"Critical|Major|Minor|Nit","file":"path","line":"123 or 120-135",
>       "title":"short title","detail":"why it's a problem","suggestion":"concrete fix / snippet"}]}
>    ```
> 6. Return a one-line summary (count by severity) as your final message.

Aspect rubrics:
- **correctness** — logic errors, edge cases, null/undefined, off-by-one, race conditions, broken control flow, incorrect error handling, regressions vs. apparent intent.
- **hygiene** — naming, readability, dead/duplicated code, structure, consistency with surrounding style, comment quality, obvious missing test coverage.
- **security** — injection, auth/authz gaps, hardcoded secrets/credentials, unsafe deserialization, missing input validation, path traversal, risky or outdated dependencies.
- **performance** — N+1 / redundant queries, unnecessary allocations or loops, algorithmic complexity, blocking I/O on hot paths, and whether the change effectively achieves its goal.
- **efficiency** — code minimalism per the *Five Lines of Code* principle (Clausen): flag logic that can shrink while still covering every case — duplicated or overlapping conditionals, branches collapsible via guard clauses / early returns, functions mixing abstraction levels ("either call or pass, but not both"), `if` chains buried mid-function instead of leading it, methods far beyond ~5 lines doing several jobs, over-engineered abstraction for a single call site, redundant flags/state replaceable by direct returns. Target the **least logic that stays readable** — never propose code golf, dense one-liners, or cryptic names (`x`, `v`, `a`); a suggestion that reduces clarity is not a finding.

## Step 3 — Collect and validate

1. Read all five `codereview-out/*.json` files.
2. If a file is missing or unparseable, note which aspect failed. If **more than half** failed,
   stop and ask the user to re-run (likely a wrong sub-agent type or transient failure).

## Step 4 — Merge (you, Opus)

1. Combine all findings.
2. **De-duplicate**: when multiple aspects flag the same line/issue, keep the single clearest
   write-up and tag it with every relevant aspect (e.g. `[correctness, performance]`).
3. **Re-rank holistically**: a sub-agent's severity is a suggestion — adjust up or down given
   the full picture and the severity definitions above.

4. **Compute the verdict** from the final severity counts (this drives the GitHub review event
   that `/pr-review` consumes):
   - `Critical > 0 || Major > 0` → **Rejected with changes** (event `REQUEST_CHANGES`)
   - else if `Minor > 0 || Nit > 0` → **Approve with changes** (event `COMMENT`)
   - else (no findings) → **Approved** (event `APPROVE`)

## Step 5 — Write `review-report.md` and report back

Write the merged report to `./review-report.md` as a **table** with a leading verdict:

```
# Code Review — <YYYY-MM-DD>

**Verdict:** <Approved | Approve with changes | Rejected with changes>  (event: <APPROVE | COMMENT | REQUEST_CHANGES>)

## Summary
Files reviewed: <N> · Critical <C> / Major <M> / Minor <m> / Nits <n>
<one-paragraph overall assessment of the change>

## Findings
| # | Severity | Aspect(s) | File | Line | Issue | Suggestion |
|---|----------|-----------|------|------|-------|------------|
| 1 | Major | correctness | path/to/file.ts | 92 | short title — why it's a problem | concrete fix |
| 2 | Minor | correctness, security | path/to/file.ts | 17 | short title — why | concrete fix |
...
```

Table rules:
- **Sort by severity** Critical → Major → Minor → Nit. Within that, keep rows for the **same
  file contiguous** (group by file) so per-file extraction is trivial for `/pr-review`.
- Collapse newlines in cell text to keep each finding on one row; escape any `|` inside cells as
  `\|`. Keep `Issue` and `Suggestion` concise — one sentence each; put longer code snippets in a
  fenced block beneath the table referenced by the row `#` if needed.
- If **zero findings**: omit the table, write `No findings.`, and set the verdict to `Approved`.

Then print the **Verdict + Summary** back in chat with a pointer to `review-report.md`.
