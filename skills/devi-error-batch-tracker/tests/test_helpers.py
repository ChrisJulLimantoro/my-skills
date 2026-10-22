from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = SKILL_ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


updater = load_script("update_findings")
cleanup = load_script("cleanup_temp")


def record(run_id: int | None, checked_at: str, summary: str = "Root cause summary"):
    return {
        "source_inputs": [
            f"https://github.com/GDP-ADMIN/repo/actions/runs/{run_id or 'missing'}"
        ],
        "checked_at": checked_at,
        "repository": "GDP-ADMIN/repo",
        "issue": 42,
        "run_id": run_id,
        "run_url": (
            f"https://github.com/GDP-ADMIN/repo/actions/runs/{run_id}" if run_id else ""
        ),
        "workflow_result": "failure" if run_id else "unknown",
        "investigation_status": "complete" if run_id else "unresolved",
        "cause": "aew-command: test failure" if run_id else "unknown",
        "summary": summary,
        "confidence": "high" if run_id else "low",
        "potential_solution": "Fix first failing assertion.",
        "exact_log": (
            "Authorization: Bearer secret-value\n"
            "TOKEN=secret-value\n"
            "error | failed"
        ),
        "log_source": "opencode.log:12",
        "confirmed_facts": ["Command exited 1."],
        "observation_note": "Checked artifacts.",
    }


class UpdateFindingsTests(unittest.TestCase):
    def test_distinct_runs_for_same_issue_and_recheck_history(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "findings.md"
            updater.update_report(
                report, updater.validate(record(100, "2026-09-10T10:00:00+07:00"))
            )
            updater.update_report(
                report, updater.validate(record(101, "2026-09-10T10:01:00+07:00"))
            )
            updater.update_report(
                report,
                updater.validate(
                    record(100, "2026-09-10T11:00:00+07:00", "Updated | root cause")
                ),
            )
            text = report.read_text()
            records = updater.decode_records(text)
            self.assertEqual({"run-100", "run-101"}, set(records))
            self.assertEqual(2, len(records["run-100"]["observations"]))
            self.assertIn(r"Updated \| root cause", text)

    def test_redacts_secrets_and_escapes_table_cells(self):
        validated = updater.validate(
            record(100, "2026-09-10T10:00:00+07:00", "A | B")
        )
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "findings.md"
            updater.update_report(report, validated)
            text = report.read_text()
            self.assertNotIn("secret-value", text)
            self.assertIn("[REDACTED]", text)
            self.assertIn(r"A \| B", text)

    def test_invalid_record_does_not_change_report(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "findings.md"
            report.write_text("original")
            invalid = record(100, "2026-09-10T10:00:00+07:00")
            invalid["confidence"] = "certain"
            with self.assertRaises(ValueError):
                updater.validate(invalid)
            self.assertEqual("original", report.read_text())

    def test_unresolved_input_has_stable_key(self):
        first = updater.validate(record(None, "2026-09-10T10:00:00+07:00"))
        second = updater.validate(record(None, "2026-09-10T11:00:00+07:00"))
        self.assertEqual(first["record_key"], second["record_key"])

    def test_timestamp_requires_timezone(self):
        with self.assertRaises(ValueError):
            updater.validate(record(100, "2026-09-10T10:00:00"))


class CleanupTests(unittest.TestCase):
    def test_target_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(root / "devi-123", cleanup.resolve_target(root, "123"))
            with self.assertRaises(ValueError):
                cleanup.resolve_target(root, "../123")

    def test_symlink_target_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root / "outside"
            outside.mkdir()
            (root / "devi-123").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                cleanup.resolve_target(root, "123")


if __name__ == "__main__":
    unittest.main()
