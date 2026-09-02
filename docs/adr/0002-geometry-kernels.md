<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — ADR 0002
-->

# ADR 0002 — Geometry kernels: deterministic tessellation, mesh contract, open exports

Status: accepted (2026-09-02). Adds the first implemented kernel group,
`geometry`, at `computational_prototype`.

## Context

The device 3D model lane needs, in every family, the same substrate: a
unit circle whose points are bit-exact across backends, closed and
consistently oriented triangle meshes with canonical digests, analytic
primitives tessellated in a fixed vertex and face order, and open-format
exports that carry provenance. `SCPN-Z-PINCH-CORE` landed exactly that
substrate for its own model; the library takes it over so no family
copies it.

## Decision

1. `trig.py`: vendored degree-15 sine and degree-16 cosine Taylor
   polynomials in Horner form on `[0, pi/4]` with exact octant and
   quadrant symmetry; segment counts are multiples of eight; no `libm`
   call. The same operation order is implemented in `rust/src/geometry/`.
2. `mesh.py`: `TriangleMesh` validates closure and orientation (every
   directed edge exactly once with its reverse), computes the signed
   volume (divergence theorem) and surface area with a fixed summation
   order, and serialises canonically (little-endian counts, float64
   vertices, uint32 faces) with a SHA-256 digest.
3. `primitives.py`: solid cylinder and annular tube on the `z` axis with
   fixed vertex and face order and outward orientation; further primitives
   (torus segment, spherical shell) are separate additions.
4. `export.py`: binary STL and glTF 2.0 binary of any validated body list,
   with caller-supplied document extras (a consumer places its schema,
   digests, units and non-claims there); float32 storage as the containers
   require, digests on the float64 bytes.
5. Native kernels mirror the unit circle, both primitives, the volume and
   the area; parity tests compare float64 bit patterns of every vertex
   coordinate, the face index streams and the measures.
6. Origin: the Python and Rust sources are the geometry modules of
   `SCPN-Z-PINCH-CORE` at its commit `598fa4c2`, renamed into this package
   and generalised only in the export entry points; `SCPN-Z-PINCH-CORE`
   retires its copies when it pins this library.

## Consequences

Four kernels enter the manifest (`geometry_unit_circle`,
`geometry_mesh_contract`, `geometry_primitives`, `geometry_exports`) at
`computational_prototype` with `VALIDATION.md#geometry-kernels` as their
evidence record; the claims inventory stays empty. Nothing here is a CAD
solid, an equilibrium boundary or an engineering model.
