# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — workflow modularity guard

"""Fail closed when the workflow definitions drift from their inventory.

Workflow YAML is governance code. This guard proves the distributed
workflow layout against the versioned machine-readable inventory
``.github/workflow-inventory.json``: every workflow file and every job is
declared and owned exactly once under one responsibility category; the
coordinator carries only trigger policy, reusable calls and one stable
fail-closed aggregate gate; reusable workflows expose only their call
surface; every third-party action is pinned to a full commit SHA; file
sizes stay inside repository policy limits. Any violation exits ``1``.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Final

import yaml

INVENTORY_RELATIVE: Final = ".github/workflow-inventory.json"
WORKFLOWS_RELATIVE: Final = ".github/workflows"
INVENTORY_SCHEMA: Final = "scpn.workflow-inventory.v1"
INVENTORY_SCHEMA_VERSION: Final = "1.0.0"
PINNED_USES: Final = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")
LOCAL_USES_PREFIX: Final = "./.github/workflows/"
KINDS: Final = frozenset({"coordinator", "reusable", "standalone"})
COORDINATOR_TOP_KEYS: Final = frozenset(
    {"name", True, "permissions", "concurrency", "jobs"}
)
GATE_JOB: Final = "gate"


def _entry_uses(job: dict[str, Any]) -> list[str]:
    """Collect every ``uses:`` reference of one job.

    Parameters
    ----------
    job
        Parsed job mapping from a workflow file.

    Returns
    -------
    list of str
        Job-level and step-level ``uses:`` values, in file order.
    """
    uses: list[str] = []
    job_uses = job.get("uses")
    if isinstance(job_uses, str):
        uses.append(job_uses)
    for step in job.get("steps") or []:
        step_uses = step.get("uses")
        if isinstance(step_uses, str):
            uses.append(step_uses)
    return uses


def _check_file_shape(
    entry: dict[str, Any], parsed: dict[Any, Any], errors: list[str]
) -> None:
    """Check one workflow file against its inventory entry.

    Parameters
    ----------
    entry
        Inventory entry for the file.
    parsed
        Parsed workflow document.
    errors
        Violation sink; findings are appended in place.
    """
    file = entry["file"]
    jobs = parsed.get("jobs")
    if not isinstance(jobs, dict):
        errors.append(f"{file}: no jobs mapping")
        return
    if sorted(jobs) != sorted(entry["jobs"]):
        errors.append(
            f"{file}: jobs {sorted(jobs)} differ from declared {sorted(entry['jobs'])}"
        )
    triggers = parsed.get(True) or parsed.get("on") or {}
    trigger_names = set(triggers) if isinstance(triggers, dict) else {str(triggers)}
    if entry["kind"] == "reusable":
        if trigger_names != {"workflow_call"}:
            errors.append(f"{file}: reusable must expose only workflow_call")
    elif "workflow_call" in trigger_names:
        errors.append(f"{file}: only reusable workflows may expose workflow_call")
    for job_name, job in jobs.items():
        if entry["kind"] != "coordinator" and "needs" in job:
            errors.append(f"{file}: job {job_name} declares cross-category needs")
        for used in _entry_uses(job):
            if used.startswith(LOCAL_USES_PREFIX):
                continue
            if not PINNED_USES.match(used):
                errors.append(f"{file}: unpinned action reference {used!r}")


def _check_coordinator(
    parsed: dict[Any, Any], reusable_files: set[str], errors: list[str]
) -> None:
    """Check the coordinator contract.

    Parameters
    ----------
    parsed
        Parsed coordinator document.
    reusable_files
        Inventory-declared reusable workflow file names.
    errors
        Violation sink; findings are appended in place.
    """
    extra = set(parsed) - COORDINATOR_TOP_KEYS
    if extra:
        errors.append(
            f"coordinator: unexpected top-level keys {sorted(map(str, extra))}"
        )
    jobs: dict[str, Any] = parsed.get("jobs", {})
    call_jobs: set[str] = set()
    called_files: list[str] = []
    for job_name, job in jobs.items():
        if job_name == GATE_JOB:
            continue
        call_jobs.add(job_name)
        used = job.get("uses")
        if not isinstance(used, str) or not used.startswith(LOCAL_USES_PREFIX):
            errors.append(f"coordinator: job {job_name} is not a local reusable call")
            continue
        called_files.append(used.removeprefix(LOCAL_USES_PREFIX))
        if "steps" in job:
            errors.append(f"coordinator: call job {job_name} must not embed steps")
    if sorted(called_files) != sorted(reusable_files):
        errors.append(
            f"coordinator: calls {sorted(called_files)} differ from "
            f"declared reusables {sorted(reusable_files)}"
        )
    gate = jobs.get(GATE_JOB)
    if not isinstance(gate, dict):
        errors.append("coordinator: aggregate gate job missing")
        return
    if set(gate.get("needs") or []) != call_jobs:
        errors.append("coordinator: gate must need every category call exactly once")
    if str(gate.get("if", "")).strip() != "always()":
        errors.append("coordinator: gate must run with if: always()")
    script = json.dumps(gate.get("steps", []))
    if "needs." not in script or "result" not in script or "exit 1" not in script:
        errors.append("coordinator: gate must fail closed on any non-success result")


def audit(root: Path) -> list[str]:
    """Audit the workflow tree of one repository root.

    Parameters
    ----------
    root
        Repository root containing ``.github``.

    Returns
    -------
    list of str
        Every violation found; empty when the tree is compliant.
    """
    errors: list[str] = []
    inventory_path = root / INVENTORY_RELATIVE
    workflows_dir = root / WORKFLOWS_RELATIVE
    try:
        inventory: dict[str, Any] = json.loads(
            inventory_path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as error:
        return [f"inventory unreadable: {error}"]
    if inventory.get("schema") != INVENTORY_SCHEMA:
        errors.append("inventory: wrong schema identifier")
    if inventory.get("schema_version") != INVENTORY_SCHEMA_VERSION:
        errors.append("inventory: wrong schema_version")
    entries: list[dict[str, Any]] = inventory.get("workflows", [])
    declared = {entry["file"] for entry in entries}
    present = {path.name for path in sorted(workflows_dir.glob("*.yml"))}
    if declared != present:
        errors.append(
            f"inventory files {sorted(declared)} differ from tree {sorted(present)}"
        )
        return errors
    categories: list[int] = []
    coordinators: list[str] = []
    reusable_files: set[str] = set()
    limits: dict[str, int] = inventory["size_limits"]
    parsed_by_file: dict[str, dict[Any, Any]] = {}
    for entry in entries:
        file = entry["file"]
        if entry["kind"] not in KINDS:
            errors.append(f"{file}: unknown kind {entry['kind']!r}")
        category = entry["category"]
        categories.append(category)
        if not (isinstance(category, int) and 1 <= category <= 11):
            errors.append(f"{file}: category outside the taxonomy")
        if entry["kind"] == "coordinator":
            coordinators.append(file)
        if entry["kind"] == "reusable":
            reusable_files.add(file)
        raw = (workflows_dir / file).read_bytes()
        if len(raw) > limits["max_bytes"]:
            errors.append(f"{file}: exceeds byte ceiling")
        if raw.count(b"\n") > limits["max_lines"]:
            errors.append(f"{file}: exceeds line ceiling")
        try:
            parsed = yaml.safe_load(raw.decode("utf-8"))
        except yaml.YAMLError as error:
            errors.append(f"{file}: YAML parse failure: {error}")
            continue
        parsed_by_file[file] = parsed
        _check_file_shape(entry, parsed, errors)
    used = set(categories)
    omitted = set(inventory.get("omitted_categories", []))
    if used & omitted or used | omitted != set(range(1, 12)):
        errors.append("inventory: categories and omissions must partition 1..11")
    if len(coordinators) != 1:
        errors.append("inventory: exactly one coordinator is required")
    elif coordinators[0] in parsed_by_file:
        _check_coordinator(parsed_by_file[coordinators[0]], reusable_files, errors)
    return errors


def main(argv: list[str]) -> int:
    """Run the guard from the command line.

    Parameters
    ----------
    argv
        Command-line arguments after the program name; an optional
        repository root (defaults to the current working directory).

    Returns
    -------
    int
        ``0`` when compliant, ``1`` when any violation exists.
    """
    root = Path(argv[0]) if argv else Path.cwd()
    errors = audit(root)
    for error in errors:
        print(f"workflow-audit: FAIL {error}")
    if errors:
        return 1
    print("workflow-audit: PASS modular inventory verified")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
