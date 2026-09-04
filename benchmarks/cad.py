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
meshing the STEP into tetrahedra, placing a ring of twelve identical rods
off the axis, and placing a latitude of ten identical rods on a sphere with
each one turned to point at its centre; each sample times one operation and
the
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
import math
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
RING_COUNT: Final = 12
RING_RADIUS_M: Final = 0.1
#: One latitude of bodies on a sphere, each aimed at its centre, so the
#: pass also measures the aimed placement of ADR 0018: count, sphere
#: radius and polar angle in degrees. The angle is deliberately not a
#: rational multiple of a turn.
SPHERE_ARRAY_COUNT: Final = 10
SPHERE_ARRAY_RADIUS_M: Final = 1.5
SPHERE_ARRAY_POLAR_DEG: Final = 59.0
#: The identity twist of a ring, as a circle point.
NO_TWIST: Final = (1.0, 0.0)
EVIDENCE_SEGMENTS: Final = 64
#: Polar steps of the spherical bodies. Sixteen is the count the
#: library's own sphere tests use, so the benchmark measures the same body.
SPHERE_RINGS: Final = 16
#: One five-sample narrow-wide-narrow profile for the revolution row.
WAIST: Final = (
    (0.0, 0.0225),
    (0.5, 0.06),
    (0.98, 0.1),
    (1.46, 0.06),
    (1.96, 0.0225),
)
#: One body that closes on the axis at both poles, so the pass also
#: measures the revolve path that appends no axis return point:
#: ``r(z) = a sqrt(1 - |z / b|^2)`` at seven samples.
SEPARATRIX: Final = (
    (-0.15, 0.0),
    (-0.1125, 0.02 * math.sqrt(1.0 - 0.75**2)),
    (-0.075, 0.02 * math.sqrt(1.0 - 0.5**2)),
    (0.0, 0.02),
    (0.075, 0.02 * math.sqrt(1.0 - 0.5**2)),
    (0.1125, 0.02 * math.sqrt(1.0 - 0.75**2)),
    (0.15, 0.0),
)


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
        assembly_evidence,
        closed_profiled_solid_brep,
        cylinder_solid_brep,
        facet_assembly,
        gmsh_volume_mesh,
        profiled_solid_brep,
        ring_brep_bodies,
        sphere_brep,
        sphere_ring_brep_bodies,
        spherical_shell_brep,
        step_bytes,
    )
    from scpn_reactor_kernels.geometry import (
        TriangleMesh,
        annular_tube,
        circle_point,
        cylinder_solid,
        inward_aim,
        radians_from_degrees,
        ring_azimuths,
        ring_offsets,
        sphere_ring_offsets,
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

    faceted = facet_assembly(assembly, LINEAR_DEFLECTION_M, ANGULAR_DEFLECTION_RAD)
    cylinder_vertices, cylinder_faces = cylinder_solid(
        0.05, 0.0, 0.3, EVIDENCE_SEGMENTS
    )
    tube_vertices, tube_faces = annular_tube(0.08, 0.1, -0.1, 0.4, EVIDENCE_SEGMENTS)
    reference_meshes = (
        TriangleMesh(
            name="inner",
            role="electrode",
            material_identifier="conductor",
            vertices=cylinder_vertices,
            faces=cylinder_faces,
        ),
        TriangleMesh(
            name="outer",
            role="wall",
            material_identifier="steel",
            vertices=tube_vertices,
            faces=tube_faces,
        ),
    )

    def evidence() -> float:
        checked = assembly_evidence(
            assembly.bodies,
            (0.05, 0.08),
            faceted,
            reference_meshes,
            LINEAR_DEFLECTION_M,
            EVIDENCE_SEGMENTS,
        )
        return sum(item.volume_relative_error for item in checked)

    def revolve_profile() -> float:
        body = profiled_solid_brep(WAIST, "waist", "synthetic", "synthetic")
        return body.volume_m3

    def revolve_closed_profile() -> float:
        body = closed_profiled_solid_brep(
            SEPARATRIX, "separatrix", "synthetic", "synthetic"
        )
        return body.volume_m3

    def revolve_sphere() -> float:
        body = sphere_brep(0.1, 0.0, SPHERE_RINGS, "sphere", "synthetic", "synthetic")
        return body.volume_m3

    def revolve_spherical_shell() -> float:
        body = spherical_shell_brep(
            0.06, 0.1, 0.0, SPHERE_RINGS, "shell", "synthetic", "synthetic"
        )
        return body.volume_m3

    rod = cylinder_solid_brep(0.006, 0.0, 0.16, "rod", "electrode", "conductor")
    rod_names = tuple(f"rod_{index:02d}" for index in range(RING_COUNT))
    centres = ring_offsets(RING_COUNT, RING_RADIUS_M)

    def place_ring() -> float:
        bodies = ring_brep_bodies(rod, rod_names, centres)
        return sum(body.volume_m3 for body in bodies)

    polar = circle_point(radians_from_degrees(SPHERE_ARRAY_POLAR_DEG))
    aimed_names = tuple(f"aimed_{index:02d}" for index in range(SPHERE_ARRAY_COUNT))
    aimed_centres = sphere_ring_offsets(
        SPHERE_ARRAY_COUNT, SPHERE_ARRAY_RADIUS_M, polar, NO_TWIST
    )
    aimed_rotations = tuple(
        inward_aim(polar, azimuth)
        for azimuth in ring_azimuths(SPHERE_ARRAY_COUNT, NO_TWIST)
    )

    def place_aimed_latitude() -> float:
        bodies = sphere_ring_brep_bodies(
            rod, aimed_names, aimed_centres, aimed_rotations
        )
        return sum(body.volume_m3 for body in bodies)

    return [
        ("brep_build_and_manifest", "cadquery_ocp", build),
        ("step_export_normalised", "cadquery_ocp", export),
        ("facet_two_bodies", "cadquery_ocp", facet),
        ("gmsh_volume_mesh", "gmsh", volume_mesh),
        ("place_ring_of_bodies", "cadquery_ocp", place_ring),
        ("place_aimed_latitude", "cadquery_ocp", place_aimed_latitude),
        ("assembly_body_evidence", "cadquery_ocp", evidence),
        ("revolve_axial_profile", "cadquery_ocp", revolve_profile),
        ("revolve_closed_profile", "cadquery_ocp", revolve_closed_profile),
        ("revolve_sphere", "cadquery_ocp", revolve_sphere),
        ("revolve_spherical_shell", "cadquery_ocp", revolve_spherical_shell),
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
            ("place_ring_of_bodies", "cadquery_ocp"),
            ("assembly_body_evidence", "cadquery_ocp"),
            ("revolve_axial_profile", "cadquery_ocp"),
            ("revolve_closed_profile", "cadquery_ocp"),
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
