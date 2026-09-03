<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — CHANGELOG
-->

# Changelog

## [Unreleased]

### Fixed

- STEP export normalisation (`cad/step.py`): the OpenCASCADE writer wraps
  long lines onto indented continuation lines at a column counted from the
  pre-renumbering usage-occurrence identifier lengths, so once the
  process-wide counter crossed a digit boundary the renumbered exports
  still differed in their wrap positions (found with a six-body assembly
  exported twice in one process). The normaliser now unfolds the writer's
  continuation lines before renumbering; repeated exports of a six-body
  assembly and an export after an in-process STEP import are byte-identical
  (regression test in `tests/test_cad_step.py`).

### Added

- CAD placement kernel `cad_placement`
  (`src/scpn_reactor_kernels/cad/placement.py`, ADR 0008): the tier-G2
  counterpart of `geometry_placement`. `translate_brep` places a B-rep body
  by a rigid translation and may rename it; `ring_brep_bodies` places one
  body once per centre of a ring, on the tier-G1 `ring_offsets`, so both
  tiers of a family sit on the same circle by construction. The analytic
  closed forms are carried over exactly and the placed solid's own measures
  are checked against them within the group's `1e-9` tolerance; the record
  and a test state the boundary rather than assuming it — OpenCASCADE
  integrates over the moved surface, so its volume of a placed solid is not
  bit-identical to its volume of the source solid, and on a ring of twelve
  identical rods the measured volumes differ in the last unit in the last
  place. Cross-tier evidence: faceting a placed solid agrees in volume with
  the tier-G1 mesh of the same body translated by the same offset, within
  the exact inscribed-polygon deficit bound. The CAD benchmark gains
  `place_ring_of_bodies` and the whole CAD table was re-measured on the
  landing tree. The kernel inventory gains the entry and its digest changes
  accordingly.

- Placement kernel `geometry_placement`
  (`src/scpn_reactor_kernels/geometry/placement.py`, ADR 0007): exact
  translation of a vertex stream, the centres of `count` identical bodies
  equally spaced on a circle around the axis, and the centre-to-centre
  distance of neighbours on that ring. A device repository can now carry a
  part that is not axisymmetric — the rods of a squirrel-cage cathode, a ring
  of feed conductors — without re-implementing geometry or substituting an
  axisymmetric body for it. The vendored circle is generalised in the same
  record: `circle_points(count)` serves any count of at least three and
  `unit_circle(segments)` becomes the tessellation entry point over the same
  points, which a test proves is bit-identical for every tessellation count,
  so no reference digest a consumer pins changes. The native crate mirrors
  both and the parity file compares bit patterns for counts 3 to 257, for the
  ring offsets and separation, and for a translated body; the geometry
  benchmark places a ring of twelve rods in the same pass so the kernel is
  measured on both backends. The kernel inventory gains the entry and its
  digest changes accordingly.

- CAD kernels (`src/scpn_reactor_kernels/cad/`, kernels `cad_brep_solids`,
  `cad_step_export`, `cad_faceting`, `cad_volume_mesh`, ADR 0006) behind
  the optional extra `cad` (`cadquery==2.8.0`, `gmsh==4.15.2`): B-rep
  solids of the cylinder and the annular tube with analytic reference
  measures and a `1e-9` tolerance, an ordered `BrepAssembly` with a
  canonical manifest and digest, deterministic STEP export (fixed header
  time stamp and file name, renumbered assembly usage identifiers, JSON
  provenance in the description), faceting into the `TriangleMesh`
  contract with the `2 d / r` deficit bound and the exact inscribed-polygon
  ratio, and a gmsh MSH 4.1 volume mesh summarised per entity against the
  B-rep volumes; lazy back-end loading with a named refusal; the library
  CI installs the extra; a standard-conformant benchmark with a committed
  local artefact. New owned domain `shared_cad_and_meshing_adapters`.
  Evidence class stated: third-party kernels, no bit-exact parity,
  determinism per environment only.

- Bessel kernels (`src/scpn_reactor_kernels/numerics/bessel.py`, kernel
  `numerics_bessel`, ADR 0005): `J0` and `J1` by the DLMF 10.2.2 ascending
  series in Horner form with exact integer-quotient coefficients, thirty
  terms, on the declared domain `|x| <= 8` (refused beyond, never
  clamped); the first zeros `j_{0,1}` and `j_{1,1}` as the correctly
  rounded OEIS expansions; verified against an exact rational evaluation
  of the same series; native kernels in `rust/src/numerics/bessel.rs`
  with scalar and stream bindings proven bit-exact by parity tests; a
  standard-conformant benchmark with a committed local artefact.

### Changed

- First consumer recorded (ADR 0004): SCPN-Z-PINCH-CORE pins the
  distribution at `0.1.0.dev0` and the kernel-inventory digest of the
  commit it depends on, consuming the four geometry kernels; the
  `consumers` table of `kernels-domain.json` and the generated inventory
  carry the entry. The README states that a consumer's digest names the
  inventory at the pinned commit, since recording the consumer changes
  the inventory.
- Second consumer recorded: SCPN-MIRROR-CORE pins the same commit and
  inventory digest for the numerics kernel `numerics_transcendental`; its
  native crate depends on `scpn-reactor-kernels-rs` as a git dependency
  at that commit, the first use of the Rust crate as a library.
- Third consumer recorded: SCPN-DENSE-PLASMA-FOCUS-CORE retired its
  byte-identical copy of the numerics kernel for the same pin.
- Fourth consumer recorded: SCPN-RFP-CORE pins the commit that introduced
  the Bessel kernel `numerics_bessel` and its inventory digest, the first
  consumer of that kernel; its native crate depends on the Rust crate at
  that commit.
- Fifth consumer recorded: SCPN-SPHEROMAK-CORE pins the same commit for
  the Bessel kernel and the unit-circle kernel (its axial phases), the
  first device consumer of `geometry_unit_circle` outside a mesh.

### Added

- Repository established as the shared kernel library of the SCPN Reactor
  Systems Research Group: kernel manifest `kernels-domain.json` (schema
  `scpn.reactor-kernels-domain.v1`) with a fail-closed validator, generated
  kernel inventory with drift check, workflow modularity guard, preflight
  orchestrator, uniform gate and workflow surfaces (ADR 0001).
- Geometry kernels (`src/scpn_reactor_kernels/geometry/`), the first
  implemented kernel group at `computational_prototype` (ADR 0002): a
  vendored deterministic unit circle, the closed-mesh contract
  (`TriangleMesh`), solid-cylinder and annular-tube tessellation, binary
  STL and glTF 2.0 binary exports of any body list, native kernels in
  `rust/` proven bit-exact by parity tests, and a standard-conformant
  benchmark with a committed local artefact.
- Numerics kernels (`src/scpn_reactor_kernels/numerics/`), the second
  implemented kernel group at `computational_prototype` (ADR 0003): a
  vendored deterministic natural logarithm, exponential and real power
  with refused (never clamped) domains, measured accuracy bounds against
  the platform `math` module, native kernels in `rust/` with scalar and
  stream bindings proven bit-exact by parity tests, and a
  standard-conformant benchmark with a committed local artefact.
