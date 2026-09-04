<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — ADR 0017
-->

# ADR 0017 — Aiming a body, and placing it on a sphere

Status: accepted (2026-09-04). Extends the kernel `geometry_placement` of
ADR 0007 from translation to rigid placement, using the arbitrary-angle
circle point of ADR 0016.

## Context

ADR 0007 gave the library translation and a ring of centres on a circle in
a plane. That covers a squirrel cage of rods and a set of feed conductors,
and it is exactly as far as it goes: **there is no rotation anywhere in the
library**, so every body still stands parallel to the axis wherever it is
put.

A machine whose bodies converge on a point cannot be modelled that way. One
device family's filed source prints thirty bodies distributed among the
nodes of a truncated icosahedron on a spherical chamber, on four latitudes
at polar angles of 20.1, 59.0, 121.0 and 159.9 degrees with five, ten, ten
and five members, each pointing at the centre. A ring of bodies in one
plane is not that arrangement, and a body that cannot be pointed is not
that body; drawing either would be the substitute the fidelity rule
forbids, and this is the second time this rollout has met that exact
choice.

## Decision

1. `geometry/placement.py` gains the rigid half of placement:
   - `axis_direction(polar, azimuth)` — the unit direction of two circle
     points;
   - `aim_rotation(polar, azimuth)` — the rotation taking the positive `z`
     axis onto that direction;
   - `inward_aim(polar, azimuth)` — the same for a body on a sphere aimed
     back at its centre;
   - `rotate(vertices, rotation)` — three products and two additions per
     coordinate, in a fixed order;
   - `ring_azimuths(count, offset)` — the azimuths of a ring, twisted;
   - `sphere_ring_offsets(count, radius_m, polar, offset)` — the centres of
     one latitude;
   - `centre_separation_m(first, second)` — the distance between two
     centres, so a consumer can prove that bodies of a given radius do not
     intersect without implementing geometry of its own;
   - `require_rotation(name, rotation, error)` — the gate.
2. **The rotation is built from two angles, never from a direction
   vector.** This is the load-bearing decision and it was measured rather
   than reasoned about. The textbook minimal rotation from `z` to a unit
   vector `d` carries a `1 / (1 + d_z)` term. As `d` approaches the
   negative `z` axis, `d_z` resolves only to the last place of one, so that
   term loses every significant digit even though `d` is still a perfect
   unit vector. Measured on an accurately built direction one microradian
   short of half a turn, `R^T R` departs from the identity by **3.6e-4**.
   The form used here is `Rz(azimuth) Ry(polar)`, which has no such term.
   Scanned over two hundred thousand angle pairs including every
   quarter-turn corner and the antipode itself, its departure is at most
   **4.440892098500626e-16** and its determinant differs from one by at
   most **5.551115123125783e-16**, while its third column reproduces
   `axis_direction` bit for bit. A test in the suite computes both forms
   and asserts the difference, so the reason for the choice cannot be lost.
3. **Both entry points take circle points, not angles.** A ring's azimuths
   are rational multiples of a turn and come from `circle_points`, which is
   exact; only the latitude needs ADR 0016's reduction. Taking pairs rather
   than angles is what keeps the exactness where it exists: a ring with no
   twist returns the plain circle **bit for bit**, and the reversals a
   sphere needs — the supplementary latitude and the opposite azimuth — are
   sign changes alone, so no angle is reduced twice.
4. **The twist between latitudes is a parameter, not a property.** Two
   rings of a real node set are rarely aligned and a source rarely prints
   the offset between them. `ring_azimuths` takes it as a circle point and
   the identity `(1, 0)` is exactly the identity.
5. **The gate checks that a rotation is a rotation.** `require_rotation`
   refuses a non-finite entry, columns that are not orthonormal within
   `1e-12`, and a determinant that is not one within four times that. A
   finiteness check alone would not be a gate: a scaling would change the
   volume of every placed body and a reflection would change its
   handedness, and a reflection passes every orthonormality check there is.
   Both are asserted in the suite.
6. **The roll about the aimed axis is a convention and the record says so.**
   A direction fixes two of three degrees of freedom. The third is chosen
   here as the azimuthal frame, which is the natural one for a body on a
   sphere. A consumer whose body is not axisymmetric about `z` and needs a
   particular clocking has to say so, and this kernel does not offer a way
   to.
7. The native crate mirrors every function and the parity file compares
   float64 bit patterns for the rotations, the directions, the twisted
   azimuths, the centres of every printed latitude, a rotated body and the
   separations. Zero mismatches.

## Consequences

A device repository can now model a converging array without writing
geometry: it tessellates one body, asks for a latitude's centres and
azimuths, aims each member with `inward_aim`, rotates and translates. The
first consumer is the thirty-body array above.

Measured, and therefore what a consumer may rely on: over the thirty
printed placements of a synthetic cylinder, the signed volume of a placed
mesh departs from the source's by at most **5.1e-14** relative and the
surface area by **1.0e-15**. Those are the numbers a device's own
tolerance should sit above.

The kernel inventory's `geometry_placement` entry gains source lines and
its digest changes, so a consumer that wants this re-pins as a governed
data change. Nothing that was already here returns different bits.

Nothing here describes a device: the kernel knows nothing about jets,
chambers or nodes, only about a body, an angle and a sphere.
