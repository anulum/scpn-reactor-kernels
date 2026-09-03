<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — ADR 0010
-->

# ADR 0010 — Bodies whose radius varies along the axis

Status: accepted (2026-09-03). Adds the kernel `geometry_profiles` to the
geometry group of ADR 0002.

## Context

Every tier-G1 primitive so far builds a body of constant radius. That was
enough for five device families, and it is not enough for the sixth.

A magnetic mirror confines a **flux tube**, and a flux tube in a mirror field
is by definition not of constant radius: flux conservation gives
`r(z) = r_mid sqrt(B_min / B(z))`, so the column is widest at the midplane
and narrowest at the throats, by a factor `sqrt(R_m)`.

This is not a modelling preference, and the filed source settles it. For the
device the mirror family's papers describe, the source prints a target plasma
of radius `0.1 m`, mirror magnets with a `5.5 cm` warm bore, and a field of
`0.86 T` at the midplane against `17 T` at the magnets. A cylinder of radius
`0.1 m` does not pass through a `5.5 cm` bore at all. The flux tube does: at
that ratio the midplane radius narrows to about `0.0225 m` at the throat,
which clears a bore of radius `0.0275 m`. Drawing that plasma as a cylinder
would not be a coarse approximation but a body that cannot exist inside the
machine whose dimensions the source prints.

The same shape appears elsewhere and will keep appearing: a tapered liner, a
horn, a conical transition, a bellows envelope, an expander throat.

## Decision

1. A new kernel `geometry_profiles`
   (`src/scpn_reactor_kernels/geometry/profiles.py`) builds surfaces of
   revolution through a sampled axial radius profile:
   - `profiled_solid(profile, segments)` — a closed solid;
   - `profiled_tube(inner_profile, outer_profile, segments)` — a closed tube
     between two aligned profiles;
   - `profile_volume_m3(profile)` and `profile_lateral_area_m2(profile)` —
     the exact closed forms of the resulting body;
   - `require_profile` and `require_aligned_profiles` — the validators, which
     name the offending sample index in every rejection.
2. A profile is an ordered sequence of `(z, radius)` samples: at least two,
   strictly increasing in `z`, radii strictly positive, all values finite.
   The surface passes exactly through those samples and is **linear between
   them**. The contract is deliberately narrow: the kernel interpolates
   nothing beyond the straight line between two samples it was given, so a
   record built on it can say what the surface is without appealing to a
   smoothing rule nobody declared. A caller who wants a finer surface passes
   finer samples, and a test proves that inserting a sample on the existing
   line changes neither closed form.
3. Two profiles must carry the same number of samples at the same heights.
   Sampling the two surfaces of an annulus at different heights would leave
   the body undefined between them, so it is refused rather than interpolated.
4. The generalisation is exact, in the same sense the arbitrary-count circle
   of ADR 0007 was: a two-sample profile of constant radius produces the
   identical vertex and face streams as `cylinder_solid`, and a pair of such
   profiles the identical streams as `annular_tube`. Both are asserted in the
   test suite, so a consumer that moves a body from a constant radius to a
   profile of the same shape keeps every pinned digest — a digest changes only
   when the shape does.
5. The closed forms are elementary and exact, because a linear profile makes
   the body a stack of conical frusta. They are not an approximation of the
   tessellated body; the tessellation is the approximation, and its volume
   deficit against the closed form is the exact inscribed-polygon deficit of
   the segment count, the same bound every other primitive carries. A test
   asserts that equality rather than an inequality.
6. The native crate mirrors both primitives and both closed forms, and the
   parity file compares float64 bit patterns for a five-sample varying
   profile, for the hollow body, and for both closed forms.
7. The geometry benchmark tessellates a varying body in the same pass, so the
   kernel is measured on both backends and its benchmark pointer is real.

## Consequences

A device repository can now model a part whose radius is a function of `z`
without writing geometry and without substituting a body of constant radius
for one that is not. The first consumer is the mirror family's flux tube.

The kernel inventory gains one entry and its digest changes, so a consumer
that wants this kernel re-pins as a governed data change. No existing digest
moves: the constant-radius primitives are untouched and the generalisation is
proven to reproduce them exactly.

Nothing here describes a device: the kernel knows a list of radii and a list
of heights, and the physical relation that produces them — flux conservation,
a taper rule, a machining drawing — stays with the caller that declares it.
