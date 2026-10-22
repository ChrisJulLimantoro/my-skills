#!/usr/bin/env python3
"""Preview or remove recorded Devi run directories beneath /tmp/opencode."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

DEFAULT_ROOT = Path("/tmp/opencode")
RUN_MARKER_RE = re.compile(r"<!-- devi-record:run-(\d+):json")


def recorded_run_ids(report: Path) -> set[str]:
    try:
        text = report.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError(f"cannot read report: {error}") from error
    return set(RUN_MARKER_RE.findall(text))


def resolve_target(root: Path, run_id: str) -> Path:
    """Return exact allowed target, rejecting traversal and symlinks."""
    if not run_id.isdigit() or int(run_id) <= 0:
        raise ValueError(f"invalid run ID: {run_id}")
    root = root.resolve()
    target = root / f"devi-{run_id}"
    if target.is_symlink():
        raise ValueError(f"refusing symlink target: {target}")
    if target.parent.resolve() != root or target.name != f"devi-{run_id}":
        raise ValueError(f"unsafe cleanup target: {target}")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--confirm", action="store_true", help="perform deletion after preview")
    parser.add_argument("--all-recorded", action="store_true")
    parser.add_argument("run_ids", nargs="*")
    args = parser.parse_args()

    try:
        recorded = recorded_run_ids(args.report)
        if args.all_recorded and args.run_ids:
            raise ValueError("use run IDs or --all-recorded, not both")
        selected = (
            sorted(recorded, key=int)
            if args.all_recorded
            else list(dict.fromkeys(args.run_ids))
        )
        if not selected:
            raise ValueError("provide at least one run ID or --all-recorded")
        targets = []
        for run_id in selected:
            if run_id not in recorded:
                raise ValueError(f"run ID is not recorded in report: {run_id}")
            targets.append(resolve_target(DEFAULT_ROOT, run_id))
    except ValueError as error:
        parser.error(str(error))

    for target in targets:
        state = "present" if target.exists() else "absent"
        print(f"{state}: {target}")
    if not args.confirm:
        print("preview only; pass --confirm to delete present directories")
        return 0

    for target in targets:
        if target.exists():
            shutil.rmtree(target)
            print(f"deleted: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
