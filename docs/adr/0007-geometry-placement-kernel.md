<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — ADR 0007
-->

# ADR 0007 — Placement kernel: bodies off the device axis

Status: accepted (2026-09-03). Adds the kernel `geometry_placement` and
generalises the unit circle of ADR 0002 to any point count.

## Context

The tier-G1 primitives build every body centred on the axis. Real machines
are not axisymmetric down to the last conductor: a plasma-focus cathode is a
squirrel cage of discrete rods on a coaxial circle, a coil set has feed
conductors, a vessel has ports. Until this record a device repository facing
such a part had exactly two options, and both were wrong: draw the part as an
axisymmetric substitute (a tube standing in for a cage of rods, which
misstates the geometry), or re-implement translation locally (which puts
geometry back into a device repository and breaks the single-implementation
rule of ADR 0002).

The first option was taken once, in the plasma-focus family, and the owner
ruled it out: the model must carry the real arrangement. This record removes
the reason it was taken.

## Decision

1. A new kernel `geometry_placement`
   (`src/scpn_reactor_kernels/geometry/placement.py`) provides the two exact
   operations placement needs:
   - `translate(vertices, dx, dy, dz)` — one IEEE-754 addition per coordinate
     in a fixed order, refusing an empty stream and non-finite offsets;
   - `ring_offsets(count, radius_m)` — the centres of `count` identical
     bodies equally spaced on a circle around the axis, each centre one
     multiplication of a circle point by the radius;
   - `ring_separation_m(count, radius_m)` — the centre-to-centre distance of
     neighbours, so a consumer can prove that bodies of a given radius on the
     ring do not intersect without implementing trigonometry of its own.
2. The unit circle of ADR 0002 is generalised: `circle_points(count)` returns
   the points for ANY count of at least three, and `unit_circle(segments)`
   becomes the tessellation entry point that validates the multiple-of-eight
   rule and returns those same points. There is one implementation, not two.
   The quadrant and the residue inside it come from integer arithmetic on
   `(k, count)`, so a point that falls on an axis is still exactly `0` and
   `±1`, and the residual angle is still reduced into `[0, pi/4]` before the
   polynomials run.
3. The generalisation is bit-preserving for every count that was already
   admissible: for a multiple of eight the new path evaluates the identical
   expressions on identically scaled operands, so `unit_circle` returns the
   same bits as before. This is asserted in the test suite (`unit_circle`
   equals `circle_points` for the tessellation counts), and the reference
   digests every consumer pins are therefore unchanged.
4. The native crate mirrors both: `circle_points`, `ring_offsets`,
   `ring_separation` and `translate` are bound, and the parity file compares
   float64 bit patterns for counts three to two hundred and fifty-seven, for
   ring offsets, for the separation and for a translated body.
5. Accuracy of the arbitrary-count circle is measured, not assumed: every
   point stays within `1e-15` of `libm` for the counts exercised, which is
   the same bound the multiple-of-eight circle carries. Bit-exactness across
   backends is the guarantee; agreement with `libm` is a measured property.
6. The geometry benchmark places a ring of twelve rods off the axis in the
   same pass, so the placement kernel is measured on both backends and the
   kernel's benchmark pointer stays valid.

## Consequences

A device repository can now model a part that is not on the axis without
writing geometry: it tessellates one body, asks for the ring offsets, and
translates. The first consumer of this kernel is the plasma-focus cathode,
which stops being an equivalent coaxial tube and becomes the rods it is.

`unit_circle` keeps its contract and its bits, so no consumer pin has to
move for correctness; consumers that want the new kernel re-pin as a governed
data change. The kernel inventory gains one entry and its digest changes, so
a consumer that re-pins records the new digest.

Nothing here describes a device: the kernel knows nothing about rods,
cathodes or coils, only about vertices and circles.
