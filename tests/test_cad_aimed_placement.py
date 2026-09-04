# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — aimed B-rep placement tests

"""Placing a B-rep body on a sphere, aimed by the tier-G1 rotation.

The measurements here are what the record is allowed to claim: how far
the back-end's own frame departs from the rotation it was handed, and how
far its measures of a placed solid depart from the analytic forms of the
source. Both are scanned over the thirty placements a filed source
prints, not sampled at one.
"""

from __future__ import annotations

import math

import pytest

from cad_fixtures import CYLINDER_EXTENT_M, CYLINDER_RADIUS_M, cylinder
from scpn_reactor_kernels.cad import (
    MEASURE_TOLERANCE,
    place_brep,
    sphere_ring_brep_bodies,
)
from scpn_reactor_kernels.errors import CadError
from scpn_reactor_kernels.geometry import (
    Rotation,
    Vertex,
    aim_rotation,
    circle_point,
    inward_aim,
    ring_azimuths,
    sphere_ring_offsets,
)
from scpn_reactor_kernels.geometry.trig import radians_from_degrees

#: No twist between latitudes.
NO_TWIST = (1.0, 0.0)

#: The latitudes and member counts a filed source prints for thirty
#: bodies on a sphere.
PRINTED_RINGS = ((5, 20.1), (10, 59.0), (10, 121.0), (5, 159.9))

#: Radius of the sphere, in metres.
SPHERE_RADIUS_M = 1.5

#: Measured worst relative departure of the back-end's measures of a
#: placed solid from the analytic forms of the source, over the thirty
#: printed placements.
PLACED_MEASURE_BOUND = 4.0e-16

#: Measured worst departure of the frame the back-end builds from the
#: tier-G1 rotation it was handed, in any component.
FRAME_BOUND = 1.1102230246251565e-16

ORIGIN = (0.0, 0.0, 0.0)


def _placements() -> list[tuple[str, Vertex, Rotation]]:
    """Return the thirty printed centres with their inward rotations."""
    out = []
    for count, degrees in PRINTED_RINGS:
        polar = circle_point(radians_from_degrees(degrees))
        centres = sphere_ring_offsets(count, SPHERE_RADIUS_M, polar, NO_TWIST)
        azimuths = ring_azimuths(count, NO_TWIST)
        for index, (centre, azimuth) in enumerate(zip(centres, azimuths, strict=True)):
            out.append((f"body_{degrees}_{index}", centre, inward_aim(polar, azimuth)))
    return out


def test_the_placement_carries_the_analytic_measures_unchanged() -> None:
    """A rigid motion leaves the closed forms invariant, so they are copied."""
    body = cylinder()
    name, centre, rotation = _placements()[0]
    placed = place_brep(body, rotation, centre, name)
    assert placed.analytic_volume_m3 == body.analytic_volume_m3
    assert placed.analytic_surface_area_m2 == body.analytic_surface_area_m2
    assert placed.role == body.role
    assert placed.material_identifier == body.material_identifier
    assert placed.name == name


def test_every_printed_placement_stays_within_the_measured_bound() -> None:
    """Scanned over all thirty, not sampled at one."""
    body = cylinder()
    worst_volume = 0.0
    worst_area = 0.0
    for name, centre, rotation in _placements():
        placed = place_brep(body, rotation, centre, name)
        worst_volume = max(worst_volume, placed.volume_relative_error())
        worst_area = max(worst_area, placed.surface_area_relative_error())
    assert worst_volume <= PLACED_MEASURE_BOUND
    assert worst_area <= PLACED_MEASURE_BOUND
    assert PLACED_MEASURE_BOUND <= MEASURE_TOLERANCE


def test_the_placed_body_reaches_inward_from_the_sphere() -> None:
    """The box proves the body leans at the centre, not away from it.

    The axis-aligned box of a cylinder is symmetric about the cylinder's
    midpoint, so the centre of the box is the midpoint of the axis. A
    body of length ``L`` standing on a sphere of radius ``R`` and aimed
    inward has that midpoint at ``R - L/2`` from the origin, and at
    ``R + L/2`` if it were aimed outward. The difference is the whole
    claim.
    """
    body = cylinder()
    length = CYLINDER_EXTENT_M[1] - CYLINDER_EXTENT_M[0]
    for _, centre, rotation in _placements():
        placed = place_brep(body, rotation, centre)
        low, high = placed.bounding_box_m()
        midpoint = tuple((low[axis] + high[axis]) / 2.0 for axis in range(3))
        assert math.dist(ORIGIN, midpoint) == pytest.approx(
            SPHERE_RADIUS_M - length / 2.0, rel=1.0e-9
        )


def test_the_name_may_be_kept_or_replaced() -> None:
    """A latitude needs one name per member; a single placement need not rename."""
    body = cylinder()
    _, centre, rotation = _placements()[0]
    assert place_brep(body, rotation, centre).name == body.name
    assert place_brep(body, rotation, centre, "renamed").name == "renamed"


def test_a_latitude_of_bodies_is_placed_in_order() -> None:
    """Names, centres and rotations line up member for member."""
    body = cylinder()
    placements = _placements()[:5]
    names = tuple(name for name, _, _ in placements)
    centres = tuple(centre for _, centre, _ in placements)
    rotations = tuple(rotation for _, _, rotation in placements)
    placed = sphere_ring_brep_bodies(body, names, centres, rotations)
    assert tuple(member.name for member in placed) == names
    for member in placed:
        assert member.volume_relative_error() <= PLACED_MEASURE_BOUND


def test_the_two_tiers_are_handed_the_same_rotation() -> None:
    """The frame the back-end builds departs from it by the measured bound.

    This is the assertion that says the tessellated body and the B-rep
    body are placed in one frame rather than two that happen to look
    alike.
    """
    cadquery = pytest.importorskip("cadquery")
    for _, centre, rotation in _placements():
        first_column = (rotation[0][0], rotation[1][0], rotation[2][0])
        third_column = (rotation[0][2], rotation[1][2], rotation[2][2])
        plane = cadquery.Plane(origin=centre, xDir=first_column, normal=third_column)
        for got, want in zip(plane.zDir.toTuple(), third_column, strict=True):
            assert abs(got - want) <= FRAME_BOUND
        for got, want in zip(plane.xDir.toTuple(), first_column, strict=True):
            assert abs(got - want) <= FRAME_BOUND


def test_a_matrix_that_is_not_a_rotation_is_refused() -> None:
    """A scaling would silently change the volume, so it is a gate."""
    body = cylinder()
    scaling: Rotation = ((2.0, 0.0, 0.0), (0.0, 2.0, 0.0), (0.0, 0.0, 2.0))
    reflection: Rotation = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, -1.0))
    broken: Rotation = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, math.nan))
    for matrix in (scaling, reflection, broken):
        with pytest.raises(CadError):
            place_brep(body, matrix, ORIGIN)


@pytest.mark.parametrize(
    "centre",
    [(math.nan, 0.0, 0.0), (0.0, math.inf, 0.0), (0.0, 0.0, math.nan)],
)
def test_a_non_finite_centre_is_refused(centre: Vertex) -> None:
    """Every component of the centre is validated."""
    body = cylinder()
    identity = aim_rotation(NO_TWIST, NO_TWIST)
    with pytest.raises(CadError):
        place_brep(body, identity, centre)


def test_an_empty_name_is_refused() -> None:
    """An empty name would produce an unnamed node in an assembly."""
    body = cylinder()
    identity = aim_rotation(NO_TWIST, NO_TWIST)
    with pytest.raises(CadError):
        place_brep(body, identity, ORIGIN, "")


def test_a_latitude_refuses_a_mismatched_or_repeated_set() -> None:
    """The three sequences must agree, and the names must be unique."""
    body = cylinder()
    placements = _placements()[:5]
    names = tuple(name for name, _, _ in placements)
    centres = tuple(centre for _, centre, _ in placements)
    rotations = tuple(rotation for _, _, rotation in placements)
    with pytest.raises(CadError):
        sphere_ring_brep_bodies(body, names, (), ())
    with pytest.raises(CadError):
        sphere_ring_brep_bodies(body, names[:-1], centres, rotations)
    with pytest.raises(CadError):
        sphere_ring_brep_bodies(body, names, centres, rotations[:-1])
    repeated = (names[0],) * len(names)
    with pytest.raises(CadError):
        sphere_ring_brep_bodies(body, repeated, centres, rotations)


def test_the_identity_placement_at_the_origin_keeps_the_body_where_it_was() -> None:
    """The smallest case: nothing moves, and the measures say so."""
    body = cylinder()
    identity = aim_rotation(NO_TWIST, NO_TWIST)
    placed = place_brep(body, identity, ORIGIN)
    assert placed.volume_m3 == pytest.approx(body.volume_m3, rel=1.0e-15)
    assert placed.surface_area_m2 == pytest.approx(body.surface_area_m2, rel=1.0e-15)
    assert CYLINDER_RADIUS_M > 0.0
