# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — transcendental kernel benchmark

"""Benchmark the transcendental kernels: Python floor versus native.

Follows the ecosystem benchmark standard: warm-up, repeated samples,
percentiles, one row per (operation, backend), unavailable backends marked
explicitly, full provenance in the artefact. The operation is one pass of
``ln``, ``exp`` and ``pow`` over a deterministic grid of arguments; each
sample times one full pass and the cost is reported per evaluation (three
evaluations per grid point); the grids are built once, outside the timed
region. The Python floor row calls the public scalar functions; the native
row calls the stream bindings (one call per kernel and pass, so the row
includes the list-to-vector conversions of the binding but amortises the
call overhead). Nothing measured here is a physics or engineering claim.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib
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

from scpn_reactor_kernels.numerics import (  # noqa: E402
    exponential,
    natural_log,
    power,
)

SCHEMA: Final = "scpn-reactor-kernels.transcendental-benchmark.v1"


def grid(points: int) -> tuple[list[float], list[float], list[float], list[float]]:
    """Return deterministic argument grids for the three kernels.

    Parameters
    ----------
    points
        Grid points per kernel.

    Returns
    -------
    tuple of lists
        Logarithm arguments spanning ``[1e-300, 1e300]`` geometrically,
        exponential arguments spanning ``[-690, 690]`` linearly, and the
        base and exponent grids of the power (bases in ``[0.1, 10]``,
        exponents in ``[-4, 4]``).
    """
    logs = [math.exp(-690.0 + 1380.0 * i / (points - 1)) for i in range(points)]
    exps = [-690.0 + 1380.0 * i / (points - 1) for i in range(points)]
    bases = [math.exp(-2.3 + 4.6 * i / (points - 1)) for i in range(points)]
    exponents = [-4.0 + 8.0 * i / (points - 1) for i in range(points)]
    return logs, exps, bases, exponents


Pass = Callable[[], tuple[float, int]]


def floor_pass_factory(points: int) -> Pass:
    """Return one full pass on the Python floor over precomputed grids.

    Parameters
    ----------
    points
        Grid points per kernel.

    Returns
    -------
    callable
        Pass returning the checksum of the results (so the work cannot be
        optimised away) and the number of evaluations.
    """
    logs, exps, bases, exponents = grid(points)

    def floor_pass() -> tuple[float, int]:
        total = 0.0
        for x in logs:
            total += natural_log(x)
        for y in exps:
            total += exponential(y) * 1e-300
        for b, e in zip(bases, exponents, strict=True):
            total += power(b, e) * 1e-4
        return total, 3 * points

    return floor_pass


def native_pass_factory(points: int) -> Pass | None:
    """Return the native pass when the native module is importable.

    Parameters
    ----------
    points
        Grid points per kernel.

    Returns
    -------
    callable or None
        The pass function, or None when scpn_reactor_kernels_native is absent.
    """
    try:
        native = importlib.import_module("scpn_reactor_kernels_native")
    except ImportError:
        return None
    logs, exps, bases, exponents = grid(points)

    def native_pass() -> tuple[float, int]:
        total = math.fsum(native.natural_log_stream(logs))
        total += math.fsum(native.exponential_stream(exps)) * 1e-300
        total += math.fsum(native.power_stream(bases, exponents)) * 1e-4
        return total, 3 * points

    return native_pass


def measure(run: Pass, warmup: int, repeats: int) -> dict[str, float]:
    """Time repeated passes and summarise them.

    Parameters
    ----------
    run
        Pass to time.
    warmup
        Discarded leading passes.
    repeats
        Timed passes.

    Returns
    -------
    dict[str, float]
        Percentiles, mean, min, max in nanoseconds per evaluation and the
        throughput in evaluations per second (P50-based).
    """
    evaluations = 1
    for _ in range(warmup):
        _, evaluations = run()
    samples: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter_ns()
        _, evaluations = run()
        samples.append((time.perf_counter_ns() - start) / evaluations)
    ordered = sorted(samples)

    def percentile(fraction: float) -> float:
        return ordered[min(len(ordered) - 1, round(fraction * (len(ordered) - 1)))]

    p50 = percentile(0.5)
    return {
        "evaluations_per_pass": float(evaluations),
        "p50_ns_per_evaluation": p50,
        "p95_ns_per_evaluation": percentile(0.95),
        "p99_ns_per_evaluation": percentile(0.99),
        "mean_ns_per_evaluation": statistics.fmean(samples),
        "min_ns_per_evaluation": ordered[0],
        "max_ns_per_evaluation": ordered[-1],
        "throughput_evaluations_per_s": 1e9 / p50,
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
    parser.add_argument("--points", type=int, default=100000)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--repeats", type=int, default=20)
    parser.add_argument("--label", default="local")
    parser.add_argument("--output", type=Path, default=ROOT / "benchmarks" / "results")
    args = parser.parse_args(argv)
    results: list[dict[str, Any]] = [
        {
            "name": "ln_exp_pow_pass",
            "backend": "python_floor",
            "stats": measure(
                floor_pass_factory(args.points), args.warmup, args.repeats
            ),
            "status": "measured",
        }
    ]
    native_pass = native_pass_factory(args.points)
    if native_pass is None:
        results.append(
            {
                "name": "ln_exp_pow_pass",
                "backend": "rust_native",
                "stats": None,
                "status": "unavailable: scpn_reactor_kernels_native not installed",
            }
        )
    else:
        stats = measure(native_pass, args.warmup, args.repeats)
        results.append(
            {
                "name": "ln_exp_pow_pass",
                "backend": "rust_native",
                "stats": stats,
                "status": "measured",
                "requires": "optional native build (rust/, maturin)",
            }
        )
        floor_p50 = results[0]["stats"]["p50_ns_per_evaluation"]
        results[1]["speedup_p50_vs_python_floor"] = (
            floor_p50 / stats["p50_ns_per_evaluation"]
        )
    artefact = {
        "schema": SCHEMA,
        "generated_at": datetime.now(UTC).isoformat(),
        "label": args.label,
        "platform": provenance(),
        "parameters": {
            "points_per_kernel": args.points,
            "warmup": args.warmup,
            "repeats": args.repeats,
        },
        "results": results,
        "non_claims": [
            "cost of the vendored series, not a physics or engineering claim",
            "shared workstation, cores not isolated; treat as indicative",
        ],
    }
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / f"transcendental.{args.label}.json"
    path.write_text(json.dumps(artefact, indent=2, sort_keys=True) + "\n", "utf-8")
    for row in results:
        stats = row["stats"]
        if stats is None:
            print(f"{row['backend']}: {row['status']}")
        else:
            print(
                f"{row['backend']}: P50 {stats['p50_ns_per_evaluation']:.1f} ns/eval, "
                f"P95 {stats['p95_ns_per_evaluation']:.1f}, "
                f"throughput {stats['throughput_evaluations_per_s']:.0f}/s"
            )
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
