# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — placement of tessellated bodies off the axis

"""Exact placement of tessellated bodies away from the device axis.

The tessellation primitives build every body centred on ``z``. Real
assemblies also carry bodies that are NOT on the axis — the rods of a
squirrel-cage cathode, a ring of feed conductors, a set of ports — and a
device repository must never re-implement geometry to place them. This
kernel provides the two exact operations that placement needs: a
translation of a vertex stream, and the offsets of ``count`` identical
bodies equally spaced on a circle of a given radius around the axis.

Both are exact in the sense the group requires: the translation is one
IEEE-754 addition per coordinate in a fixed order, and the ring offsets
are the deterministic circle points of
:func:`~scpn_reactor_kernels.geometry.trig.circle_points` scaled by the
radius, so the native kernel reproduces every coordinate bit for bit.
Nothing here describes a device.
"""

from __future__ import annotations

import math

from scpn_reactor_kernels.errors import GeometryError
from scpn_reactor_kernels.geometry.mesh import Vertex
from scpn_reactor_kernels.geometry.trig import circle_points, require_circle_points
from scpn_reactor_kernels.validation import require_finite, require_positive


def translate(
    vertices: tuple[Vertex, ...],
    offset_x_m: float,
    offset_y_m: float,
    offset_z_m: float,
) -> tuple[Vertex, ...]:
    """Translate a vertex stream by a fixed offset.

    Parameters
    ----------
    vertices
        Vertex stream of a tessellated body.
    offset_x_m, offset_y_m, offset_z_m
        Translation in metres; every component finite.

    Returns
    -------
    tuple of Vertex
        The translated stream, one addition per coordinate in the order
        ``x``, ``y``, ``z``.

    Raises
    ------
    GeometryError
        If the stream is empty or any offset component is non-finite.
    """
    if not vertices:
        raise GeometryError("vertices: must not be empty")
    require_finite("offset_x_m", offset_x_m, GeometryError)
    require_finite("offset_y_m", offset_y_m, GeometryError)
    require_finite("offset_z_m", offset_z_m, GeometryError)
    return tuple(
        (x + offset_x_m, y + offset_y_m, z + offset_z_m) for x, y, z in vertices
    )


def ring_offsets(count: int, radius_m: float) -> tuple[tuple[float, float], ...]:
    """Return the centres of ``count`` bodies equally spaced on a circle.

    Parameters
    ----------
    count
        Number of bodies on the circle; at least three.
    radius_m
        Radius of the circle their centres lie on; strictly positive.

    Returns
    -------
    tuple of (float, float)
        ``(x, y)`` of each centre, starting on the positive ``x`` axis and
        increasing in angle; one multiplication per coordinate.

    Raises
    ------
    GeometryError
        If the count is below three or the radius is not strictly positive.
    """
    require_circle_points(count)
    require_positive("radius_m", radius_m, GeometryError)
    return tuple(
        (radius_m * cosine, radius_m * sine) for cosine, sine in circle_points(count)
    )


def ring_separation_m(count: int, radius_m: float) -> float:
    """Return the centre-to-centre distance of neighbours on the ring.

    Parameters
    ----------
    count
        Number of bodies on the circle; at least three.
    radius_m
        Radius of the circle their centres lie on; strictly positive.

    Returns
    -------
    float
        Distance between the first two centres of :func:`ring_offsets`,
        computed as a square root of the sum of two squares, which is the
        same distance for every neighbouring pair by construction. A
        device uses it to prove that identical bodies of a given radius on
        the ring do not intersect.

    Raises
    ------
    GeometryError
        If the count is below three or the radius is not strictly positive.
    """
    offsets = ring_offsets(count, radius_m)
    first_x, first_y = offsets[0]
    second_x, second_y = offsets[1]
    delta_x = second_x - first_x
    delta_y = second_y - first_y
    return math.sqrt(delta_x * delta_x + delta_y * delta_y)
