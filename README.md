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
Two kernel groups are implemented: the geometry kernels — deterministic
circle points for any count, a closed-mesh contract with canonical bytes and
digests, solid-cylinder and annular-tube tessellation, exact placement of
bodies off the axis, and binary STL and glTF 2.0 exports (ADR 0002 and ADR
0007, evidence: `VALIDATION.md#geometry-kernels`) —
and the numerics kernels — a vendored deterministic natural logarithm,
exponential and real power with refused, never clamped, domains (ADR 0003,
evidence: `VALIDATION.md#numerics-kernels`) — each with native kernels
proven bit-exact against the Python floor. The claim inventory is empty
and verified by the domain validator.

## Why a kernel library

A closed form implemented twenty times is twenty sources of truth. A
closed form left inside one family's solver ties nineteen other families
to a solver they do not consume. This library is the single implementation
of every published relation and standard method that more than one device
family needs, versioned and pinned by digest, with one evidence record per
kernel. Its contract, fixed in
[`docs/adr/0001-repository-boundary.md`](docs/adr/0001-repository-boundary.md):

- every kernel is a pure-Python floor (the public API, zero runtime
  dependencies, Python 3.12 or newer);
- every numerical kernel has an optional native counterpart in `rust/`
  that reproduces the floor bit for bit, proven by parity tests that
  compare float64 bit patterns, never tolerances; anything a platform
  `libm` would evaluate differently between languages (trigonometry,
  logarithm, exponential, power) is vendored on both sides;
- every input outside a kernel's declared domain is refused with an error
  naming the field and the bound; nothing is clamped, defaulted or
  silently corrected, and no kernel returns a non-finite value;
- every kernel carries statement- and branch-complete tests, a benchmark
  row per the ecosystem benchmark standard, and its sources in the
  manifest.

## Implemented kernels

### Geometry (`scpn_reactor_kernels.geometry`, ADR 0002)

The substrate of every device 3D model in the group: a unit circle whose
points are bit-exact across backends (degree-15 sine and degree-16 cosine
Taylor polynomials on `[0, pi/4]` with exact octant and quadrant
symmetry), a closed and consistently oriented triangle-mesh contract
(`TriangleMesh`: closure and orientation validation, signed volume by the
divergence theorem, surface area, bounding box, canonical bytes and a
SHA-256 digest), analytic primitives tessellated in a fixed vertex and
face order (solid cylinder, annular tube), and open-format exports
(binary STL, glTF 2.0 binary) that carry caller-supplied provenance.

```python
from scpn_reactor_kernels import TriangleMesh, annular_tube, glb_bytes

vertices, faces = annular_tube(0.10, 0.11, 0.0, 1.6, segments=64)
wall = TriangleMesh(
    name="chamber_wall",
    role="structure",
    material_identifier="steel",
    vertices=vertices,
    faces=faces,
)
volume_m3 = wall.signed_volume_m3()  # positive: outward orientation
digest = wall.digest_sha256()  # over the float64 canonical bytes
document = glb_bytes([wall], extras={"schema": "your.model.schema.v1"})
```

### Numerics (`scpn_reactor_kernels.numerics`, ADR 0003)

Deterministic `natural_log`, `exponential` and `power` built only from
`+ - * /`, exact binary decomposition and exact power-of-two scaling:
`ln(x) = k ln 2 + 2 atanh((m - 1)/(m + 1))` with `x = m 2^k` and `m` in
`[sqrt(1/2), sqrt(2))`; `exp(y) = 2^k exp(r)` with the Cody–Waite
reduction of `ln 2`; `pow(x, y) = exp(y ln x)`. The logarithm needs a
positive normal double, the exponential an argument in `[-708, 709]` so
that the result is a normal double; the tests bound both to `1e-15`
relative against the platform `math` module over their whole domains and
the power to `1e-13` for `|y ln x| <= 100`.

```python
from scpn_reactor_kernels import natural_log, power

inductance_factor = natural_log(0.16 / 0.116)  # ln(b / a) of a coaxial gun
scaled = power(0.862, 3.8)  # a real-exponent scaling law
```

The Bessel functions `J0` and `J1` (ADR 0005) serve the relaxed-state
profiles of the reversed-field pinch and the spheromak: the DLMF 10.2.2
series in Horner form with exact integer-quotient coefficients, thirty
terms, on the declared domain `|x| <= 8` (refused beyond), verified against
an exact rational evaluation of the series to `2e-14` absolute; the first
zeros `j_{0,1}` and `j_{1,1}` are the correctly rounded OEIS expansions.

```python
from scpn_reactor_kernels import BESSEL_J0_FIRST_ZERO, bessel_j0, bessel_j1

theta = 1.6  # pinch parameter of a Bessel-function-model profile
reversal = theta * bessel_j0(2.0 * theta) / bessel_j1(2.0 * theta)  # F(theta)
theta_at_reversal = BESSEL_J0_FIRST_ZERO / 2.0  # where F crosses zero
```

### Native kernels (`rust/`, optional)

The crate `scpn-reactor-kernels-rs` (library `scpn_reactor_kernels_native`,
optional Python distribution `scpn-reactor-kernels-native` built with
maturin) mirrors every numerical kernel operation for operation and
exposes scalar and stream bindings. The Python floor is always the default;
the native module is an acceleration a consumer may install, never a
requirement, and the parity tests skip hermetically when it is absent.

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt maturin
VIRTUAL_ENV=.venv PATH=.venv/bin:$PATH maturin develop --release -m rust/Cargo.toml
.venv/bin/pytest -q tests/test_geometry_native_parity.py tests/test_numerics_native_parity.py
```

The CAD kernels (ADR 0006, optional extra `cad`) build the same
primitives as B-rep solids on the pinned OpenCASCADE kernel through
CadQuery, keep them in an ordered assembly with a canonical manifest,
export a deterministic STEP file (fixed header time stamp, renumbered
assembly identifiers, provenance in the description), facet the solids
back into the closed-mesh contract, place a body off the axis or once per
centre of a ring (ADR 0008, the tier-G2 counterpart of the tessellating
placement, on the same circle points), and mesh a STEP assembly into
tetrahedra with gmsh. Their measures are checked against the analytic
forms within declared tolerances; they carry no bit-exact parity because
the kernels are third-party, and that boundary is stated in the evidence
record — including the fact that the back-end's measure of a placed solid
is not bit-identical to its measure of the source solid.

```bash
pip install "scpn-reactor-kernels[cad] @ git+https://github.com/anulum/scpn-reactor-kernels.git@<commit>"
```

```python
from scpn_reactor_kernels.cad import (
    BrepAssembly,
    annular_tube_brep,
    cylinder_solid_brep,
    step_bytes,
)

assembly = BrepAssembly(
    (
        cylinder_solid_brep(0.05, 0.0, 0.3, "inner", "electrode", "conductor"),
        annular_tube_brep(0.08, 0.1, -0.1, 0.4, "outer", "wall", "steel"),
    )
)
step = step_bytes(assembly, {"design_digest": "..."})  # deterministic bytes
```

## Consuming and pinning

Consumers install the pure-Python distribution `scpn-reactor-kernels` (no
release is published yet; install from a repository checkout) and record
`{distribution, version, inventory_sha256}` of the generated
[`kernel-inventory.json`](kernel-inventory.json) in their own manifests.
The inventory is derived from the kernel manifest
[`kernels-domain.json`](kernels-domain.json) (schema
`scpn.reactor-kernels-domain.v1`) and drift-checked, so a pin identifies
the exact set of implemented kernels and their evidence pointers. A kernel
whose numerical output changes for any input is a breaking change of that
kernel and bumps the major version. The `consumers` list of the manifest is
updated when a consumer lands its pin; because that update changes the
inventory, a consumer's digest always names the inventory at the commit it
pins, never the inventory that lists it. Consumers so far: SCPN-Z-PINCH-CORE
(geometry kernels; ADR 0004), SCPN-MIRROR-CORE and
SCPN-DENSE-PLASMA-FOCUS-CORE (numerics kernel, with their native crates
depending on this repository's Rust crate at the same commit), and
SCPN-RFP-CORE and SCPN-SPHEROMAK-CORE (Bessel kernel, pinned at the
commit that introduced it, native crates likewise; the spheromak also
consumes the unit-circle kernel for its axial phases).

## Scope

This repository owns, for the reactor systems portfolio:

- shared physics kernels: published closed forms (fusion reactivities,
  radiation and collision coefficients, confinement criteria, circuit
  elements, filament fields and inductances) implemented exactly as cited,
  with declared validity ranges and no device assumption;
- shared geometry kernels: deterministic tessellation of analytic bodies,
  the closed-mesh contract, and open-format exporters used by every device
  3D model;
- shared numerical substrate and integrators with bit-exact native
  counterparts;
- the machine-readable kernel inventory (`kernels-domain.json`) that
  consumers pin by version and digest.

Planned kernel groups and their ordering are listed in
[`ROADMAP.md`](ROADMAP.md); nothing listed there carries an implementation
or a claim until it appears in the inventory with evidence.

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
here says nothing about any device's performance. The numerics kernels are
not correctly rounded; their accuracy is the measured bound recorded in
`VALIDATION.md`.

## Repository layout

| Path | Role |
|---|---|
| `kernels-domain.json` | portable source of library identity, kernel inventory and consumers |
| `kernel-inventory.json` | generated inventory of the implemented kernels (drift-checked) |
| `src/scpn_reactor_kernels/geometry/` | deterministic unit circle, mesh contract, primitives, STL/GLB exports |
| `src/scpn_reactor_kernels/numerics/` | deterministic natural logarithm, exponential and real power |
| `src/scpn_reactor_kernels/validation.py` | shared fail-closed input validation |
| `rust/` | native kernels (`scpn-reactor-kernels-rs`), bit-exact with the Python floor |
| `benchmarks/` | standard-conformant benchmarks and committed local artefacts |
| `docs/adr/` | decision records (boundary, geometry kernels, numerics kernels) |
| `docs/THREAT_MODEL.md` | assets, trust boundaries, misuse paths |
| `tools/` | manifest validator, inventory generator, workflow guard, preflight |
| `tests/` | statement- and branch-complete tests for `src/` and `tools/`, native parity tests |
| `.github/workflows/` | read-only CI definitions (no publication) |

## Architecture

The boundary and the position of this library in the SCPN ecosystem are
defined in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and fixed by
[`docs/adr/0001-repository-boundary.md`](docs/adr/0001-repository-boundary.md);
the kernel groups are recorded in
[`docs/adr/0002-geometry-kernels.md`](docs/adr/0002-geometry-kernels.md) and
[`docs/adr/0003-numerics-transcendental-kernels.md`](docs/adr/0003-numerics-transcendental-kernels.md).
The threat model is in [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md).

## Validation

Every gate currently active in this repository is listed in
[`VALIDATION.md`](VALIDATION.md), together with the evidence record of
each kernel group (what is exercised, what is anchored, what is not
claimed). The local sequence is:

```bash
make venv        # .venv with the pinned development toolchain
make lint        # ruff check + ruff format --check
make typecheck   # mypy --strict src tools tests benchmarks
make test        # pytest with 100 % statement and branch coverage
make validate    # kernel manifest and inventory checks
make rust        # native crate: fmt, clippy (warnings denied), tests
make preflight   # the full fail-closed gate sequence
```

Hosted CI runs the same gates read-only (static analysis and policy,
tests with complete coverage, the native crate with parity and a
benchmark smoke, licensing, secrets, dependency and workflow audits); it
publishes nothing.

## Benchmarks

Every number in [`docs/benchmarks.md`](docs/benchmarks.md) is regenerated
by a script under `benchmarks/` per the ecosystem benchmark standard
(warm-up, repeated samples, percentiles, one row per backend, provenance in
the committed artefact) and is labelled with the host it was measured on.
Nothing there is a physics or engineering claim.

## Contributing, governance, support

Contributions follow [`CONTRIBUTING.md`](CONTRIBUTING.md) (every commit
carries the provenance header, the authorship line and a seat trailer, and
passes the full gate sequence); decisions follow
[`GOVERNANCE.md`](GOVERNANCE.md); support routes are in
[`SUPPORT.md`](SUPPORT.md); conduct is governed by
[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

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
