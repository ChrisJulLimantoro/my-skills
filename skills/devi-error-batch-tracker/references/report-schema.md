# Findings record schema

Prepare one UTF-8 JSON object per investigation. Updater validates enums, normalizes lists,
redacts common secret shapes, and atomically rebuilds managed Markdown sections.

## Required fields

| Field | Type | Contract |
| --- | --- | --- |
| `source_inputs` | string array | Original comment, run, artifact, or local paths |
| `checked_at` | string | ISO-8601 timestamp with timezone |
| `repository` | string | Exact `owner/repo`, or `unknown` |
| `issue` | string or integer | Canonical issue/PR identifier, or `unknown` |
| `run_id` | string/integer/null | Positive GitHub run ID when resolved |
| `run_url` | string | Canonical Actions URL, or empty string |
| `workflow_result` | string | `success`, `failure`, `cancelled`, `timed_out`, or `unknown` |
| `investigation_status` | string | `complete`, `partial`, or `unresolved` |
| `cause` | string | Concise primary root cause/category |
| `summary` | string | LLM causal summary |
| `confidence` | string | `high`, `medium`, or `low` |
| `potential_solution` | string | Concrete fix or next discriminating check |

At least one `source_inputs` value is required. When `run_id` is null, updater derives stable
record identity from first source input, allowing unresolved links to be revisited.

## Evidence fields

These fields are optional strings or string arrays unless noted:

- `workflow_name`, `workflow_status`, `head_sha`, `created_at`, `updated_at`
- `artifacts`: array of strings or objects; objects are rendered as compact JSON
- `session_evidence`
- `confirmed_facts`
- `hypotheses`
- `exact_log`
- `log_source`
- `source_files`
- `evidence_gaps`
- `observation_note`

Use empty values rather than invented evidence. `exact_log` contains only shortest decisive
excerpt. Put line-bearing origin in `log_source`, for example
`opencode.log:481-486 (2026-09-10T03:14:22Z)`.

## Example

```json
{
  "source_inputs": ["https://github.com/ORG/REPO/actions/runs/123"],
  "checked_at": "2026-09-10T12:00:00+07:00",
  "repository": "ORG/REPO",
  "issue": 42,
  "run_id": 123,
  "run_url": "https://github.com/ORG/REPO/actions/runs/123",
  "workflow_name": "Digital Employee - Agentic Engineering Workflows",
  "workflow_result": "failure",
  "investigation_status": "complete",
  "cause": "aew-command: validation failed",
  "summary": "Implementation completed, but required validation exited non-zero.",
  "confidence": "high",
  "exact_log": "ERROR validation command exited with status 1",
  "log_source": "opencode.log:481",
  "confirmed_facts": ["Validation tool returned exit status 1."],
  "hypotheses": [],
  "evidence_gaps": [],
  "potential_solution": "Reproduce validation at recorded commit and fix first failing assertion.",
  "observation_note": "Initial artifact investigation."
}
```

Generated report contains a current index, current per-run assessment, exact log block, evidence
lists, and dated observation history. Content outside managed markers is preserved; content inside
them is regenerated.
