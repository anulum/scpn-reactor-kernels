<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — ADR 0018
-->

# ADR 0018 — Aimed B-rep placement (tier G2)

Status: accepted (2026-09-04). The tier-G2 twin of ADR 0017, extending the
kernel `cad_placement` of ADR 0008.

## Context

ADR 0008 gave tier G2 the translation ADR 0007 gave tier G1, for the same
reason: a device repository must never re-implement geometry. ADR 0017 adds
aiming to tier G1, and a family whose exact model is a B-rep assembly needs
the same operation there or the two tiers stop describing one machine.

## Decision

1. `cad/placement.py` gains `place_brep(body, rotation, centre, name)` and
   `sphere_ring_brep_bodies(body, names, centres, rotations)`.
2. **The rotation is the tier-G1 rotation, not a second one.** The
   placement is handed to the back-end as the frame whose first and third
   columns are those of that matrix, which is how it takes a rigid motion.
   The back-end re-orthogonalises the frame; measured over the thirty
   placements a filed source prints, the frame it builds departs from the
   matrix it was given by at most **1.1102230246251565e-16** in any
   component. That measurement is the assertion which says the tessellated
   body and the B-rep body are placed in one frame rather than in two that
   happen to look alike.
3. The analytic measures are carried over unchanged, because a rigid motion
   leaves the closed forms invariant, exactly as ADR 0008 established for
   translation.
4. `require_rotation` of ADR 0017 is reused with the B-rep error class, so
   a matrix that scales or reflects is refused in both tiers by one
   implementation.
5. **OpenCASCADE stays a pinned third-party kernel and is not the bit-exact
   floor of the group**, and this shows here as it did for translation: the
   back-end integrates over the moved surface. Measured over the same
   thirty placements, its volume of the placed solid departs from the
   analytic volume of the source by at most **3.7e-16** relative and its
   area by **3.8e-16**, both inside the group's declared measure tolerance.

## Consequences

A family whose bodies converge on a point can carry both tiers, and the
record can say that one rotation placed both. A consumer's evidence bound
for a placed body is the measured one above rather than a bound reused by
analogy from an unplaced one.

The kernel inventory's `cad_placement` entry gains a source line and its
digest changes.

Nothing here describes a device.
