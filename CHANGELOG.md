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

### Added

- Sine and cosine of an angle a source prints (`geometry_unit_circle`,
  ADR 0016). Every angle this library had needed was a rational multiple
  of a turn, which `circle_points` reaches by integer arithmetic without
  ever forming an angle. A filed source prints latitudes instead — one
  device family's node set sits at 20.1, 43.4, 59.0, 80.1, 99.9, 121.0,
  136.6 and 159.9 degrees — and none of those can be reached that way.

  The new path reduces the angle against a three-word split of `pi/2` in
  a fixed operation order and then evaluates **the same two polynomials**.
  The domain is declared and refused at its edge: the quadrant index is
  bounded at `2^21`, measured against the nearest indices at which either
  reduction product stops being exact (5340355 and 4017387).

  **The residue is not strictly bounded by `pi/4`, and the record says
  so** rather than asserting a bound that does not hold. The quotient
  picking the index is formed with a rounded `2/pi`, so the quarter turn
  is passed by one unit in the last place at `pi/4` and by `3.9e-10` at
  the top of the domain — where the result is still accurate to one unit
  in the last place, measured.

  `circle_points` stays the entry point for rings and tessellations, and
  a test measures why the two are not interchangeable: for a
  thirty-member ring only 4 of 30 points come out identical, and the
  exact zeros and ones on the axes belong to the count-based path alone.

  Native parity is bit-exact over a scan of the domain; agreement with
  the platform library is `2.220446049250313e-16` at worst.

- The rectangular prism (`geometry_primitives`, `cad_brep_solids`,
  ADR 0015): the first body in this library that is **not a solid of
  revolution**, and the first that is tessellated exactly rather than
  approximated. It carries no segment count, because there is no
  inscribed approximation to refine, and a test asserts that absence on
  the signature itself.

  Two module descriptions said every body here was a solid of revolution.
  Both are corrected rather than quietly widened, because consuming
  families word their non-claims around them.

  **The evidence bounds could not be reused by analogy.** Measured over
  nine prisms from 1 micrometre to 10 metres and aspect ratios to
  1000:1, at every deflection the back-end accepts: the mesher returns
  8 vertices and 12 triangles every time, no deflection changes any
  measure, and the worst relative volume deviation is 2.581e-16 — falling
  on either side of the analytic value. The chord bound `2 d / r` needs a
  radius a prism has no such thing as, and supplying the half-width gives
  eleven orders of slack; the polygon bound is 0.0997 against a measured
  difference of exactly zero. So a body without curvature declares a
  round-off tolerance of `1e-12` instead — four orders above the measured
  ceiling, three orders below the curved bodies' measure tolerance — and
  a caller states which regime a body is in by passing its smallest
  circular radius or `None`.

### Fixed

- The faceted-volume deviation is compared **in magnitude** rather than
  one-sidedly. A faceted volume arbitrarily *larger* than its analytic
  form previously passed without comment. No curved body's evidence
  changes — an inscribed faceting always undershoots — so this is a
  strict tightening; it surfaced only because a prism's deviation is
  signed.

- Spherical bodies `geometry_spheres`
  (`src/scpn_reactor_kernels/geometry/spheres.py`, ADR 0013): the sphere's
  axial profile, sampled uniformly in polar angle from the first half turn of
  `circle_points` on twice the ring count, so the poles land on exactly
  `centre ± radius` with a radius of exactly zero and every coordinate is
  bit-identical to the native kernel; the named composition that revolves it;
  and the spherical shell, which is not a tube between aligned profiles and
  could not be built as one. The angular sampling was chosen by measurement:
  its volume deficit falls as the square of the ring count, the ratio between
  successive doublings running 3.990, 3.998, 3.999, 4.000. No ideal-sphere
  closed forms are exposed — these bodies are inscribed polyhedra, and the
  library already gives the exact volume of the body actually built.
- B-rep spherical bodies `cad_spheres`
  (`src/scpn_reactor_kernels/cad/spheres.py`, ADR 0014): the tier-G2 twins.
  The shell's generating polyline touches the axis along two segments, where
  the cavity's poles sit inside the outer body, and there is no way to bound
  the region without them; the back-end was measured to revolve it exactly,
  the volume equalling the difference of the two frustum stacks with a
  relative error of zero at sixteen rings.

### Changed

- The revolve helper of `cad.profiles` is shared with `cad.spheres` and lost
  its leading underscore for that reason. It is still not part of the
  package's public surface.
- Both benchmarks gained the new bodies and were rerun; the recorded results
  and the tables in `docs/benchmarks.md` are refreshed rather than carried
  over. The tessellation pass is larger than the previous run by the shell,
  so the two are not comparable row by row, and the record says so.


- CAD axial profile kernel `cad_profiles`
  (`src/scpn_reactor_kernels/cad/profiles.py`, ADR 0011): the tier-G2 twin of
  `geometry_profiles`, revolving the closed polyline through the profile's
  samples about the axis. The profile contract is not restated but imported:
  the same validators, the same rules, the same messages, surfacing under the
  CAD error type, so a caller who moves a profile between tiers meets one
  contract rather than two that could drift. The analytic references are the
  tier-G1 frustum-stack closed forms plus the end discs or annuli, exact for a
  linear profile, and the back-end agrees with them to `1e-16` on the solid
  and `2e-15` on the tube against a `1e-9` tolerance. A test proves the two
  tiers describe one body: faceting the revolved solid agrees in volume with
  the tessellated mesh of the same profile within the exact polygon deficit.
  The CAD benchmark gains `revolve_axial_profile`; a revolution costs about
  three times an extrusion, which is the price of a shape an extrusion cannot
  express.

- Axial profile kernel `geometry_profiles`
  (`src/scpn_reactor_kernels/geometry/profiles.py`, ADR 0010): surfaces of
  revolution through a sampled `(z, radius)` profile — a closed solid, a
  closed tube between two aligned profiles, and the exact frustum-stack
  closed forms of the resulting body. Every tier-G1 primitive so far built a
  body of constant radius; a magnetic mirror confines a flux tube, whose
  radius is a function of the field along the axis, and the filed source for
  that family prints a plasma radius and a magnet bore that a body of
  constant radius cannot satisfy at the same time. The surface passes exactly
  through the samples it is given and is linear between them: the kernel
  interpolates nothing beyond that, so a record built on it can say what the
  surface is without appealing to an undeclared smoothing rule. The
  generalisation is exact — a two-sample profile of constant radius
  reproduces `cylinder_solid` vertex for vertex, and a pair of them
  `annular_tube` — so no pinned digest moves for a shape that did not change.
  The tessellated volume differs from the closed form by exactly the
  inscribed-polygon deficit of the segment count, asserted as an equality
  rather than a bound. The native crate mirrors both primitives and both
  closed forms with bit-pattern parity, and the geometry benchmark
  tessellates a varying body in the same pass. The kernel inventory gains the
  entry and its digest changes accordingly.

### Fixed

- Bounding box of a B-rep body (`cad/solids.py`): the kernel's optimal box
  consults an attached triangulation by default, so once a body had been
  faceted its recorded box became the box of the faceted approximation —
  looser by the mesher's deflection — and every assembly manifest digest
  taken after a faceting differed from one taken before, for the same
  geometry and with nothing in the record saying why. The box is now taken
  from the geometry alone, without the triangulation and without the shape
  tolerance, so it is the exact box and does not depend on whether an
  unrelated kernel has run over the body (regression test in
  `tests/test_cad_solids.py`). Found while building the second tier-G2
  device model, whose placement identities are read from these boxes.
  Consumers that pin a manifest or model digest containing bounding boxes
  re-pin it when they re-pin the library: this is a governed data change.

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

- CAD body evidence kernel `cad_evidence`
  (`src/scpn_reactor_kernels/cad/evidence.py`, ADR 0009): the fail-closed
  record of one B-rep body against its analytic closed forms, the
  chord-deficit bound of its faceting and the tier-G1 mesh of the same body,
  plus the assembly form that keeps the body order. It refuses at
  construction — a violated bound raises with the body and the bound named —
  and refuses a ragged input rather than zipping four sequences of different
  lengths into a short answer. The machinery was written once inside a device
  repository; none of it is device knowledge, and keeping it there would have
  copied the same two hundred lines into every family that gains a CAD model,
  with nothing forcing the copies to stay equal. A family now writes its
  schema identity, its body composition and its non-claims, and consumes the
  evidence. The pilot family's copy is recorded in ADR 0009 as a second
  implementation scheduled to migrate; the library is the reference. The CAD
  benchmark gains `assembly_body_evidence`.

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

- Native surface documentation is now a compiler gate, not a habit: the crate
  denies `missing_docs`, `missing_debug_implementations` and `unsafe_code`, and
  denies rustdoc's broken and private intra-doc links and invalid Rust code
  blocks. `cargo doc --no-deps` joins the local `rust` target and the hosted
  `rust` job, so a public item that ships without documentation fails the build
  rather than accumulating as debt for the next reader.

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
