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
design record: `docs/adr/0002-geometry-kernels.md`; kernels
`geometry_unit_circle`, `geometry_mesh_contract`, `geometry_primitives`,
`geometry_exports` in `kernels-domain.json`).

What is exercised, all under the 100 % statement-and-branch coverage gate
(`src/scpn_reactor_kernels/geometry/`):

- **Deterministic unit circle** (`trig.py`): vendored degree-15 sine and
  degree-16 cosine Taylor polynomials in Horner form on `[0, pi/4]` with
  exact octant and quadrant symmetry. Tests prove every point of circles
  with 8 to 4096 segments agrees with `math.cos`/`math.sin` to `1e-15`,
  that points at multiples of `pi/2` are exactly `0` and `±1`, that every
  quadrant is an exact sign/swap image of the first, that no negative zero
  is emitted, and that inadmissible segment counts (below 8, not a
  multiple of 8, booleans) are refused.
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
- **Exports** (`export.py`): binary STL (header, triangle count, unit
  normals, float32 vertices, zero attributes, exact byte length) and glTF
  2.0 binary of any body list (magic, version, chunk types and alignment,
  node names, accessor counts, types and `min`, buffer-view alignment,
  position and index streams read back, caller-supplied document extras)
  verified with minimal specification-level readers; determinism of the
  bytes; the file writers.
- **Native parity**: `rust/src/geometry/` mirrors the unit circle, both
  primitives, the signed volume and the surface area;
  `tests/test_geometry_native_parity.py` compares float64 bit patterns of
  every vertex coordinate, the face index streams and the measures, and
  the refusal paths of the bindings.
- **Benchmark**: `benchmarks/geometry_tessellation.py` per the ecosystem
  benchmark standard; results in `docs/benchmarks.md` and the committed
  local artefact `benchmarks/results/geometry_tessellation.local.json`.

Bounded claims — what is NOT claimed:

- The kernels tessellate analytic surfaces from declared parameters; no
  body is a CAD solid, an equilibrium boundary or an engineering model, and
  no material property, load, field or neutronic quantity is carried.
- No value describes, approximates or validates any real machine; the
  benchmark measures tessellation cost, not physics.
- Maturity stays `computational_prototype`.
