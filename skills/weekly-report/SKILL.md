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
GITHUB_OWNER: GDP-ADMIN
GITHUB_USER:  chrisjulius-gdplabs
REPOS:        glair-vision-engineering, glair-ocr, gl-sdk, glaip-sdk, ai-agent-platform, glair-vision-node-sdk, glair-vision-python-sdk, glair-vision-go, glair-vision-java
AUTHOR_NAME:  Christopher Julius Limantoro
TIMEZONE:     Asia/Jakarta (WIB, UTC+07:00)
OUTPUT_DIR:   ~/.claude/skills/weekly-report/output
TEMPLATE:     ~/.claude/skills/weekly-report/template.md
OAUTH:        ~/.claude/skills/weekly-report/google_oauth.py
```

**Prerequisites** (one-time):

- `gh` CLI installed and authenticated (`gh auth status`). Scopes need `repo` + `read:org`.
  No GitHub token is stored in this skill — `gh` provides it.
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

### 2. GitHub activity (via `gh` — no token needed)

For each repo in `REPOS`, using `GITHUB_OWNER`/`GITHUB_USER` and the window from step 1:

- **Authored PRs** (for Accomplishments):
  `gh pr list --repo $OWNER/$REPO --author '@me' --search "updated:>=<MON-DATE>" --state all --json number,title,url,state,body,mergedAt,updatedAt`
- **Commits**:
  `gh api "repos/$OWNER/$REPO/commits?author=$GITHUB_USER&since=<ISO>&until=<ISO>" --jq '.[].commit.message'`
  (Use commits to catch un-PR'd work; dedupe against PR titles.)
- **Deployments** = the authored PRs whose `mergedAt` falls inside the window.
- **Reviewed PRs**:
  `gh search prs --reviewed-by '@me' --owner $OWNER --updated ">=<MON-DATE>" --json repository,number,title,url`
  (filter to the configured repos).

Run repos in parallel where practical. Skip repos that error (e.g. no access) and note them.

Then **summarize as Claude** into the report's house style — for each significant PR:

```
* <pr title> [<REPO>#<num>](<url>)
    * **Description:** <one-line what/why>
    * **Status:** <Done | In Review | Merged | ...>
    * **Key Changes Implemented:**
        * <bullet>
```

Group by repo if multiple. Build `deployments` and `prs_reviewed` as bullet lists of
`<title> [<REPO>#<num>](<url>)` (indented two spaces). Use "* None" when a list is empty.

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

- **WFO days** — use AskUserQuestion, `multiSelect: true`, one option per weekday
  Mon–Fri with its date (e.g. "Monday, Jan 5th"). Plus nothing-selected = none.
- **Out-of-office days** — same checklist style, separate question (can combine with WFO
  in one AskUserQuestion call as two questions).
- **Issues** — ask for current issues/blockers (free text; "None" allowed).
- **Next Actions** — ask for upcoming tasks (free text; "None" allowed).
- **Key Metrics / OMTM** — ask for the OMTM line(s).
- **Bug counts** — ask for: major & minor bugs this **month**, and major & minor bugs this
  **half-year** (H1 = Jan–Jun, H2 = Jul–Dec of the current year).

Format multi-item answers as markdown bullet lists; render selected WFO/OOO days as
`* Monday, Jan 5th, 2026` lines (or "None").

### 6. Assemble and save

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
- To retarget repos or change the author/timezone, edit the CONFIG block above. To point
  at a different Google OAuth client or token, set `GOOGLE_CLIENT_SECRET_FILE` /
  `WEEKLY_REPORT_TOKEN_FILE` before running, or edit the defaults in `google_oauth.py`.
