---
name: devi-error-link-debugging
description: This skill should be used when the user asks to "debug a Devi error link", "investigate a devi-gdplabs failure", "trace an opencode workflow failure", or "inspect an opencode DB artifact", or shares a devi-gdplabs comment, GitHub Actions run, or opencode artifact link. It retrieves the workflow artifacts, replays the SQLite WAL safely, correlates session, message, part, and log evidence, and explains the actual failure.
version: 0.1.0
trigger: /devi-error-link-debugging
---

# Devi Error Link Debugging

Investigate failed `Digital Employee - Agentic Engineering Workflows` runs referenced by a
`devi-gdplabs` bot comment, GitHub Actions run, or OpenCode database/log artifact. Treat the bot
comment as a pointer only. Determine the actual failure from downloaded artifacts and correlate
the SQLite session data with `opencode.log`.

Keep all downloaded data under `/tmp/opencode/devi-<runID>/`. Do not modify the repository,
GitHub comments, workflow runs, or downloaded source artifacts. Redact tokens, credentials,
authorization headers, and other secrets from the final report.

## Prerequisites

Require:

- Authenticated `gh` CLI with access to the target repository and workflow artifacts.
- `python3` with the standard-library `sqlite3` module.
- `unzip`, `rg`, and standard shell utilities.

Do not use the `sqlite3` CLI. It is unavailable in the target environment. Use `python3 -c`
with the copied database instead.

## Step 1 - Resolve the Input

Accept any of these inputs:

- GitHub issue or pull-request comment URL containing `#issuecomment-<commentID>`.
- GitHub Actions run URL containing `/actions/runs/<runID>`.
- GitHub artifact URL containing `/actions/artifacts/<artifactID>`.
- Repository plus explicit comment, run, or artifact identifiers.
- A local directory containing an already-downloaded OpenCode database or log.

Extract `<org>`, `<repo>`, `<commentID>`, `<runID>`, and `<artifactID>` from the input. Preserve
the repository owner and name exactly.

For a comment URL, fetch the comment:

```bash
gh api repos/<org>/<repo>/issues/comments/<commentID>
```

Inspect `body`, `html_url`, `issue_url`, and any linked Actions run URL. The bot text is usually
generic; use it only to locate the workflow run.

For a run URL, fetch run metadata:

```bash
gh api repos/<org>/<repo>/actions/runs/<runID>
```

Record `id`, `name`, `status`, `conclusion`, `event`, `head_sha`, `workflow_id`, `run_number`,
`created_at`, `updated_at`, and `html_url`.

If the comment does not expose a run ID, search its body and related issue metadata for links
matching `/actions/runs/<runID>`. If no run can be resolved, report the missing identifier and
stop before downloading unrelated artifacts.

## Step 2 - List and Select Artifacts

List artifacts for the resolved run:

```bash
gh api repos/<org>/<repo>/actions/runs/<runID>/artifacts \
  --paginate \
  --jq '.artifacts[] | [.id, .name, .size_in_bytes, .expired] | @tsv'
```

Record the artifact ID, name, size, expiration state, and archive URL for every relevant artifact.

Prefer these artifact names:

- `opencode-db-<issue>-<runID>` - SQLite session database and sidecar files.
- `opencode-logs-<runID>-1` - `opencode.log`.

Do not infer artifact IDs from names. Use the IDs returned by the API. If an expected artifact is
missing or expired, continue with available evidence and state the gap explicitly.

## Step 3 - Download Artifacts

Create the run-specific workspace:

```bash
devi_dir="/tmp/opencode/devi-<runID>"
mkdir -p "$devi_dir"
```

Download each selected artifact using its API ID:

```bash
gh api repos/<org>/<repo>/actions/artifacts/<artifactID>/zip \
  > "$devi_dir/<artifact-name>.zip"

unzip -q "$devi_dir/<artifact-name>.zip" \
  -d "$devi_dir/<artifact-name>"
```

Keep the original ZIP files and extracted directories. Inspect extracted paths with:

```bash
find "$devi_dir" -maxdepth 5 -type f -print
```

Locate `opencode.db`, `opencode.db-wal`, `opencode.db-shm`, and related files. Treat all files
next to `opencode.db` as part of the database state.

## Step 4 - Copy the Database Before Opening

Never open the database directly from the extracted artifact directory. Copy the complete
database directory to a writable location so SQLite can replay the WAL:

```bash
db_file="$(find "$devi_dir" -type f -name opencode.db -print -quit)"
db_source_dir="$(dirname "$db_file")"
db_open_dir="$devi_dir/db-open"

mkdir -p "$db_open_dir"
cp -a "$db_source_dir"/. "$db_open_dir"/
```

Confirm that the copy contains the main database and any WAL/SHM files:

```bash
find "$db_open_dir" -maxdepth 1 -type f -printf '%f\n' | sort
```

Open the copied database with Python:

```bash
python3 -c '
import sqlite3, sys
db = sys.argv[1]
connection = sqlite3.connect(db)
tables = connection.execute(
    "SELECT name FROM sqlite_master WHERE type = '\''table'\'' ORDER BY name"
).fetchall()
print("\n".join(row[0] for row in tables))
connection.close()
' "$db_open_dir/opencode.db"
```

Inspect table columns before querying data:

```bash
python3 -c '
import sqlite3, sys
connection = sqlite3.connect(sys.argv[1])
for table in ("session", "message", "part"):
    print(f"\n[{table}]")
    try:
        for row in connection.execute(f"PRAGMA table_info({table})"):
            print(row)
    except sqlite3.Error as error:
        print(error)
connection.close()
' "$db_open_dir/opencode.db"
```

Adapt queries to the discovered schema. Do not assume column names or timestamps without checking
`PRAGMA table_info`.

## Step 5 - Inspect Session, Message, and Part Data

Extract the session record associated with the failed run or issue. Prioritize:

- Session title and directory.
- Model provider and model name.
- Session status and timestamps.
- Cost, token counts, and usage fields.
- Session ID and parent/session relationships.

Inspect `message.data` as JSON. Look for:

- User and assistant roles.
- Model/provider metadata.
- Tool-call requests.
- Tool results and errors.
- Finish reasons, interruptions, and retry information.
- Structured error fields hidden inside JSON.

Inspect `part.data` as JSON and correlate parts with their message and session IDs. Preserve
execution order. Tool calls and tool outputs show what actually happened, including malformed
arguments, command failures, permission errors, timeouts, empty outputs, and failed recovery
attempts.

Use Python to parse JSON fields rather than relying on grep against serialized database rows.
Print compact records containing IDs, timestamps, types, roles, tool names, arguments, outputs,
and error fields. Avoid dumping secrets or entire large payloads.

## Step 6 - Inspect the OpenCode Log

Locate `opencode.log` in the extracted logs artifact. Search for high-signal failures:

```bash
rg -n -i \
  'error|fail|exception|traceback|panic|timeout|denied|unauthorized|rate.?limit|exit code|killed|oom|cancel' \
  "$devi_dir"/opencode-logs-*/opencode.log
```

Read surrounding context for each match. Correlate log timestamps with message and part
timestamps. Distinguish the original failure from later cleanup, retry, cancellation, or
reporting errors.

## Step 7 - Explain the Root Cause

Produce a concise evidence-backed report containing:

1. **Input and run** - comment/run URL, repository, run ID, workflow, status, conclusion, and
   commit.
2. **Artifacts** - selected artifact names, IDs, expiration state, and missing expected files.
3. **Session evidence** - title, model, cost, token usage, status, and relevant timestamps.
4. **Execution evidence** - ordered `message.data` and `part.data` findings, especially tool
   calls and outputs.
5. **Log evidence** - exact high-signal error lines with minimal surrounding context.
6. **Failure explanation** - one causal chain connecting the first actionable failure to the final
   workflow conclusion.
7. **Confidence and gaps** - separate confirmed facts from hypotheses; identify unavailable or
   expired artifacts.
8. **Recommended next action** - concrete code, workflow, configuration, or retry investigation.

State clearly when the `devi-gdplabs` comment contains no diagnostic information. Never claim a
root cause based only on generic bot text, run conclusion, or an uncorrelated log line.

## Quality Gates

Complete the investigation only after:

- Fetching the original comment or run metadata.
- Listing artifacts and recording artifact IDs.
- Downloading every available relevant artifact.
- Copying the complete database directory, including WAL/SHM sidecars, before opening it.
- Inspecting session, `message.data`, and `part.data`.
- Searching `opencode.log` for errors and correlating timestamps.
- Explaining the failure with direct evidence.
- Reporting missing, expired, or ambiguous evidence.
- Redacting secrets from the report.
