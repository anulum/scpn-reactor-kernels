<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — ADR 0012
-->

# ADR 0012 — Bodies that close on the axis, at both tiers

Status: accepted (2026-09-04). Extends `geometry_profiles` and
`cad_profiles`, and corrects `cad_faceting`. No new kernel, no kernel
whose output changes for an input it already accepted.

## Context

ADR 0010 and ADR 0011 gave both tiers a body whose radius varies along the
axis. Their contract demands a **strictly positive radius at every
sample**, which was the right contract for what they were written for: a
flux tube, a tapered liner, a horn, a bellows envelope. All of those keep
a bore.

A consumer then needed a body those primitives cannot express. The
separatrix of a compact toroid is a closed surface whose radius falls to
zero at both poles — the shape published as `r²/a² + |z|^m / b^m = 1`,
so `r(z) = a·sqrt(1 - |z/b|^m)`. It is a profile of revolution in every
respect except that it touches the axis, and touching the axis is exactly
what the contract forbids:

    require_profile("separatrix", closed)
    GeometryError: separatrix[0].radius: must be strictly positive, got 0.0

The consumer could have sampled the profile short of its poles and drawn a
truncated body. That would be a substitute for the part rather than the
part, so it is not what happened; under the group's standing rule, when
the shared library cannot express a part, **the library gains the
capability**.

## Decision

1. **One record, not one per tier.** ADR 0010 and 0011 are separate
   because they added two kernels with two different back-ends and two
   different evidence classes. This is one capability with one rationale,
   reaching two kernels and correcting a third. Splitting it would
   duplicate the reasoning and leave neither half stating the whole
   decision.

2. **`require_closed_profile`** admits a profile whose first or last
   radius is exactly zero, with every interior radius strictly positive
   and the heights strictly increasing as before. At least one end must be
   zero — a profile positive at both ends is an open profile and belongs
   to `require_profile`, which is unchanged. A profile zero at both ends
   needs at least three samples, because it must still carry one ring of
   positive radius between its poles. A cone is admitted: one pole and one
   disc is a valid body and refusing it would be arbitrary.

3. **`closed_profiled_solid` emits an apex vertex per pole, never a
   ring.** A ring of zero radius would place `segments` identical points
   on the axis and give every face touching them zero area. The faces are
   the faces the open primitive would emit with the degenerate ones
   removed: collapsing a band's lower ring to one vertex leaves
   `(apex, upper + j, upper + i)` of the two quad triangles, and
   collapsing its upper ring leaves `(lower + i, lower + j, apex)`. An end
   of positive radius keeps its disc.

4. **No new closed form.** The frustum-stack volume
   `sum (pi/3)(r_i² + r_i r_{i+1} + r_{i+1}²) Δz` becomes the cone volume
   when an end radius is zero, and the lateral-area sum becomes the cone
   lateral area; a pole has no disc to add. `profile_volume_m3` and
   `profile_lateral_area_m2` therefore serve both kinds of profile, and
   `require_revolution_profile` is where that is decided — a zero end
   radius selects the closed contract, anything else the open one. The
   test suite proves the reduction is exact rather than approximate: a
   cone's volume from the general sum equals `pi r² h / 3` bit for bit.

5. **Native parity moves with it.** `geometry_profiles` carries
   `native_parity: true`, so `closed_profiled_solid` has its Rust mirror
   and its bit-exactness test, for a separatrix and for a cone, at 8, 32
   and 64 segments.

6. **`cad_profiles`** gains `closed_profiled_solid_brep`. The generating
   polyline is the profile itself; where an end already sits on the axis
   no return point is appended, because appending one would repeat a
   vertex and leave a zero-length segment. The analytic references need no
   special case, since a pole's disc has zero radius and therefore zero
   area.

7. **`cad_faceting` is corrected, and the mesh contract is not.** Faceting
   a body with a pole exposed a defect that had no way of showing before:
   the mesher emits several distinct parametric vertices at the apex, they
   weld to one index by exact coordinate equality, and a triangle spanning
   two of them becomes `(a, b, b)`. The mesh contract admits no repeated
   index and refused the body.

   The fix is in `weld`, which now drops a triangle it has collapsed. It
   is not a relaxation of the contract, and it cannot hide a defect: the
   collapsed triangle has zero area, and its directed edges `(a, b)` and
   `(b, a)` are each other's reverse and cancel within the face itself, so
   removing it leaves every other face's edge pairing exactly as it was. A
   genuine duplicate edge or orientation fault still fails the contract. A
   body with no point on the axis loses no face, which the test asserts.

## Addendum (2026-09-04) — a back-end limit the first consumer found

Building an FRC separatrix at tier G2 surfaced a limit of the CAD
revolution that no test in this repository had reached: **the revolved
volume stops matching the exact frustum sum when two adjacent profile
radii come close together.** Measured on one shape at 17 samples, the
agreement is exact to 2e-16 where the radii are well separated and
degrades to between 5e-5 and 3e-4 as they crowd; a deliberately
flat-topped polyline reproduces it with nothing device-like about it.

Three things are worth stating plainly.

It is **not** a property of the closed profile this record introduces. The
open primitive of ADR 0011 gives the same numbers for the same shape
lifted off the axis, so the limit has been there since that record and
was simply never reached by a profile in this suite: the `WAIST` fixture
has generous radius steps everywhere.

It is **not** a property of the tier-G1 tessellation, which is exact for
every one of those profiles. That is what locates it in the back-end
rather than in the profile contract or the closed forms.

It is **caught**. A consumer that composes bodies through
`assembly_evidence` is refused a body whose measured volume misses its
analytic form by more than `MEASURE_TOLERANCE`, naming the body and the
bound. That is the guard working as designed, and it is how the limit was
found. A consumer that calls `profiled_solid_brep` or
`closed_profiled_solid_brep` directly and never checks the evidence is not
protected, which is the reason this is written down here and in
`VALIDATION.md` rather than left in a commit message.

No bound is promised. The test pins the behaviour either side of the
threshold so a back-end change cannot alter it silently.

## Consequences

Additive throughout. `require_profile`, `profiled_solid`, `profiled_tube`
and their Rust mirrors are untouched, and no kernel produces a different
output for any input it already accepted — so **no consumer pin has to
move for correctness**, and no major version bump is due. A consumer that
wants the new body re-pins as a governed change and records the new
inventory digest, exactly as ADR 0007 describes.

The one behavioural change outside the new functions is `weld` dropping
collapsed triangles. No previously accepted body produced one: every body
the library could build before had a strictly positive radius everywhere,
so nothing welded to a sliver. The existing faceting tests pass unchanged,
which is the evidence for that claim rather than an assertion of it.
