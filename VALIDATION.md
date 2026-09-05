<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — VALIDATION
-->

# Validation

Every gate currently active in this repository, with its exact scope,
followed by the evidence record of each implemented kernel group.

## Local gates

| Gate | Command | Scope |
|---|---|---|
| Lint | `ruff check .` | all Python under `src/`, `tools/`, `tests/` and `benchmarks/` |
| Format | `ruff format --check .` | same scope |
| Typing | `mypy --strict src tools tests benchmarks` | zero errors, strict mode |
| Tests + coverage | `pytest -q --cov=src --cov=tools --cov-branch --cov-fail-under=100` | 100 % statement and branch coverage of `src/` and `tools/` |
| Kernel manifest | `python3 tools/validate_kernels_domain.py kernels-domain.json` | schema, identity, kernel item shape with resolvable module, evidence and benchmark pointers, source lists, ceiling rule, consumer pins, boundary invariants |
| Kernel inventory | `python3 tools/generate_kernel_inventory.py --check` | committed inventory byte-identical to a fresh generation |
| Licensing | `reuse lint` | REUSE 3.x compliance of the full tree |
| Workflow lint | `actionlint` | all files under `.github/workflows/` |
| Workflow modularity | `python3 tools/audit_workflows.py` | distributed workflow inventory: single ownership per job, coordinator/gate contract, action pinning, size ceilings |
| Native kernels | `make rust` (`cargo fmt --check`, `cargo clippy --all-targets --features python -- -D warnings`, `cargo test` in `rust/`) | formatting, lints with warnings denied, kernel unit tests |
| Native parity | `pytest -q tests/test_geometry_native_parity.py` | bit-exact float64 agreement of every native kernel with the Python floor (skipped hermetically when the optional native module is absent) |
| Documentation | `python3 tools/preflight.py --only docs` | UTF-8 readability and relative-link integrity of every Markdown file |
| Orchestrated | `python3 tools/preflight.py` | fail-closed run of all gates above |

## Workflow gates

Definitions are present in-repository; they run on the hosted platform
only once a remote exists under separate owner authority. The hosted
surface is modular: `ci.yml` is a coordinator that carries only trigger
policy, two reusable-workflow calls, and one stable fail-closed `gate` job
aggregating every category. Every job is declared and owned exactly once in
the versioned inventory `.github/workflow-inventory.json`, which the
workflow-modularity guard verifies locally and in hosted CI.

| Workflow | Purpose |
|---|---|
| `ci.yml` | coordinator and stable required gate |
| `reusable-static-policy.yml` | lint, format, typing, kernel manifest and inventory policy, workflow guard |
| `reusable-tests.yml` | tests with complete statement and branch coverage; native crate gates, parity and benchmark smoke |
| `pre-commit.yml` | exact pre-commit parity |
| `codeql.yml` | Python code scanning |
| `security-audit.yml` | secrets, dependency, licence, and workflow policy |
| `docs.yml` | strict documentation and link validation, no deployment |
| `sbom.yml` | reproducible dependency inventory, no release |
| `scorecard.yml` | read-only supply-chain analysis |

## Shared ecosystem gate

From the monorepo root:

```bash
python3 agentic-shared/scripts/repository_tier0_scaffold_audit.py \
  03_CODE/SCPN-REACTOR-SYSTEMS/repositories/SCPN-REACTOR-KERNELS --json
```

checks the pre-publication local-scaffold profile. This repository now has
an authorised origin remote and ignored external source records, so that
bootstrap profile is not a pass/fail gate for the published repository: its
zero-remote and object-only external-JSON assumptions do not apply. Retain
its diagnostic output and verify the applicable repository gates above;
never remove the remote or rewrite source records to satisfy that profile.

## Geometry kernels

Evidence record of the `geometry` kernel group (`computational_prototype`;
design records: `docs/adr/0002-geometry-kernels.md`,
`docs/adr/0007-geometry-placement-kernel.md` and
`docs/adr/0010-axial-profile-primitive.md`,
`docs/adr/0012-bodies-that-close-on-the-axis.md`,
`docs/adr/0015-bodies-without-curvature.md`,
`docs/adr/0016-arbitrary-angle-trigonometry.md` and
`docs/adr/0017-aimed-and-spherical-placement.md`; kernels
`geometry_unit_circle`, `geometry_mesh_contract`, `geometry_primitives`,
`geometry_exports`, `geometry_placement`, `geometry_profiles` in
`kernels-domain.json`).

What is exercised, all under the 100 % statement-and-branch coverage gate
(`src/scpn_reactor_kernels/geometry/`):

- **Deterministic circle points** (`trig.py`): vendored degree-15 sine and
  degree-16 cosine Taylor polynomials in Horner form on `[0, pi/4]` with
  exact octant and quadrant symmetry. `circle_points(count)` serves any
  count of at least three; `unit_circle(segments)` is the tessellation
  entry point that additionally enforces the multiple-of-eight rule and
  returns the same points, proven by a test that the two agree exactly for
  every tessellation count, so the reference digests consumers pin are
  unchanged by the generalisation. Tests prove every point of circles with
  8 to 4096 segments and of arbitrary counts (3, 5, 6, 7, 9, 12, 13, 20,
  100) agrees with `math.cos`/`math.sin` to `1e-15`, that points on an axis
  are exactly `0` and `±1` for every count divisible by four, that every
  quadrant is an exact sign/swap image of the first, that no negative zero
  is emitted, and that inadmissible counts (below 8 or not a multiple of 8
  for a tessellation, below 3 for a circle, booleans) are refused.
- **Arbitrary-angle circle point** (`trig.py`, ADR 0016): the same two
  polynomials, reached through a three-word Cody–Waite split of `pi/2` in
  a fixed operation order, for the angles a source prints and
  `circle_points` cannot reach. Tests prove the split sums to the double
  `pi/2` and leaves a remainder below `1e-30` against `pi` to fifty
  digits; that both reduction products are exact for every admissible
  index and that the nearest indices which break either (5340355 and
  4017387) lie outside the domain; that the domain accepts its edge and
  refuses the next double on both signs; that every quadrant branch is
  placed correctly; that a scan of 4001 angles across the whole domain
  agrees with `math.cos`/`math.sin` within `2.220446049250313e-16`, one
  unit in the last place of one; that `cos^2 + sin^2` holds; that the
  residue overshoots `pi/4` by one unit in the last place at `pi/4`
  itself and by `3.9e-10` at the worst point of the domain, where the
  result is still accurate to one unit in the last place; and that the
  count-based path keeps exact zeros and ones on the axes where this one
  cannot, so the two are measured to be **not** interchangeable.
- **Mesh contract** (`mesh.py`, `TriangleMesh`): closure and consistent
  orientation (every directed edge exactly once with its reverse), refusal
  of too few vertices or faces, non-finite coordinates, out-of-range or
  repeated indices, degenerate faces, duplicated or flipped faces and open
  surfaces; signed volume (divergence theorem), surface area and bounding
  box on the unit tetrahedron against closed forms; the documented
  canonical byte layout and SHA-256; the summary record.
- **Primitives** (`primitives.py`: solid cylinder, annular tube): vertex
  and face counts, closure and outward orientation (positive signed
  volume), the exact polygon-prism identity (mesh volume equals the
  inscribed-polygon area times height from the same circle points to
  `1e-14` relative), the tube volume as the exact difference of two
  cylinder volumes, quadratic convergence of the volume to `pi r^2 h`
  (error ratio 4 per doubling of segments, checked at 64 and 128) and of
  the areas to the closed forms; every refusal branch (radii, extents,
  ordering, segments).
- **Axial profiles** (`profiles.py`: profiled solid and profiled tube): a
  two-sample profile of constant radius reproduces the vertex and face
  streams of `cylinder_solid` exactly, and a pair of such profiles those of
  `annular_tube` exactly, for every tessellation count tested — so a body
  that moves from a constant radius to a profile of the same shape keeps
  every pinned digest. A genuinely varying five-sample body satisfies the
  closed-mesh contract with the declared vertex and face counts and the
  expected bounding box; the hollow form closes over both surfaces and both
  annuli. The tessellated volume differs from the exact frustum-stack
  closed form by exactly the inscribed-polygon deficit of the segment count
  (equality to `1e-9` relative at 8, 64 and 512 segments), which is the
  statement that the closed form is exact and the tessellation is the
  approximation, not the other way round. The closed forms agree with the
  textbook cone and cylinder forms to `1e-15`, and are unchanged by
  inserting a sample on the existing straight line — the profile is linear
  between samples, so such a sample is not new information. Refusals: fewer
  than two samples, a malformed pair, a non-finite height, a non-positive
  radius, a height that does not increase, two profiles of different
  lengths, samples at different heights, an outer radius that does not
  exceed its inner radius, and an inadmissible segment count; every message
  names the offending sample index.
- **Bodies that close on the axis** (`profiles.py`:
  `closed_profiled_solid`, ADR 0012): a profile whose first or last radius
  is exactly zero builds a body that comes to a point, which the open
  contract cannot express. A pole is one apex vertex and not a ring — the
  test counts the vertices on the axis to prove it — and the body
  satisfies the same closed-mesh contract with the declared vertex and
  face counts. The tessellated volume is the exact one times the
  inscribed-polygon ratio of the segment count, to `1e-12` relative at 8,
  64 and 512 segments; the comparison is stated as a **ratio** rather than
  as a deficit because both deficit forms cancel five digits at 512
  segments and would report a disagreement that is arithmetic rather than
  geometry. No new closed form was added and none is needed: a cone's
  volume from the general frustum sum equals `pi r^2 h / 3` bit for bit,
  and its lateral area equals `pi r l` bit for bit. A cone is admitted
  either way up, and the two orientations give the same volume exactly.
  The native mirror agrees bit for bit on a separatrix and on a cone at 8,
  32 and 64 segments. Refusals: a profile positive at both ends (that is
  an open profile), two poles with no ring between them, a negative pole
  radius, a non-positive interior radius, and everything the open contract
  refuses; every message names the offending sample index.
- **Exports** (`export.py`): binary STL (header, triangle count, unit
  normals, float32 vertices, zero attributes, exact byte length) and glTF
  2.0 binary of any body list (magic, version, chunk types and alignment,
  node names, accessor counts, types and `min`, buffer-view alignment,
  position and index streams read back, caller-supplied document extras)
  verified with minimal specification-level readers; determinism of the
  bytes; the file writers.
- **Placement** (`placement.py`): `translate` is one addition per
  coordinate in a fixed order, proven to move a tessellated body rigidly
  (face stream and axial coordinates unchanged, the transverse extent
  shifted) and to refuse an empty stream and non-finite offsets;
  `ring_offsets` returns the scaled circle points, starting on the positive
  `x` axis; `ring_separation_m` equals the analytic chord
  `2 R sin(pi / count)` to `1e-15` and is proven equal for every
  neighbouring pair of the ring, which is what a consumer uses to show that
  identical bodies on the ring do not intersect; counts below three and
  non-positive or non-finite radii are refused.
- **Aiming and spherical placement** (`placement.py`, ADR 0017): tests
  prove that aiming along `z` is exactly the identity; that the third
  column of the rotation is `axis_direction` of the same two circle
  points, bit for bit; that `R^T R` departs from the identity by at most
  `4.440892098500626e-16` and the determinant from one by four times
  that, at every printed latitude including half a turn; that the
  angle-built rotation beats the vector-built one, by computing the
  textbook minimal rotation from the same direction one microradian short
  of half a turn and measuring its departure at over `1e-4`; that the
  inward aim is the exact negation of the outward axis and points at the
  centre for all thirty of a printed node set's members; that every
  centre of a latitude lies on the sphere and shares one height exactly;
  that a ring with no twist is the plain circle bit for bit and a
  half-turn twist negates every member; that a rotated body's signed
  volume and surface area drift by at most `5.1e-14` and `1.0e-15`
  relative over those thirty placements; that the closest pair of the
  thirty centres is `0.6059943008542816` metres apart, which is what
  bounds the largest body radius that cannot intersect; and that the
  gate is a gate — a scaling is refused, and so is a **reflection**,
  which passes every orthonormality check and is caught only by the
  determinant. The tolerance is accepted at its edge and refused at the
  next case on either side.
- **Native parity**: `rust/src/geometry/` mirrors the circle points, both
  constant-radius primitives, both profiled primitives and their closed
  forms, the placement kernel, the signed volume and the surface area;
  `tests/test_geometry_native_parity.py` compares float64 bit patterns of
  every vertex coordinate, the face index streams, the measures, the circle
  points and ring offsets for counts 3 to 257, the ring separation, a
  translated body, a five-sample profiled solid and profiled tube, the
  frustum-stack volume and lateral area, the arbitrary-angle circle point
  over a scan of its whole domain, the degree conversion, the aiming and
  inward rotations, the axis directions, the twisted ring azimuths, the
  centres of every printed latitude, a rotated body and the centre
  separations, and the refusal paths of the bindings.
- **Benchmark**: `benchmarks/geometry_tessellation.py` per the ecosystem
  benchmark standard, tessellating three bodies on the axis, placing a ring
  of twelve rods off it and tessellating one five-sample profiled body, so
  the placement and profile kernels are measured on both backends; results
  in `docs/benchmarks.md` and the committed local artefact
  `benchmarks/results/geometry_tessellation.local.json`.

Bounded claims — what is NOT claimed:

- The kernels tessellate analytic surfaces from declared parameters; no
  body is a CAD solid, an equilibrium boundary or an engineering model, and
  no material property, load, field or neutronic quantity is carried.
- No value describes, approximates or validates any real machine; the
  benchmark measures tessellation cost, not physics.
- Maturity stays `computational_prototype`.

### Spherical bodies

Design record: `docs/adr/0013-spherical-bodies.md`.

- The sphere profile sampled uniformly in **polar angle**, taken from the
  first half turn of `circle_points` on twice the ring count. Both poles
  land on exactly `centre ± radius` with a radius of exactly zero and the
  equator on exactly the centre with the sphere's own radius, all asserted
  as equalities rather than tolerances because the angles come from the
  deterministic circle kernel rather than from an approximation.
- The reason that sampling was chosen over uniform sampling in height,
  asserted rather than stated: the volume deficit falls as the square of
  the ring count, the ratio between successive doublings measured at
  3.990, 3.998, 3.999 and 4.000.
- Heights strictly increasing at every ring count from two to 1024.
- The documented vertex and face counts, and the mesh volume equal to the
  profile volume times the inscribed-polygon ratio at every ring count —
  which is what shows the polar and circumferential resolutions are
  independent.
- The spherical shell as two closed surfaces with the inner one reversed:
  exactly twice a sphere's vertices and faces, a volume equal to the
  difference of the two spheres and an area equal to their sum. The volume
  is asserted within a relative tolerance, measured at 213 units in the
  last place at eight rings and 357 at thirty-two.
- Fail-closed refusal of a ring count below two, of a non-finite centre,
  and of radii that do not nest, each naming its field.


## Numerics kernels

Evidence record of the `numerics` kernel group (`computational_prototype`;
design records: `docs/adr/0003-numerics-transcendental-kernels.md` and
`docs/adr/0005-numerics-bessel-kernels.md`; kernels `numerics_transcendental`
and `numerics_bessel` in `kernels-domain.json`).

What is exercised, all under the 100 % statement-and-branch coverage gate
(`src/scpn_reactor_kernels/numerics/`):

- **Constants**: every literal is proven to be the correctly rounded
  double it claims (`ln 2`, `1/ln 2`, `sqrt(1/2)`, the smallest normal),
  the Cody–Waite parts sum exactly to `ln 2`, and integer multiples of the
  high part up to `|k| = 1100` are proven exact with rational arithmetic.
- **Binary decomposition**: `x = m 2^k` exactly (rational check) with
  `m` in `[sqrt(1/2), sqrt(2))` from the smallest normal to the largest
  finite double.
- **Exact points**: `ln 1 = 0`, `ln 2^k = k ln 2` for every normal
  exponent, `exp 0 = 1`, `x^0 = 1`, `2^10 = 1024`.
- **Accuracy against the platform `math` module** (the evidence bound,
  not a correct-rounding claim): the logarithm within `1e-15` relative on
  a 50 000-point seeded sweep of the whole normal range and a second sweep
  of `[0.5, 2]`; the exponential within `1e-15` relative on sweeps of
  `[-708, 709]` and `[-1, 1]` and at both domain edges (the lower edge
  staying a normal number); the power within `1e-13` relative for bases in
  `[e^-20, e^20]` and exponents in `[-5, 5]`; both series pieces on their
  reduced intervals; the inverse identities `exp(ln x) = x` and
  `ln(exp y) = y` within `2e-13`.
- **Monotonicity** on dense grids of both kernels (no series glitch).
- **Refusals**: non-finite, zero, negative and subnormal logarithm
  arguments; non-finite and out-of-domain exponential arguments; invalid
  bases, non-finite exponents and results that would overflow or be
  subnormal for the power; the error type sits under `KernelInputError`.
- **Native parity**: `rust/src/numerics/transcendental.rs` mirrors all
  three kernels; `tests/test_numerics_native_parity.py` compares float64
  bit patterns of 10 000-point seeded sweeps per kernel through both the
  scalar and the stream bindings, and the refusal paths of the bindings.
- **Benchmark**: `benchmarks/transcendental.py` per the ecosystem
  benchmark standard; results in `docs/benchmarks.md` and the committed
  local artefact `benchmarks/results/transcendental.local.json`.
- **Bessel functions `J0`, `J1`** (`bessel.py`; DLMF 10.2.2 series in
  Horner form, thirty terms, domain `|x| <= 8`): the two zero constants are
  proven to be the correctly rounded doubles of the OEIS expansions
  A115368 and A115369; both orders agree with an exact rational
  evaluation of the same series (sixty terms, `fractions.Fraction` on the
  exact binary argument) within `2e-14` absolute on a 400-point grid of the
  domain and around both zeros; the thirty-term truncation differs from
  sixty terms by less than `1e-15` at the domain edge; `J0(0) = 1` and
  `J1(0) = 0` exactly; `J0` is even and `J1` odd bit for bit; the OEIS
  zeros are zeros of the series within `1e-14` with the sign change; the
  derivative identity `J0' = -J1` holds to `1e-9` by central difference;
  non-finite and out-of-domain arguments are refused (the edges `±8` are
  admitted). Native parity: `rust/src/numerics/bessel.rs`; a 5 000-point
  seeded sweep through the scalar and stream bindings plus the refusal
  paths. Benchmark: `benchmarks/bessel.py`, artefact
  `benchmarks/results/bessel.local.json`.

Bounded claims — what is NOT claimed:

- The kernels are not correctly rounded; their accuracy is the measured
  bound above, and the power's error grows with `|y ln x|`; the Bessel
  series is exact-rational-verified only on `|x| <= 8` and refuses beyond.
- No value describes any physical quantity; the benchmark measures series
  cost, not physics.
- Maturity stays `computational_prototype`.

## CAD kernels

Evidence record of the `cad` kernel group (`computational_prototype`;
design records `docs/adr/0006-cad-kernels.md`,
`docs/adr/0008-cad-placement-kernel.md`,
`docs/adr/0009-cad-body-evidence-in-the-library.md` and
`docs/adr/0011-cad-axial-profile-primitive.md`,
`docs/adr/0012-bodies-that-close-on-the-axis.md`,
`docs/adr/0015-bodies-without-curvature.md` and
`docs/adr/0018-cad-aimed-placement.md`; kernels
`cad_brep_solids`, `cad_step_export`, `cad_faceting`, `cad_volume_mesh`,
`cad_profiles`, `cad_evidence` and `cad_placement` in
`kernels-domain.json`). The group adapts two pinned third-party kernels
(CadQuery 2.8.0 on OpenCASCADE 7.9 and gmsh 4.15.2) behind the optional
extra `cad`; the evidence class is stated below and differs from the
bit-exact groups.

What is exercised, all under the 100 % statement-and-branch coverage gate
(`src/scpn_reactor_kernels/cad/`; the library's CI installs the extra, so
none of it is skipped there):

- **Back-end loading**: a missing back-end is refused by name with the
  install hint (`CadUnavailableError`, a `KernelInputError`), the
  version report falls back to `unavailable` per back-end, and nothing
  outside the group imports the back-ends.
- **B-rep solids** (`solids.py`): the cylinder and the annular tube built
  by the kernel agree with the analytic volume and area of the primitive
  within `1e-9` relative (measured `0` and `1.5e-16` in the local run);
  bounding boxes agree exactly with the extents and are taken from the
  geometry alone, so faceting a body does not move its box and does not
  change the assembly manifest digest (regression test); every argument
  is validated before the kernel is asked for a shape; the assembly keeps the body
  order, refuses empty lists and duplicate names, and its manifest is
  canonical with a stable digest.
- **STEP export** (`step.py`): two exports of one assembly are
  byte-identical, including past the digit boundary of the writer's
  process-wide usage-occurrence counter (six-body assembly exported
  repeatedly in one process) and across an interleaved in-process STEP
  import (the writer's continuation lines are unfolded before the
  identifiers are renumbered, so the wrap column cannot leak the
  pre-renumbering identifier lengths); the header carries the fixed file
  name and time stamp,
  the generator name and the caller's provenance with Part 21 escaping
  (apostrophes doubled); the usage-occurrence identifiers are renumbered
  from one in order; different extras change the bytes and the digest;
  re-importing the written file reproduces both volumes within `1e-9`;
  non-JSON extras and a writer output without the header entities are
  refused.
- **Faceting** (`facet.py`): the faceted cylinder and tube validate as
  closed, outward-oriented `TriangleMesh` bodies (the G1 contract); the
  faceted volume lies below the analytic one within the declared bound
  `2 d / r` (measured deficit `2.0e-4` against the bound `4.0e-3` at
  `d = 1e-4 m`, `r = 0.05 m`); the tube's area is within 1 % of the
  analytic one; the exact inscribed-polygon ratio equals the G1 prism
  volume ratio to `1e-12` for 8, 16 and 64 segments; the weld merges only
  exact duplicates and keeps first-occurrence order; non-positive
  deflections are refused; the faceted bodies pass through the STL
  exporter unchanged.
- **Volume mesh** (`volume_mesh.py`): two runs on the same STEP bytes
  give the same MSH 4.1 bytes and digest; the sum of the tetrahedra
  volumes agrees with the B-rep total within 2 % and per entity within
  3 % at a characteristic length of `0.02 m` (the chordal deficit of the
  declared coarseness, not a kernel error); the summary carries node and
  element counts per entity; the unit right tetrahedron has volume `1/6`
  independent of orientation; empty STEP bytes, non-positive lengths, a
  STEP without a volume and a non-tetrahedral element type are refused,
  and the back-end is finalised on every path.
- **Placement** (`placement.py`): a translated body carries the analytic
  closed forms of its source unchanged and its own measured volume and
  area stay within `1e-9` relative of them; the bounding box shifts by
  exactly the offset in every component; the identity (role, material
  token) survives and the caller may rename a member of a ring; faceting
  a placed solid agrees in volume with the tier-G1 mesh of the same body
  translated by the same offset, within the exact inscribed-polygon
  deficit bound of the reference tessellation; a ring built on the
  tier-G1 `ring_offsets` puts every member's box centre on the circle to
  `1e-9`; non-finite offsets are named in the refusal, and the ring
  refuses an empty centre list, a mismatched name count and repeated
  names. One test states the boundary of the evidence class explicitly:
  the back-end integrates over the moved surface, so the measured volumes
  of identical placed bodies are NOT required to be equal to one another
  — only to agree with the analytic form within the declared tolerance.
- **Aimed placement** (`placement.py`, ADR 0018): a body placed with the
  tier-G1 aiming rotation carries the analytic closed forms unchanged;
  over the thirty placements of a printed node set its measured volume
  and area depart from those forms by at most `4.0e-16` relative,
  measured; the frame the back-end builds from the rotation departs from
  the rotation by at most `1.1102230246251565e-16` in any component,
  which is the assertion that says both tiers are placed in one frame;
  the box of a placed cylinder has its midpoint at `R - L/2` from the
  centre of the sphere rather than `R + L/2`, which is what aiming it
  inward means; and a scaling, a reflection, a non-finite entry, a
  non-finite centre, an empty name, mismatched sequences and repeated
  names are all refused.
- **Axial profiles** (`profiles.py`): the revolved solid and the revolved
  tube agree with the exact frustum-stack closed forms — volume and area,
  end discs and annuli included — within the declared `1e-9` relative
  tolerance (measured `1.4e-16` on the solid and `2.0e-15` on the tube in
  the reference environment); a two-sample constant profile carries the
  identical analytic references as the extruded cylinder, and a pair of
  them the identical references as the extruded tube; faceting the
  revolved solid agrees in volume with the tier-G1 mesh of the same
  profile within the exact polygon deficit of the reference count, which
  is the test that the two tiers describe one body rather than two similar
  ones; the body assembles and its manifest record carries the usual
  measures; and the profile contract is the tier-G1 contract, reused
  rather than restated, so every rejection carries the geometry group's
  wording and sample index under the CAD error type.
- **Bodies that close on the axis** (`profiles.py`:
  `closed_profiled_solid_brep`, ADR 0012): a revolved separatrix and a
  revolved cone agree with the same two closed forms within the declared
  tolerance, with no new formula on either side — a pole contributes no
  disc, so the cone's area carries exactly one disc term and the
  separatrix's none. Faceting the closed body agrees with its tier-G1
  twin, which is the same two-tiers-one-body test the open profile
  carries. The contract is again the tier-G1 contract under the CAD error
  type.
- **A measured limit of the revolution** (`profiles.py`, ADR 0012
  addendum): the revolved volume stops matching the exact frustum sum when
  two adjacent profile radii come close together — exact to 2e-16 where
  the radii are well separated, between 5e-5 and 3e-4 as they crowd, on a
  deliberately flat-topped polyline. The limit is the CAD back-end's, not
  the closed profile's: the open primitive shows the same numbers for the
  same shape lifted off the axis, and the tier-G1 tessellation is exact
  for every one of those profiles. A test pins the behaviour on both sides
  of the threshold, for the open and the closed primitive, and asserts
  that tier G1 builds them all. No bound is promised; what protects a
  consumer is the evidence kernel, which refuses a body whose measured
  volume misses its analytic form by more than the measure tolerance.
- **Welding at a pole** (`facet.py`, ADR 0012): faceting a body that comes
  to a point exposed a defect no previously buildable body could show. The
  mesher emits several distinct parametric vertices at the apex; they weld
  to one index by exact coordinate equality, and a triangle spanning two
  of them collapses to a repeated index, which the mesh contract refuses.
  `weld` now drops a triangle it has collapsed. **The mesh contract is
  unchanged and was not relaxed**: the dropped triangle has zero area, and
  its two non-degenerate directed edges are each other's reverse and
  cancel within the face itself, so every other face's edge pairing is
  exactly as it was and a genuine duplicate or orientation fault still
  fails. A test builds the collapse deliberately and asserts that the
  triangle which does not collapse survives untouched; every existing
  faceting test passes unchanged, which is the evidence that no body built
  before this record loses a face.
- **Body evidence** (`evidence.py`): the checked record of one body
  carries every measured value next to the bound it is under, and refuses
  at construction — each of the four bounds (both measure tolerances, the
  chord deficit of the faceting, the polygon deficit against the tier-G1
  mesh) is proven to raise, naming the body and the bound; the assembly
  form keeps the body order and refuses a ragged input rather than
  zipping four sequences of different lengths into a short answer; the
  record is frozen after it has been checked.
- **Benchmark**: `benchmarks/cad.py` per the ecosystem benchmark standard
  (seven operations, back-end versions in the provenance); results in
  `docs/benchmarks.md` and the committed local artefact
  `benchmarks/results/cad.local.json`.

Bounded claims — what is NOT claimed:

- No bit-exact parity: the B-rep and meshing kernels are third-party C++
  code; the library proves agreement with analytic closed forms within
  declared tolerances and determinism within one environment, recorded
  with the back-end versions. Identity of STEP or MSH bytes across
  OpenCASCADE or gmsh versions is not claimed.
- The faceting and the volume mesh are approximations whose deficits are
  bounded, not eliminated; they are inputs to simulation lanes, not
  results of any simulation.
- No body describes any device; no engineering, neutronic or structural
  quantity is carried. Maturity stays `computational_prototype`.

### B-rep spherical bodies

Design record: `docs/adr/0014-cad-spherical-bodies.md`.

- The sphere as its profile revolved, with no disc at either pole, and its
  analytic references equal to the frustum stack of that profile.
- **The shell's polyline touches the axis along two segments**, where the
  cavity's poles sit inside the outer body, and there is no way to bound
  the region without them. The back-end accepts it and the revolved volume
  equals the difference of the two frustum stacks exactly: relative error
  zero at sixteen rings and of order 1e-16 at sixty-four, against a
  declared tolerance of 1e-9.
- A vanishing cavity approaching the solid sphere, with the gap falling as
  the cube of the cavity radius — asserted to a part in a billion, which
  is what a sphere's volume does and a mistaken construction would not.
- Both builders refusing by the caller's own field names. The first draft
  of the shell let the profile builder report both radii as `radius_m`,
  so the two tiers refused the same input differently; a test asserts the
  names and the builder now validates them itself.

## Bodies without curvature

Evidence record of the rectangular prism and the faceting regime it
needs (`computational_prototype`; design record
`docs/adr/0015-bodies-without-curvature.md`; kernels
`geometry_primitives`, `cad_brep_solids`, `cad_faceting` and
`cad_evidence` in `kernels-domain.json`).

**Until this was added every body in this library was a solid of
revolution**, and two module descriptions said so. Both are corrected
rather than widened, because a consuming family words its non-claims
around them.

What is exercised, under the same 100 % statement-and-branch gate:

- The tier-G1 prism: exactly 8 vertices and 12 triangles, closed and
  outward-oriented under the mesh contract, its volume and area equal to
  the analytic closed forms, centred on the axis in `x` and `y` and
  spanning its declared axial extent, each of its three dimensions
  entering the volume exactly once, and every side and extent refused by
  name.
- **That it takes no segment count**, asserted on the signature itself
  against the cylinder's, because the absence is the statement: there is
  no inscribed approximation here to refine.
- The B-rep prism against the same closed forms within the measure
  tolerance, and every side and extent refused by name.
- `facet_bounds` in both regimes, and an assembly that mixes a curved
  body with a planar one, each carrying its own bounds in order.

Measured, rather than assumed:

- **A prism is faceted exactly.** Over nine prisms spanning 1 micrometre
  to 10 metres and aspect ratios to 1000:1, at every linear deflection
  the back-end accepts (1e-7 to 1.0) and angular deflections from 0.01 to
  1.0 rad, the mesher returned 8 vertices and 12 triangles every time and
  neither deflection changed any measure. Worst relative volume
  deviation: **2.581e-16**, falling on either side of the analytic value.
- **The circular bounds would have been decorative.** Supplying the
  half-width as a radius gives a chord bound eleven orders above that
  deviation, and the polygon bound is 0.0997 against a measured
  difference of exactly zero. A test states both.
- **The declared planar tolerance is `1e-12`**: four orders above the
  measured ceiling as a stated margin, three orders below the curved
  bodies' measure tolerance. A test proves it still refuses a prism wrong
  by one part in ten thousand, so it is not decorative in the other
  direction.
- **The back-end has its own deflection floor**, unrelated to the body:
  a 1 m prism is refused below about 1e-7 m with a numeric error from the
  mesher. Recorded because it bounds what any consumer at that scale may
  ask for.

A defect this exposed, and fixed for every body:

- The faceted-volume deviation was compared **one-sidedly**
  (`deficit > bound`), so a faceted volume arbitrarily *larger* than its
  analytic form passed without comment. It is now compared in magnitude.
  No curved body's evidence changes, because an inscribed faceting always
  undershoots; the change is a strict tightening, and it surfaced only
  because a prism's deviation is signed.

## Evidence that cannot certify itself

Evidence record of the fail-closed contract of `cad_evidence`
(`computational_prototype`; kernel `cad_evidence` in
`kernels-domain.json`; module
`src/scpn_reactor_kernels/cad/evidence.py`).

**Every bound in this kernel used to be a bare comparison against a
number the caller handed in, and a bare comparison is not a check.** An
independent probe of the public constructor accepted four records that
describe nothing:

| Record | Why it was admitted |
|---|---|
| `volume_relative_error = nan` | a NaN compares `False` against a bound and against its negation |
| `volume_relative_error = -1.0` | a negative magnitude passes any *must not exceed* test |
| `faceted_volume_deficit_bound = nan` beside a deficit of `1e100` | the bound itself was never checked |
| analytic volume 1, B-rep volume 100, claimed error 0 | the claim was never confronted with the measures |

All four are now refused at construction, each naming the field that
refused it, and each is a regression test.

What is exercised, under the same 100 % statement-and-branch gate — 80
tests over 95 statements and 34 branches of the module:

- Every one of the twelve numeric fields against `nan`, `+inf` and
  `-inf`; every one of the six measures against zero and a negative
  value; every one of the five magnitudes against a negative value; each
  of the three identity fields against the empty string.
- **Each bound at its exact value and at the representable neighbours
  either side, constructed from raw measures rather than from an
  injected error.** An analytic volume of `1e9` against a B-rep volume of
  `1e9 + 1.0` gives a relative error of exactly `1e-9`, which is the
  declared measure tolerance to the bit; one unit in the last place above
  that volume is refused and one below is accepted.
- A signed deficit on both sides, with a faceted volume that overshoots
  accepted within the bound and refused beyond it.
- A recomputed ratio that overflows to infinity from finite measures with
  a positive denominator, which the supplied fields alone cannot catch.
- Identity mismatches one component at a time, in the faceting and in the
  reference mesh, and an assembly handed its reference meshes in the
  wrong order.
- Real curved and planar bodies, and an assembly that mixes them.

Measured, rather than assumed:

- **The recomputation is bit-exact through the public path, so the
  consistency check needs no allowance and is granted none.** Over the
  library's cylinder, tube and prism, all four derived quantities equal
  the values the record's own measures give, bit for bit:

  | Body | volume error | area error | deficit | mesh difference |
  |---|---|---|---|---|
  | cylinder | `0.0` | `0.0` | `1.986277073990545e-4` | `1.406979256978618e-3` |
  | tube | `1.533832311662575e-16` | `0.0` | `9.23432639085042e-5` | `1.513263700469106e-3` |
  | prism | `2.509727251123853e-16` | `1.1800839972631342e-16` | `-1.2548636255619264e-16` | `0.0` |

  An allowance would have been room for a claimed error to drift from the
  geometry it claims to describe, and nothing in the measurement asks for
  one.
- **The bounds are compared against the recomputed values, not the
  supplied ones.** The practical consequence is that a bound can no
  longer be tripped by overwriting an error field — a test must move a
  measure — which is what the previous test module did and why it proved
  less than it appeared to.

The change refuses where there was no refusal; no valid record's values
change. A consumer that builds evidence through `body_evidence` or
`assembly_evidence` is unaffected, and one constructing `BodyEvidence`
directly must supply measures its errors agree with.

## A volume that survives being moved

Evidence record of the translation stability of the mesh measure
(`computational_prototype`; kernel `geometry_mesh_contract` in
`kernels-domain.json`; modules
`src/scpn_reactor_kernels/geometry/mesh.py` and
`rust/src/geometry/mesh.rs`).

**The divergence theorem is exactly translation-invariant in real
arithmetic and catastrophically is not in floating point.** Summed over
products of absolute coordinates, each term grows with the square of the
distance to the origin while the total does not, so a body away from the
origin was measured as a difference of large numbers. The previous form
did exactly that.

What it did, measured against the exact rational value of the same
meshes:

| Case | Previous relative error |
|---|---|
| unit tetrahedron at the origin | `5.55e-17` |
| the same at `(1e8, 1e8, 1e8)` | `2.00e8` — returned `33333333.333333332` |
| the same at `(-1e8, 1e8, -1e8)` | returned **exactly zero** |
| cylinder at 10 km | `3.13e-2` — three per cent |
| sphere at `1e8` m | `1.26e9` |

The zero is the one to keep in mind. It is not a large error; it is a
closed body reported as having no volume, silently, with the sign lost
as well as the magnitude.

The measure is now summed about the mesh's own first vertex and
accumulated with a compensation that keeps the part of each term the
running total was too large to hold. **The operation order is contract,
not implementation detail**, because the parity tests compare float64 bit
patterns between the two languages.

What is exercised, under the same 100 % statement-and-branch gate — 36
tests over 107 statements and 38 branches of the Python module, and four
Rust tests:

- The tetrahedron at eight offsets to `1e8` m, including mixed signs and
  a single-axis move, recovering one sixth; and the stronger claim that
  at exactly representable offsets the answer is **bit-identical** to the
  unmoved one, not merely close.
- Four body families — cylinder, annular tube, sphere and spherical
  shell — at two segment counts and three offsets, each scored against
  **the exact value of the divergence-theorem sum computed in rational
  arithmetic**. That oracle is independent of both implementations, which
  is the point: two backends agreeing is not evidence that either is
  right.
- A uniformly inward mesh keeping a negative volume a hundred thousand
  kilometres from the origin.
- Bit-exact Python-to-Rust parity on translated bodies at four offsets,
  not only at the origin. A native kernel that reordered the compensation
  would agree at the origin and differ here.
- An empty vertex slice measuring zero in the native kernel rather than
  indexing past the end, which is what the previous form did and which no
  validated mesh can reach.

Measured, rather than assumed:

- **Worst relative error against the exact rational value: `5.8e-16`**,
  over four body families at five offsets from the origin to `1e8` m.
  The previous form's worst over the same set was `1.26e9`.
- **The compensation is not decorative.** Dropping it while keeping the
  local origin gives a worst error of `1.10e-14` — nineteen times worse
  — and on the spherical shell alone, whose nineteen hundred faces cancel
  between the outer surface and the cavity, `1.10e-14` against
  `7.85e-17`. A test asserts the ratio, so the compensation cannot
  quietly become a no-op.
- **A bounding-box midpoint was measured as the alternative origin** and
  is better by about a quarter in the worst case, `4.22e-16` against
  `5.76e-16`. It was not adopted: it needs a reduction over every vertex
  and a division reproduced bit-exactly in a second language, for a gain
  two orders inside the coordinate resolution that already bounds the
  answer.
- **Translation drift is a different quantity and no summation improves
  it.** Translating a mesh rounds every coordinate at the new magnitude,
  so the body itself changes shape; the fixture drift is compared against
  `3 * ulp(offset) / L` at the smallest feature `L`. Over four bodies at
  offsets from 100 m to `1e8` m the measured drift never exceeded
  **9.4 %** of that bound.

Compatibility, before and after:

| Consumer surface | Before | After |
|---|---|---|
| canonical mesh bytes and digest | vertices and faces only | unchanged |
| body volume of a consuming family's five bodies | — | moves by `6.5e-16` to `2.9e-14` relative |
| that family's two device-state record digests | — | both change |

**This is a breaking change of the mesh measure**, because it alters a
kernel's output for valid inputs. The movement is the size of the error
the previous form carried and is towards the exact value. Consumers
embed volumes in digested records and must regenerate their fixture
digests when they move their pin; no consumer sees the change until then,
because each pins this library at a commit.

## Measures the format can hold, and measures it cannot

Evidence record of the exponent-range behaviour of the mesh measures
(`computational_prototype`; kernel `geometry_mesh_contract` in
`kernels-domain.json`; modules
`src/scpn_reactor_kernels/geometry/mesh.py` and
`rust/src/geometry/mesh.rs`).

**A norm computed as the square root of a sum of squares leaves the
exponent range long before its own answer does.** Squaring costs half the
range in each direction, so a body whose area is an ordinary double was
measured as infinity at one end and, at the other, refused as a
degenerate triangle.

What the previous form did, with the boundaries bisected rather than
estimated:

| | Previous | Now |
|---|---|---|
| smallest scale with a correct area | `9.543299509722758e-79` | `2.222758749485082e-162` (tested face-area cutoff) |
| largest scale with a correct area | `8.798296151866603e+76` | `8.716619296087305e+153` |
| at a scale of `1e100` | area `inf`, exact `2.37e200` | correct |
| far enough down | **triangle refused as degenerate** | measured |

About 160 orders of magnitude of representable results were being
discarded.

The repair rescales the norm by the largest component **only where the
direct sum of squares would fail** — it is kept wherever the sum lands on
a finite normal double.

What is exercised, under the same 100 % statement-and-branch gate — dedicated public
tests over the current module of the Python module, and eight
Rust tests:

- Areas at scales whose squares overflow (`1e77` to `1e153`) and whose
  squares fall subnormal (`1e-100` to `1e-160`), each against the closed
  form.
- **That nothing which already worked has moved**, asserted bit for bit
  against the previous expression at five ordinary scales, and measured
  separately over 3660 face norms and five body areas of the library's
  cylinder, tube, prism, sphere and shell: every one identical.
- The largest measurable scale and **the very next representable double**,
  which is refused by name.
- The deep subnormal band, scored against the exact area of the vertices
  actually handed in — not of the body they approximate, which at that
  scale is a different thing.
- A genuinely collinear triangle still refused, and its nearest
  non-degenerate neighbour now measured instead of refused with the same
  message.
- A record refusing to serialise a measure it cannot hold.
- Bit-exact Python-to-Rust parity at five scales spanning both branches,
  and the stated split where the two differ.

## Extreme-coordinate range and final-value checks

Current range checks additionally exercise power-of-two scaling before cross
products and determinants overflow. At tetrahedron scale `8e153` the surface
area is approximately `1.5142562584220406e308`; at scale `8e102` the volume is
approximately `8.533333333333333e307`. Both are finite despite overflowing
unscaled intermediate values. A triangle with orthogonal edges `1.4e154`
returns area `9.8e307` and unit normal `(0, 0, 1)`.

The historical half-maximum area ceiling and refusal at volume scale `1e103`
were intermediate arithmetic defects, not limits of the final quantities.
Dedicated tests now compare those results with rational/Decimal oracles.
For subnormal total areas, the scaled face sum is rounded back only once;
normal-range calculations retain the original arithmetic order where finite.
Python and Rust share bounded power-of-two multiplication steps. Truly
unrepresentable public face areas raise GeometryError; mesh validation may
therefore reject such faces before a summary is requested. The low-level Rust
measure functions retain IEEE nonfinite results for unrepresentable measures.

Scaling extends the tested dynamic range; it does not prove accuracy for all
ill-conditioned or extremely anisotropic meshes. Test oracle tolerances apply
to their recorded geometries, not a universal error bound.

## Geometry a container can hold, and geometry it cannot

Evidence record of the float32 storage contract of the open-format exports
(`computational_prototype`; kernel `geometry_exports` in
`kernels-domain.json`; module
`src/scpn_reactor_kernels/geometry/export.py`).

**Binary STL and glTF both store positions as float32, and neither writer
used to look at what that did.** A tetrahedron one metre across, on a grid
`1e8` m from the origin, was written by both containers as four corners
that decode to a single point and four triangles of zero area. The bytes
were otherwise perfect: correct header, correct triangle count, correct
length, repeatable. Reproducer:
`evidence/claude_k04/k04_reproducer.py`.

### What float32 actually costs, measured before anything was chosen

A float32 holds about seven decimal digits, so what survives storage is
not a body's size but the ratio between its coordinates and its smallest
feature. Measured on the fixture bodies, whose finest wall is one
centimetre:

| Offset from the origin | Worst relative facet-area error | Collapsed facets |
|---|---|---|
| 0 m | `7.17e-7` | 0 |
| 100 m | `1.03e-3` | 0 |
| 10 km | `1.16e-1` | 0 |
| 100 km | `3.62e-1` | 0 |
| 200 km | — | 16 |

**The collapse the audit reported is the end of the damage, not the
start.** Four decades of silent, unbounded error come first, and a check
for degenerate triangles alone passes every one of them.

### The contract both writers enforce

Every stored coordinate is inside the float32 range, no facet collapses,
and no facet's area changes by more than `EXPORT_AREA_TOLERANCE`
(`1.0e-3`). The bound was chosen from the bodies that exist rather than
from the format: across the **fifty bodies of the six device families**
that use these writers the worst measured loss is `5.61e-6`, and the
library's own fixtures sit at `7.7e-7`, so the bound is about a hundred
and eighty times above anything real. It cannot be tightened much
further, because a rebased body is no better than the same body at the
origin and the tube is already at `7.2e-7` there. Measurement:
`evidence/claude_k04/tolerance_scan.json` and `device_bodies.txt`.

The contract is versioned in `EXPORT_STORAGE_CONTRACT` rather than in
`STL_HEADER` or `GLTF_GENERATOR`, because those strings are in every byte
stream the library produces and changing them would rewrite every export
in order to distinguish a corpus of older files that measurably does not
exist: no `.stl`, `.glb` or `.gltf` is committed in this repository or in
any of the six consumer repositories, and no consumer records a digest of
export bytes.

### What each container can offer instead of refusing

**GLB has a node transform.** A body that does not survive absolute
storage is stored about the midpoint of its own bounding box with that
midpoint in the node's `translation`, which composes with the mesh and
leaves the body where it was. The reported tetrahedron is carried at
`1e12` m — a hundred million times its previous usable offset — with its
facet areas inside the tolerance.

**Binary STL has no transform of any kind**, so a rebase there really does
move the device. The writer refuses and names the translation that would
work; a caller passes it through the new `translation_m` argument and owns
the value afterwards, because the file cannot record it. A refusal names a
remedy only after measuring that the remedy works on the bodies that were
refused.

The rebase is an ordinary double. Two cheaper rules were measured on the
same bodies from the origin to `1e12` m and both are far worse: rounding
the midpoint to a float32 costs `8.0e-2` at `1e12`, and snapping it to a
power of two collapses facets from `1e6` upwards. The midpoint leaves a
rebased body exactly as accurate as the same body at the origin, `7.17e-7`
at every offset measured. Evidence:
`evidence/claude_k04/translation_candidates.json`.

### Boundaries, bisected rather than estimated

| | Largest accepted | Smallest refused |
|---|---|---|
| offset of a one-metre tetrahedron | `16484177.499999998` | `16484177.5` |
| offset of the fixture bodies | `63.99925751495179` | `63.9992575149518` |
| coordinate magnitude | `3.4028234663852886e+38` | the next double above |

Each pair is two adjacent doubles, so every refusal test asserts the
nearest failing case. Evidence: `evidence/claude_k04/boundaries.json`.

A coordinate above the float32 range previously escaped as
`OverflowError` from the standard library, which named neither the body
nor the vertex and was in neither writer's documented contract. It is now
a `GeometryError` naming both. The range is checked **before** anything is
converted, because the conversion is what raised; the first draft of this
repair checked afterwards and the reproducer caught it.

### Nothing that was already right moved

Every export of the library's four fixture sets and of **all fifty bodies
of the six device families** is byte-for-byte identical to the bytes the
previous writer produced, and each of those six repositories' own export
tests — 49 in total — passes against the repaired writer unchanged.
Evidence: `evidence/claude_k04/byte_identity.json` and
`consumer_impact.txt`.

### What is exercised, under a 100 % statement-and-branch gate

30 tests over 152 statements and 40 branches of the module:

- Both containers decoded with spec-level readers and **every triangle
  measured again from its decoded float32 corners**, against an area
  formula written out in the tests rather than taken from the code that
  decides. Testing headers, lengths or byte repeatability passes on the
  collapsed file.
- The reported collapse refused by STL and carried by GLB, with the node
  translation composed back and the world positions recovered.
- The boundaries above, each asserted at the adjacent double.
- A fine feature at the origin stored, and the same feature at the far end
  of a metre-long body refused — **the size of a feature is not what
  decides; where it sits is**, and a writer gated on feature size would
  get both wrong.
- A translation that destroys the body in doubles before any float32
  rounding, refused as such.
- A translation that is not three finite numbers, refused per component
  and for its arity.
- Both branches of the remedy: the translation that works, and a body
  the recommended midpoint does not recover.
- Ordinary documents carrying no `translation` key at all.

## Gmsh session ownership

ADR 0019 selects refusal of pre-initialised caller sessions. The reviewed
borrow-and-restore candidate left derived state changed and is not shipped.
The public call checks ownership under its lock before Gmsh mutations, raises
CadError for an existing session, and otherwise initialises with
interruptible=False and finalises from finally. Worker-thread calls are
supported through serial owned sessions. External Gmsh access must not race
these calls; process isolation is required for independent concurrent sessions.

Real-backend tests retain caller model entities, options and bounding-box state
on valid and invalid STEP refusals; measure deterministic owned meshes; verify
worker-thread use and cleanup after an actual unsupported-element result.
No mocked backend establishes any lifecycle claim.

## A row that was checked by whatever unpacked it next

Evidence record of the public mesh boundary (`computational_prototype`;
kernel `geometry_mesh_contract` in `kernels-domain.json`; modules
`src/scpn_reactor_kernels/geometry/mesh.py` and the native entry points
in `rust/src/lib.rs`).

`TriangleMesh` validated that coordinates were finite and that indices
were in range. **It did not validate the shape or the type of a row**,
and the consequence is that each consumer of a row checked it
differently, or not at all. Reproducer:
`evidence/claude_k06/k06_reproducer.py`.

| Malformed row | Construction | Where it actually failed |
|---|---|---|
| vertex of four coordinates | **accepted** | `struct.error` in canonical bytes, digest, GLB and the summary record |
| vertex of two coordinates | `IndexError: tuple index out of range` | inside the face measure |
| coordinate that is a string | `TypeError: must be real number, not str` | inside `math.isfinite` |
| face index that is a float | `TypeError: tuple indices must be integers` | indexing the vertex list |
| rows given as lists | **accepted** | `TypeError: unhashable type: 'list'` on `hash()` |

None names the field, the row or the body; none is the error type this
module documents; and the first is the one the acceptance criterion is
about, because a validated mesh could not always be encoded by the
declared canonical layout.

### The contract now checked before anything indexes or unpacks

Exactly three components per row on both streams; a coordinate is a real
number and finite, named by row **and axis**; an index satisfies the
integer protocol, so an integer from another library is accepted while a
fractional one is refused rather than truncated. A boolean is refused on
both streams, and on the index stream it is now refused **as a type
rather than as a range**, which is the honest reason: `True` names vertex
one perfectly well; what is wrong is that a caller who wrote it did not
mean an index.

Rows are normalised into tuples of floats and ints on construction, which
makes the frozen, slotted, hashable dataclass truthful: lists are
accepted, `hash()` works, and the mesh no longer aliases a caller's
mutable rows.

### Nothing that was already valid moved

`evidence/claude_k06/digest_identity.json` and `device_digests.txt`.
Twelve library fixture bodies and the fifty bodies of the six device
families, each digest compared against the committed code: **all
identical**. A mesh built from lists, from tuples, or with integer
coordinates gives the same canonical bytes as the reference.

### The two boundaries, compared rather than assumed

`evidence/claude_k06/boundary_policy.json`. The native entry points were
asked the same malformed questions.

| Input | Native, before | Native, now | Python |
|---|---|---|---|
| stream not a multiple of three | refused | refused | refused |
| index out of range | refused | refused | refused |
| fractional index | refused, not coerced | refused, not coerced | refused, not coerced |
| **non-finite coordinate** | **accepted, returns NaN** | **refused, by row and axis** | refused, by row and axis |
| empty streams | accepted, `0.0` | accepted, `0.0` | refused: four vertices required |
| boolean index | accepted as `1` | accepted as `1` | refused as a type |

The non-finite case was a real gap: a NaN measure compares false against
every bound it is later checked against, which is precisely the failure
the evidence contract exists to prevent. It is closed in the same words
as the Python refusal.

**The last two rows are deliberate and are asserted in the suite**, so
neither can drift without a test saying so. The native entry points take
flat streams rather than a body, so they carry no minimum-body invariant:
an empty mesh has volume zero and that is the right answer for a raw
kernel, while `TriangleMesh` requires four vertices because a closed
surface does. A boolean index reaches the native side through the
back-end's own integer conversion, which this repository does not own.

### What is exercised, under a 100 % statement-and-branch gate

92 tests over 199 statements and 62 branches of the Python module:

- Every malformed row shape on both streams, and a stream that is not a
  sequence at all, each refused by field and row.
- Every non-real coordinate type and every non-integer index type,
  refused by row and position.
- An integer from another library accepted through `__index__`, because
  requiring the concrete `int` type would drop a capability for the sake
  of the check.
- A mesh built from mutable lists: normalised, hashable, equal in digest
  to the same mesh built from tuples, and **unaffected when the caller
  mutates the list afterwards**.
- All four encoding entry points on a validated mesh, which is the
  acceptance criterion stated as an assertion.
- The native boundary refusing a non-finite coordinate at two different
  rows and axes, refusing the shapes the constructor refuses, and the two
  declared differences.

## Breaking development version

Python floor and optional native distribution are `2.0.0.dev0`; the Rust crate
is `2.0.0-dev.0`. This major development generation explicitly marks changed
mesh measures and stricter CAD evidence/refusal contracts. Existing consumer
manifest records retain their old versions and source commits: none has been
silently migrated. Adopting consumers must regenerate measure-bearing digests,
run native/analytic checks and obtain fresh receiver acceptance. This local
version change is not a release or publication receipt.


### Exact neighbour regression and additional constructor refusal

The tetrahedron at scale 8.716619296087305e153 has exact area below float64's
maximum; its nextafter neighbour has exact area above it, checked with a
Decimal oracle over the actual binary input coordinates. The test requires
acceptance then refusal without an unchecked interval. An integer coordinate
outside float64's range now raises GeometryError instead of OverflowError.
The midpoint export helper is public; its recommendation is a heuristic,
not proof that every alternative translation or unit choice fails.
