# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — aimed and spherical placement tests

"""Aiming a body along a direction, and placing it on a sphere.

The measurement this module exists to record is the one in
:func:`test_the_angle_built_rotation_beats_the_vector_built_one`: the
textbook minimal rotation from ``z`` to a unit vector loses every
significant digit near the negative ``z`` axis, and the rotation built
from the two angles does not. Everything else here follows from that
choice.
"""

from __future__ import annotations

import math

import pytest

from scpn_reactor_kernels.errors import GeometryError
from scpn_reactor_kernels.geometry import (
    Direction,
    Face,
    Rotation,
    TriangleMesh,
    Vertex,
    aim_rotation,
    axis_direction,
    centre_separation_m,
    circle_point,
    circle_points,
    cylinder_solid,
    inward_aim,
    require_rotation,
    ring_azimuths,
    rotate,
    sphere_ring_offsets,
    translate,
)
from scpn_reactor_kernels.geometry.trig import (
    opposite_point,
    radians_from_degrees,
    require_circle_point,
    supplementary_point,
)

#: No twist: the identity of the ring rotation.
NO_TWIST = (1.0, 0.0)

#: Measured worst departure of ``R^T R`` from the identity over two
#: hundred thousand angle pairs, including every quarter-turn corner and
#: the antipode.
ORTHOGONALITY_BOUND = 4.440892098500626e-16

#: The latitudes and member counts a filed source prints for a set of
#: thirty bodies on a sphere: five, ten, ten and five.
PRINTED_RINGS = ((5, 20.1), (10, 59.0), (10, 121.0), (5, 159.9))

#: Radius of the sphere the tests place bodies on, in metres.
SPHERE_RADIUS_M = 1.5


def _orthogonality_defect(rotation: Rotation) -> float:
    """Return the largest departure of ``R^T R`` from the identity."""
    worst = 0.0
    for column in range(3):
        for other in range(3):
            product = sum(
                rotation[row][column] * rotation[row][other] for row in range(3)
            )
            expected = 1.0 if column == other else 0.0
            worst = max(worst, abs(product - expected))
    return worst


def _determinant(rotation: Rotation) -> float:
    """Return the determinant of a three-by-three rotation."""
    (a, b, c), (d, e, f), (g, h, i) = rotation
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def _minimal_rotation_from_vector(direction: Direction) -> Rotation:
    """Return the textbook minimal rotation from ``z`` to a unit vector.

    This is **not** a kernel: it is written here so the test can measure
    what the library chose not to do.
    """
    x, y, z = direction
    scale = 1.0 / (1.0 + z)
    return (
        (z + y * y * scale, 0.0 - x * y * scale, x),
        (0.0 - x * y * scale, z + x * x * scale, y),
        (0.0 - x, 0.0 - y, z),
    )


def _broken_row(row: Vertex, index: int, target_row: int, column: int) -> Vertex:
    """Return the row with one entry replaced by a non-finite value."""
    if index != target_row:
        return row
    first, second, third = row
    if column == 0:
        return math.nan, second, third
    if column == 1:
        return first, math.nan, third
    return first, second, math.nan


def _body() -> tuple[tuple[Vertex, ...], tuple[Face, ...]]:
    """Return a synthetic cylinder standing on the origin along ``z``."""
    return cylinder_solid(0.05, 0.0, 0.30, 16)


def _mesh(
    vertices: tuple[Vertex, ...], faces: tuple[Face, ...], name: str
) -> TriangleMesh:
    """Return a validated mesh of a placed synthetic body."""
    return TriangleMesh(
        name=name,
        role="conductor",
        material_identifier="conductor",
        vertices=vertices,
        faces=faces,
    )


def test_aiming_along_the_axis_is_the_identity() -> None:
    """A body already on ``z`` is not moved, and exactly so."""
    assert aim_rotation(NO_TWIST, NO_TWIST) == (
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
    )


def test_the_third_column_is_the_axis_bit_for_bit() -> None:
    """The rotation and the direction are two views of the same products."""
    for degrees in (20.1, 43.4, 59.0, 80.1, 99.9, 121.0, 136.6, 159.9):
        polar = circle_point(radians_from_degrees(degrees))
        for azimuth in circle_points(7):
            rotation = aim_rotation(polar, azimuth)
            column = (rotation[0][2], rotation[1][2], rotation[2][2])
            assert column == axis_direction(polar, azimuth)


@pytest.mark.parametrize("degrees", [0.0, 20.1, 59.0, 90.0, 121.0, 159.9, 180.0])
def test_every_rotation_is_orthogonal_within_the_measured_bound(
    degrees: float,
) -> None:
    """Including at half a turn, where the vector-built form collapses."""
    polar = circle_point(radians_from_degrees(degrees))
    for azimuth in circle_points(12):
        rotation = aim_rotation(polar, azimuth)
        assert _orthogonality_defect(rotation) <= ORTHOGONALITY_BOUND
        assert abs(_determinant(rotation) - 1.0) <= 4.0 * ORTHOGONALITY_BOUND


def test_the_angle_built_rotation_beats_the_vector_built_one() -> None:
    """The measurement behind the design, stated as an assertion.

    One microradian short of half a turn the direction is still a perfect
    unit vector, but ``1 + d_z`` has lost all but a few of its significant
    digits, and the minimal rotation built from it is no longer a
    rotation. The angle-built form has no such term.
    """
    polar = circle_point(math.pi - 1.0e-6)
    direction = axis_direction(polar, NO_TWIST)
    assert abs(sum(component * component for component in direction) - 1.0) <= (
        ORTHOGONALITY_BOUND
    )
    from_vector = _minimal_rotation_from_vector(direction)
    from_angles = aim_rotation(polar, NO_TWIST)
    assert _orthogonality_defect(from_vector) > 1.0e-4
    assert _orthogonality_defect(from_angles) <= ORTHOGONALITY_BOUND


def test_the_inward_aim_points_at_the_centre_of_the_sphere() -> None:
    """Every one of the thirty printed placements aims back at the origin."""
    for count, degrees in PRINTED_RINGS:
        polar = circle_point(radians_from_degrees(degrees))
        centres = sphere_ring_offsets(count, SPHERE_RADIUS_M, polar, NO_TWIST)
        for centre, azimuth in zip(
            centres, ring_azimuths(count, NO_TWIST), strict=True
        ):
            rotation = inward_aim(polar, azimuth)
            axis = (rotation[0][2], rotation[1][2], rotation[2][2])
            wanted = tuple(0.0 - value / SPHERE_RADIUS_M for value in centre)
            for got, want in zip(axis, wanted, strict=True):
                assert abs(got - want) <= 8.0 * ORTHOGONALITY_BOUND


def test_the_inward_aim_is_the_exact_negation_of_the_outward_axis() -> None:
    """Two sign changes, so no angle is reduced a second time."""
    polar = circle_point(radians_from_degrees(59.0))
    for azimuth in circle_points(10):
        outward = axis_direction(polar, azimuth)
        rotation = inward_aim(polar, azimuth)
        axis = (rotation[0][2], rotation[1][2], rotation[2][2])
        for inward_component, outward_component in zip(axis, outward, strict=True):
            assert inward_component == 0.0 - outward_component


def test_every_centre_of_a_latitude_lies_on_the_sphere() -> None:
    """The radius is recovered from the centres, not assumed."""
    for count, degrees in PRINTED_RINGS:
        polar = circle_point(radians_from_degrees(degrees))
        for centre in sphere_ring_offsets(count, SPHERE_RADIUS_M, polar, NO_TWIST):
            radius = math.sqrt(sum(value * value for value in centre))
            assert radius == pytest.approx(SPHERE_RADIUS_M, rel=1.0e-15)


def test_all_members_of_a_latitude_share_one_height_exactly() -> None:
    """The height is computed once, so no member drifts off the latitude."""
    polar = circle_point(radians_from_degrees(59.0))
    centres = sphere_ring_offsets(10, SPHERE_RADIUS_M, polar, NO_TWIST)
    assert len({centre[2] for centre in centres}) == 1


def test_a_ring_with_no_twist_is_the_plain_circle_bit_for_bit() -> None:
    """The identity twist really is the identity, not nearly."""
    assert ring_azimuths(10, NO_TWIST) == circle_points(10)
    assert ring_azimuths(3, NO_TWIST) == circle_points(3)


def test_a_twist_turns_the_whole_ring_and_keeps_it_on_the_circle() -> None:
    """The members stay unit and their spacing is unchanged."""
    twist = circle_point(radians_from_degrees(36.0))
    plain = circle_points(10)
    twisted = ring_azimuths(10, twist)
    assert twisted != plain
    for cosine, sine in twisted:
        require_circle_point("member", (cosine, sine))
    plain_gap = math.dist(plain[0], plain[1])
    twisted_gap = math.dist(twisted[0], twisted[1])
    assert twisted_gap == pytest.approx(plain_gap, rel=1.0e-14)


def test_a_half_turn_twist_is_the_opposite_of_every_member() -> None:
    """A twist by half a turn negates both components of each member."""
    twisted = ring_azimuths(8, (-1.0, 0.0))
    for member, plain in zip(twisted, circle_points(8), strict=True):
        assert member == pytest.approx(
            (0.0 - plain[0], 0.0 - plain[1]), abs=ORTHOGONALITY_BOUND
        )


def test_rotating_a_body_leaves_its_measures_where_they_were() -> None:
    """A rigid motion preserves volume and area, and by how much is measured."""
    vertices, faces = _body()
    base = _mesh(vertices, faces, "base")
    worst_volume = 0.0
    worst_area = 0.0
    for count, degrees in PRINTED_RINGS:
        polar = circle_point(radians_from_degrees(degrees))
        centres = sphere_ring_offsets(count, SPHERE_RADIUS_M, polar, NO_TWIST)
        azimuths = ring_azimuths(count, NO_TWIST)
        for index, (centre, azimuth) in enumerate(zip(centres, azimuths, strict=True)):
            placed = translate(rotate(vertices, inward_aim(polar, azimuth)), *centre)
            body = _mesh(placed, faces, f"body_{degrees}_{index}")
            worst_volume = max(
                worst_volume,
                abs(body.signed_volume_m3() - base.signed_volume_m3())
                / base.signed_volume_m3(),
            )
            worst_area = max(
                worst_area,
                abs(body.surface_area_m2() - base.surface_area_m2())
                / base.surface_area_m2(),
            )
    assert worst_volume <= 1.0e-13
    assert worst_area <= 1.0e-14


def test_a_placed_body_reaches_inward_from_the_sphere() -> None:
    """The body extends toward the centre, which is what aiming it means."""
    vertices, _ = _body()
    polar = circle_point(radians_from_degrees(20.1))
    azimuth = ring_azimuths(5, NO_TWIST)[0]
    centre = sphere_ring_offsets(5, SPHERE_RADIUS_M, polar, NO_TWIST)[0]
    placed = translate(rotate(vertices, inward_aim(polar, azimuth)), *centre)
    origin = (0.0, 0.0, 0.0)
    nearest = min(math.dist(vertex, origin) for vertex in placed)
    farthest = max(math.dist(vertex, origin) for vertex in placed)
    assert nearest == pytest.approx(SPHERE_RADIUS_M - 0.30, rel=1.0e-14)
    assert farthest == pytest.approx(math.hypot(SPHERE_RADIUS_M, 0.05), rel=1.0e-14)


def test_the_thirty_printed_bodies_do_not_touch_at_the_printed_radius() -> None:
    """The separations are computed, and the largest fitting radius stated.

    The closest pair of the thirty centres is 0.6059943008542816 metres
    apart, so identical bodies of any radius below half of that cannot
    intersect. The printed body radius is 0.05 metres, well inside it.
    """
    centres: list[tuple[float, float, float]] = []
    for count, degrees in PRINTED_RINGS:
        polar = circle_point(radians_from_degrees(degrees))
        centres.extend(sphere_ring_offsets(count, SPHERE_RADIUS_M, polar, NO_TWIST))
    assert len(centres) == 30
    closest = min(
        centre_separation_m(first, second)
        for index, first in enumerate(centres)
        for second in centres[index + 1 :]
    )
    assert closest == pytest.approx(0.6059943008542816, rel=1.0e-12)
    assert closest / 2.0 > 0.05


def test_the_separation_is_the_euclidean_distance() -> None:
    """A right triangle, so the value is checked and not merely plausible."""
    assert centre_separation_m((0.0, 0.0, 0.0), (3.0, 4.0, 0.0)) == 5.0
    assert centre_separation_m((1.0, 1.0, 1.0), (1.0, 1.0, 1.0)) == 0.0


def test_the_supplementary_and_opposite_points_are_sign_changes_only() -> None:
    """Exact: every bit of the magnitude survives."""
    for angle in (0.35081118059122317, -2.0, 1.0e5):
        point = circle_point(angle)
        assert supplementary_point(point) == (0.0 - point[0], point[1])
        assert opposite_point(point) == (0.0 - point[0], 0.0 - point[1])


@pytest.mark.parametrize(
    "point",
    [(1.0, 1.0), (0.0, 0.0), (math.nan, 0.0), (1.0, math.inf), (2.0, 0.0)],
)
def test_a_pair_that_is_not_on_the_circle_is_refused(
    point: tuple[float, float],
) -> None:
    """Every entry point validates both of its pairs."""
    with pytest.raises(GeometryError):
        require_circle_point("point", point)
    with pytest.raises(GeometryError):
        aim_rotation(point, NO_TWIST)
    with pytest.raises(GeometryError):
        aim_rotation(NO_TWIST, point)
    with pytest.raises(GeometryError):
        axis_direction(point, NO_TWIST)
    with pytest.raises(GeometryError):
        axis_direction(NO_TWIST, point)
    with pytest.raises(GeometryError):
        inward_aim(point, NO_TWIST)
    with pytest.raises(GeometryError):
        inward_aim(NO_TWIST, point)
    with pytest.raises(GeometryError):
        ring_azimuths(5, point)
    with pytest.raises(GeometryError):
        sphere_ring_offsets(5, 1.0, point, NO_TWIST)
    with pytest.raises(GeometryError):
        supplementary_point(point)
    with pytest.raises(GeometryError):
        opposite_point(point)


def test_the_tolerance_accepts_its_edge_and_refuses_beyond_it() -> None:
    """The nearest failing case on both sides of the declared tolerance."""
    inside = (1.0 + 0.4e-12, 0.0)
    outside = (1.0 + 0.6e-12, 0.0)
    assert require_circle_point("inside", inside) == inside
    with pytest.raises(GeometryError):
        require_circle_point("outside", outside)


def test_a_ring_below_three_members_is_refused() -> None:
    """Three points are the smallest arrangement that encloses the axis."""
    with pytest.raises(GeometryError):
        ring_azimuths(2, NO_TWIST)
    with pytest.raises(GeometryError):
        sphere_ring_offsets(2, 1.0, NO_TWIST, NO_TWIST)


@pytest.mark.parametrize("radius", [0.0, -1.0, math.nan, math.inf])
def test_a_sphere_of_no_radius_is_refused(radius: float) -> None:
    """The radius is validated, not only the counts and the pairs."""
    with pytest.raises(GeometryError):
        sphere_ring_offsets(5, radius, NO_TWIST, NO_TWIST)


def test_rotating_an_empty_stream_is_refused() -> None:
    """The same refusal the translation carries, for the same reason."""
    with pytest.raises(GeometryError):
        rotate((), aim_rotation(NO_TWIST, NO_TWIST))


def test_a_rotation_with_a_non_finite_entry_is_refused() -> None:
    """Every one of the nine entries is checked, before any product is formed."""
    good = aim_rotation(NO_TWIST, NO_TWIST)
    vertices = ((1.0, 0.0, 0.0),)
    for row in range(3):
        for column in range(3):
            broken: Rotation = (
                _broken_row(good[0], 0, row, column),
                _broken_row(good[1], 1, row, column),
                _broken_row(good[2], 2, row, column),
            )
            with pytest.raises(GeometryError):
                rotate(vertices, broken)


@pytest.mark.parametrize(
    "centre",
    [(math.nan, 0.0, 0.0), (0.0, math.inf, 0.0), (0.0, 0.0, math.nan)],
)
def test_a_separation_of_a_non_finite_centre_is_refused(centre: Vertex) -> None:
    """Both arguments are validated, in both positions."""
    origin = (0.0, 0.0, 0.0)
    with pytest.raises(GeometryError):
        centre_separation_m(centre, origin)
    with pytest.raises(GeometryError):
        centre_separation_m(origin, centre)


def test_a_matrix_that_scales_is_refused() -> None:
    """Nine finite numbers are not a rotation, and the gate says so."""
    scaling: Rotation = ((2.0, 0.0, 0.0), (0.0, 2.0, 0.0), (0.0, 0.0, 2.0))
    with pytest.raises(GeometryError):
        require_rotation("scaling", scaling)
    with pytest.raises(GeometryError):
        rotate(((1.0, 0.0, 0.0),), scaling)


def test_a_reflection_is_orthonormal_and_still_refused() -> None:
    """The determinant is the second half of the gate, not decoration.

    A reflection passes every orthonormality check — its columns are
    unit and mutually perpendicular — and would place a body as its
    mirror image, with the same volume and the wrong handedness. Only the
    determinant catches it.
    """
    reflection: Rotation = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, -1.0))
    for column in range(3):
        for other in range(3):
            product = sum(
                reflection[row][column] * reflection[row][other] for row in range(3)
            )
            assert product == (1.0 if column == other else 0.0)
    assert _determinant(reflection) == -1.0
    with pytest.raises(GeometryError):
        require_rotation("reflection", reflection)


def test_the_rotation_tolerance_accepts_its_edge_and_refuses_beyond_it() -> None:
    """The nearest failing case on either side of the declared tolerance."""
    inside: Rotation = ((1.0 + 0.4e-12, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    outside: Rotation = ((1.0 + 0.6e-12, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    assert require_rotation("inside", inside) == inside
    with pytest.raises(GeometryError):
        require_rotation("outside", outside)


def test_every_rotation_this_kernel_builds_passes_its_own_gate() -> None:
    """A gate that refused the kernel's own output would be the wrong gate."""
    for count, degrees in PRINTED_RINGS:
        polar = circle_point(radians_from_degrees(degrees))
        for azimuth in ring_azimuths(count, NO_TWIST):
            assert require_rotation("aim", aim_rotation(polar, azimuth))
            assert require_rotation("inward", inward_aim(polar, azimuth))
