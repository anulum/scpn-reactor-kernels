<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — ADR 0016
-->

# ADR 0016 — Sine and cosine of an angle a source prints

Status: accepted (2026-09-04). Extends the kernel `geometry_unit_circle`
of ADR 0002 and ADR 0007 with a reduction for angles that are not
rational multiples of a turn.

## Context

Every angle this library has needed until now has been a rational
multiple of a turn. A tessellation divides the circle into `segments`
equal arcs; a ring divides it into `count`. `circle_points(count)` serves
both by finding the quadrant and the residue with **integer arithmetic on
`(k, count)`**, so no angle is ever formed, the residual is reduced into
`[0, pi/4]` exactly, and a point that falls on an axis is exactly `0` and
`±1`. That exactness is a real property and consumers depend on it.

A filed source does not describe its machine that way. It prints
latitudes. One device family's source places its bodies on a sphere at
polar angles of 20.1, 43.4, 59.0, 80.1, 99.9, 121.0, 136.6 and 159.9
degrees; none of those is a rational multiple of a turn, and none can be
reached through `circle_points`. Until this record a repository facing
such an angle had the same two wrong options ADR 0007 described for
placement: substitute an angle the library can reach, which misstates the
geometry, or call the platform `sin` and `cos` in a device repository,
which puts geometry back where ADR 0002 removed it and gives up
bit-exactness with the native kernel.

## Decision

1. `geometry/trig.py` gains an arbitrary-angle path on **the same two
   polynomials**: `circle_point(angle_rad)` returns `(cos, sin)`, with
   `sine` and `cosine` as its two named accessors.
2. The angle is reduced against a **three-word split of `pi/2`** in a
   fixed operation order, the same Cody–Waite shape the exponential
   kernel already uses for `ln 2`. The quadrant index is
   `floor(x * 2/pi + 1/2)` — one product, one addition and a floor, so
   nothing depends on a language's rounding convention — and the residue
   is `((x - n A) - n B) - n C`. The first two words carry 22 and 21
   trailing zero mantissa bits, so both products are exact for every
   index the domain admits; what is left of `pi/2` beyond all three words
   is below `1.1e-37`.
3. `radians_from_degrees(degrees)` is the one place a printed angle is
   converted, as `(degrees * pi) / 180`.
4. **The domain is declared and refused at its edge, never wrapped.**
   `MAX_QUADRANT_INDEX` is `2^21`, whose 21 significant bits fit the
   exactness argument against the 31 and 32 bits the first two words
   need. The bound is measured rather than assumed: the first index at
   which `n * PIO2_A` is inexact is 5340355 and the first at which
   `n * PIO2_B` is inexact is 4017387, both above it, and the tests
   assert the nearest failing case on either side.
   `MAX_ANGLE_RAD` is `2^21 * pi/2`, about `3.294e6`.
5. **The residue is not strictly bounded by `pi/4`, and the record says
   so.** The quotient that picks the index is formed with a rounded
   `2/pi`, so at a half-quadrant the index can be the neighbour of the
   nearest one. Scanned at the half-quadrant points across the whole
   domain, the residue exceeds `pi/4` by at most `1.2e-16` per radian of
   angle — `3.9e-10` at the top of the domain, and one unit in the last
   place at `pi/4` itself. The polynomials are evaluated there anyway,
   and at the worst such point the result still agrees with the platform
   library to one unit in the last place. A bound that does not hold
   would be worse than the honest one.
6. The native crate mirrors the whole path and the parity file compares
   float64 bit patterns over a scan of the domain: 4003 angles across
   eight turns, the four quarter turns, the printed latitudes, both edges
   of the domain and the worst-residue point. Zero mismatches.
7. **`circle_points` stays the entry point for rings and tessellations.**
   The two paths are not interchangeable and a test says so: reaching the
   members of a ring through `circle_point` gives a set that differs in
   the last places, is no longer exactly symmetric, and loses the exact
   zeros and ones on the axes — measured at 4 of 30 points identical for
   a thirty-member ring, with a largest difference of `7.6e-16`.

## Consequences

A device repository can model a body at a printed latitude without
writing trigonometry and without losing native parity. The exactness that
the count-based path has on the axes is not weakened, because that path
is untouched; what is added is a second entry point whose weaker
guarantee is stated rather than implied.

Accuracy, measured over the declared domain and not assumed: every
`(cos, sin)` agrees with the platform library within `2.220446049250313e-16`,
one unit in the last place of one. Bit-exactness with the native kernel
is the guarantee; agreement with `libm` is a measured property, exactly
as ADR 0007 framed it for the arbitrary-count circle.

The kernel inventory's `geometry_unit_circle` entry gains a source line
and its digest changes, so a consumer that wants this kernel re-pins as a
governed data change. No existing behaviour moves: every function that
was here returns the same bits.

Nothing here describes a device: the kernel knows nothing about
latitudes, jets or spheres, only about an angle.
