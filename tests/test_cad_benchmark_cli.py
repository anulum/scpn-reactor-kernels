# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — public CAD benchmark catalogue regression

"""Exercise the CAD benchmark CLI with genuine optional backend compositions."""

from __future__ import annotations

import importlib.util
import json
import math
import runpy
import sys
from pathlib import Path

import pytest

BENCHMARK = Path(__file__).resolve().parents[1] / "benchmarks" / "cad.py"
EXPECTED_OPERATIONS = (
    ("brep_build_and_manifest", "cadquery_ocp"),
    ("step_export_normalised", "cadquery_ocp"),
    ("facet_two_bodies", "cadquery_ocp"),
    ("gmsh_volume_mesh", "gmsh"),
    ("place_ring_of_bodies", "cadquery_ocp"),
    ("place_aimed_latitude", "cadquery_ocp"),
    ("assembly_body_evidence", "cadquery_ocp"),
    ("revolve_axial_profile", "cadquery_ocp"),
    ("revolve_closed_profile", "cadquery_ocp"),
    ("revolve_sphere", "cadquery_ocp"),
    ("revolve_spherical_shell", "cadquery_ocp"),
)


@pytest.mark.parametrize(("warmup", "repeats"), [(0, 1), (2, 3)])
@pytest.mark.parametrize("git_mode", ["available", "absent"])
def test_public_cli_retains_every_operation_and_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    warmup: int,
    repeats: int,
    git_mode: str,
) -> None:
    """Write all eleven rows through the real CLI in the observed environment."""
    cadquery_present = importlib.util.find_spec("cadquery") is not None
    gmsh_present = importlib.util.find_spec("gmsh") is not None
    if git_mode == "absent":
        empty_path = tmp_path / "empty-command-path"
        empty_path.mkdir()
        monkeypatch.setenv("PATH", str(empty_path))
    output = tmp_path / "nested" / "results"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(BENCHMARK),
            "--warmup",
            str(warmup),
            "--repeats",
            str(repeats),
            "--label",
            "catalogue-regression",
            "--output",
            str(output),
        ],
    )
    with pytest.raises(SystemExit) as stopped:
        runpy.run_path(str(BENCHMARK), run_name="__main__")
    assert stopped.value.code == 0
    target = output / "cad.catalogue-regression.json"
    artefact = json.loads(target.read_text(encoding="utf-8"))
    assert artefact["schema"] == "scpn-reactor-kernels.cad-benchmark.v1"
    assert artefact["label"] == "catalogue-regression"
    assert artefact["parameters"]["warmup"] == warmup
    assert artefact["parameters"]["repeats"] == repeats
    rows = artefact["results"]
    assert tuple((row["name"], row["backend"]) for row in rows) == EXPECTED_OPERATIONS
    printed = capsys.readouterr().out
    assert str(target) in printed
    for row in rows:
        available = cadquery_present and (row["backend"] != "gmsh" or gmsh_present)
        assert row["name"] in printed
        if available:
            assert row["status"] == "measured"
            stats = row["stats"]
            assert all(math.isfinite(value) and value > 0 for value in stats.values())
            assert (
                stats["min_ms_per_operation"]
                <= stats["p50_ms_per_operation"]
                <= stats["p95_ms_per_operation"]
                <= stats["p99_ms_per_operation"]
                <= stats["max_ms_per_operation"]
            )
            assert (
                stats["min_ms_per_operation"]
                <= stats["mean_ms_per_operation"]
                <= stats["max_ms_per_operation"]
            )
            assert math.isclose(
                stats["throughput_operations_per_s"],
                1e3 / stats["p50_ms_per_operation"],
                rel_tol=1e-12,
            )
        else:
            assert row["stats"] is None
            assert row["status"].startswith("unavailable:")
            assert "optional CAD back-end is not installed" in row["status"]
    if git_mode == "absent":
        assert artefact["platform"]["commit"] == "unknown"
    assert artefact["platform"]["isolated_cores"] is False
