# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — workflow modularity guard tests

"""Exercise every fail-closed branch of the workflow modularity guard."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from audit_workflows import audit, main

REPO = Path(__file__).resolve().parent.parent
INVENTORY = ".github/workflow-inventory.json"
WORKFLOWS = ".github/workflows"


def _tree(tmp_path: Path) -> Path:
    """Copy the committed workflow surface into a scratch repository root.

    Parameters
    ----------
    tmp_path
        Pytest-provided scratch directory.

    Returns
    -------
    Path
        Root of the copied surface.
    """
    root = tmp_path / "repo"
    (root / ".github").mkdir(parents=True)
    shutil.copytree(REPO / WORKFLOWS, root / WORKFLOWS)
    shutil.copy(REPO / INVENTORY, root / INVENTORY)
    return root


def _mutate_inventory(root: Path, **overrides: Any) -> None:
    """Rewrite top-level inventory fields in place.

    Parameters
    ----------
    root
        Scratch repository root.
    **overrides
        Top-level fields to replace.
    """
    path = root / INVENTORY
    record = json.loads(path.read_text(encoding="utf-8"))
    record.update(overrides)
    path.write_text(json.dumps(record), encoding="utf-8")


def _edit(root: Path, name: str, old: str, new: str) -> None:
    """Apply one exact textual substitution to a workflow file.

    Parameters
    ----------
    root
        Scratch repository root.
    name
        Workflow file name.
    old
        Exact text to replace (must be present).
    new
        Replacement text.
    """
    path = root / WORKFLOWS / name
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_committed_tree_is_compliant() -> None:
    """The committed workflow surface passes its own guard."""
    assert audit(REPO) == []


def test_main_reports_pass_for_committed_tree(capsys: Any) -> None:
    """The command-line entry point reports PASS for the committed tree."""
    assert main([str(REPO)]) == 0
    assert "workflow-audit: PASS" in capsys.readouterr().out


def test_main_defaults_to_working_directory(capsys: Any, monkeypatch: Any) -> None:
    """Without arguments the guard audits the current working directory."""
    monkeypatch.chdir(REPO)
    assert main([]) == 0
    capsys.readouterr()


def test_main_fails_closed_without_inventory(tmp_path: Path, capsys: Any) -> None:
    """A missing inventory is a failure, never a pass."""
    assert main([str(tmp_path)]) == 1
    assert "inventory unreadable" in capsys.readouterr().out


def test_wrong_schema_and_version_are_rejected(tmp_path: Path) -> None:
    """Schema identifier and version are pinned."""
    root = _tree(tmp_path)
    _mutate_inventory(root, schema="other", schema_version="9.9.9")
    errors = audit(root)
    assert any("wrong schema identifier" in error for error in errors)
    assert any("wrong schema_version" in error for error in errors)


def test_undeclared_workflow_file_is_rejected(tmp_path: Path) -> None:
    """Every workflow file must be declared exactly once."""
    root = _tree(tmp_path)
    (root / WORKFLOWS / "stray.yml").write_text("name: stray\n", encoding="utf-8")
    errors = audit(root)
    assert any("differ from tree" in error for error in errors)


def test_unknown_kind_and_category_are_rejected(tmp_path: Path) -> None:
    """Kind and category vocabulary is closed."""
    root = _tree(tmp_path)
    path = root / INVENTORY
    record = json.loads(path.read_text(encoding="utf-8"))
    record["workflows"][3]["kind"] = "mystery"
    record["workflows"][3]["category"] = 99
    path.write_text(json.dumps(record), encoding="utf-8")
    errors = audit(root)
    assert any("unknown kind" in error for error in errors)
    assert any("outside the taxonomy" in error for error in errors)
    assert any("must partition 1..11" in error for error in errors)


def test_size_ceilings_fail_closed(tmp_path: Path) -> None:
    """Byte and line ceilings bound every workflow file."""
    root = _tree(tmp_path)
    _mutate_inventory(root, size_limits={"max_lines": 1, "max_bytes": 1})
    errors = audit(root)
    assert any("exceeds byte ceiling" in error for error in errors)
    assert any("exceeds line ceiling" in error for error in errors)


def test_yaml_parse_failure_is_reported(tmp_path: Path) -> None:
    """A syntactically broken workflow is a finding, not a crash."""
    root = _tree(tmp_path)
    (root / WORKFLOWS / "docs.yml").write_text("jobs: [::\n", encoding="utf-8")
    errors = audit(root)
    assert any("YAML parse failure" in error for error in errors)


def test_missing_jobs_mapping_is_rejected(tmp_path: Path) -> None:
    """A workflow without a jobs mapping is rejected."""
    root = _tree(tmp_path)
    (root / WORKFLOWS / "docs.yml").write_text("name: Docs\n", encoding="utf-8")
    errors = audit(root)
    assert any("no jobs mapping" in error for error in errors)


def test_job_set_drift_is_rejected(tmp_path: Path) -> None:
    """Declared and real job names must match exactly."""
    root = _tree(tmp_path)
    _edit(root, "docs.yml", "  validate:", "  renamed:")
    errors = audit(root)
    assert any("differ from declared" in error for error in errors)


def test_reusable_must_expose_only_workflow_call(tmp_path: Path) -> None:
    """A reusable workflow must not carry direct triggers."""
    root = _tree(tmp_path)
    _edit(root, "reusable-tests.yml", "on:\n  workflow_call:", "on:\n  push:")
    errors = audit(root)
    assert any("must expose only workflow_call" in error for error in errors)


def test_only_reusables_may_expose_workflow_call(tmp_path: Path) -> None:
    """A standalone workflow must not be callable."""
    root = _tree(tmp_path)
    _edit(root, "docs.yml", "on:\n  push:", "on:\n  workflow_call:\n  push:")
    errors = audit(root)
    assert any("only reusable workflows may expose" in error for error in errors)


def test_scalar_trigger_is_normalised(tmp_path: Path) -> None:
    """A scalar ``on:`` value is treated as one trigger name."""
    root = _tree(tmp_path)
    _edit(
        root,
        "docs.yml",
        "on:\n  push:\n  pull_request:\n  workflow_dispatch:",
        "on: push",
    )
    assert audit(root) == []


def test_quoted_on_key_is_recognised(tmp_path: Path) -> None:
    """A quoted ``"on"`` key resolves like the bare boolean form."""
    root = _tree(tmp_path)
    _edit(
        root,
        "docs.yml",
        "on:\n  push:\n  pull_request:\n  workflow_dispatch:",
        '"on":\n  push:',
    )
    assert audit(root) == []


def test_cross_category_needs_are_rejected(tmp_path: Path) -> None:
    """Only the coordinator may declare job dependencies."""
    root = _tree(tmp_path)
    _edit(root, "docs.yml", "  validate:\n", "  validate:\n    needs: []\n")
    errors = audit(root)
    assert any("cross-category needs" in error for error in errors)


def test_unpinned_action_is_rejected(tmp_path: Path) -> None:
    """Every third-party action must be pinned to a full commit SHA."""
    root = _tree(tmp_path)
    _edit(
        root,
        "docs.yml",
        "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
        "actions/checkout@v7",
    )
    errors = audit(root)
    assert any("unpinned action reference" in error for error in errors)


def test_coordinator_extra_top_key_is_rejected(tmp_path: Path) -> None:
    """The coordinator carries only policy, calls and the gate."""
    root = _tree(tmp_path)
    _edit(root, "ci.yml", "name: CI\n", "name: CI\nenv:\n  STRAY: value\n")
    errors = audit(root)
    assert any("unexpected top-level keys" in error for error in errors)


def test_coordinator_call_job_must_use_local_reusable(tmp_path: Path) -> None:
    """A coordinator call job must reference a same-repository reusable."""
    root = _tree(tmp_path)
    _edit(
        root,
        "ci.yml",
        "    uses: ./.github/workflows/reusable-tests.yml",
        "    uses: other/repo/.github/workflows/x.yml"
        "@0000000000000000000000000000000000000000",
    )
    errors = audit(root)
    assert any("is not a local reusable call" in error for error in errors)
    assert any(
        "differ from\ndeclared reusables".replace("\n", " ") in error
        for error in errors
    )


def test_coordinator_call_job_must_not_embed_steps(tmp_path: Path) -> None:
    """A coordinator call job must not carry inline steps."""
    root = _tree(tmp_path)
    _edit(
        root,
        "ci.yml",
        "    uses: ./.github/workflows/reusable-tests.yml\n",
        "    uses: ./.github/workflows/reusable-tests.yml\n    steps: []\n",
    )
    errors = audit(root)
    assert any("must not embed steps" in error for error in errors)


def test_gate_must_exist(tmp_path: Path) -> None:
    """The aggregate gate job is mandatory."""
    root = _tree(tmp_path)
    _edit(root, "ci.yml", "  gate:", "  gatex:")
    errors = audit(root)
    assert any("aggregate gate job missing" in error for error in errors)


def test_gate_needs_every_category(tmp_path: Path) -> None:
    """The gate must depend on every category call exactly once."""
    root = _tree(tmp_path)
    _edit(root, "ci.yml", "    needs: [static-policy, tests]", "    needs: [tests]")
    errors = audit(root)
    assert any("gate must need every category call" in error for error in errors)


def test_gate_must_run_always(tmp_path: Path) -> None:
    """The gate must run even when a category fails or is cancelled."""
    root = _tree(tmp_path)
    _edit(root, "ci.yml", "    if: always()", "    if: success()")
    errors = audit(root)
    assert any("if: always()" in error for error in errors)


def test_gate_script_must_fail_closed(tmp_path: Path) -> None:
    """The gate script must inspect results and exit non-zero on defect."""
    root = _tree(tmp_path)
    _edit(root, "ci.yml", "              exit 1", "              true")
    errors = audit(root)
    assert any("fail closed on any non-success result" in error for error in errors)


def test_exactly_one_coordinator_is_required(tmp_path: Path) -> None:
    """Zero or two coordinators are both rejected."""
    root = _tree(tmp_path)
    path = root / INVENTORY
    record = json.loads(path.read_text(encoding="utf-8"))
    record["workflows"][1]["kind"] = "coordinator"
    path.write_text(json.dumps(record), encoding="utf-8")
    errors = audit(root)
    assert any("exactly one coordinator" in error for error in errors)


def test_unparsed_coordinator_skips_contract_check(tmp_path: Path) -> None:
    """A coordinator that fails YAML parsing reports only the parse error."""
    root = _tree(tmp_path)
    (root / WORKFLOWS / "ci.yml").write_text("jobs: [::\n", encoding="utf-8")
    errors = audit(root)
    assert any("YAML parse failure" in error for error in errors)
    assert not any("aggregate gate job missing" in error for error in errors)
