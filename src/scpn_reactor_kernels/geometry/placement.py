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

A body also has to be **aimed**. A ring of guns on a sphere points at the
centre, and a body that cannot be pointed is a body drawn in the wrong
place. The aiming rotation here is built from a polar and an azimuthal
circle point rather than from a direction vector, which is what keeps it
well conditioned everywhere — including at the negative ``z`` axis, where
the textbook minimal rotation from ``z`` to a vector loses every
significant digit. Nothing here describes a device.
"""

from __future__ import annotations

import math
from typing import Final

from scpn_reactor_kernels.errors import GeometryError, KernelInputError
from scpn_reactor_kernels.geometry.mesh import Vertex
from scpn_reactor_kernels.geometry.trig import (
    CirclePoint,
    circle_points,
    opposite_point,
    require_circle_point,
    require_circle_points,
    supplementary_point,
)
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


#: A rotation as its three rows. Every entry is a product of components of
#: the two supplied circle points, so the matrix carries no arithmetic of
#: its own beyond those products and their sign changes.
Rotation = tuple[Vertex, Vertex, Vertex]

#: A unit vector, as the axis a body is aimed along.
Direction = tuple[float, float, float]

#: Largest departure from orthonormality a supplied rotation may carry.
#: Measured: the rotations this kernel builds depart by at most
#: ``4.4e-16`` over two hundred thousand angle pairs, so this admits every
#: one of them with room to spare while refusing a matrix that scales or
#: reflects.
ROTATION_TOLERANCE: Final = 1.0e-12


def axis_direction(polar: CirclePoint, azimuth: CirclePoint) -> Direction:
    """Return the unit direction of a polar and an azimuthal angle.

    Parameters
    ----------
    polar
        ``(cos, sin)`` of the angle from the positive ``z`` axis.
    azimuth
        ``(cos, sin)`` of the angle around ``z`` from the positive ``x``
        axis.

    Returns
    -------
    tuple of (float, float, float)
        ``(sin(polar) cos(azimuth), sin(polar) sin(azimuth), cos(polar))``,
        two multiplications and a copy.

    Raises
    ------
    GeometryError
        If either pair is not a point of the unit circle.
    """
    polar_cosine, polar_sine = require_circle_point("polar", polar)
    azimuth_cosine, azimuth_sine = require_circle_point("azimuth", azimuth)
    return (
        polar_sine * azimuth_cosine,
        polar_sine * azimuth_sine,
        polar_cosine,
    )


def aim_rotation(polar: CirclePoint, azimuth: CirclePoint) -> Rotation:
    """Return the rotation that takes the positive ``z`` axis to a direction.

    Parameters
    ----------
    polar
        ``(cos, sin)`` of the angle from the positive ``z`` axis.
    azimuth
        ``(cos, sin)`` of the angle around ``z``.

    Returns
    -------
    tuple of three rows
        ``Rz(azimuth) Ry(polar)``, whose third column is exactly
        :func:`axis_direction` of the same two points.

    Raises
    ------
    GeometryError
        If either pair is not a point of the unit circle.

    Notes
    -----
    **The rotation is built from the two angles, never from a direction
    vector**, and that is the whole design. The textbook minimal rotation
    from ``z`` to a unit vector ``d`` divides by ``1 + d_z``, which loses
    every significant digit as ``d`` approaches the negative ``z`` axis
    because ``d_z`` resolves only to the last place of one. Measured on
    accurately built directions, that form departs from orthogonality by
    ``3.6e-4`` at a polar angle one microradian short of half a turn.
    This form has no such term: scanned over two hundred thousand angle
    pairs including every quarter-turn corner and the antipode itself,
    ``R^T R`` departs from the identity by at most
    ``4.440892098500626e-16`` and the determinant from one by
    ``5.551115123125783e-16``, while the third column reproduces
    :func:`axis_direction` bit for bit.

    **The roll about the aimed axis is a convention, not a consequence.**
    A direction fixes two of the three degrees of freedom; the third is
    chosen here as the azimuthal frame, which is the natural one for a
    body placed on a sphere. A consumer whose body is not axisymmetric
    about ``z`` and needs a particular clocking has to say so, and this
    kernel does not offer a way to.
    """
    polar_cosine, polar_sine = require_circle_point("polar", polar)
    azimuth_cosine, azimuth_sine = require_circle_point("azimuth", azimuth)
    return (
        (
            azimuth_cosine * polar_cosine,
            0.0 - azimuth_sine,
            azimuth_cosine * polar_sine,
        ),
        (
            azimuth_sine * polar_cosine,
            azimuth_cosine,
            azimuth_sine * polar_sine,
        ),
        (0.0 - polar_sine, 0.0, polar_cosine),
    )


def require_rotation(
    name: str, rotation: Rotation, error: type[KernelInputError] = GeometryError
) -> Rotation:
    """Validate a matrix as a rotation, not merely as nine finite numbers.

    Parameters
    ----------
    name
        Name of the argument, for the refusal message.
    rotation
        The three rows under validation.
    error
        Error class to raise; the B-rep tier passes its own.

    Returns
    -------
    tuple of three rows
        The validated rotation.

    Raises
    ------
    KernelInputError
        If any entry is non-finite, if ``R^T R`` departs from the
        identity by more than :data:`ROTATION_TOLERANCE`, or if the
        determinant departs from one by more than four times it. A
        matrix that scales or reflects would move a body and silently
        change its volume or its handedness, so a finiteness check alone
        would not be a gate.
    """
    for row_index, row in enumerate(rotation):
        for column_index, entry in enumerate(row):
            require_finite(f"{name}[{row_index}][{column_index}]", entry, error)
    for column in range(3):
        for other in range(3):
            product = sum(
                rotation[row][column] * rotation[row][other] for row in range(3)
            )
            expected = 1.0 if column == other else 0.0
            if abs(product - expected) > ROTATION_TOLERANCE:
                raise error(
                    f"{name}: columns must be orthonormal within "
                    f"{ROTATION_TOLERANCE!r}, got {product!r} where "
                    f"{expected!r} was required"
                )
    (a, b, c), (d, e, f), (g, h, i) = rotation
    determinant = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if abs(determinant - 1.0) > 4.0 * ROTATION_TOLERANCE:
        raise error(
            f"{name}: determinant must be one within "
            f"{4.0 * ROTATION_TOLERANCE!r}, got {determinant!r}"
        )
    return rotation


def rotate(vertices: tuple[Vertex, ...], rotation: Rotation) -> tuple[Vertex, ...]:
    """Rotate a vertex stream about the origin.

    Parameters
    ----------
    vertices
        Vertex stream of a tessellated body, built about ``z``.
    rotation
        The rotation, normally from :func:`aim_rotation`.

    Returns
    -------
    tuple of Vertex
        The rotated stream, three products and two additions per
        coordinate in the order ``x``, ``y``, ``z``.

    Raises
    ------
    GeometryError
        If the stream is empty or the matrix is not a rotation.
    """
    if not vertices:
        raise GeometryError("vertices: must not be empty")
    require_rotation("rotation", rotation)
    (first, second, third) = rotation
    return tuple(
        (
            first[0] * x + first[1] * y + first[2] * z,
            second[0] * x + second[1] * y + second[2] * z,
            third[0] * x + third[1] * y + third[2] * z,
        )
        for x, y, z in vertices
    )


def ring_azimuths(count: int, offset: CirclePoint) -> tuple[CirclePoint, ...]:
    """Return the azimuths of ``count`` members of a ring, twisted by an offset.

    Parameters
    ----------
    count
        Number of members; at least three.
    offset
        ``(cos, sin)`` of the angle the whole ring is turned by. Two rings
        of a real node set are rarely aligned, and the twist between them
        is a declared quantity of the device, not a property of a circle.

    Returns
    -------
    tuple of (float, float)
        ``(cos, sin)`` of each member's azimuth, in increasing angle. An
        offset of ``(1, 0)`` returns the points of
        :func:`~scpn_reactor_kernels.geometry.trig.circle_points`
        unchanged, bit for bit, because the rotation by it is the
        identity in exact arithmetic and in these operations.

    Raises
    ------
    GeometryError
        If the count is below three or the offset is not a point of the
        unit circle.
    """
    require_circle_points(count)
    offset_cosine, offset_sine = require_circle_point("offset", offset)
    return tuple(
        (
            cosine * offset_cosine - sine * offset_sine,
            sine * offset_cosine + cosine * offset_sine,
        )
        for cosine, sine in circle_points(count)
    )


def sphere_ring_offsets(
    count: int,
    radius_m: float,
    polar: CirclePoint,
    offset: CirclePoint,
) -> tuple[Vertex, ...]:
    """Return the centres of ``count`` bodies on one latitude of a sphere.

    Parameters
    ----------
    count
        Number of bodies on the latitude; at least three.
    radius_m
        Radius of the sphere their centres lie on; strictly positive.
    polar
        ``(cos, sin)`` of the latitude, measured from the positive ``z``
        axis.
    offset
        ``(cos, sin)`` of the twist of this latitude's ring.

    Returns
    -------
    tuple of Vertex
        ``(x, y, z)`` of each centre. The height and the radius in the
        plane are each one multiplication, and every centre then costs one
        more per coordinate, so all members of a latitude share the same
        ``z`` bit for bit.

    Raises
    ------
    GeometryError
        If the count is below three, the radius is not strictly positive,
        or either pair is not a point of the unit circle.
    """
    require_positive("radius_m", radius_m, GeometryError)
    polar_cosine, polar_sine = require_circle_point("polar", polar)
    height = radius_m * polar_cosine
    plane_radius = radius_m * polar_sine
    return tuple(
        (plane_radius * cosine, plane_radius * sine, height)
        for cosine, sine in ring_azimuths(count, offset)
    )


def inward_aim(polar: CirclePoint, azimuth: CirclePoint) -> Rotation:
    """Return the rotation aiming ``z`` from a point of a sphere at its centre.

    Parameters
    ----------
    polar
        ``(cos, sin)`` of the latitude the body sits on.
    azimuth
        ``(cos, sin)`` of the body's azimuth.

    Returns
    -------
    tuple of three rows
        The rotation whose axis is the exact negation of
        :func:`axis_direction` of the same two points: the latitude is
        reflected through the equator and the azimuth turned half a turn,
        both by sign changes alone, so no angle is formed a second time
        and no reduction runs twice.

    Raises
    ------
    GeometryError
        If either pair is not a point of the unit circle.
    """
    return aim_rotation(supplementary_point(polar), opposite_point(azimuth))


def centre_separation_m(first: Vertex, second: Vertex) -> float:
    """Return the distance between two body centres.

    Parameters
    ----------
    first, second
        Centres, in metres.

    Returns
    -------
    float
        The Euclidean distance, a square root of the sum of three
        squares. A device uses it to prove that bodies of a given radius
        placed on a sphere do not intersect, without implementing
        geometry of its own.

    Raises
    ------
    GeometryError
        If any coordinate is non-finite.
    """
    for name, centre in (("first", first), ("second", second)):
        for index, value in enumerate(centre):
            require_finite(f"{name}[{index}]", value, GeometryError)
    delta_x = second[0] - first[0]
    delta_y = second[1] - first[1]
    delta_z = second[2] - first[2]
    return math.sqrt(delta_x * delta_x + delta_y * delta_y + delta_z * delta_z)
