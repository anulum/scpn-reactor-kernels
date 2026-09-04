<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — ADR 0015
-->

# ADR 0015 — Bodies without curvature, and the bounds they actually need

Status: accepted (2026-09-04). Amends ADR 0002 (geometry kernels),
ADR 0006 (CAD kernels) and ADR 0009 (body evidence in the library), each
of which was written when every body in this library was a solid of
revolution.

## Context

A consuming family needs a rectangular prism. Its cited source fully
dimensions exactly one target and that target is a plane slab of square
cross-section driven against a rigid wall — not a body of revolution, and
so not buildable from anything this library had.

**Until now every body here was a solid of revolution, and the library
said so in its own words.** `cad/solids.py` described itself as returning
a shape that "is an exact solid of revolution", and
`geometry/primitives.py` described its output as inscribed polygon
prisms. Those sentences are load-bearing rather than decorative: a
consuming family words its non-claims around them — *"every body here is
an inscribed polyhedron of revolution, and its own profile is its
analytic reference"* — and the evidence kernel bounds a body's faceting
at a circular radius. Adding a prism makes all of that false for one
body. The choice was to revisit those statements honestly or to widen
them quietly, and quietly would have left every consumer's non-claims
overclaiming.

## Decision

**The prism is added to the existing primitive kernels rather than to
new ones.** `geometry_primitives` is responsible for deterministic
tessellation of analytic bodies and `cad_brep_solids` for their B-rep
twins; a prism is one of each. Splitting it out would have created two
kernels whose responsibility is the first one's, and the group's rule is
that a module is a responsibility rather than a line count. The kernel
count therefore stays at seventeen while four kernels' declared sources
change.

**The library's self-description is corrected, not widened.** Both module
docstrings now say plainly that not every body here is a solid of
revolution, name the prism as the exception, and say what follows from
it. A consumer reading either module learns the distinction at the point
where it matters.

**A body states whether it has curvature, and the caller must say
which.** `body_evidence` takes the body's smallest circular radius, or
`None` where there is none, and `facet_bounds` selects the regime from
that. `None` is not a default and cannot be reached by omission.

## Why the circular bound could not be reused

This is the part that would have been easy to get wrong, so it was
measured first.

**A prism is faceted exactly.** Measured over nine prisms spanning
1 micrometre to 10 metres and aspect ratios to 1000:1, at every linear
deflection the back-end accepts — 1e-7 to 1.0, seven orders — and angular
deflections from 0.01 to 1.0 radians: the mesher returned **8 vertices
and 12 triangles every single time**, and neither deflection changed any
measure. There is no chord, nothing converges, and refining nothing
improves nothing.

**The worst relative volume deviation over that whole set was
2.581e-16**, one or two units in the last place of a double, and it falls
on **either side** of the analytic value.

Both facts break the existing bound in a way that is worth stating
exactly, because the failure is silent:

- The chord bound `2 d / r` needs a circular radius `r` that a prism does
  not have. Supplying the half-width instead — the obvious fudge — gives
  `8e-5` at the fixture's scale against a measured deviation of `2.6e-16`:
  **eleven orders of slack**.
- The polygon bound `1 - (n / 2 pi) sin(2 pi / n)` compares against an
  inscribed polygon prism that, for this body, is the body. At the
  reference segment count it is `0.0997` against a measured difference of
  exactly zero.
- Worse, the check was **one-sided**: `deficit > bound`. A prism's
  deviation is negative about as often as positive, so a negative
  deviation of any magnitude would have passed.

Reusing the circular bounds would therefore not have been merely loose.
It would have produced a check that passes whatever the mesher does — an
evidence record that looks the same as a real one and proves nothing.

**So the declared bound for a body without curvature is a round-off
tolerance**, `PLANAR_FACETING_TOLERANCE = 1e-12`. It sits about four
orders above the measured ceiling as a stated margin against back-end
drift, and three orders **below** the curved bodies' `MEASURE_TOLERANCE`
of `1e-9`, because an exact body admits a stronger claim than an
approximated one. A test asserts that it is tight enough to refuse a
prism wrong by one part in ten thousand, so the tolerance is not
decorative in the other direction either.

## A defect this exposed in the existing check

The faceted-volume deviation is now compared **in magnitude**, for every
body and not only for prisms. The previous one-sided comparison would
have admitted a faceted volume arbitrarily *larger* than its analytic
form without comment, which is as much a defect as one that is smaller.
No curved body's evidence changes: an inscribed faceting always
undershoots, so every existing deviation is positive and the comparison
is the same one it was. The change is a strict tightening, and it was
found only because a prism's deviation is signed.

## Consequences

- `geometry_primitives` gains `rectangular_prism` — no segment count,
  because there is nothing to refine — and `cad_brep_solids` gains
  `rectangular_prism_brep`.
- `cad_faceting` gains the measured planar tolerance;  `cad_evidence`
  gains `facet_bounds` and the magnitude comparison.
- Four kernels' declared sources change, so `kernel-inventory.json` and
  its SHA-256 change. **Every consuming family pins that digest**, so
  every consumer's contract test will report drift until it moves its
  pin deliberately. Only the family that needs the prism should move;
  the rest have no reason to, and mixed pins are structurally fine
  because each repository holds its own pin against its own manifest.
- The kernel count stays at seventeen.
- 100 % statement and branch coverage of every changed module.
