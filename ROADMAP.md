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
