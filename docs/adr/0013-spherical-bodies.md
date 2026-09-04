<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — ADR 0013
-->

# ADR 0013 — Spherical bodies

Status: accepted (2026-09-04). Extends ADR 0010 (axial profile primitive) and
ADR 0012 (bodies that close on the axis).

## Context

Five device families in the rollout that consumes this library need a
sphere: the inertial-confinement capsule and its shells, the
inertial-electrostatic grids, and the converging jets of a
magneto-inertial array. None of them could express one, and the rollout
plan recorded the sphere and the spherical shell as missing primitives.

They were only half missing. A sphere is a body that closes on the axis
at both poles, which is exactly what ADR 0012 taught
`closed_profiled_solid` to tessellate, and `closed_profiled_solid_brep`
to revolve. What the library lacked was not a tessellation kernel but the
**profile**, and the one body a profile genuinely cannot express.

## Decision

Add `geometry.spheres` with three names and deliberately not a fourth.

**`sphere_profile` — the content of the increment.** It samples the
sphere uniformly in **polar angle**, not in height. Both converge, but
only the angular sampling converges cleanly: measured, its volume deficit
falls as the square of the ring count, the ratio between successive
doublings running 3.990, 3.998, 3.999, 4.000. Uniform sampling in `z`
crowds samples where the surface is flat and starves them where it turns
fastest, and its deficit falls more slowly and less regularly.

The angles come from `circle_points` evaluated on **twice** the ring
count and read over its first half turn. That is not a convenience. It is
what puts the poles on exactly `centre ± radius` with a radius of exactly
zero, the equator on exactly the centre with a radius of exactly the
sphere's, and every coordinate bit-identical to the native kernel — both
read the same vendored polynomial trigonometry at the same indices.
Measured, the heights stay strictly increasing to at least 1024 rings,
where the smallest step is still 5e-6 of the radius.

**`sphere_solid` — a named composition, nothing more.** It is
`closed_profiled_solid(sphere_profile(...))`, and it exists so that a
consumer names the body it wants rather than assembling it.

**`spherical_shell` — the body that needed new code.** A shell is *not*
a tube between two aligned profiles and cannot be built as one: below the
inner sphere's poles its cross-section is an annulus and above them a
full disc, so the two surfaces do not stand over one another sample for
sample. It is instead two closed surfaces, the outer as built and the
inner with every triangle reversed so that it faces the cavity.

## What was deliberately not added

**No ideal-sphere closed forms.** `4/3 pi r^3` and `4 pi r^2` describe a
sphere; these bodies are polyhedra inscribed in one. A consumer handed
both would sooner or later compare a body to a solid it is not, and the
library already provides `profile_volume_m3`, which is exact for the body
actually built. The difference is not small at usable resolutions: at
sixty-four rings the polyhedron holds 99.94 % of the sphere's volume.

**No relaxation of `require_aligned_profiles`.** A shell could have been
reached by letting a tube's profiles meet at zero radius. That rule also
guards the torus, whose profiles meet at a *positive* radius, and
loosening it for one case would have weakened it for the other. The shell
got its own kernel instead.

## Consequences

Native parity is bit-exact and tested: the profile stream, the sphere's
vertices and faces through the existing closed-profile kernel, and the
shell's two surfaces with their index offset and reversed winding.

The tessellation benchmark gains the shell in both its floor and native
passes and was rerun; the recorded results are refreshed rather than
carried over.

100 % statement and branch coverage of the new module.
