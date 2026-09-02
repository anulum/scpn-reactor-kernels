<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — README
-->

# SCPN Reactor Kernels

Shared physics and geometry kernel library of the SCPN Reactor Systems
Research Group. The device-family repositories of the group (twenty
reactor concepts from tokamaks to fusion–fission hybrids) need the same
published closed forms and the same numerical substrate: fusion
reactivities, radiation and collision coefficients, confinement criteria,
integrators, filament fields and inductances, deterministic tessellation of
analytic bodies and open-format mesh exports. This repository is the one
place those kernels are implemented, verified and benchmarked, so that no
device repository carries a second copy.

**Evidence maturity: `computational_prototype`** (per kernel; ADR 0001).
One kernel group is implemented: the geometry kernels — a vendored
deterministic unit circle, a closed-mesh contract with canonical bytes and
digests, solid-cylinder and annular-tube tessellation, and binary STL and
glTF 2.0 exports — with native kernels proven bit-exact against the
Python floor (ADR 0002, evidence: `VALIDATION.md#geometry-kernels`). The
claim inventory is empty and verified by the domain validator.

## Scope

This repository owns, for the reactor systems portfolio:

- shared physics kernels: published closed forms (fusion reactivities,
  radiation and collision coefficients, confinement criteria, circuit
  elements, filament fields and inductances) implemented exactly as cited,
  with declared validity ranges and no device assumption;
- shared geometry kernels: deterministic tessellation of analytic bodies,
  the closed-mesh contract, and open-format exporters used by every device
  3D model;
- shared numerical integrators with bit-exact native counterparts;
- the machine-readable kernel inventory (`kernels-domain.json`) that
  consumers pin by version and digest.

Every kernel ships a pure-Python floor (the public API, zero runtime
dependencies), an optional native kernel in `rust/` reproducing the floor
bit for bit, parity tests by float64 bit pattern, statement- and
branch-complete tests, a benchmark row, and its sources.

## Explicit exclusions

- **Device truth** (configurations, geometry parameters, operating
  envelopes, diagnostics, clocks, lifecycle): the device-family
  repositories `SCPN-<FAMILY>-CORE`.
- **Solver mathematics and validation evidence**: `SCPN-FUSION-CORE`; no
  solver is implemented here and no FUSION code is copied. Where a kernel
  overlaps a FUSION helper, the kernel is cross-checked against it as
  evidence, nothing more.
- **Typed signal semantics and comparability**: `SCPN-PHASE-ORCHESTRATOR`.
- **Control admission and action formation**: `SCPN-CONTROL`.
- **Machine protection**: independent systems retain the final veto.
- **Portfolio presentation, identity, entitlement, and execution gating**:
  `SCPN-STUDIO`.

## Non-claims

This repository is not machine-ready, not safety-certified, and not
reactor-ready. It contains no solver, no controller, no dataset, no
experimental correlation, and no published artefact; every kernel is a
computational prototype of a cited closed form or a standard method, and
no value describes or validates any real machine. A kernel's presence
here says nothing about any device's performance.

## Architecture

The boundary and the position of this library in the SCPN ecosystem are
defined in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and fixed by
[`docs/adr/0001-repository-boundary.md`](docs/adr/0001-repository-boundary.md).
The threat model is in [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md).

## Validation

Every gate currently active in this repository is listed in
[`VALIDATION.md`](VALIDATION.md). The local sequence is:

```bash
make lint        # ruff check + ruff format --check
make typecheck   # mypy --strict src tools tests benchmarks
make test        # pytest with 100 % statement and branch coverage
make validate    # kernel manifest and inventory checks
make rust        # native crate: fmt, clippy (warnings denied), tests
make preflight   # the full fail-closed gate sequence
```

## Security

See [`SECURITY.md`](SECURITY.md) for the supported states and the private
reporting route (protoscience@anulum.li).

## Licensing

AGPL-3.0-or-later for the public repository, with a commercial licence
available (see [`NOTICE.md`](NOTICE.md)). Licence texts are under
[`LICENSES/`](LICENSES/); machine-readable licensing metadata follows
REUSE 3.x (`REUSE.toml`).

## Citation

Citation metadata is provided in [`CITATION.cff`](CITATION.cff). No release,
version, or DOI exists yet; cite the repository state you inspected.
