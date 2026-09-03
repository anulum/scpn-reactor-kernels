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
``math.sin`` and ``math.cos`` in the test suite. Nothing here describes a
device; it is the numerical substrate of the geometry.
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
