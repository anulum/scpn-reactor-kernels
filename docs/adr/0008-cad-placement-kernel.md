<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — ADR 0008
-->

# ADR 0008 — CAD placement: B-rep bodies off the device axis

Status: accepted (2026-09-03). Adds the kernel `cad_placement` to the CAD
group of ADR 0006 and is the tier-G2 counterpart of ADR 0007.

## Context

ADR 0007 gave tier G1 the placement it was missing, and the plasma-focus
cathode became the cage of rods it is. Tier G2 was then in exactly the
position tier G1 had been in: the CAD group of ADR 0006 offers only
axis-centred constructors, so the B-rep model of that same family could not
be built without either drawing an axisymmetric substitute or reaching into
the back-end from a device repository. Both are refused by the same rule that
produced ADR 0007 — when the shared library cannot express a part, the
library gains the capability.

## Decision

1. A new kernel `cad_placement` (`src/scpn_reactor_kernels/cad/placement.py`)
   provides:
   - `translate_brep(body, dx, dy, dz, name=None)` — a rigid translation of a
     `BrepBody` through the back-end's `Shape.translate`, refusing non-finite
     offsets and an empty rename before the back-end is touched. A ring needs
     one name per member, so the caller may rename here.
   - `ring_brep_bodies(body, names, offsets)` — one placement of a body per
     centre, refusing an empty ring, a name count that does not match the
     centre count, and repeated names.
2. The centres are NOT re-derived here. They are the tier-G1
   `ring_offsets` of ADR 0007, so one set of centres serves both tiers and
   the two models of a family are placed on the same circle by construction.
3. The analytic closed forms carried by a `BrepBody` are invariant under a
   rigid motion, so they are carried over exactly. The back-end's own measure
   of the placed solid is a different matter, and this record states it rather
   than assuming it: OpenCASCADE integrates over the moved surface, so its
   volume of a placed solid is **not** bit-identical to its volume of the
   source solid — on a ring of twelve identical rods the measured volumes
   differ in the last unit in the last place. What the kernel claims is the
   pair that is true and testable: the placed solid's measured volume and area
   stay within the group's declared relative tolerance `1e-9` of the analytic
   forms, and the bounding box shifts by exactly the offset. A test asserts
   the boundary explicitly so no later reader mistakes tolerance for identity.
4. Cross-tier evidence: the faceting of a placed solid is compared against the
   tier-G1 mesh of the same body translated by the same offset, and the two
   agree in volume within the exact inscribed-polygon deficit bound of the
   reference tessellation — the same bound the rest of the CAD group uses.
5. No native parity. The kernel is an adapter of a third-party C++ kernel, so
   `native_parity` is `false`, as for every other member of the CAD group.
6. The CAD benchmark gains `place_ring_of_bodies` (twelve rods on a circle),
   so the kernel's benchmark pointer is real.

## Consequences

Every family whose tier-G1 model carries an off-axis part can now carry the
same part in tier G2, with the two tiers placed on identical centres. The
plasma-focus cathode is the first consumer.

The kernel inventory gains one entry and its digest changes, so a consumer
that wants this kernel re-pins as a governed data change.

Nothing here describes a device: the kernel knows nothing about rods or
cathodes, only about a solid and a translation.
