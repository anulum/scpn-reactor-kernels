# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — kernel inventory generation tests

"""Contract tests for the generated public kernel inventory."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from generate_kernel_inventory import generate_inventory, main
from manifest_io import sha256_of_file

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "kernels-domain.json"
KERNEL_IDENTIFIERS = [
    "geometry_unit_circle",
    "geometry_mesh_contract",
    "geometry_primitives",
    "geometry_exports",
    "geometry_profiles",
    "geometry_placement",
    "numerics_transcendental",
    "numerics_bessel",
    "cad_brep_solids",
    "cad_step_export",
    "cad_faceting",
    "cad_volume_mesh",
    "cad_profiles",
    "cad_evidence",
    "cad_placement",
]


def test_inventory_reports_exact_kernel_set() -> None:
    """The inventory carries exactly the manifest's kernel entries."""
    inventory = generate_inventory(MANIFEST)
    assert inventory["schema"] == "scpn.kernel-inventory.v1"
    assert inventory["project"] == "SCPN-REACTOR-KERNELS"
    assert inventory["library"]["distribution"] == "scpn-reactor-kernels"
    assert inventory["evidence_maturity"] == "computational_prototype"
    assert inventory["implemented_kernel_count"] == 15
    assert [k["identifier"] for k in inventory["kernels"]] == KERNEL_IDENTIFIERS
    assert [c["project"] for c in inventory["consumers"]] == [
        "SCPN-Z-PINCH-CORE",
        "SCPN-MIRROR-CORE",
        "SCPN-DENSE-PLASMA-FOCUS-CORE",
        "SCPN-RFP-CORE",
        "SCPN-SPHEROMAK-CORE",
    ]
    assert inventory["claims"] == []
    assert inventory["source"]["manifest_sha256"] == sha256_of_file(MANIFEST)


def test_committed_inventory_is_in_sync(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The committed inventory matches a fresh generation byte for byte."""
    monkeypatch.chdir(REPO)
    assert main(["--check"]) == 0
    assert "PASS in sync" in capsys.readouterr().out


def test_write_then_check_round_trip(tmp_path: Path) -> None:
    """A written inventory immediately passes its own drift check."""
    manifest = tmp_path / "kernels-domain.json"
    shutil.copyfile(MANIFEST, manifest)
    inventory = tmp_path / "kernel-inventory.json"
    argv = ["--manifest", str(manifest), "--inventory", str(inventory)]
    assert main([*argv, "--write"]) == 0
    assert main([*argv, "--check"]) == 0


def test_manual_edit_is_reported_as_drift(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Any manual inventory edit fails the drift check."""
    manifest = tmp_path / "kernels-domain.json"
    shutil.copyfile(MANIFEST, manifest)
    inventory = tmp_path / "kernel-inventory.json"
    argv = ["--manifest", str(manifest), "--inventory", str(inventory)]
    assert main([*argv, "--write"]) == 0
    inventory.write_bytes(inventory.read_bytes() + b" ")
    assert main([*argv, "--check"]) == 1
    assert "FAIL drift" in capsys.readouterr().out


def test_missing_inventory_fails_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An absent committed inventory is a failure, not a skip."""
    argv = [
        "--manifest",
        str(MANIFEST),
        "--inventory",
        str(tmp_path / "absent.json"),
        "--check",
    ]
    assert main(argv) == 1
    assert "cannot read committed inventory" in capsys.readouterr().out


def test_non_list_kernels_fail_generation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A manifest whose kernels field is not a list is refused."""
    manifest = tmp_path / "kernels-domain.json"
    manifest.write_text(json.dumps({"kernels": "none"}), encoding="utf-8")
    argv = [
        "--manifest",
        str(manifest),
        "--inventory",
        str(tmp_path / "out.json"),
        "--check",
    ]
    assert main(argv) == 1
    assert "kernel-inventory: FAIL" in capsys.readouterr().out


def test_mode_flag_is_required() -> None:
    """Exactly one of ``--check`` or ``--write`` must be given."""
    with pytest.raises(SystemExit):
        main(["--manifest", str(MANIFEST)])
