# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — geometry tessellation benchmark

"""Benchmark the geometry kernels: Python floor versus native.

Follows the ecosystem benchmark standard: warm-up, repeated samples,
percentiles, one row per (operation, backend), unavailable backends marked
explicitly, full provenance in the artefact. The operation is the
tessellation of three synthetic bodies (two solid cylinders and one
annular tube) at a declared segment count followed by the signed volume
and surface area of every body; each sample times one full pass and the
cost is reported per generated face. The Python floor row includes the
mesh validation every public build performs; the native row calls the
kernels per body through the binding (call-through cost, not a vectorised
pipeline). Nothing measured here is a physics or engineering claim.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib
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

from scpn_reactor_kernels.geometry import (  # noqa: E402
    TriangleMesh,
    annular_tube,
    cylinder_solid,
    ring_offsets,
    translate,
)

SCHEMA: Final = "scpn-reactor-kernels.geometry-tessellation-benchmark.v1"
BODIES: Final = (
    ("cylinder", 0.05, None, 0.0, 1.0),
    ("tube", 0.1, 0.11, 0.0, 1.6),
    ("column", 0.01, None, 1.0, 1.5),
)
#: One ring of identical rods placed off the axis, so the pass also measures
#: the placement kernel: (count, ring radius, rod radius, z_low, z_high).
RING: Final = (12, 0.13, 0.012, 0.0, 1.6)


def floor_pass(segments: int) -> tuple[float, int]:
    """Run one full pass on the Python floor.

    Parameters
    ----------
    segments
        Circumferential segments per body.

    Returns
    -------
    (float, int)
        Checksum of the measures (so the work cannot be optimised away)
        and the number of generated faces.
    """
    total = 0.0
    faces = 0
    for name, first, second, low, high in BODIES:
        if second is None:
            vertices, indices = cylinder_solid(first, low, high, segments)
        else:
            vertices, indices = annular_tube(first, second, low, high, segments)
        mesh = TriangleMesh(
            name=name,
            role="synthetic",
            material_identifier="synthetic",
            vertices=vertices,
            faces=indices,
        )
        total += mesh.signed_volume_m3() + mesh.surface_area_m2()
        faces += mesh.face_count
    count, ring_radius, rod_radius, low, high = RING
    rod_vertices, rod_faces = cylinder_solid(rod_radius, low, high, segments)
    for index, (offset_x, offset_y) in enumerate(ring_offsets(count, ring_radius)):
        mesh = TriangleMesh(
            name=f"rod_{index:02d}",
            role="synthetic",
            material_identifier="synthetic",
            vertices=translate(rod_vertices, offset_x, offset_y, 0.0),
            faces=rod_faces,
        )
        total += mesh.signed_volume_m3() + mesh.surface_area_m2()
        faces += mesh.face_count
    return total, faces


def native_pass_factory() -> Callable[[int], tuple[float, int]] | None:
    """Return the native pass when the native module is importable.

    Returns
    -------
    callable or None
        The pass function, or None when scpn_reactor_kernels_native is absent.
    """
    try:
        native = importlib.import_module("scpn_reactor_kernels_native")
    except ImportError:
        return None

    def native_pass(segments: int) -> tuple[float, int]:
        total = 0.0
        faces = 0
        for _, first, second, low, high in BODIES:
            if second is None:
                vertices, indices = native.tessellate_cylinder(
                    first, low, high, segments
                )
            else:
                vertices, indices = native.tessellate_annular_tube(
                    first, second, low, high, segments
                )
            total += native.mesh_volume(vertices, indices)
            total += native.mesh_area(vertices, indices)
            faces += len(indices) // 3
        count, ring_radius, rod_radius, low, high = RING
        rod_vertices, rod_faces = native.tessellate_cylinder(
            rod_radius, low, high, segments
        )
        offsets = native.ring_offsets(count, ring_radius)
        for index in range(count):
            moved = native.translate(
                rod_vertices, offsets[2 * index], offsets[2 * index + 1], 0.0
            )
            total += native.mesh_volume(moved, rod_faces)
            total += native.mesh_area(moved, rod_faces)
            faces += len(rod_faces) // 3
        return total, faces

    return native_pass


def measure(
    run: Callable[[int], tuple[float, int]],
    segments: int,
    warmup: int,
    repeats: int,
) -> dict[str, float]:
    """Time repeated passes and summarise them.

    Parameters
    ----------
    run
        Pass to time.
    segments
        Circumferential segments per body.
    warmup
        Discarded leading passes.
    repeats
        Timed passes.

    Returns
    -------
    dict[str, float]
        Percentiles, mean, min, max in microseconds per generated face and
        the throughput in faces per second (P50-based).
    """
    faces = 1
    for _ in range(warmup):
        _, faces = run(segments)
    samples: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter_ns()
        _, faces = run(segments)
        samples.append((time.perf_counter_ns() - start) / 1e3 / faces)
    ordered = sorted(samples)

    def percentile(fraction: float) -> float:
        return ordered[min(len(ordered) - 1, round(fraction * (len(ordered) - 1)))]

    p50 = percentile(0.5)
    return {
        "faces_per_pass": float(faces),
        "p50_us_per_face": p50,
        "p95_us_per_face": percentile(0.95),
        "p99_us_per_face": percentile(0.99),
        "mean_us_per_face": statistics.fmean(samples),
        "min_us_per_face": ordered[0],
        "max_us_per_face": ordered[-1],
        "throughput_faces_per_s": 1e6 / p50,
    }


def provenance() -> dict[str, Any]:
    """Collect the environment provenance of a run.

    Returns
    -------
    dict[str, Any]
        Interpreter, platform, CPU model, commit and host-load context.
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
    parser.add_argument("--segments", type=int, default=4096)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--repeats", type=int, default=20)
    parser.add_argument("--label", default="local")
    parser.add_argument("--output", type=Path, default=ROOT / "benchmarks" / "results")
    args = parser.parse_args(argv)
    results: list[dict[str, Any]] = [
        {
            "name": "tessellation_and_measures",
            "backend": "python_floor",
            "stats": measure(floor_pass, args.segments, args.warmup, args.repeats),
            "status": "measured",
        }
    ]
    native_pass = native_pass_factory()
    if native_pass is None:
        results.append(
            {
                "name": "tessellation_and_measures",
                "backend": "rust_native",
                "stats": None,
                "status": "unavailable: scpn_reactor_kernels_native not installed",
            }
        )
    else:
        stats = measure(native_pass, args.segments, args.warmup, args.repeats)
        results.append(
            {
                "name": "tessellation_and_measures",
                "backend": "rust_native",
                "stats": stats,
                "status": "measured",
                "requires": "optional native build (rust/, maturin)",
            }
        )
        floor_p50 = results[0]["stats"]["p50_us_per_face"]
        results[1]["speedup_p50_vs_python_floor"] = floor_p50 / stats["p50_us_per_face"]
    artefact = {
        "schema": SCHEMA,
        "generated_at": datetime.now(UTC).isoformat(),
        "label": args.label,
        "platform": provenance(),
        "parameters": {
            "segments": args.segments,
            "warmup": args.warmup,
            "repeats": args.repeats,
        },
        "results": results,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    target = args.output / f"geometry_tessellation.{args.label}.json"
    target.write_text(
        json.dumps(artefact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"benchmark: wrote {target}")
    for row in results:
        print(f"  {row['backend']}: {row['status']} {row['stats']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
