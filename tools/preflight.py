# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — fail-closed preflight orchestrator

"""Run every local gate of this repository and fail closed on any defect.

The gate plan mirrors ``VALIDATION.md``: lint, formatting, strict typing,
tests with complete statement and branch coverage, the kernel manifest
validator, the kernel inventory drift check, REUSE licensing lint,
workflow lint, the workflow modularity guard, and documentation link
validation. A gate whose tool is
missing fails — a missing gate is never a pass. ``--only NAME`` runs a
single gate, which the ``make docs`` target uses for the documentation
check.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

MARKDOWN_LINK: Final = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
EXTERNAL_TARGET: Final = re.compile(r"^(https?:|mailto:|#)")
SKIPPED_DIRECTORIES: Final = frozenset({".git", ".venv", "__pycache__"})


@dataclass(frozen=True, slots=True)
class GateResult:
    """Outcome of one gate run.

    Attributes
    ----------
    name
        Gate identifier from the gate plan.
    passed
        Whether the gate succeeded.
    detail
        Human-readable failure context; empty on success.
    """

    name: str
    passed: bool
    detail: str


def run_command_gate(name: str, command: list[str], root: Path) -> GateResult:
    """Run one external command gate with fail-closed semantics.

    Parameters
    ----------
    name
        Gate identifier.
    command
        Argument vector to execute.
    root
        Working directory for the command.

    Returns
    -------
    GateResult
        Failure when the command exits non-zero or cannot be executed at
        all (a missing tool is a failed gate, not a pass).
    """
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return GateResult(name, False, f"cannot execute {command[0]}: {exc}")
    if completed.returncode != 0:
        detail = (completed.stdout + completed.stderr).strip()
        return GateResult(name, False, detail or f"exit {completed.returncode}")
    return GateResult(name, True, "")


def iter_markdown_files(root: Path) -> Iterable[Path]:
    """Yield every repository Markdown file outside skipped directories.

    Parameters
    ----------
    root
        Repository root to scan.

    Yields
    ------
    Path
        Markdown files in sorted order.
    """
    for path in sorted(root.rglob("*.md")):
        if SKIPPED_DIRECTORIES.isdisjoint(path.relative_to(root).parts[:-1]):
            yield path


def check_docs(root: Path) -> list[str]:
    """Validate documentation encoding and relative link integrity.

    Parameters
    ----------
    root
        Repository root to scan.

    Returns
    -------
    list[str]
        Findings; empty when every Markdown file reads as UTF-8 and every
        relative link target exists.
    """
    findings: list[str] = []
    for path in iter_markdown_files(root):
        relative = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            findings.append(f"{relative}: unreadable: {exc}")
            continue
        for match in MARKDOWN_LINK.finditer(text):
            target = match.group(1)
            if EXTERNAL_TARGET.match(target):
                continue
            resolved = (path.parent / target.split("#", 1)[0]).resolve()
            if not resolved.exists():
                findings.append(f"{relative}: broken relative link {target!r}")
    return findings


def docs_gate(root: Path) -> GateResult:
    """Run the documentation gate.

    Parameters
    ----------
    root
        Repository root to scan.

    Returns
    -------
    GateResult
        Aggregated documentation findings.
    """
    findings = check_docs(root)
    return GateResult("docs", not findings, "; ".join(findings))


def build_gate_plan(root: Path) -> list[tuple[str, list[str] | None]]:
    """Build the ordered gate plan for one repository root.

    Parameters
    ----------
    root
        Repository root the gates run against.

    Returns
    -------
    list of (str, list[str] or None)
        Gate names with their command vectors; ``None`` marks the internal
        documentation gate.
    """
    bin_dir = root / ".venv" / "bin"
    python = str(bin_dir / "python")
    validate = [python, "tools/validate_kernels_domain.py", "kernels-domain.json"]
    return [
        ("ruff-check", [str(bin_dir / "ruff"), "check", "."]),
        ("ruff-format", [str(bin_dir / "ruff"), "format", "--check", "."]),
        (
            "mypy",
            [str(bin_dir / "mypy"), "--strict", "src", "tools", "tests", "benchmarks"],
        ),
        (
            "tests",
            [
                str(bin_dir / "pytest"),
                "-q",
                "--cov=src",
                "--cov=tools",
                "--cov-branch",
                "--cov-fail-under=100",
            ],
        ),
        ("kernels-domain", validate),
        ("kernel-inventory", [python, "tools/generate_kernel_inventory.py", "--check"]),
        ("reuse", [str(bin_dir / "reuse"), "lint"]),
        ("actionlint", ["actionlint"]),
        ("workflows", [python, "tools/audit_workflows.py"]),
        ("docs", None),
    ]


def run_gates(root: Path, only: str | None) -> int:
    """Run the gate plan and report a fail-closed aggregate.

    Parameters
    ----------
    root
        Repository root the gates run against.
    only
        Optional single gate name to run.

    Returns
    -------
    int
        ``0`` when every selected gate passes, ``1`` when any fails, ``2``
        when ``only`` names no gate.
    """
    plan = build_gate_plan(root)
    selected = [gate for gate in plan if only is None or gate[0] == only]
    if not selected:
        print(f"preflight: unknown gate {only!r}")
        return 2
    failures = 0
    for name, command in selected:
        result = (
            docs_gate(root)
            if command is None
            else run_command_gate(name, command, root)
        )
        status = "PASS" if result.passed else "FAIL"
        print(f"preflight: {status} {name}")
        if not result.passed:
            failures += 1
            print(f"  {result.detail}")
    if failures:
        print(f"preflight: FAIL gates_failed={failures}")
        return 1
    print(f"preflight: PASS gates={len(selected)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the preflight command-line interface.

    Parameters
    ----------
    argv
        Argument vector; ``None`` reads ``sys.argv``.

    Returns
    -------
    int
        Aggregate exit status from :func:`run_gates`.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = Path(__file__).resolve().parents[1]
    parser.add_argument("--root", type=Path, default=default_root)
    parser.add_argument("--only", default=None)
    args = parser.parse_args(argv)
    return run_gates(args.root, args.only)


if __name__ == "__main__":
    sys.exit(main())
