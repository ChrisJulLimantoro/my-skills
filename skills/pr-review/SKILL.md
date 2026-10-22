---
name: pr-review
description: Review a real GitHub PR end-to-end. Fetches the PR diff with gh, runs a 6-aspect parallel review (correctness, security, performance, hygiene, efficiency, testing — runs the unit tests, measures coverage of new code, and runs pre-commit/ruff when the repo uses them) internally, reads prior comments/reviews to reconcile whether earlier requested changes were addressed, then posts inline per-file comments plus an overall review whose verdict maps to APPROVE / REQUEST_CHANGES. Confirms before posting. Has a local mode (no PR yet) and a report-only mode. Trigger - /pr-review
trigger: /pr-review
---

# /pr-review

Review a GitHub pull request and publish the review back to GitHub. You are the orchestrator
AND the final merger: 6 sub-agents gather findings in parallel; you de-duplicate, re-rank,
compute the verdict, reconcile against any prior review, and post a single GitHub review with
inline per-file comments.

This skill is **self-contained** — it inlines the review engine and **must not** invoke
`/codereview` (that is the local-only internal tool). All GitHub I/O goes through the
authenticated `gh` CLI.

## Inputs

Invoked as: `/pr-review [PR number | URL]`

- If a PR number/URL is given, use it.
- Otherwise default to the PR for the **current branch** (`gh pr view` with no number).
- Several PRs may be given (`/pr-review 1971 2069`). Run the whole flow per PR with its own
  scratch subdir (`<SCRATCH>/<n>/…`) and report file (`review-report-pr-<n>.md`); the
  sub-agents of all PRs may be dispatched in one message.
- `--local` (or no PR exists for the current branch): **local mode**. Base = the repo's default
  branch (or `--base <branch>`); diff = `git fetch origin <base> && git diff origin/<base>...HEAD`
  → `<SCRATCH>/pr.diff`; changed files = the same with `--name-only`; `<WT>` = the current
  checkout (no review worktree); "Reviewed at" uses `git rev-parse HEAD`. Skip Step 1 (size from
  `git diff --shortstat`), Step 4,
  Step 5, and Step 6.2–6.4. Report file: `review-report-<branch>.md`. Implies report-only.
- `--report-only` (and always when this skill runs inside a sub-agent): stop after Step 6.1 —
  write the report and return it; never post. The caller posts after the user's OK.

## Prerequisites

- `gh` CLI installed and authenticated (`gh auth status`). No token is stored in this skill.
- Run from inside the target git repo (so `gh` resolves owner/repo), or pass a full PR URL.

## PR-head checkout (worktree)

Sub-agents need the files **at the PR head**, not whatever the local checkout happens to be on
(an existing branch worktree is often stale). Always create a detached worktree from origin:

```
git fetch origin <headRefName>
git worktree add --detach .worktrees/pr-<n>-review origin/<headRefName>
```

If the path already exists, `git -C <path> checkout --detach origin/<headRefName>` instead.
Never move or reset the author's own branch worktree. Pass this path to every sub-agent as
`<WT>` and treat it as read-only.

## Scratchpad

Put all temp artifacts in the session scratchpad dir (the one named in the environment's
"Scratchpad Directory" reminder), e.g. `<SCRATCH>/pr.diff`, `<SCRATCH>/pr-files.txt`,
`<SCRATCH>/pr-review-out/`, `<SCRATCH>/review-payload.json`. Write the human-readable
`review-report.md` to the **current working directory** for visibility. Never pollute the repo
with the JSON/diff temp files.

## Step 1 — Resolve the PR and gather context (all via `gh`)

Collect and stash these. `<n>` = PR number, `<owner>/<repo>` = repo slug.

1. Repo slug: `gh repo view --json nameWithOwner -q .nameWithOwner`.
2. PR metadata: `gh pr view [<n>] --json number,headRefOid,headRefName,baseRefName,title,state,author,changedFiles,additions,deletions`.
   - `number` → `<n>`; `headRefOid` → the `commit_id` required by the reviews API and the
     commit shown in the report's "Reviewed at" table.
   - `changedFiles`, `additions`, `deletions` feed both the Step 2 size heuristic and the
     "Reviewed at" table.
3. Diff → `<SCRATCH>/pr.diff`:  `gh pr diff <n>`.
   - **This must reflect GitHub's PR changes, not a local `git diff`.** GitHub computes the PR
     against its *own* base branch (`baseRefName` from step 2), which is frequently **not** `main`
     (stacked PRs, feature-branch bases). A local `git diff main...HEAD` will over-report files
     that already merged into the PR's base. Always source the diff from GitHub.
   - If `gh pr diff` ever returns empty/odd output (e.g. it fell back to a local ref), fetch the
     diff straight from the API instead:
     `gh api repos/<owner>/<repo>/pulls/<n> -H "Accept: application/vnd.github.v3.diff" > <SCRATCH>/pr.diff`.
4. Changed files (authoritative, from GitHub) → `<SCRATCH>/pr-files.txt`:
   `gh api repos/<owner>/<repo>/pulls/<n>/files --paginate -q '.[].filename'`.
   - This is the canonical changed-files set GitHub shows on the PR. Prefer it over
     `gh pr diff --name-only`. Cross-check that the file count matches the PR's `changedFiles`
     (from `gh pr view <n> --json changedFiles`); if they differ, the diff is stale/wrong-base —
     re-fetch via the API before reviewing. The same endpoint also returns per-file `patch`
     fields if you need hunk data without parsing the full diff.
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

## Step 2 — Gather findings (inline for small PRs, 6-aspect parallel agents otherwise)

**First decide whether to fan out to sub-agents.** Spawning 6 agents on a tiny PR is overkill.

Size heuristic (using `changedFiles` / `additions` / `deletions` from Step 1.2):
- **Small** = `changedFiles <= 5` **AND** `additions + deletions <= 150`. This is a guideline —
  use judgment (e.g. one 400-line file is *not* small; ten one-line doc tweaks *is* small).
- **Small → review inline yourself (no sub-agents).** Read `pr.diff` and the changed files
  directly and produce findings for **all six aspects** (correctness, hygiene, security,
  performance, efficiency, testing) using the same rubrics and severity scale below. Write the results
  to the same `<SCRATCH>/pr-review-out/<ASPECT>.json` files (same shape as item 8) so Step 3's
  merge logic is unchanged. The evidence bar, severity scale and per-aspect cap apply in full.
- **Not small → dispatch the 6 parallel Agents** as described below.

### Parallel path (non-small PRs)

Dispatch **all six Agent calls in one message** so they run concurrently. Use
`subagent_type: "general-purpose"` for each (Explore is read-only and cannot write the JSON).
First create `<SCRATCH>/pr-review-out/`.

Model per aspect:
- `model: "sonnet"` → **correctness**, **security**, **performance**, **efficiency**, **testing**
- `model: "haiku"` → **hygiene** (treat its severities as suggestions only; in practice it
  over-rates, e.g. calling an unused return value "Major")

Portability: `subagent_type` and `model` are Claude Code Agent options. In tools without them
(e.g. Codex, OpenCode), dispatch the six aspects through that tool's own sub-agent mechanism with
its default model, or, if it has none, review every aspect inline as in the small path.

If Step 1 found prior reviews, first write `<SCRATCH>/prior.md`: one line per prior finding
(reviewer, file:line, concern, and the author's claimed fix if they replied). Every sub-agent
gets it, so they verify fixes instead of rediscovering the same issues.

Give every sub-agent this shared contract, substituting the scratchpad paths and the
aspect-specific rubric:

> You are a code reviewer focused **only** on the **<ASPECT>** aspect of a code change.
>
> Inputs:
> - Unified diff: `<SCRATCH>/pr.diff`
> - Changed files list: `<SCRATCH>/pr-files.txt`
> - Read-only checkout at the PR head: `<WT>` (diff paths are relative to it; only the
>   testing aspect runs commands there, per its rubric)
> - Prior findings to re-check (only if Step 1 found any): `<SCRATCH>/prior.md`
>
> Do this:
> 1. Read the diff in full. Open changed files in `<WT>` for context beyond the hunks. Do not
>    review files outside the diff. Never read `.env` files.
> 2. Find issues that fall under **<ASPECT>** using this rubric: **<RUBRIC>**.
> 3. **Evidence bar — a finding must survive all three questions, or drop it:**
>    - *Is it real?* Trace the actual call path in `<WT>`. Don't infer behavior from names. If
>      a cheap check settles it (a focused test, a one-line Python call, `--help` of a CLI the
>      code shells out to), run it. If you cannot confirm, say so in `detail` and cap severity
>      at Minor.
>    - *Is it introduced by this PR?* Behavior that already exists unchanged on the base (the
>      same pattern in a sibling path, an older bug the diff merely touches) is not this PR's
>      finding. Mention it once in `detail` of a related finding, or skip it.
>    - *What concretely breaks?* Write `failure_scenario`: concrete input/state → wrong
>      result. If you can only describe a theoretical attacker or an unlikely environment
>      (a forger who only harms themselves, a millisecond TOCTOU window, a symlinked `/home`),
>      it is at most a Nit — usually drop it.
> 4. Assign severity by **realistic impact**, not by how scary the category sounds:
>    - **Critical** — the change's main path is broken for normal use, or there is data loss or
>      an exploitable hole reachable by realistic actors.
>    - **Major** — a real bug users will plausibly hit (an edge case of normal use, a
>      documented flag that doesn't work), or a perf problem on a hot path.
>    - **Minor** — a real but low-impact/low-likelihood issue, or a clearly worthwhile
>      simplification (duplicated logic, dead code).
>    - **Nit** — optional polish.
>    Style, naming, length and structure findings are never above Minor.
> 5. Quality over quantity: report at most **5** findings (correctness/security may exceed
>    this only for verified Major+ findings). An empty list is a good answer.
> 6. Prior findings (if `prior.md` is given): for each one in your aspect, check whether the
>    claimed fix really holds in `<WT>`. Record it in `prior_status`. Only re-report it as a
>    finding if the fix is incomplete or introduced a new bug.
> 7. **Line numbers:** `line` is the **new-file line number on the RIGHT side** and must fall
>    inside a `@@ -a,b +c,d @@` hunk of the diff (an added or context line). Check this
>    against the diff, not just the file. Use `"side":"LEFT"` + old line only for deleted lines.
> 8. **Write** `<SCRATCH>/pr-review-out/<ASPECT>.json`:
>    ```json
>    {"aspect":"<ASPECT>","findings":[
>      {"severity":"Critical|Major|Minor|Nit","file":"path","line":123,"side":"RIGHT",
>       "title":"short title","detail":"why it's a problem","failure_scenario":"input/state → wrong result",
>       "verified":"how you confirmed it (code path read / command run) or 'unconfirmed'",
>       "suggestion":"concrete fix / snippet"}],
>     "prior_status":[{"prior":"<id>","status":"Resolved|Still Open|Not an issue","note":"..."}]}
>    ```
>    The **testing** aspect also adds
>    `"checks":[{"name":"tests|coverage|pre-commit|ruff","command":"...","status":"pass|fail|not run","detail":"counts / diff-coverage % / failing hooks / why not run"}]`.
> 9. Return a one-line summary (count by severity) as your final message.

Aspect rubrics:
- **correctness** — logic errors, edge cases, null/undefined, off-by-one, race conditions, broken control flow, incorrect error handling, regressions vs. apparent intent.
- **hygiene** — naming, readability, dead/duplicated code, structure, consistency with surrounding style, comment quality, docs that contradict the code, obvious missing test coverage — especially tests that mock away the very boundary that is broken (e.g. monkeypatching a helper whose real signature the code calls wrongly).
- **security** — injection, auth/authz gaps, hardcoded secrets/credentials, unsafe deserialization, missing input validation, path traversal, risky or outdated dependencies. Name the realistic actor and what they gain; a scenario where the "attacker" only hurts themselves, or which needs an already-compromised host, is not a finding.
- **performance** — N+1 / redundant queries, unnecessary allocations or loops, algorithmic complexity, blocking I/O on hot paths, and whether the change effectively achieves its goal. Check whether the path is actually hot and whether the cost already exists elsewhere (e.g. an extra API call on a path that already calls the same API).
- **testing** — whether the new/changed code is proven by tests, and whether the repo's gates pass. Unlike the other aspects, **run commands** in `<WT>`:
  1. Detect the repo's commands from `AGENTS.md`/`CLAUDE.md`, `Makefile`, `pyproject.toml`/`ruff.toml`, `package.json`, `.pre-commit-config.yaml`, and CI workflows. Run only what the repo configures.
  2. **Tests:** run the suite (or the focused tests touching changed files when the full suite is slow). Any failure caused by this change is Critical (main path) or Major; a failure that also occurs on the base is context, not a finding.
  3. **Coverage of new code:** run with coverage (e.g. `pytest --cov --cov-report=xml`), then `uvx diff-cover coverage.xml --compare-branch=origin/<base>` for changed-line coverage. Target = the repo's configured threshold, else ≥90% of new lines. No coverage tool (e.g. bash tests) → map every new function/branch to the test exercising it. Untested new logic with real failure risk (error paths, branches, parsing) is Major; minor uncovered glue is Minor. Also flag tests that assert nothing meaningful or mock away the boundary under test.
  4. **pre-commit:** `pre-commit run --files <changed files>` when `.pre-commit-config.yaml` exists. **ruff:** `ruff check` + `ruff format --check` on changed Python files when the repo configures ruff and pre-commit does not run it. Failures are Minor, or Major when CI enforces the hook. Put the autofix diff (`git -C <WT> diff`) in `suggestion`, then restore with `git -C <WT> checkout -- .` (local mode: never touch the author's checkout — use `--show-diff-on-failure` / `ruff format --diff` instead of autofixing).
  5. Missing environment/dependencies is **not** a finding: record the check as `not run` with the reason.
- **efficiency** — code minimalism per the *Five Lines of Code* principle (Clausen): flag logic that can shrink while still covering every case — duplicated or overlapping conditionals, branches collapsible via guard clauses / early returns, functions mixing abstraction levels ("either call or pass, but not both"), `if` chains buried mid-function instead of leading it, methods far beyond ~5 lines doing several jobs, over-engineered abstraction for a single call site, redundant flags/state replaceable by direct returns. Target the **least logic that stays readable** — never propose code golf, dense one-liners, or cryptic names (`x`, `v`, `a`); a suggestion that reduces clarity is not a finding. Prefer the few findings with real payoff (logic that exists twice and can drift, dead code, a flag that changes nothing) over generic "this function is long" remarks.

## Step 3 — Merge, verify, verdict (you, Opus)

1. Read all six `<SCRATCH>/pr-review-out/*.json`. If a file is missing/unparseable, note the
   aspect; if **more than half** failed, stop and ask the user to re-run.
2. **De-duplicate**: when multiple aspects flag the same line/issue, keep the clearest write-up
   and tag it with every relevant aspect (e.g. `[correctness, security]`). Merge findings that
   share one root cause or one fix (e.g. two flags ignored on the same failure path).
3. **Skeptic pass — mandatory, do it yourself before showing anything to the user.** Sub-agents
   systematically over-report and over-rate. For **every** finding, ask:
   - *Real?* For each Critical/Major, read the code path yourself. Where a cheap reproduction
     exists, run it (call the function, run the CLI with `--help` or against a temp dir, run
     one focused test). A finding marked `"verified":"unconfirmed"` may not stay above Minor.
   - *Introduced here?* If the same pattern exists unchanged on the base or in a sibling path,
     drop it, or note it once as context. If the PR's bug actually lives on the base branch
     (e.g. a signature renamed in an earlier merged PR), say so: the fix may belong elsewhere.
   - *Concrete impact?* Re-rate from the `failure_scenario` and the deployment context: is the
     feature flagged off or unreleased? Is the trigger human-initiated? Did the author already
     verify this live? Downgrade or drop theoretical, self-harm-only and millisecond-window
     findings.
   - *Agents disagree?* (e.g. one says pagination truncates, another says it is correct) Read
     the code and keep only the correct claim.
   Record what you dropped and why; the user will want to see it.
4. **Noise budget:** after the skeptic pass, a review should typically carry ≤ ~8 findings.
   If there are more, keep every verified Critical/Major and cut the weakest Minor/Nit
   (style first). An oversized list hides the real blocker.
5. **Compute the verdict** from the final counts:
   - `Critical > 0 || Major > 0` → **Rejected with changes** → event `REQUEST_CHANGES`
   - else if `Minor > 0 || Nit > 0` → **Approve with changes** → event `APPROVE` (approve; the findings ride along as recommendations)
   - else → **Approved** → event `APPROVE`

## Step 4 — Reconcile prior review (only if prior reviews/comments/threads exist)

For each prior finding (from Step 1's reviews, inline comments, and GraphQL threads), decide
whether it has been **addressed**:
- Parse `pr.diff` hunk headers (`@@ -a,b +c,d @@`) to know which regions changed in the current head.
- Mark **Resolved** if the GraphQL thread has `isResolved: true`, or the current code no longer
  exhibits the problem (verify; use the sub-agents' `prior_status`).
- `isOutdated: true` only means the lines moved. It is **not** proof of a fix, and neither is
  an author reply saying "Fixed in <sha>". Check the code.
- Mark **Not an issue** if verification shows the prior concern was wrong (say why).
- Otherwise mark **Still Open**.
- Prior findings by **other reviewers** that are still open: do not post a duplicate inline
  comment on the same issue. Reference them in the table ("Still Open — agree, see #n") and
  only add an inline comment if you have new evidence (a reproduction, a missed caller).
- Bot reviews (Qodo/PR-agent, Qodana) count as prior findings too, but verify them like any
  sub-agent claim; they are often wrong.

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
   - `**Verdict:** <…>` (verdict text only — do **not** append `(event: …)`; the event is sent
     via the API payload, not shown in the body)
   - `## Reviewed at` table (immediately after the Verdict line) recording the inspected commit
     and base, built from Step 1.2 metadata:
     ```
     ## Reviewed at
     | Field | Value |
     |-------|-------|
     | Commit | `<short 7-char headRefOid>` (`<full headRefOid>`) |
     | Branch | `<headRefName>` → `<baseRefName>` |
     | Files | <changedFiles> changed (+<additions>/-<deletions>) |
     ```
   - `## Summary` line with counts + one-paragraph assessment
   - `## Findings` table — slim columns only: `# | Severity | Aspect(s) | File | Line`, sorted
     Critical→Nit, files contiguous. Do **not** put Issue/Suggestion text in the table.
   - `## Details` section below the table: one short paragraph per finding, keyed by its `#`,
     spelling out the issue and the concrete suggestion (e.g. `**1.** <issue>. **Suggestion:** <fix>`).
   - `## Tests & coverage` table from the testing aspect's `checks`: `Check | Command | Status | Detail`
     (tests, diff coverage %, pre-commit, ruff; `not run` rows keep their reason)
   - `## Prior review status` table from Step 4 (omit if none)
   - per-file `### <path>` fallback findings from 5.1 (omit if none)
4. **Event** from the verdict: `APPROVE` (Approved / Approve with changes) / `REQUEST_CHANGES`.
5. Write `<SCRATCH>/review-payload.json`:
   ```json
   { "commit_id": "<headRefOid>", "body": "<overall body md>", "event": "<EVENT>",
     "comments": [ ...inline objects... ] }
   ```

## Step 6 — Confirm, then submit

1. Write the same human-readable content to `./review-report.md` and **print the Verdict +
   Summary + tables in chat**. `review-report.md` contains the same body as the GitHub review,
   including the `## Reviewed at` table, so the local report and the posted comment agree on
   which commit was inspected. In chat (not in the GitHub body), also list the findings the
   skeptic pass **dropped or downgraded**, with a one-line reason each. That way the user can
   challenge the cuts, and seeing them builds trust in what remains.
2. **Ask the user to confirm before posting** (this is an outward-facing action). Show the
   verdict/event and how many inline comments will be posted. Do **not** post on your own.
   - Note: GitHub rejects `APPROVE`/`REQUEST_CHANGES` on the user's **own** PR. If the PR author
     is the authenticated user (any event other than `COMMENT`), warn that GitHub will reject it and
     offer to submit as `COMMENT` instead.
3. On confirmation, submit **one** review (inline comments + verdict atomically):
   ```
   gh api repos/<owner>/<repo>/pulls/<n>/reviews -X POST --input <SCRATCH>/review-payload.json
   ```
4. **Failure handling:** if the API rejects a comment whose line isn't in the diff
   (`"... is not part of the pull request"`), remove that comment from `comments[]`, append its
   finding to the per-file body fallback, and re-submit. Report the created review URL when done.
