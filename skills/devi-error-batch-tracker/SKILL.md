---
name: devi-error-batch-tracker
description: Investigate multiple Devi or OpenCode workflow links independently, correlate artifacts and source evidence, and maintain a local Markdown findings ledger. Use for batch Devi failure analysis or repeated tracking across workflow runs; use devi-error-link-debugging for a single report that does not need persistent tracking.
---

# Devi Error Batch Tracker

Investigate multiple `Digital Employee - Agentic Engineering Workflows` links and update one
durable local report. This skill coordinates investigations; sibling
`devi-error-link-debugging` skill remains the authority for resolving a link, downloading
artifacts, replaying the OpenCode SQLite WAL, correlating session/message/part records with
`opencode.log`, and establishing root cause.

Default report:

```text
<this-skill-directory>/output/devi-error-findings.md
```

Accept an explicit report path when user supplies one. Do not modify GitHub, workflow runs,
downloaded artifacts, or developer checkouts. Redact secrets before writing any record.

## Batch Workflow

1. Collect every supplied comment, run, artifact, or local-artifact link. Process links
   sequentially so each run's evidence and report update remain isolated.
2. Read `../devi-error-link-debugging/SKILL.md` completely, then apply its workflow and quality
   gates to each link. A generic bot comment is only a pointer, never root-cause evidence.
3. Resolve a canonical run ID when possible. Distinct run IDs from same issue are distinct
   records. Multiple inputs resolving to same run are one record with all source inputs.
4. Classify both dimensions independently:
   - `workflow_result`: `success`, `failure`, `cancelled`, `timed_out`, or `unknown`.
   - `investigation_status`: `complete`, `partial`, or `unresolved`.
5. Read [workflow context](references/workflow-context.md) when classifying failing layer or
   inspecting source. Read [report schema](references/report-schema.md) before preparing a record.
6. After each link, write one sanitized JSON record beneath that run's
   `/tmp/opencode/devi-<runID>/` directory. For an unresolved link, use a temporary file under
   `/tmp/opencode/`. Pass it to updater immediately:

   ```bash
   python3 <this-skill-directory>/scripts/update_findings.py \
     --report <report-path> \
     --record <record.json>
   ```

   Invalid records must not alter existing report. Record missing or expired evidence and
   continue with remaining links.
7. Return report path, processed/partial/unresolved counts, and retained temporary run paths.

## Source Inspection

Inspect source only when artifact evidence identifies a relevant command, stack frame, workflow
step, configuration, or commit. Prefer `git show <commit>:<path>` from a matching local checkout.
Do not fetch, pull, switch, reset, or otherwise mutate that checkout.

If required commit is unavailable locally, clone or fetch a detached exact commit into:

```text
/tmp/opencode/devi-<runID>/source/<owner>-<repo>/
```

Use trigger repository's `head_sha` for its source. Resolve reusable-workflow or action versions
from run/job metadata when possible; do not assume current `main` represents failed run. State
gap when an exact referenced revision cannot be established.

## Evidence Rules

- Quote shortest decisive log excerpt with original file and line numbers. Preserve exact text
  except secrets, which become `[REDACTED]`.
- Connect first actionable failure to retries, cleanup, reporting, and final workflow conclusion.
  Do not mistake a later symptom for cause.
- Separate confirmed facts from hypotheses. Set confidence from evidence quality.
- A successful workflow with no qualifying error uses cause `No failure detected` and says no
  decisive error line exists.
- Recommend a concrete code, workflow, configuration, permission, capacity, or retry action. If
  evidence cannot support a fix, recommend next discriminating check instead.
- Rechecking same run updates current assessment and appends a dated observation. Never erase
  prior observations.

## Cleanup Mode

Temporary evidence is retained by default. Cleanup is a separate, explicit user request. Before
deletion, confirm report was written successfully and obtain authorization for exact run IDs.
Preview first, then confirm:

```bash
python3 <this-skill-directory>/scripts/cleanup_temp.py \
  --report <report-path> <runID> [<runID> ...]

python3 <this-skill-directory>/scripts/cleanup_temp.py \
  --report <report-path> --confirm <runID> [<runID> ...]
```

Use `--all-recorded` only when user explicitly requests cleanup of every recorded run. Helper
refuses unresolved records, unrecorded IDs, symlinks, and paths outside
`/tmp/opencode/devi-<runID>/`.

## Completion Gates

- Every input produced or updated a visible record, including unresolved links.
- Every complete record passed sibling debugger's quality gates.
- Workflow result and investigation status were not conflated.
- Exact log evidence is minimal, attributed, correlated, and redacted.
- Same-issue runs remain separate; same-run observations remain historical.
- Report update completed before any optional cleanup.
