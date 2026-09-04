<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — ADR 0014
-->

# ADR 0014 — B-rep spherical bodies

Status: accepted (2026-09-04). The tier-G2 counterpart of ADR 0013, extending
ADR 0011 (CAD axial profile primitive).

## Context

ADR 0013 splits the spherical bodies in two: the solid sphere is a closed
profile the library already revolves, and the shell is a shape it had no
way to describe. The same split holds at the B-rep tier, and the shell
raises a question the tessellated tier does not.

## Decision

Add `cad.spheres` with `sphere_brep` and `spherical_shell_brep`.

**`sphere_brep` delegates.** It is the sphere's profile handed to
`closed_profiled_solid_brep`. Both poles sit on the axis, so neither end
carries a disc, and the analytic references are the frustum-stack volume
and the lateral area of the profile actually built.

**`spherical_shell_brep` revolves a polyline that touches the axis.**
The generating region between two concentric spheres is bounded by the
two arcs *and* by two segments of the axis, where the cavity's poles sit
inside the outer body. There is no way to describe the region without
them.

That was the risk in this increment, and it was measured rather than
assumed: the back-end accepts the polyline, and the revolved volume
equals the difference of the two frustum stacks **exactly** — relative
error zero at sixteen rings and of order 1e-16 at sixty-four, against a
declared tolerance of 1e-9. So the analytic references need no allowance
for the construction.

The revolve helper of `cad.profiles` is shared rather than duplicated. It
lost its leading underscore for that reason and is still not part of the
package's public surface.

## A consistency defect this found

The tessellated `spherical_shell` validated its radii by their own names;
the first draft of `spherical_shell_brep` did not, and let the profile
builder report both of them as `radius_m`. The two tiers therefore
refused the same bad input with different messages. Caught by a test that
asserted the field name, and fixed by validating in the B-rep builder
too — the refusal has to name the field the caller passed, not the field
some inner function happened to call it.

## Consequences

The CAD benchmark gains `revolve_sphere` and `revolve_spherical_shell`
and was rerun; the shell costs about 14 ms against the sphere's 8, which
is roughly what revolving two profiles instead of one should cost.

100 % statement and branch coverage of the new module. The suite skips
hermetically when the optional back-end is absent, as every tier-G2 suite
in this library does.
