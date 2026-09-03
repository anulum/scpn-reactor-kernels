<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — ROADMAP
-->

# Roadmap

Planned work and implemented capability are kept strictly separate. Anything
listed under "Planned" carries no implementation, no code, and no claim in
this repository until it appears in the kernel inventory with evidence.

## Implemented

- Kernel manifest (`kernels-domain.json`) with validator; generated kernel
  inventory with drift check; workflow modularity guard; preflight.
- **Geometry kernels** (landed 2026-09-02) — vendored deterministic unit
  circle (polynomial sine and cosine with exact octant symmetry), the
  closed-mesh contract (`TriangleMesh`: closure and orientation
  validation, signed volume, surface area, canonical bytes, SHA-256),
  solid-cylinder and annular-tube tessellation, binary STL and glTF 2.0
  binary exports of any body list, native kernels bit-exact with the
  Python floor, and a standard-conformant benchmark;
  `computational_prototype` (ADR 0002, `VALIDATION.md#geometry-kernels`).
  Origin: moved from `SCPN-Z-PINCH-CORE` (its copies are retired once it
  pins this library).
- **Placement kernel** (landed 2026-09-03) — exact translation of a vertex
  stream, the centres of identical bodies equally spaced on a circle around
  the axis, and their neighbour separation, so a device can carry a part that
  is not axisymmetric (a squirrel-cage cathode, a ring of feed conductors)
  without re-implementing geometry; the unit circle is generalised to any
  point count of at least three while keeping the tessellation counts
  bit-identical, and both are mirrored natively and measured in the geometry
  benchmark; `computational_prototype` (ADR 0007,
  `VALIDATION.md#geometry-kernels`).

- **Axial profile kernel** (landed 2026-09-03) — bodies whose radius varies
  along the axis: a closed solid and a closed tube through a sampled
  `(z, radius)` profile, linear between samples and interpolating nothing
  beyond that, with the exact frustum-stack volume and lateral area. A
  constant-radius profile reproduces the existing primitives vertex for
  vertex, so the generalisation moves no pinned digest; the tessellation
  deficit against the closed form is exactly the polygon deficit of the
  segment count. Mirrored natively with bit-pattern parity and measured in
  the geometry benchmark; `computational_prototype` (ADR 0010,
  `VALIDATION.md#geometry-kernels`). Consumers: any family with a part whose
  radius is a function of the axis, first the mirror flux tube.
- **Numerics kernels** (landed 2026-09-02) — vendored deterministic natural
  logarithm (exact binary decomposition and the odd series of
  `atanh`), exponential (Cody–Waite reduction and Taylor series) and real
  power, with refused rather than clamped domains, native kernels
  bit-exact with the Python floor, measured accuracy bounds against the
  platform `math` module, and a standard-conformant benchmark;
  `computational_prototype` (ADR 0003, `VALIDATION.md#numerics-kernels`).
  The physics kernel groups below consume this group instead of `libm`.
- **Bessel kernels** (landed 2026-09-02) — `J0` and `J1` by the DLMF
  ascending series in Horner form on `|x| <= 8` with the OEIS first zeros,
  verified against an exact rational evaluation, native kernels bit-exact
  with the Python floor, and a standard-conformant benchmark;
  `computational_prototype` (ADR 0005, `VALIDATION.md#numerics-kernels`).
  Consumers: the reversed-field-pinch Bessel-function model and the
  spheromak Taylor eigenvalue.

- **CAD kernels** (landed 2026-09-03) — tier G2 behind the optional extra
  `cad`: B-rep solids of the cylinder and the annular tube on the pinned
  OpenCASCADE kernel checked against the analytic forms, an ordered
  assembly with a canonical manifest, deterministic STEP export
  (normalised header and identifiers, provenance in the description),
  faceting back into the closed-mesh contract with a declared deficit
  bound, and a gmsh tetrahedral volume mesh checked against the B-rep
  volumes; no bit-exact parity by design (third-party kernels), a
  standard-conformant benchmark; `computational_prototype` (ADR 0006,
  `VALIDATION.md#cad-kernels`). Consumers: the tier-G2 lane of the device
  repositories (pilot SCPN-Z-PINCH-CORE).

- **CAD placement** (landed 2026-09-03) — `cad_placement` (ADR 0008): the
  tier-G2 counterpart of the tessellating placement kernel. A rigid
  translation of a B-rep body and one placement per centre of a ring, on
  the same circle points tier G1 uses, so both models of a family sit on
  one circle by construction. The analytic closed forms are carried over
  exactly; the placed solid's measured volume and area are checked against
  them within `1e-9`, and the record states plainly that they are not
  bit-identical to the source solid's measures. Consumers: the tier-G2
  model of any family with an off-axis part, first the plasma-focus
  cathode cage.

- **CAD body evidence** (landed 2026-09-03) — `cad_evidence` (ADR 0009):
  the fail-closed record of one body against its analytic closed forms,
  the chord-deficit bound of the faceting and the tier-G1 mesh of the same
  body, refusing at construction and refusing a ragged assembly. It was
  written once in a device repository and belongs here, because none of
  those checks is device knowledge; a family now writes its composition
  and its record, not a checking apparatus. Consumers: every tier-G2
  device model.

## Planned (no implementation exists; ordering is not a commitment)

1. **Collision kernels** — Coulomb logarithms, Spitzer resistivity,
   Braginskii collision and equilibration times (NRL Plasma Formulary;
   Braginskii 1965), each with its regime of validity.
2. **Reactivity kernels** — Bosch–Hale (1992) parametrisation for D-T,
   D-D (both branches) and D-³He with a vendored correctly-rounded cube
   root; p-¹¹B (Nevins and Swain 2000) once the source is on file.
3. **Radiation and confinement kernels** — bremsstrahlung and synchrotron
   losses, Lawson criterion, triple product, ignition margin.
4. **Integrators** — Dormand–Prince 5(4) with dense output and bit-exact
   native counterpart; the entry point of the multi-language chain.
5. **Circuit and field kernels** — series RLC discharge with energy
   accounting; Biot–Savart of filament segments and loops; Neumann mutual
   inductance; circular-loop self inductance.
6. **Geometry extensions** — torus segments and spherical shells; material
   register; adapters for neutronics geometry and B-rep CAD (separate
   tooling decisions).

## Not planned in this repository

Device configurations, equilibria, transport, stability solvers,
controllers, machine-protection logic, presentation, and any direct
actuation path.
