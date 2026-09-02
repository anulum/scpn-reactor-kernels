# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — preflight orchestrator tests

"""Contract tests for the fail-closed preflight orchestrator."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from preflight import (
    build_gate_plan,
    check_docs,
    docs_gate,
    iter_markdown_files,
    main,
    run_command_gate,
    run_gates,
)

REPO = Path(__file__).resolve().parents[1]


def test_run_command_gate_passes_on_zero_exit(tmp_path: Path) -> None:
    """A zero-exit command yields a passing gate result."""
    result = run_command_gate("ok", [sys.executable, "-c", "pass"], tmp_path)
    assert result.passed
    assert result.detail == ""


def test_run_command_gate_captures_failure_output(tmp_path: Path) -> None:
    """A non-zero command fails and carries the tool output."""
    command = [sys.executable, "-c", "print('broken'); raise SystemExit(3)"]
    result = run_command_gate("bad", command, tmp_path)
    assert not result.passed
    assert "broken" in result.detail


def test_run_command_gate_silent_failure_reports_exit_code(tmp_path: Path) -> None:
    """A silent non-zero command still reports its exit status."""
    command = [sys.executable, "-c", "raise SystemExit(4)"]
    result = run_command_gate("silent", command, tmp_path)
    assert not result.passed
    assert result.detail == "exit 4"


def test_run_command_gate_fails_closed_on_missing_tool(tmp_path: Path) -> None:
    """A missing executable is a failed gate, never a pass."""
    result = run_command_gate("absent", [str(tmp_path / "no-such-tool")], tmp_path)
    assert not result.passed
    assert "cannot execute" in result.detail


def test_iter_markdown_files_skips_internal_directories(tmp_path: Path) -> None:
    """Markdown under ``.venv`` and ``.git`` is not documentation."""
    (tmp_path / "README.md").write_text("root", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "vendored.md").write_text("skip", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "notes.md").write_text("skip", encoding="utf-8")
    found = [path.name for path in iter_markdown_files(tmp_path)]
    assert found == ["README.md"]


def test_check_docs_accepts_valid_links(tmp_path: Path) -> None:
    """External, anchor, and resolvable relative links all pass."""
    (tmp_path / "target.md").write_text("target", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "[ext](https://example.org) [anchor](#top) [rel](target.md)",
        encoding="utf-8",
    )
    assert check_docs(tmp_path) == []


def test_check_docs_reports_broken_relative_link(tmp_path: Path) -> None:
    """A relative link to a missing file is a finding."""
    (tmp_path / "README.md").write_text("[gone](missing.md)", encoding="utf-8")
    findings = check_docs(tmp_path)
    assert len(findings) == 1
    assert "broken relative link" in findings[0]


def test_check_docs_reports_unreadable_file(tmp_path: Path) -> None:
    """A Markdown file that is not UTF-8 is a finding."""
    (tmp_path / "README.md").write_bytes(b"\xff\xfe broken")
    findings = check_docs(tmp_path)
    assert len(findings) == 1
    assert "unreadable" in findings[0]


def test_docs_gate_wraps_findings(tmp_path: Path) -> None:
    """The documentation gate passes and fails on the same evidence."""
    (tmp_path / "README.md").write_text("clean", encoding="utf-8")
    assert docs_gate(tmp_path).passed
    (tmp_path / "README.md").write_text("[gone](missing.md)", encoding="utf-8")
    assert not docs_gate(tmp_path).passed


def test_repository_documentation_is_link_clean() -> None:
    """Every relative link in this repository's documentation resolves."""
    assert check_docs(REPO) == []


def test_gate_plan_covers_every_validation_surface(tmp_path: Path) -> None:
    """The plan names every gate from VALIDATION.md exactly once."""
    names = [name for name, _ in build_gate_plan(tmp_path)]
    assert names == [
        "ruff-check",
        "ruff-format",
        "mypy",
        "tests",
        "kernels-domain",
        "kernel-inventory",
        "reuse",
        "actionlint",
        "workflows",
        "docs",
    ]


def test_gate_plan_validator_carries_the_kernel_manifest(tmp_path: Path) -> None:
    """The validator gate names the kernel manifest and no other file."""
    command = dict(build_gate_plan(tmp_path))["kernels-domain"]
    assert command is not None
    assert command[1:] == ["tools/validate_kernels_domain.py", "kernels-domain.json"]


def test_run_gates_only_docs_pass_and_fail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Running a single gate reports PASS with 0 and FAIL with 1."""
    (tmp_path / "README.md").write_text("clean", encoding="utf-8")
    assert run_gates(tmp_path, "docs") == 0
    assert "preflight: PASS gates=1" in capsys.readouterr().out
    (tmp_path / "README.md").write_text("[gone](missing.md)", encoding="utf-8")
    assert run_gates(tmp_path, "docs") == 1
    output = capsys.readouterr().out
    assert "preflight: FAIL gates_failed=1" in output
    assert "broken relative link" in output


def test_run_gates_rejects_unknown_gate(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unknown gate name is a usage error, not a silent pass."""
    assert run_gates(tmp_path, "no-such-gate") == 2
    assert "unknown gate" in capsys.readouterr().out


def test_run_gates_full_plan_fails_closed_without_toolchain(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A root without its pinned toolchain fails every command gate."""
    (tmp_path / "README.md").write_text("clean", encoding="utf-8")
    assert run_gates(tmp_path, None) == 1
    output = capsys.readouterr().out
    assert "FAIL ruff-check" in output
    assert "PASS docs" in output


def test_main_runs_selected_gate(capsys: pytest.CaptureFixture[str]) -> None:
    """The command-line interface wires ``--root`` and ``--only``."""
    assert main(["--root", str(REPO), "--only", "docs"]) == 0
    assert "preflight: PASS gates=1" in capsys.readouterr().out
