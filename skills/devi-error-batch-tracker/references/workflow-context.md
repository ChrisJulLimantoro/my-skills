# Devi and AEW workflow context

Use this map to classify where a failure occurred. It supplements artifact evidence; it never
replaces evidence from failed run.

## System boundary

`Digital Employee - Agentic Engineering Workflows` in `ai-agent-platform` receives issue comments,
repository dispatches, issue closure, or manual dispatch. Its local GitHub workflow delegates
execution to a reusable Action Hub workflow. Run metadata and referenced workflow/job data are
therefore needed to identify exact automation revision.

Devi application source lives in `digital-employee` monorepo at:

```text
gdplabs/applications/digital-employee-engineering-workflows/
```

Local checkout commonly exists at:

```text
/home/julius/glair/digital-employee/gdplabs/applications/digital-employee-engineering-workflows/
```

Treat this absolute path as a convenience, not a required or current revision.

## Runtime flow

| Layer | Responsibility | Useful evidence |
| --- | --- | --- |
| GitHub trigger | Selects event and invokes reusable workflow | Run metadata, event payload, workflow/job logs |
| Action Hub | Builds runner environment, invokes Devi, uploads artifacts | Referenced workflow revision, step logs, artifact inventory |
| Devi coordinator | Classifies supported intent, selects one GitHub target, preserves user payload | Coordinator output and application logs |
| Devi specialist | Routes durable workflow and applies OpenCode engineering workflow skill | Specialist messages, session mapping, application logs |
| OpenCode runner | Starts or resumes model session and emits NDJSON/log/SQLite state | Session, message, part tables and `opencode.log` |
| AEW command | Runs `gl-*` specification, plan, implementation, review, fix, or PR lifecycle | Tool calls, command output, AEW state and artifacts |
| Target repository | Supplies issue-specific code, tests, config, and permissions | Exact run commit, linked PR/issue, failing source/test |
| GitHub reporting | Posts one bounded result to issue or PR | API response, reporting state, final job logs |

## State model

Keep these dimensions independent:

| Dimension | Meaning |
| --- | --- |
| Durable mapping | Whether issue is unmapped, in Sentry intake, or in delivery |
| AEW state | Current workflow stage and its validated result |
| OpenCode outcome | Successful run, stale session, or terminal runner failure |
| Reporting | Owed, already reported, posted, or transport failure |

A successful OpenCode process does not prove AEW completion or GitHub reporting. Likewise, a
reporting failure does not prove repository implementation failed.

## Root-cause categories

Choose narrowest supported category: `trigger`, `action-infrastructure`, `devi-routing`,
`session-store`, `opencode-runner`, `model-or-provider`, `aew-command`, `target-repository`,
`github-reporting`, `cleanup`, or `unknown`. Name one primary cause and describe secondary effects
in causal chain.

AEW uses canonical `gl-` command names such as `gl-issue-to-pr`, `gl-plan`, `gl-implement`, and
`gl-review`. Deprecated non-prefixed aliases should not be treated as current workflow ownership.

## Revision-safe source inspection

1. Inspect trigger repository at run `head_sha`.
2. Resolve reusable workflow/action references from run or job metadata where available.
3. Inspect Devi source at revision deployed by that workflow when it can be proven.
4. Inspect target repository source only after execution evidence identifies a relevant path,
   command, test, or commit.
5. If only current source is available, label comparisons as hypotheses and lower confidence.
