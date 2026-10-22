#!/usr/bin/env python3
"""Atomically upsert sanitized Devi investigation records into a Markdown ledger."""

from __future__ import annotations

import argparse
import fcntl
import base64
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

WORKFLOW_RESULTS = {"success", "failure", "cancelled", "timed_out", "unknown"}
INVESTIGATION_STATUSES = {"complete", "partial", "unresolved"}
CONFIDENCES = {"high", "medium", "low"}
RECORD_RE = re.compile(
    r"<!-- devi-record:(?P<key>[a-z0-9-]+):json\n"
    r"(?P<data>[A-Za-z0-9+/=\n]+?)\n-->",
    re.MULTILINE,
)
MANAGED_RE = re.compile(
    r"<!-- devi-managed:start -->.*?<!-- devi-managed:end -->", re.DOTALL
)
SECRET_PATTERNS = (
    (re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s]+"), r"\1[REDACTED]"),
    (
        re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
        "[REDACTED]",
    ),
    (re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|glpat-[A-Za-z0-9_-]{16,})\b"), "[REDACTED]"),
    (
        re.compile(
            r"(?i)\b(token|api[_-]?key|client[_-]?secret|password)\b(\s*[:=]\s*)"
            r"(?:\"[^\"]+\"|'[^']+'|[^\s,;]+)"
        ),
        r"\1\2[REDACTED]",
    ),
)


def redact(value: str) -> str:
    """Redact common credential shapes before persistence."""
    for pattern, replacement in SECRET_PATTERNS:
        value = pattern.sub(replacement, value)
    return value


def clean_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact(value.strip())
    if isinstance(value, list):
        return [clean_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): clean_value(item) for key, item in value.items()}
    return value


def string_list(value: Any, field: str) -> list[str]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field} must be an array")
    result: list[str] = []
    for item in value:
        if isinstance(item, dict):
            item = json.dumps(item, sort_keys=True, ensure_ascii=False)
        if not isinstance(item, str):
            raise ValueError(f"{field} entries must be strings or objects")
        if item.strip():
            result.append(redact(item.strip()))
    return result


def validate(raw: Any) -> dict[str, Any]:
    """Validate, normalize, redact, and assign stable record identity."""
    if not isinstance(raw, dict):
        raise ValueError("record must be a JSON object")
    record = clean_value(raw)
    required = (
        "source_inputs", "checked_at", "repository", "issue", "workflow_result",
        "investigation_status", "cause", "summary", "confidence", "potential_solution",
    )
    missing = [field for field in required if field not in record]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")

    record["source_inputs"] = string_list(record["source_inputs"], "source_inputs")
    if not record["source_inputs"]:
        raise ValueError("source_inputs must contain at least one value")
    for field in ("checked_at", "repository", "cause", "summary", "potential_solution"):
        if not isinstance(record[field], str) or not record[field].strip():
            raise ValueError(f"{field} must be a non-empty string")
    try:
        checked_at = datetime.fromisoformat(record["checked_at"])
    except ValueError as error:
        raise ValueError("checked_at must be an ISO-8601 timestamp") from error
    if checked_at.tzinfo is None or checked_at.utcoffset() is None:
        raise ValueError("checked_at must include a timezone")
    if record["workflow_result"] not in WORKFLOW_RESULTS:
        raise ValueError("invalid workflow_result")
    if record["investigation_status"] not in INVESTIGATION_STATUSES:
        raise ValueError("invalid investigation_status")
    if record["confidence"] not in CONFIDENCES:
        raise ValueError("invalid confidence")

    run_id = record.get("run_id")
    if run_id in (None, ""):
        record["run_id"] = None
        digest = hashlib.sha256(record["source_inputs"][0].encode()).hexdigest()[:12]
        record["record_key"] = f"unresolved-{digest}"
    else:
        run_text = str(run_id)
        if not run_text.isdigit() or int(run_text) <= 0:
            raise ValueError("run_id must be a positive integer or null")
        record["run_id"] = run_text
        record["record_key"] = f"run-{run_text}"

    for field in (
        "artifacts", "confirmed_facts", "hypotheses", "source_files", "evidence_gaps",
    ):
        record[field] = string_list(record.get(field), field)
    for field in (
        "run_url", "workflow_name", "workflow_status", "head_sha", "created_at",
        "updated_at", "session_evidence", "exact_log", "log_source", "observation_note",
    ):
        value = record.get(field, "")
        if value is None:
            value = ""
        if not isinstance(value, str):
            raise ValueError(f"{field} must be a string")
        record[field] = redact(value.strip())
    record["issue"] = str(record["issue"])
    return record


def decode_records(text: str) -> dict[str, dict[str, Any]]:
    """Recover structured records embedded in managed Markdown."""
    records: dict[str, dict[str, Any]] = {}
    for match in RECORD_RE.finditer(text):
        try:
            encoded = "".join(match.group("data").split())
            payload = base64.b64decode(encoded, validate=True)
            record = json.loads(payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                f"invalid embedded record {match.group('key')}: {error}"
            ) from error
        if record.get("record_key") != match.group("key"):
            raise ValueError(f"embedded record key mismatch: {match.group('key')}")
        records[match.group("key")] = record
    return records


def observation(record: dict[str, Any]) -> dict[str, str]:
    return {
        field: record.get(field, "")
        for field in (
            "checked_at", "workflow_result", "investigation_status", "cause",
            "summary", "confidence", "observation_note",
        )
    }


def merge(existing: dict[str, Any] | None, incoming: dict[str, Any]) -> dict[str, Any]:
    """Update current assessment while preserving dated observation history."""
    if existing is None:
        incoming["first_seen"] = incoming["checked_at"]
        incoming["observations"] = [observation(incoming)]
        return incoming
    if existing.get("record_key") != incoming["record_key"]:
        raise ValueError("cannot merge different record keys")
    incoming["first_seen"] = existing.get("first_seen", incoming["checked_at"])
    incoming["source_inputs"] = list(
        dict.fromkeys([*existing.get("source_inputs", []), *incoming["source_inputs"]])
    )
    observations = existing.get("observations", [])
    current = observation(incoming)
    if current not in observations:
        observations.append(current)
    incoming["observations"] = observations
    return incoming


def cell(value: Any) -> str:
    text = str(value or "").replace("|", r"\|").replace("\r", " ").replace("\n", "<br>")
    return text or "—"


def bullet_list(values: list[str]) -> str:
    return "\n".join(f"- {value}" for value in values) if values else "- None recorded."


def fenced(value: str) -> str:
    if not value:
        return "_No decisive error line was found or available._"
    fence = "````" if "```" in value else "```"
    return f"{fence}text\n{value}\n{fence}"


def record_link(record: dict[str, Any]) -> str:
    run_id = record.get("run_id")
    run_url = record.get("run_url")
    if run_id and run_url:
        return f"[{run_id}]({run_url})"
    return run_id or "unresolved"


def render_record(record: dict[str, Any]) -> str:
    payload = base64.b64encode(
        json.dumps(record, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).decode("ascii")
    observations = [
        "| Checked | Workflow | Investigation | Cause | Summary | Confidence | Note |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    history_fields = (
        "checked_at", "workflow_result", "investigation_status", "cause",
        "summary", "confidence", "observation_note",
    )
    for item in record.get("observations", []):
        observations.append(
            "| " + " | ".join(cell(item.get(field, "")) for field in history_fields) + " |"
        )
    metadata = (
        "| Field | Value |\n"
        "| --- | --- |\n"
        f"| Repository | {cell(record['repository'])} |\n"
        f"| Issue/PR | {cell(record['issue'])} |\n"
        f"| Run | {cell(record_link(record))} |\n"
        f"| Workflow | {cell(record.get('workflow_name'))} |\n"
        f"| Workflow status | {cell(record.get('workflow_status'))} |\n"
        f"| Workflow result | {cell(record['workflow_result'])} |\n"
        f"| Investigation | {cell(record['investigation_status'])} |\n"
        f"| Commit | {cell(record.get('head_sha'))} |\n"
        f"| First seen | {cell(record.get('first_seen'))} |\n"
        f"| Last checked | {cell(record['checked_at'])} |\n"
        f"| Confidence | {cell(record['confidence'])} |"
    )
    title = f"{record['repository']} {record['issue']} — Run {record_link(record)}"
    history = "\n".join(observations)
    return f"""<!-- devi-record:{record['record_key']}:start -->
## {title}

{metadata}

### Current assessment

**Cause:** {record['cause']}

**LLM summary:** {record['summary']}

**Potential solution:** {record['potential_solution']}

**Session evidence:** {record.get('session_evidence') or 'None recorded.'}

### Exact decisive log

Source: {record.get('log_source') or 'Unavailable'}

{fenced(record.get('exact_log', ''))}

### Evidence

**Inputs**

{bullet_list(record['source_inputs'])}

**Artifacts**

{bullet_list(record['artifacts'])}

**Confirmed facts**

{bullet_list(record['confirmed_facts'])}

**Hypotheses**

{bullet_list(record['hypotheses'])}

**Source files inspected**

{bullet_list(record['source_files'])}

**Evidence gaps**

{bullet_list(record['evidence_gaps'])}

### Observation history

{history}

<!-- devi-record:{record['record_key']}:json
{payload}
-->
<!-- devi-record:{record['record_key']}:end -->"""


def sort_key(record: dict[str, Any]) -> tuple[str, int, str]:
    run_id = record.get("run_id")
    return (record.get("repository", ""), int(run_id) if run_id else -1, record["record_key"])


def render_managed(records: dict[str, dict[str, Any]]) -> str:
    ordered = sorted(records.values(), key=sort_key)
    lines = [
        "<!-- devi-managed:start -->",
        "## Run index",
        "",
        "| Issue | Run | Workflow result | Investigation | Cause | LLM summary "
        "| Confidence | Last checked |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    index_fields = (
        "workflow_result", "investigation_status", "cause",
        "summary", "confidence", "checked_at",
    )
    for record in ordered:
        values = [
            cell(f"{record['repository']}#{record['issue']}"),
            cell(record_link(record)),
            *(cell(record[field]) for field in index_fields),
        ]
        lines.append("| " + " | ".join(values) + " |")
    lines.extend(("", "## Run details", ""))
    lines.append("\n\n".join(render_record(record) for record in ordered))
    lines.extend(("", "<!-- devi-managed:end -->"))
    return "\n".join(lines)


def update_report(report: Path, incoming: dict[str, Any]) -> None:
    """Serialize report upserts so concurrent agents cannot lose each other’s records."""
    report.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = report.with_name(f".{report.name}.lock")
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        _update_report_unlocked(report, incoming)


def _update_report_unlocked(report: Path, incoming: dict[str, Any]) -> None:
    """Validate all prior state, then replace report atomically."""
    original = report.read_text(encoding="utf-8") if report.exists() else ""
    records = decode_records(original)
    records[incoming["record_key"]] = merge(records.get(incoming["record_key"]), incoming)
    managed = render_managed(records)
    if MANAGED_RE.search(original):
        updated = MANAGED_RE.sub(lambda _match: managed, original, count=1)
    else:
        prefix = original.rstrip()
        if not prefix:
            prefix = (
                "# Devi Error Findings\n\n"
                "This local ledger is maintained by `devi-error-batch-tracker`. "
                "Managed sections are regenerated; secrets are redacted."
            )
        updated = f"{prefix}\n\n{managed}\n"

    report.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{report.name}.", dir=report.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write(updated)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, report)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--record", required=True, type=Path)
    args = parser.parse_args()
    try:
        raw = json.loads(args.record.read_text(encoding="utf-8"))
        record = validate(raw)
        update_report(args.report, record)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    print(f"updated {args.report} ({record['record_key']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
