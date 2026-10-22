---
name: weekly-report
description: Generate my weekly report (GitHub + Google Calendar + Gmail forms), ask for the manual bits, then sync to Google Docs. Runs from any directory. Trigger - /weekly-report
trigger: /weekly-report
---
# /weekly-report

Generate a GDP Labs–style weekly report from anywhere. GitHub data comes from the
authenticated `gh` CLI, Calendar/Gmail/Docs come from a normal Google OAuth 2.0 flow
(via the bundled `google_oauth.py` helper — no MCP servers), and Claude writes the
accomplishment summaries. Manual sections are gathered by asking the user interactively.
**All times are WIB (UTC+07:00).**

---

## CONFIG (edit these values to set up)

```
GITHUB_USER:  auto  # resolve from the authenticated `gh` account; override only when needed
AUTHOR_NAME:  Christopher Julius Limantoro
TIMEZONE:     Asia/Jakarta (WIB, UTC+07:00)
OUTPUT_DIR:   ~/.claude/skills/weekly-report/output
TEMPLATE:     ~/.claude/skills/weekly-report/template.md
OAUTH:        ~/.claude/skills/weekly-report/google_oauth.py
```

**Prerequisites** (one-time):

- `gh` CLI installed and authenticated (`gh auth status`). The token must be able to read
  every repository that should appear in the report; `repo` + `read:org` are sufficient for
  the private repositories in scope. No GitHub token is stored in this skill — `gh` provides it.
- Python 3 with `google-auth`, `google-auth-oauthlib`, and `google-api-python-client`
  installed (`pip install google-auth google-auth-oauthlib google-api-python-client`).
- A Google OAuth **client-secret JSON** for a Desktop/Installed app, with these APIs
  enabled in the GCP project: **Calendar, Gmail, Docs, and Drive** (Drive powers the
  title-based Doc lookup in step 8 — enable it at
  `https://console.developers.google.com/apis/api/drive.googleapis.com/overview`). The
  helper defaults to the client-secret path used by the weekly-report-generator repo;
  override with `GOOGLE_CLIENT_SECRET_FILE` if needed.
- First run of any Google step (or `python3 OAUTH auth`) opens a browser to authorize.
  The token is cached (reusing the repo's `tokens/google_token.json` when present, else
  `~/.claude/skills/weekly-report/google_token.json`) and auto-refreshed afterward —
  scopes are read-only for Calendar/Gmail/Drive plus write for Docs. If you upgraded from
  an earlier version, the first run re-opens the browser once to grant the new Drive scope.

### Google helper commands (`OAUTH` = the path above)

All read commands print JSON to stdout; render times in WIB.

- `python3 OAUTH auth` — run/refresh OAuth (one-time browser consent).
- `python3 OAUTH calendar --start <ISO> --end <ISO>` — events in the window.
- `python3 OAUTH forms --after YYYY/MM/DD` — Google Forms receipt submissions.
- `python3 OAUTH find-doc --contains "Weekly Report" --contains "<name>"` — search Google
  Drive for Docs whose **title** contains every `--contains` term (repeatable), newest
  first. This is how the weekly-report Doc is located.
- `python3 OAUTH find-doc-email --after YYYY/MM/DD [--query "weekly report"]` — **fallback**:
  search Gmail for weekly-report emails and extract any Google Doc links/IDs.
- `python3 OAUTH update-doc --id <DOC_ID> --file <PATH>` — replace a Doc's body.

---

## Workflow

Follow these steps in order. Compute everything in **WIB (Asia/Jakarta)** and render every
time as WIB.

### 1. Determine the week

- Get the current date in WIB. Compute this week's **Monday** and **Friday** dates.
- Define the GitHub activity window: `since` = Monday 00:00:00 WIB, `until` = now
  (capped at Friday 23:59:59 WIB). Convert to UTC ISO-8601 for the GitHub API.
- The report `period` string is `DD Mon YYYY - DD Mon YYYY` (Monday – Friday).
- Tell the user the period you're generating for.

### Active PR definition

Treat a PR as active only when at least one qualifying account event falls inside exact UTC
`since`/`until`: PR creation (`created_at`), an account-authored or account-committed PR
commit, a review submitted by the account (`submitted_at`), a conversation or inline review
comment authored by the account (`created_at`), or a merge (`merged_at`) of a connected PR.
Use `updated_at` and `involves` only to discover candidates; never use them alone as activity
proof.

After event validation, exclude `state: closed` unless `merged_at` itself falls inside the
window. Closed, unmerged PRs never appear. A PR merged during the window remains active even
though GitHub marks it closed. A PR closed after an in-window creation, commit, review, or comment
is excluded when no in-window merge exists.

### 2. GitHub activity (account-wide via `gh api`)

Do not fetch all account PRs and sort them locally. Use server-side search qualifiers for every
candidate query, then apply exact UTC timestamp checks locally. Search date ranges are coarse day
bounds; event timestamps decide whether a PR is active. Use range syntax
`YYYY-MM-DD..YYYY-MM-DD`, not separate `>=` and `<=` qualifiers.

Resolve account with `gh api user --jq '.login'`. Use configured `GITHUB_USER` only when it
intentionally differs from the authenticated account. Search every repository visible to that
account. Use `--method GET`, `--paginate`, and `per_page=100`. Request lightweight fields only;
never include `body` in candidate output.

```sh
GH_API_HEADERS=(-H 'Accept: application/vnd.github+json' -H 'X-GitHub-Api-Version: 2022-11-28')

gh api --method GET --paginate search/issues "${GH_API_HEADERS[@]}" \
  -f q="is:pr <QUALIFIERS>" \
  -F per_page=100 \
  --jq '.items[] | {repository: (.repository_url | sub("^.*/repos/"; "")), number, title, url: .html_url, author: .user.login, state, created_at, closed_at, updated_at}'
```

Set `END_DATE` to Friday when running after Friday; otherwise use today's date. Filter candidate
timestamps against exact UTC `since` and `until`. Run filtered searches sequentially, honor
`Retry-After`, and back off/retry on secondary-rate-limit responses. Keep stable key
`<repository full name>#<number>`.

Run only these filtered searches:

- **Created:** `is:pr author:${GITHUB_USER} created:${MON_DATE}..${END_DATE}`. Finds creation events and authored
  accomplishment candidates.
- **Merged:** `is:pr involves:${GITHUB_USER} merged:${MON_DATE}..${END_DATE}`. Finds connected merge events,
  including PRs now closed. Filter `author == GITHUB_USER` for `deployments`.
- **Reviewed:** `is:pr reviewed-by:${GITHUB_USER} updated:${MON_DATE}..${END_DATE}`. `updated` is only
  a candidate bound; validate review `submitted_at` exactly.
- **Open involved:** `is:pr is:open involves:${GITHUB_USER} updated:${MON_DATE}..${END_DATE}`. Residual commit or
  comment candidates only.
- **Open authored:** `is:pr is:open author:${GITHUB_USER}`. Mandatory Next Actions query; prevents old open
  authored PRs from being missed.

Do not search `review-requested` for activity: a request is not a qualifying event. Do not run global
`search/commits` queries in the default flow.

The merged search replaces separate connected-merged and author-merged searches. Hydrate only
merged candidates, closed candidates needing merge-state validation, and final authored
accomplishment PRs. Search records are sufficient for reviewed output and open-PR links:

```sh
gh api --method GET --paginate search/issues "${GH_API_HEADERS[@]}" \
  -f q="is:pr involves:${GITHUB_USER} merged:${MON_DATE}..${END_DATE}" \
  -F per_page=100 \
  --jq '.items[] | {repository: (.repository_url | sub("^.*/repos/"; "")), number, title, url: .html_url, author: .user.login, state, closed_at, updated_at}'
```

Hydrate selected PRs with authoritative `created_at`, `closed_at`, and `merged_at`. Request
`body` only for authored PRs that will be summarized:

```sh
gh api "repos/${REPOSITORY}/pulls/${NUMBER}" "${GH_API_HEADERS[@]}" \
  --jq '{number, title, html_url, body, state, draft, user: .user.login, created_at, closed_at, merged_at, updated_at, additions, deletions, changed_files}'
```

#### Review validation and output

Use one paginated GraphQL request through `gh api` for reviewed candidates. Request PR identity, PR author,
review author, and review timestamp only:

```sh
gh api graphql --paginate \
  -f query='query($q:String!, $endCursor:String) {
    search(query:$q, type:ISSUE, first:100, after:$endCursor) {
      nodes {
        ... on PullRequest {
          repository { nameWithOwner }
          number
          title
          url
          author { login }
          reviews(last:100) {
            totalCount
            nodes { author { login } submittedAt }
          }
        }
      }
      pageInfo { hasNextPage endCursor }
    }
  }' \
  -F q="is:pr reviewed-by:${GITHUB_USER} updated:${MON_DATE}..${END_DATE}"
```

Keep review nodes where `author.login == GITHUB_USER` and `submittedAt` is inside exact
`since`/`until`. Remove PRs authored by the account before rendering
`prs_reviewed`. If `totalCount > 100`, fall back to paginated
`repos/${REPOSITORY}/pulls/${NUMBER}/reviews` while selecting only `user.login` and
`submitted_at`. Never fetch or render review bodies.

Render reviewed PRs only as:

```text
* <title> [<REPO>#<number>](<url>)
```

#### Residual activity validation

Start active set from exact creation, review, and merge events. Inspect only `open-involved`
candidates not already active. Closed, unmerged PRs cannot qualify and need no residual inspection.

For each residual PR, inspect commits through the PR endpoint. This replaces global commit search
and commit-to-PR lookups:

```sh
gh api --method GET --paginate "repos/${REPOSITORY}/pulls/${NUMBER}/commits" "${GH_API_HEADERS[@]}" \
  -F per_page=100 \
  --jq '.[] | {author: .author.login, committer: .committer.login, author_date: .commit.author.date, committer_date: .commit.committer.date}'
```

Keep PR when GitHub-linked `.author.login` or `.committer.login` equals `GITHUB_USER` and
the matching timestamp is inside exact UTC `since`/`until`. Use commits only as activity evidence;
do not retain messages, SHAs, commit URLs, or standalone commits in the report.

To preserve comment activity without collecting details, inspect only metadata on residual open
candidates and discard it after filtering account and timestamp:

```sh
gh api --method GET --paginate "repos/${REPOSITORY}/issues/${NUMBER}/comments" "${GH_API_HEADERS[@]}" \
  -F per_page=100 --jq '.[] | {author: .user.login, timestamp: .created_at}'

gh api --method GET --paginate "repos/${REPOSITORY}/pulls/${NUMBER}/comments" "${GH_API_HEADERS[@]}" \
  -F per_page=100 --jq '.[] | {author: .user.login, timestamp: .created_at}'
```

An account-authored conversation or inline review comment inside the exact window qualifies the
PR. Do not store comment/review bodies, excerpts, IDs, or comment/review links. Store only an
internal evidence flag and PR identity. If monitoring is needed, render only
`**PR Monitoring:** Review/comment activity detected; inspect [<REPO>#<number>](<url>)`.

Deployments are authored PRs whose hydrated `merged_at` is inside the exact UTC window. Summarize selected
authored PRs into `github_accomplishments`, the existing **Accomplishments** section:

```
* <pr title> [<REPO>#<num>](<url>)
    * **Description:** <one-line what/why>
    * **Status:** <Done | In Review | Merged | ...>
    * **Key Changes Implemented:**
        * <bullet>
    * **PR Monitoring:** <Review/comment activity detected; inspect PR; or None>
```

Keep `deployments` and `prs_reviewed` as existing indented bullet-list subsections. Add
qualifying commit/comment-only PRs as one-line title and PR-link items under existing
Accomplishments section. Do not add report sections or template placeholders. Do not add review or
comment details. Use `* None` when empty. Note search caps or API failures instead of treating them as
no activity.

The shell is zsh. Quote query arguments and endpoint variables. Use a quoted read loop with an
explicit delimiter or a zsh array for JSONL; never rely on word splitting of an unquoted variable.

### 3. Meetings — Google Calendar (OAuth)

- Run `python3 OAUTH calendar --start <Mon 00:00 WIB ISO> --end <Fri 23:59:59 WIB ISO>`.
  If it prints an OAuth URL, share it with the user and wait for them to authorize.
- The helper returns a JSON array of `{summary, start, end, eventType, allDay}`. Skip
  `eventType` `workingLocation`/`outOfOffice` and all-day "Out of office"/holiday noise
  unless meaningful.
- Group by day, rendered as:

  ```
  * **Monday, Jan 5th, 2026**
    * 9:00 AM – 9:45 AM: <event title>
  ```

  Times in WIB. Skip all-day "Out of office"/holiday noise unless meaningful. If none,
  `  * None`.

### 4. Google Forms filled — Gmail (OAuth)

- Run `python3 OAUTH forms --after YYYY/MM/DD` with this week's Monday date. It returns a
  JSON array of `{title, date}` from Google Forms receipt emails
  (`forms-receipts-noreply@google.com`).
- Convert each `date` (RFC-2822) to WIB and render as
  `  * <title> (submitted on <Weekday, Mon Dth, YYYY at H:MM AM/PM> WIB)`.
- If none, `  * None`.

### 5. Ask the user for the manual sections (pause here)

Gather these interactively. **Learning is NOT asked** — it stays the empty stub from the
template.

**AskUserQuestion allows at most 4 options per question.** A Mon–Fri checklist does not
fit in one question — Friday silently disappears. Split the days across two questions.

- **WFO days** — two AskUserQuestion questions, both `multiSelect: true`:
    - Q1 "Which days did you work from office?" → 4 options: Monday, Tuesday, Wednesday,
      Thursday (each with its date, e.g. "Monday, Jan 5th").
    - Q2 "Any more WFO days, and which days were you out of office?" → options:
      "WFO Friday, <date>", "OOO: none", "OOO: one or more days".
    - If Q2 selects "OOO: one or more days", follow up with a separate question listing
      the weekdays (≤ 4 options per question) to pin down which.
    - Nothing selected = none.
- **Issues** — ask for current issues/blockers (free text; "None" allowed).
- **Next Actions** — ask for upcoming tasks (free text; "None" allowed). Always prepend the
  mandatory action to close every currently open authored PR found in step 2:
  `* Close the open PR: <title> [<REPO>#<num>](<url>)`. List each open authored PR when there are
  multiple. If none is open, render `* None` for this mandatory item; do not ask the user to close
  a PR owned by someone else.
- **Key Metrics / OMTM** — ask for the OMTM line(s). Users often paste a long multi-line
  block here; the UI strips newlines, so reflow it into markdown bullets when rendering.
- **Bug counts** — ask **in its own AskUserQuestion call, after OMTM is answered**: major &
  minor bugs this **month**, and major & minor bugs this **half-year** (H1 = Jan–Jun,
  H2 = Jul–Dec of the current year). Asking it alongside OMTM invites the user to paste the
  same block into both. These are bugs reported against the author's own work — never
  derive them from an OMTM bug table (P0/P1/P2 do not map to Major/Minor); ask.

Format multi-item answers as markdown bullet lists; render selected WFO/OOO days as
`* Monday, Jan 5th, 2026` lines (or "None").

### 6. Assemble and save

- Fold internal `prs_involved` and `pr_comments` output into
  `github_accomplishments`; do not add placeholders or sections to the template.
- Read `TEMPLATE`, then substitute every placeholder:
  `{AUTHOR_NAME} {period} {issues} {github_accomplishments} {deployments} {prs_reviewed}`
  `{google_forms_filled} {meetings_and_activities} {wfo_days} {omtm}`
  `{major_bugs_current_month} {minor_bugs_current_month} {major_bugs_half_year}`
  `{minor_bugs_half_year} {current_month} {current_year} {half_year} {half_year_year}`
  `{next_steps} {out_of_office_days}`.
  (`current_month` = full month name; `half_year` = "H1"/"H2"; `half_year_year`/`current_year` = year.)
- Write to `OUTPUT_DIR/Weekly_Report_<YYYY-MM-DD-mon>_to_<YYYY-MM-DD-fri>.md` (create
  `OUTPUT_DIR` if missing). Report the saved path.

### 7. Review pause

Show the report (or its path) and ask the user to review/edit and **confirm** before
syncing. **Do not sync automatically.**

### 8. Sync to Google Docs (only after confirmation)

- Locate the target Doc by **title** (a new Weekly Report Doc is created each week, named
  with the author and the week's date range):
  `python3 OAUTH find-doc --contains "Weekly Report" --contains "<AUTHOR_NAME>"`.
  This returns candidates `{id, name, modifiedTime, link}`, newest first.
- From the candidates, pick the Doc whose **title matches the current week's date range**.
  If none clearly matches, or several do, show the user the candidate titles/links and
  **confirm which one** before writing. Never assume — overwriting the wrong Doc is
  destructive.
- If `find-doc` returns nothing, fall back to
  `python3 OAUTH find-doc-email --after <Mon YYYY/MM/DD>` and confirm the extracted Doc
  with the user before proceeding.
- Once the Doc ID is confirmed, replace its body via
  `python3 OAUTH update-doc --id <DOC_ID> --file <saved report path>`.
- **Fallback** (if the API write fails, e.g. no access to the Doc): give the user the Doc
  link + the report markdown, and these steps — in Google Docs: Tools → Preferences →
  enable Markdown; then Ctrl+A, Ctrl+X, right-click → **Paste as Markdown**.

---

## Notes

- Everything is WIB. Double-check Calendar/Gmail timestamps are converted to UTC+07:00.
- Auth: `gh` handles GitHub; `google_oauth.py` handles Google via a standard OAuth 2.0
  flow (no MCP). The OAuth client-secret file and cached token live outside this skill —
  no secrets are stored in the skill itself.
- GitHub scope follows the authenticated account; set `GITHUB_USER` only for a deliberate
  override. Change the report author/timezone in CONFIG. To point at a different Google OAuth
  client or token, set `GOOGLE_CLIENT_SECRET_FILE` / `WEEKLY_REPORT_TOKEN_FILE` before running,
  or edit defaults in `google_oauth.py`.
