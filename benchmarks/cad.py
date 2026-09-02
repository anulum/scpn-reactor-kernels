# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — CAD kernel benchmark

"""Benchmark the CAD kernels: B-rep build, STEP export, faceting, volume mesh.

Follows the ecosystem benchmark standard: warm-up, repeated samples,
percentiles, one row per (operation, backend), unavailable backends marked
explicitly, full provenance in the artefact. The operations are, on one
synthetic two-body assembly (a solid cylinder and an annular tube):
building the B-rep bodies and the assembly manifest, exporting the
normalised STEP bytes, faceting both bodies into closed meshes, and
meshing the STEP into tetrahedra; each sample times one operation and the
cost is reported per operation. The backends are the pinned third-party
kernels (``cadquery_ocp`` for the first three, ``gmsh`` for the last);
there is no Python-floor row because these kernels have no bit-exact
floor by design (ADR 0006). Nothing measured here is a physics or
engineering claim.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import platform
import shutil
import statistics
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

ROOT: Final = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scpn_reactor_kernels.cad._backend import backend_versions  # noqa: E402
from scpn_reactor_kernels.errors import CadUnavailableError  # noqa: E402

SCHEMA: Final = "scpn-reactor-kernels.cad-benchmark.v1"
LINEAR_DEFLECTION_M: Final = 1.0e-4
ANGULAR_DEFLECTION_RAD: Final = 0.1
CHARACTERISTIC_LENGTH_M: Final = 0.02


def operations() -> list[tuple[str, str, Callable[[], float]]]:
    """Build the timed operations on the synthetic assembly.

    Returns
    -------
    list of (name, backend, callable)
        Each callable performs one operation and returns a checksum.

    Raises
    ------
    CadUnavailableError
        If the CAD back-end is absent.
    """
    from scpn_reactor_kernels.cad import (
        BrepAssembly,
        annular_tube_brep,
        cylinder_solid_brep,
        facet_assembly,
        gmsh_volume_mesh,
        step_bytes,
    )

    def build() -> float:
        assembly = BrepAssembly(
            (
                cylinder_solid_brep(0.05, 0.0, 0.3, "inner", "electrode", "conductor"),
                annular_tube_brep(0.08, 0.1, -0.1, 0.4, "outer", "wall", "steel"),
            )
        )
        return float(len(assembly.manifest_sha256()))

    assembly = BrepAssembly(
        (
            cylinder_solid_brep(0.05, 0.0, 0.3, "inner", "electrode", "conductor"),
            annular_tube_brep(0.08, 0.1, -0.1, 0.4, "outer", "wall", "steel"),
        )
    )
    extras = {"benchmark": SCHEMA}
    step = step_bytes(assembly, extras)

    def export() -> float:
        return float(len(step_bytes(assembly, extras)))

    def facet() -> float:
        meshes = facet_assembly(assembly, LINEAR_DEFLECTION_M, ANGULAR_DEFLECTION_RAD)
        return sum(mesh.signed_volume_m3() for mesh in meshes)

    def volume_mesh() -> float:
        return gmsh_volume_mesh(step, CHARACTERISTIC_LENGTH_M).total_volume_m3

    return [
        ("brep_build_and_manifest", "cadquery_ocp", build),
        ("step_export_normalised", "cadquery_ocp", export),
        ("facet_two_bodies", "cadquery_ocp", facet),
        ("gmsh_volume_mesh", "gmsh", volume_mesh),
    ]


def measure(run: Callable[[], float], warmup: int, repeats: int) -> dict[str, float]:
    """Time repeated operations and summarise them.

    Parameters
    ----------
    run
        Operation to time.
    warmup
        Discarded leading runs.
    repeats
        Timed runs.

    Returns
    -------
    dict[str, float]
        Percentiles, mean, min, max in milliseconds per operation and the
        throughput in operations per second (P50-based).
    """
    for _ in range(warmup):
        run()
    samples: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter_ns()
        run()
        samples.append((time.perf_counter_ns() - start) / 1e6)
    ordered = sorted(samples)

    def percentile(fraction: float) -> float:
        return ordered[min(len(ordered) - 1, round(fraction * (len(ordered) - 1)))]

    p50 = percentile(0.5)
    return {
        "p50_ms_per_operation": p50,
        "p95_ms_per_operation": percentile(0.95),
        "p99_ms_per_operation": percentile(0.99),
        "mean_ms_per_operation": statistics.fmean(samples),
        "min_ms_per_operation": ordered[0],
        "max_ms_per_operation": ordered[-1],
        "throughput_operations_per_s": 1e3 / p50,
    }


def provenance() -> dict[str, Any]:
    """Collect the environment provenance of a run.

    Returns
    -------
    dict[str, Any]
        Interpreter, platform, CPU model, commit, host load and back-end versions.
    """
    cpu_model = "unknown"
    with contextlib.suppress(OSError):
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("model name"):
                cpu_model = line.split(":", 1)[1].strip()
                break
    load = "unavailable"
    with contextlib.suppress(OSError):
        load = Path("/proc/loadavg").read_text(encoding="utf-8").split()[0]
    commit = "unknown"
    git = shutil.which("git")
    if git is not None:
        with contextlib.suppress(OSError):
            commit = subprocess.run(
                [git, "rev-parse", "HEAD"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            ).stdout.strip()
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_model": cpu_model,
        "load_average_1min_at_start": load,
        "commit": commit,
        "isolated_cores": False,
        "backends": backend_versions(),
    }


def main(argv: list[str] | None = None) -> int:
    """Run the benchmark command-line interface.

    Parameters
    ----------
    argv
        Argument vector; None reads sys.argv.

    Returns
    -------
    int
        0 on completion.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--label", default="local")
    parser.add_argument("--output", type=Path, default=ROOT / "benchmarks" / "results")
    args = parser.parse_args(argv)
    results: list[dict[str, Any]] = []
    try:
        timed = operations()
    except CadUnavailableError as exc:
        for name, backend in (
            ("brep_build_and_manifest", "cadquery_ocp"),
            ("step_export_normalised", "cadquery_ocp"),
            ("facet_two_bodies", "cadquery_ocp"),
            ("gmsh_volume_mesh", "gmsh"),
        ):
            results.append(
                {
                    "name": name,
                    "backend": backend,
                    "stats": None,
                    "status": f"unavailable: {exc}",
                }
            )
    else:
        for name, backend, run in timed:
            results.append(
                {
                    "name": name,
                    "backend": backend,
                    "stats": measure(run, args.warmup, args.repeats),
                    "status": "measured",
                    "requires": "optional extra scpn-reactor-kernels[cad]",
                }
            )
    artefact = {
        "schema": SCHEMA,
        "generated_at": datetime.now(UTC).isoformat(),
        "label": args.label,
        "platform": provenance(),
        "parameters": {
            "warmup": args.warmup,
            "repeats": args.repeats,
            "linear_deflection_m": LINEAR_DEFLECTION_M,
            "angular_deflection_rad": ANGULAR_DEFLECTION_RAD,
            "characteristic_length_m": CHARACTERISTIC_LENGTH_M,
        },
        "results": results,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    target = args.output / f"cad.{args.label}.json"
    target.write_text(
        json.dumps(artefact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"benchmark: wrote {target}")
    for row in results:
        print(f"  {row['name']} [{row['backend']}]: {row['status']} {row['stats']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
