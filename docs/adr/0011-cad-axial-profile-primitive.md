<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — ADR 0011
-->

# ADR 0011 — B-rep bodies whose radius varies along the axis

Status: accepted (2026-09-03). Adds the kernel `cad_profiles` to the CAD
group of ADR 0006 and is the tier-G2 counterpart of ADR 0010.

## Context

ADR 0010 gave the tessellating tier bodies whose radius is a function of the
axis, because a mirror confines a flux tube and the filed source's printed
dimensions do not close for a body of constant radius. The solid tier was
then in the position the tessellating tier had been in, and for the same
reason: its constructors extrude a circle, so every solid they build has one
radius.

## Decision

1. A new kernel `cad_profiles` (`src/scpn_reactor_kernels/cad/profiles.py`)
   provides `profiled_solid_brep` and `profiled_tube_brep`, which revolve the
   closed polyline through the profile's samples about the axis.
2. The profile contract is not restated. It is the tier-G1 contract, imported
   and reused: the same validators, the same rules, the same messages. A
   rejection surfaces under the CAD error type carrying the geometry group's
   wording, so a caller who moves a profile between tiers meets one contract
   stated once rather than two that could drift.
3. The analytic references are the tier-G1 closed forms — the frustum-stack
   volume and lateral area, plus the end discs for the solid and the two end
   annuli for the tube. They are exact for a linear profile, so the evidence
   kernel checks the pinned third-party B-rep kernel against them at the same
   declared relative tolerance the cylinder and the tube use. Measured in the
   reference environment: `1e-16` on the solid and `2e-15` on the tube, against
   a tolerance of `1e-9`.
4. The two tiers are proven to describe ONE body, not two similar ones: a test
   facets the revolved solid and compares its volume against the tessellated
   mesh of the same profile, within the exact polygon deficit of the reference
   count. If the revolve and the tessellation had disagreed about the shape,
   that is where it would appear.
5. The generalisation is checked against the existing constructors as far as
   this tier honestly can: a two-sample constant profile carries the identical
   analytic references as `cylinder_solid_brep`, and a pair of them the
   identical references as `annular_tube_brep`, with both bodies measured
   inside the tolerance. The tier-G1 claim — identical vertex streams — is a
   stronger statement that only the tessellating tier can make, and it is made
   there, not here.
6. No native parity: an adapter of a third-party C++ kernel, like every other
   member of the CAD group.
7. The CAD benchmark gains `revolve_axial_profile`, so the kernel's benchmark
   pointer is real.

## Consequences

A family whose tier-G1 model carries a body of varying radius can carry the
same body in tier G2, from the same samples, with the same closed forms
checking both. The mirror flux tube is the first consumer.

The kernel inventory gains one entry and its digest changes, so a consumer
that wants this kernel re-pins as a governed data change.

Nothing here describes a device: the kernel knows a polyline and an axis, and
the physical relation that produced the radii stays with the caller that
declared it.
