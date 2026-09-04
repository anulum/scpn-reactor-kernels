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
    "geometry_spheres",
    "geometry_placement",
    "numerics_transcendental",
    "numerics_bessel",
    "cad_brep_solids",
    "cad_step_export",
    "cad_faceting",
    "cad_volume_mesh",
    "cad_profiles",
    "cad_spheres",
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
    assert inventory["implemented_kernel_count"] == 17
    assert [k["identifier"] for k in inventory["kernels"]] == KERNEL_IDENTIFIERS
    projects = [c["project"] for c in inventory["consumers"]]
    assert len(projects) == 17
    assert projects == sorted(projects)
    levitated = next(
        row
        for row in inventory["consumers"]
        if row["project"] == "SCPN-LEVITATED-DIPOLE-CORE"
    )
    assert levitated == {
        "project": "SCPN-LEVITATED-DIPOLE-CORE",
        "version": "0.1.0.dev0",
        "source_commit": "4095aa8304974fd44d02c718d36eafc69b254944",
        "inventory_sha256": (
            "704bcca75675615fa87ff1c1debdf594f3dcdb9df17b19de48ef28046f95a303"
        ),
    }
    assert all(
        set(row) == {"project", "version", "source_commit", "inventory_sha256"}
        for row in inventory["consumers"]
    )
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


def test_explicit_device_manifests_are_authoritative(tmp_path: Path) -> None:
    """Explicit manifests replace, sort, and close the local consumer mirror."""
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    pin = {
        "version": "1.2.3",
        "source_commit": "1" * 40,
        "inventory_sha256": "2" * 64,
        "distribution": "scpn-reactor-kernels",
        "kernels": ["geometry_unit_circle"],
    }
    first.write_text(
        json.dumps({"project": "SCPN-Z-CORE", "kernel_library": pin}),
        encoding="utf-8",
    )
    second.write_text(
        json.dumps({"project": "SCPN-A-CORE", "kernel_library": pin}),
        encoding="utf-8",
    )
    rows = generate_inventory(MANIFEST, [first, second])["consumers"]
    assert [row["project"] for row in rows] == ["SCPN-A-CORE", "SCPN-Z-CORE"]
    assert all(
        set(row) == {"project", "version", "source_commit", "inventory_sha256"}
        for row in rows
    )


@pytest.mark.parametrize(
    ("payload", "fragment"),
    [
        ({"project": "", "kernel_library": {}}, "project"),
        ({"project": "SCPN-X", "kernel_library": None}, "kernel_library"),
        (
            {"project": "SCPN-X", "kernel_library": {"version": "1.0.0"}},
            "missing",
        ),
    ],
)
def test_malformed_explicit_consumer_fails(
    tmp_path: Path, payload: dict[str, object], fragment: str
) -> None:
    """Incomplete device authority cannot enter the reverse inventory."""
    device = tmp_path / "device.json"
    device.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match=fragment):
        generate_inventory(MANIFEST, [device])


def test_duplicate_explicit_projects_fail(tmp_path: Path) -> None:
    """Two manifests cannot claim one reverse-inventory project row."""
    device = tmp_path / "device.json"
    device.write_text(
        json.dumps(
            {
                "project": "SCPN-X",
                "kernel_library": {
                    "version": "1.0.0",
                    "source_commit": "1" * 40,
                    "inventory_sha256": "2" * 64,
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unique"):
        generate_inventory(MANIFEST, [device, device])


def test_invalid_local_consumer_mirror_fails(tmp_path: Path) -> None:
    """Standalone generation rejects non-list and non-closed mirror rows."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["consumers"] = "bad"
    path = tmp_path / "kernels-domain.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="must be a list"):
        generate_inventory(path)
    manifest["consumers"] = [{"project": "SCPN-X"}]
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="contain exactly"):
        generate_inventory(path)
    manifest["consumers"] = [
        {
            "project": "",
            "version": "1.0.0",
            "source_commit": "1" * 40,
            "inventory_sha256": "2" * 64,
        }
    ]
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="non-empty strings"):
        generate_inventory(path)
