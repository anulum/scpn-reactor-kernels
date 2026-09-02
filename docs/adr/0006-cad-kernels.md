<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — ADR 0006
-->

# ADR 0006 — CAD kernels (tier G2): B-rep solids, STEP, faceting and volume mesh on a pinned third-party kernel

Status: accepted (2026-09-03). Adds the kernel group `cad` (kernels
`cad_brep_solids`, `cad_step_export`, `cad_faceting`, `cad_volume_mesh`)
at `computational_prototype` behind the optional extra `cad`.

## Context

The device repositories' tier-G1 models (ADR 0002 consumers) are analytic
triangle meshes: enough for viewing, volumes and simple neutronics of
cylinders, not for engineering CAD or for finite-element and Monte-Carlo
meshing. The programme needs, from the same validated design point, B-rep
solids that any CAD or simulation tool consumes (STEP), a faceting that
returns the G1 mesh contract, and a tetrahedral volume mesh. Writing a
B-rep kernel is out of scope; OpenCASCADE (through CadQuery) and gmsh are
the free, mature tools, so the library adapts them. That changes the
evidence class of this group and the record states it.

## Decision

1. The group sits behind `[project.optional-dependencies] cad` with exact
   pins (`cadquery==2.8.0`, `gmsh==4.15.2`); nothing else in the library
   imports the back-ends, which load lazily and are refused by name
   (`CadUnavailableError`) with the install hint when absent. The library's
   own CI installs the extra so the group's tests never skip there;
   consumers skip hermetically without the extra.
2. `cad_brep_solids`: `cylinder_solid_brep` and `annular_tube_brep` take
   the argument lists of their G1 twins plus the body identity and return
   a `BrepBody` carrying the analytic volume and area of the primitive;
   the kernel's measured volume, area and bounding box are checked against
   the analytic forms within `MEASURE_TOLERANCE = 1e-9` relative.
   `BrepAssembly` keeps the bodies in order, refuses duplicates and
   projects a canonical manifest with a SHA-256 digest: the manifest is
   the record, the STEP file its export.
3. `cad_step_export`: the OpenCASCADE Part 21 writer's output is made
   deterministic by rewriting the `FILE_NAME` time stamp and name to fixed
   literals, renumbering the `NEXT_ASSEMBLY_USAGE_OCCURRENCE` identifiers
   (a process-wide counter in the writer) from one in order of appearance,
   and placing the generator name and the caller's JSON provenance into
   `FILE_DESCRIPTION` with Part 21 escaping; two exports of one assembly
   are byte-identical in one environment and a re-import reproduces the
   volumes within the tolerance.
4. `cad_faceting`: the incremental mesher's per-face triangles are welded
   by exact coordinate equality into one `TriangleMesh`, whose contract
   proves closure and outward orientation; the relative volume deficit of
   a circular body is bounded by `2 d / r` for linear deflection `d`, and
   the exact inscribed-polygon ratio `(n / 2 pi) sin(2 pi / n)` of the G1
   tessellation is exposed (from the unit-circle kernel) so a consumer can
   compare G1 and G2 bodies against the same analytic value.
5. `cad_volume_mesh`: gmsh imports the STEP into its OpenCASCADE model,
   meshes in three dimensions with a fixed option set and a declared
   characteristic length, and writes MSH 4.1 ASCII; the kernel sums the
   tetrahedra volumes per volume entity in fixed order so the mesh is
   checked against the B-rep volumes, and refuses any non-tetrahedral
   element. Two runs give the same bytes in one environment.
6. Evidence class: OpenCASCADE and gmsh are pinned third-party kernels
   (C++), not this library's bit-exact floor; `native_parity` is `false`
   for the group and the bit-exact rule (Python floor ↔ our Rust) does not
   apply inside them. Determinism is claimed per environment and recorded
   with the back-end versions (`backend_versions()`), never across
   versions; a version bump of the extra is a governed data change that
   re-pins every consumer's STEP and mesh digests.
7. A standard-conformant benchmark (`benchmarks/cad.py`) times the four
   operations with the back-end versions in its provenance; there is no
   Python-floor row by design.

## Consequences

Maturity stays `computational_prototype`; the claims inventory stays
empty; the manifest gains the owned domain
`shared_cad_and_meshing_adapters`. The tier-G2 lane of the research group
(its plan of 2026-09-03) consumes this group: the pilot device repository builds
the same named bodies as its G1 model, records the assembly manifest, the
STEP digest and the back-end versions, and proves its bodies against the
analytic forms and its faceting against the G1 volumes. Torus and sphere
primitives, DAGMC-ready faceting for OpenMC and per-body physical groups in
the volume mesh are separate increments with their own sources.
