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

proves the Tier-0 local-scaffold machine profile (required and forbidden
paths, Git/remote boundary, workflow pins and permissions, badge non-claims,
JSON integrity, defensive ignore rules).

## Geometry kernels

Evidence record of the `geometry` kernel group (`computational_prototype`;
design records: `docs/adr/0002-geometry-kernels.md`,
`docs/adr/0007-geometry-placement-kernel.md` and
`docs/adr/0010-axial-profile-primitive.md`; kernels
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
- **Native parity**: `rust/src/geometry/` mirrors the circle points, both
  constant-radius primitives, both profiled primitives and their closed
  forms, the placement kernel, the signed volume and the surface area;
  `tests/test_geometry_native_parity.py` compares float64 bit patterns of
  every vertex coordinate, the face index streams, the measures, the circle
  points and ring offsets for counts 3 to 257, the ring separation, a
  translated body, a five-sample profiled solid and profiled tube, the
  frustum-stack volume and lateral area, and the refusal paths of the
  bindings.
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
`docs/adr/0011-cad-axial-profile-primitive.md`; kernels
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
