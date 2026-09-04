# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — deterministic unit-circle trigonometry

"""Vendored deterministic sine and cosine for bit-exact tessellation.

Mesh vertices are generated from points on the unit circle. Platform
``libm`` implementations of ``sin`` and ``cos`` are not guaranteed to be
correctly rounded and differ between languages and libraries, so the
native kernels could not reproduce the Python floor bit for bit if either
side called them. Both sides therefore evaluate the same degree-15 sine
and degree-16 cosine Taylor polynomials in Horner form on ``[0, pi/4]``
with the identical operation order, and build the remaining points by
exact octant and quadrant symmetry (sign changes and swaps only). The
truncation error of both polynomials on ``[0, pi/4]`` is below one half
unit in the last place of the result; the accumulated rounding error is
a few units in the last place, bounded by the accuracy test against
``math.sin`` and ``math.cos`` in the test suite.

Two entry points sit on those polynomials and the choice between them is
not a matter of taste. :func:`circle_points` serves angles that are exact
rational multiples of a turn — the segments of a tessellation, the members
of a ring — and finds their quadrant by integer arithmetic on the count,
so no angle is ever formed and no reduction is needed. :func:`circle_point`
serves a single arbitrary angle, which a source prints as a latitude or a
phase and which is not such a multiple; it reduces the angle against a
three-word split of ``pi/2`` in a fixed operation order, the same
Cody–Waite shape the exponential kernel uses for ``ln 2``. The domain of
that reduction is declared and refused at its edge rather than wrapped.

Nothing here describes a device; it is the numerical substrate of the
geometry.
"""

from __future__ import annotations

import math
from typing import Final

from scpn_reactor_kernels.errors import GeometryError

HALF_PI: Final = math.pi / 2.0
MIN_SEGMENTS: Final = 8
SEGMENT_MULTIPLE: Final = 8
MIN_CIRCLE_POINTS: Final = 3

# Reciprocal factorials as exact integer quotients (every integer below is
# exactly representable, so each quotient is correctly rounded identically
# in every IEEE-754 implementation).
_S3: Final = 1.0 / 6.0
_S5: Final = 1.0 / 120.0
_S7: Final = 1.0 / 5040.0
_S9: Final = 1.0 / 362880.0
_S11: Final = 1.0 / 39916800.0
_S13: Final = 1.0 / 6227020800.0
_S15: Final = 1.0 / 1307674368000.0
_C2: Final = 1.0 / 2.0
_C4: Final = 1.0 / 24.0
_C6: Final = 1.0 / 720.0
_C8: Final = 1.0 / 40320.0
_C10: Final = 1.0 / 3628800.0
_C12: Final = 1.0 / 479001600.0
_C14: Final = 1.0 / 87178291200.0
_C16: Final = 1.0 / 20922789888000.0


def sine_polynomial(angle_rad: float) -> float:
    """Evaluate the degree-15 Taylor sine on the reduced interval.

    Parameters
    ----------
    angle_rad
        Angle in radians; intended for ``0 <= angle_rad <= pi/4``.

    Returns
    -------
    float
        ``x - x^3/3! + ... - x^15/15!`` evaluated in Horner form in
        ``x^2``, with the fixed operation order shared by the native kernel.
    """
    square = angle_rad * angle_rad
    polynomial = 0.0 - _S15
    polynomial = polynomial * square + _S13
    polynomial = polynomial * square - _S11
    polynomial = polynomial * square + _S9
    polynomial = polynomial * square - _S7
    polynomial = polynomial * square + _S5
    polynomial = polynomial * square - _S3
    polynomial = polynomial * square + 1.0
    return angle_rad * polynomial


def cosine_polynomial(angle_rad: float) -> float:
    """Evaluate the degree-16 Taylor cosine on the reduced interval.

    Parameters
    ----------
    angle_rad
        Angle in radians; intended for ``0 <= angle_rad <= pi/4``.

    Returns
    -------
    float
        ``1 - x^2/2! + ... + x^16/16!`` evaluated in Horner form in
        ``x^2``, with the fixed operation order shared by the native kernel.
    """
    square = angle_rad * angle_rad
    polynomial = _C16
    polynomial = polynomial * square - _C14
    polynomial = polynomial * square + _C12
    polynomial = polynomial * square - _C10
    polynomial = polynomial * square + _C8
    polynomial = polynomial * square - _C6
    polynomial = polynomial * square + _C4
    polynomial = polynomial * square - _C2
    return polynomial * square + 1.0


def require_segments(segments: int) -> int:
    """Validate a tessellation segment count.

    Parameters
    ----------
    segments
        Number of circumferential segments.

    Returns
    -------
    int
        The validated count.

    Raises
    ------
    GeometryError
        If ``segments`` is below :data:`MIN_SEGMENTS` or not a multiple of
        :data:`SEGMENT_MULTIPLE` (the octant symmetry needs eight equal
        arcs).
    """
    if isinstance(segments, bool) or segments < MIN_SEGMENTS:
        raise GeometryError(
            f"segments: must be at least {MIN_SEGMENTS}, got {segments!r}"
        )
    if segments % SEGMENT_MULTIPLE != 0:
        raise GeometryError(
            f"segments: must be a multiple of {SEGMENT_MULTIPLE}, got {segments!r}"
        )
    return segments


def require_circle_points(count: int) -> int:
    """Validate a count of equally spaced circle points.

    Parameters
    ----------
    count
        Number of points on the circle.

    Returns
    -------
    int
        The validated count.

    Raises
    ------
    GeometryError
        If ``count`` is below :data:`MIN_CIRCLE_POINTS`; three points are
        the smallest arrangement that encloses the axis.
    """
    if isinstance(count, bool) or count < MIN_CIRCLE_POINTS:
        raise GeometryError(
            f"count: must be at least {MIN_CIRCLE_POINTS}, got {count!r}"
        )
    return count


def circle_points(count: int) -> tuple[tuple[float, float], ...]:
    """Return equally spaced circle points for any count, bit-exact across backends.

    The angle of point ``k`` is ``2 pi k / count``. The quadrant and the
    residue inside it are found by integer arithmetic on ``(k, count)``,
    so a point that falls exactly on an axis is exactly ``0`` and ``±1``;
    the residual angle is always reduced into ``[0, pi/4]`` before the
    polynomials are evaluated, and the remaining points follow by exact
    sign changes and swaps. Every floating-point operation has the fixed
    order the native kernel repeats, so the result agrees bit for bit
    across backends for every count.

    Parameters
    ----------
    count
        Number of points; at least three.

    Returns
    -------
    tuple of (float, float)
        ``(cos, sin)`` of ``2 pi k / count`` for ``k = 0 .. count - 1`` in
        increasing angle, starting at ``(1, 0)``.

    Raises
    ------
    GeometryError
        If the count is below three.
    """
    require_circle_points(count)
    points: list[tuple[float, float]] = []
    for index in range(count):
        quadrant, residue = divmod(4 * index, count)
        if 2 * residue <= count:
            angle = (HALF_PI * residue) / count
            cosine, sine = cosine_polynomial(angle), sine_polynomial(angle)
        else:
            angle = (HALF_PI * (count - residue)) / count
            cosine, sine = sine_polynomial(angle), cosine_polynomial(angle)
        if quadrant == 0:
            points.append((cosine, sine))
        elif quadrant == 1:
            points.append((0.0 - sine, cosine))
        elif quadrant == 2:
            points.append((0.0 - cosine, 0.0 - sine))
        else:
            points.append((sine, 0.0 - cosine))
    return tuple(points)


def unit_circle(segments: int) -> tuple[tuple[float, float], ...]:
    """Return equally spaced unit-circle points for a tessellation.

    A tessellation segment count is restricted to multiples of eight (the
    octant symmetry of the primitives); the points themselves are those of
    :func:`circle_points`, which this function only validates for.

    Parameters
    ----------
    segments
        Number of points; at least 8 and a multiple of 8.

    Returns
    -------
    tuple of (float, float)
        ``(cos, sin)`` of ``2 pi k / segments`` for ``k = 0 ..
        segments - 1`` in increasing angle, starting at ``(1, 0)``; points
        at multiples of ``pi/2`` are exactly ``0`` and ``±1``.

    Raises
    ------
    GeometryError
        If the segment count is invalid.
    """
    require_segments(segments)
    return circle_points(segments)


# Three-word split of ``pi/2``. The first two words carry trailing zero
# mantissa bits (22 and 21 respectively), so ``n * PIO2_A`` and
# ``n * PIO2_B`` are exact for every quadrant index the declared domain
# admits; the third word carries the remainder, and what is left of
# ``pi/2`` beyond all three is below ``1.1e-37``.
PIO2_A: Final = 1.57079632673412561417e00
PIO2_B: Final = 6.07710050630396597660e-11
PIO2_C: Final = 2.02226624879595063154e-21

#: ``2 / pi``, the reciprocal used to find the quadrant index.
TWO_OVER_PI: Final = 2.0 / math.pi

#: Degrees in half a turn; a printed angle is normally in degrees.
DEGREES_PER_HALF_TURN: Final = 180.0

#: Largest quadrant index whose products with the first two words of the
#: split stay exact. Measured, not assumed: the first index at which
#: ``n * PIO2_A`` becomes inexact is 5340355 and the first at which
#: ``n * PIO2_B`` does is 4017387, both well above this power of two,
#: which is the largest whose significand fits the exactness argument
#: (21 significant bits against the 31 and 32 the two words need).
MAX_QUADRANT_INDEX: Final = 2097152

#: Largest angle magnitude the reduction accepts, in radians.
MAX_ANGLE_RAD: Final = MAX_QUADRANT_INDEX * HALF_PI


def radians_from_degrees(degrees: float) -> float:
    """Convert an angle in degrees to radians in a fixed operation order.

    Parameters
    ----------
    degrees
        Angle in degrees; finite.

    Returns
    -------
    float
        ``(degrees * pi) / 180``, one multiplication then one division, so
        the native kernel reproduces the result bit for bit. A source that
        prints an angle prints it in degrees, and this is the one place
        the conversion happens.

    Raises
    ------
    GeometryError
        If the angle is not finite.
    """
    if not math.isfinite(degrees):
        raise GeometryError(f"degrees: must be finite, got {degrees!r}")
    return (degrees * math.pi) / DEGREES_PER_HALF_TURN


def require_reducible_angle(angle_rad: float) -> float:
    """Validate an angle against the declared reduction domain.

    Parameters
    ----------
    angle_rad
        Angle in radians.

    Returns
    -------
    float
        The validated angle.

    Raises
    ------
    GeometryError
        If the angle is not finite or its magnitude exceeds
        :data:`MAX_ANGLE_RAD`. The domain is refused, never wrapped: an
        angle outside it is a caller's error, and silently reducing it
        would hide the loss of meaning that the argument's own
        representation carries at that magnitude.
    """
    if not math.isfinite(angle_rad):
        raise GeometryError(f"angle_rad: must be finite, got {angle_rad!r}")
    if abs(angle_rad) > MAX_ANGLE_RAD:
        raise GeometryError(
            f"angle_rad: magnitude must not exceed {MAX_ANGLE_RAD!r}, got {angle_rad!r}"
        )
    return angle_rad


def quadrant_reduction(angle_rad: float) -> tuple[int, float]:
    """Reduce an angle to a quadrant index and a residue in ``[-pi/4, pi/4]``.

    Parameters
    ----------
    angle_rad
        Angle in radians, inside the declared domain.

    Returns
    -------
    tuple of (int, float)
        The quadrant index ``n`` (the nearest integer to
        ``angle_rad / (pi/2)``, ties upward) and the residue
        ``angle_rad - n pi/2`` computed by subtracting the three words of
        the split in a fixed order.

    Raises
    ------
    GeometryError
        If the angle leaves the declared domain.

    Notes
    -----
    The index comes from ``floor(x * 2/pi + 1/2)``, the same shape the
    exponential kernel uses for its own Cody–Waite reduction, so both are
    a floor of one product and one addition and nothing about the result
    depends on a language's rounding convention.

    **The residue is not strictly bounded by ``pi/4``.** The quotient
    that picks the index is formed with a rounded ``2/pi``, so near a
    half-quadrant the index can be the neighbour of the nearest one and
    the residue then passes ``pi/4`` by an amount that grows with the
    angle. Scanned over the whole domain at the half-quadrant points, the
    excess is at most ``1.2e-16`` times the magnitude of the angle —
    ``3.9e-10`` at the top of the domain. The polynomials are evaluated
    at that residue anyway and their agreement with the platform library
    at the worst such point is one unit in the last place, measured, so
    the overshoot costs nothing; stating it is better than a bound that
    does not hold.
    """
    require_reducible_angle(angle_rad)
    index = math.floor(angle_rad * TWO_OVER_PI + 0.5)
    count = float(index)
    residue = ((angle_rad - count * PIO2_A) - count * PIO2_B) - count * PIO2_C
    return index, residue


def circle_point(angle_rad: float) -> tuple[float, float]:
    """Return ``(cos, sin)`` of an arbitrary angle, bit-exact across backends.

    Parameters
    ----------
    angle_rad
        Angle in radians, inside the declared domain.

    Returns
    -------
    tuple of (float, float)
        ``(cos(angle_rad), sin(angle_rad))``, from the same degree-15 and
        degree-16 polynomials :func:`circle_points` uses, evaluated on the
        residue of :func:`quadrant_reduction` and placed by the quadrant
        index through sign changes and swaps only.

    Raises
    ------
    GeometryError
        If the angle leaves the declared domain.

    Notes
    -----
    :func:`circle_points` stays the entry point for the equally spaced
    points of a tessellation or a ring: its angles are exact rational
    multiples of a turn, so it finds its quadrant by integer arithmetic
    and never needs this reduction. This function is for the angles a
    source prints — a latitude, a phase — which are not such multiples.
    Accuracy against the platform ``math`` module is measured in the test
    suite and stays within one unit in the last place across the domain;
    bit-exactness with the native kernel is the guarantee.
    """
    index, residue = quadrant_reduction(angle_rad)
    sine_value = sine_polynomial(residue)
    cosine_value = cosine_polynomial(residue)
    quadrant = index % 4
    if quadrant == 0:
        return cosine_value, sine_value
    if quadrant == 1:
        return 0.0 - sine_value, cosine_value
    if quadrant == 2:
        return 0.0 - cosine_value, 0.0 - sine_value
    return sine_value, 0.0 - cosine_value


def sine(angle_rad: float) -> float:
    """Return the sine of an arbitrary angle.

    Parameters
    ----------
    angle_rad
        Angle in radians, inside the declared domain.

    Returns
    -------
    float
        ``sin(angle_rad)``, the second member of :func:`circle_point`.

    Raises
    ------
    GeometryError
        If the angle leaves the declared domain.
    """
    return circle_point(angle_rad)[1]


def cosine(angle_rad: float) -> float:
    """Return the cosine of an arbitrary angle.

    Parameters
    ----------
    angle_rad
        Angle in radians, inside the declared domain.

    Returns
    -------
    float
        ``cos(angle_rad)``, the first member of :func:`circle_point`.

    Raises
    ------
    GeometryError
        If the angle leaves the declared domain.
    """
    return circle_point(angle_rad)[0]
