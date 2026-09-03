<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — Architecture
-->

# Architecture

## Purpose and evidence state

`SCPN-REACTOR-KERNELS` is the shared kernel library of the SCPN Reactor
Systems Research Group. It owns two implemented kernel groups at
`computational_prototype` in `src/scpn_reactor_kernels/`: the geometry
kernels (design records ADR 0002 and ADR 0007, evidence record
`VALIDATION.md#geometry-kernels`; owned domain `shared_geometry_kernels`)
and the numerics kernels (design record ADR 0003, evidence record
`VALIDATION.md#numerics-kernels`; the numerical substrate of the owned
domain `shared_physics_kernels`).
Every other section below describes boundaries and contracts. The claim
inventory is empty; the kernel inventory is generated and drift-checked.

## Why a library

Twenty device-family repositories each need the same published closed
forms (reactivities, radiation, collisions, confinement criteria, fields,
inductances, circuit elements), the same integrators and the same
tessellation and export substrate. Copying them twenty times would create
twenty sources of truth; leaving them inside the tokamak solver would tie
eighteen non-tokamak families to a solver they do not consume. The library
is the single implementation, versioned and pinned by digest, with one
evidence record per kernel.

## The kernel contract

Every kernel satisfies all of the following before it enters the manifest:

1. A published form or a standard method, cited in the module docstring
   with the exact equation and its validity range; the source is on file
   in the private ledger where legally obtainable, otherwise the record
   says so.
2. A pure-Python floor as the public API with zero runtime dependencies,
   strict typing, NumPy-convention docstrings, fail-closed input
   validation (non-finite and out-of-range inputs are refused, never
   clamped).
3. A native kernel in `rust/` with the identical operation order, using
   only correctly rounded operations (`+ - * /`, `sqrt`) and vendored
   deterministic implementations of anything else (polynomial
   trigonometry, cube roots), so results agree with the floor bit for bit.
4. Parity tests comparing float64 bit patterns, never tolerances.
5. Statement- and branch-complete tests with analytic anchors (published
   reference values, closed-form identities, convergence orders).
6. A benchmark row per backend following the ecosystem benchmark standard.
7. An entry in `kernels-domain.json` (identifier, module, sources, maturity,
   evidence pointer, native parity flag, benchmark pointer).

## Position in the SCPN ecosystem

```text
SCPN-REACTOR-KERNELS (shared closed forms, integrators, geometry substrate)
   │  exact version + inventory digest pinned by each consumer
   ├──────────────► SCPN-<FAMILY>-CORE ×20 (device truth, device models)
   │  E2 cross-checks where a private helper overlaps (evidence only)
   ├ - - - - - - -► SCPN-FUSION-CORE      (solver mathematics, evidence)
   │  kernel inventory schema (data only; no plan, no observation)
   └ - - - - - - -► SCPN-PHASE-ORCHESTRATOR (semantics, comparability)

No path from this library reaches SCPN-CONTROL, SCPN-STUDIO, machine
protection or any actuator; it computes numbers from declared inputs.
```

## Repository layout

| Path | Role |
|---|---|
| `kernels-domain.json` | portable source of library identity, kernel inventory and consumers |
| `kernel-inventory.json` | generated inventory of the implemented kernels (drift-checked) |
| `src/scpn_reactor_kernels/geometry/` | deterministic circle points, mesh contract, primitives, axial profiles, off-axis placement, STL/GLB exports |
| `src/scpn_reactor_kernels/numerics/` | deterministic natural logarithm, exponential, real power and the Bessel functions |
| `src/scpn_reactor_kernels/cad/` | tier-G2 adapters on pinned third-party kernels (optional extra `cad`): B-rep solids, assembly manifest, deterministic STEP, faceting, placement off the axis, fail-closed body evidence, gmsh volume mesh |
| `src/scpn_reactor_kernels/validation.py` | shared fail-closed input validation |
| `rust/` | native kernels (`scpn-reactor-kernels-rs`), bit-exact with the Python floor |
| `benchmarks/` | standard-conformant benchmarks and committed local artefacts |
| `docs/THREAT_MODEL.md` | assets, trust boundaries, misuse paths |
| `docs/adr/` | decision records |
| `tools/` | manifest validator, inventory generator, workflow guard, preflight |
| `tests/` | statement- and branch-complete tests for `src/` and `tools/`, native parity tests |
| `.github/workflows/` | read-only CI definitions (no publication) |

## Contract surfaces and versioning

- `kernels-domain.json` follows schema `scpn.reactor-kernels-domain.v1`;
  unknown schemas are rejected by consumers.
- The distribution `scpn-reactor-kernels` follows semantic versioning; a
  kernel whose numerical output changes for any input is a breaking change
  of that kernel and bumps the major version.
- Consumers record `{distribution, version, inventory_sha256}` in their own
  manifests; the `consumers` list here is updated when a consumer lands.

## What would change this architecture

A kernel promoted beyond `computational_prototype` (documented accepted
cases with thresholds), a consumer's first pin, publication of the
distribution, or a FUSION seam migration that retires an overlapping
helper — each recorded as a versioned change in a new ADR.
