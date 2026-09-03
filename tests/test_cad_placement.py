# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — B-rep placement tests

"""Translation leaves every measure invariant, shifts the box, and refuses."""

from __future__ import annotations

import math

import pytest

from cad_fixtures import CYLINDER_RADIUS_M, cylinder, tube
from scpn_reactor_kernels.cad import (
    MEASURE_TOLERANCE,
    BrepAssembly,
    facet_body,
    inscribed_polygon_area_ratio,
    ring_brep_bodies,
    translate_brep,
)
from scpn_reactor_kernels.errors import CadError
from scpn_reactor_kernels.geometry import (
    TriangleMesh,
    cylinder_solid,
    ring_offsets,
    translate,
)

OFFSET_M = (0.11, -0.07, 0.013)


def test_translation_carries_the_analytic_measures_unchanged() -> None:
    """The closed forms are invariant; the measured solid stays in tolerance."""
    body = cylinder()
    placed = translate_brep(body, *OFFSET_M)
    assert placed.analytic_volume_m3 == body.analytic_volume_m3
    assert placed.analytic_surface_area_m2 == body.analytic_surface_area_m2
    assert placed.volume_relative_error() <= MEASURE_TOLERANCE
    assert placed.surface_area_relative_error() <= MEASURE_TOLERANCE


def test_the_measure_of_a_placed_solid_is_not_claimed_bit_identical() -> None:
    """OpenCASCADE integrates the moved surface; only the tolerance is claimed.

    The kernel is a pinned third-party numerical kernel, not the group's
    bit-exact floor. This test states the boundary rather than hiding it:
    every placed member of a ring of identical bodies agrees with the
    analytic form inside the declared tolerance, and the measured volumes
    of the members are not required to be equal to one another.
    """
    bodies = ring_brep_bodies(
        cylinder(),
        tuple(f"rod_{index:02d}" for index in range(8)),
        ring_offsets(8, 0.4),
    )
    volumes = {body.volume_m3 for body in bodies}
    assert all(body.volume_relative_error() <= MEASURE_TOLERANCE for body in bodies)
    assert all(
        abs(volume - bodies[0].analytic_volume_m3) / bodies[0].analytic_volume_m3
        <= MEASURE_TOLERANCE
        for volume in volumes
    )


def test_translation_shifts_the_bounding_box_by_the_offset() -> None:
    """Every box component moves by exactly its offset component."""
    body = tube()
    placed = translate_brep(body, *OFFSET_M)
    low, high = body.bounding_box_m()
    placed_low, placed_high = placed.bounding_box_m()
    for index, offset in enumerate(OFFSET_M):
        assert math.isclose(placed_low[index], low[index] + offset, abs_tol=1.0e-9)
        assert math.isclose(placed_high[index], high[index] + offset, abs_tol=1.0e-9)


def test_translation_keeps_the_identity_and_may_rename() -> None:
    """Role and material token survive; the name is the caller's choice."""
    body = cylinder()
    kept = translate_brep(body, 0.0, 0.0, 1.0)
    assert kept.name == body.name
    renamed = translate_brep(body, 0.0, 0.0, 1.0, "rod_00")
    assert renamed.name == "rod_00"
    assert renamed.role == body.role
    assert renamed.material_identifier == body.material_identifier


def test_placed_body_facets_to_the_translated_tier_g1_mesh() -> None:
    """Faceting a placed solid agrees with translating the G1 mesh in volume."""
    body = cylinder()
    placed = translate_brep(body, OFFSET_M[0], OFFSET_M[1], 0.0)
    faceted = facet_body(placed, 1.0e-4, 0.1)
    vertices, faces = cylinder_solid(CYLINDER_RADIUS_M, 0.0, 0.3, 64)
    reference = TriangleMesh(
        name="inner",
        role="electrode",
        material_identifier="conductor",
        vertices=translate(vertices, OFFSET_M[0], OFFSET_M[1], 0.0),
        faces=faces,
    )
    analytic = body.analytic_volume_m3
    difference = abs(faceted.signed_volume_m3() - reference.signed_volume_m3())
    assert difference / analytic <= 1.0 - inscribed_polygon_area_ratio(64)
    low, high = faceted.bounding_box()
    assert math.isclose(0.5 * (low[0] + high[0]), OFFSET_M[0], abs_tol=1.0e-6)
    assert math.isclose(0.5 * (low[1] + high[1]), OFFSET_M[1], abs_tol=1.0e-6)


def test_ring_of_placed_bodies_assembles_with_the_tier_g1_centres() -> None:
    """One solid placed once per ring centre gives a valid assembly."""
    count = 12
    radius = 0.5
    names = tuple(f"rod_{index:02d}" for index in range(count))
    bodies = ring_brep_bodies(cylinder(), names, ring_offsets(count, radius))
    assert tuple(body.name for body in bodies) == names
    manifest = BrepAssembly(bodies).manifest()
    assert manifest["body_count"] == count
    for body in bodies:
        assert body.volume_relative_error() <= MEASURE_TOLERANCE
        low, high = body.bounding_box_m()
        centre_x = 0.5 * (low[0] + high[0])
        centre_y = 0.5 * (low[1] + high[1])
        assert math.isclose(math.hypot(centre_x, centre_y), radius, abs_tol=1.0e-9)


def test_placement_refuses_a_non_finite_offset() -> None:
    """A non-finite offset component is named in the refusal."""
    body = cylinder()
    for index, name in enumerate(("offset_x_m", "offset_y_m", "offset_z_m")):
        offsets = [0.0, 0.0, 0.0]
        offsets[index] = math.nan
        with pytest.raises(CadError, match=name):
            translate_brep(body, offsets[0], offsets[1], offsets[2])
    with pytest.raises(CadError, match="offset_z_m"):
        translate_brep(body, 0.0, 0.0, math.inf)


def test_placement_refuses_an_empty_name() -> None:
    """An empty rename is refused before the back-end is touched."""
    with pytest.raises(CadError, match="name"):
        translate_brep(cylinder(), 0.0, 0.0, 0.0, "")


def test_ring_refuses_a_mismatched_or_repeated_name_set() -> None:
    """The ring needs one unique name per centre and a non-empty ring."""
    body = cylinder()
    offsets = ring_offsets(3, 0.4)
    with pytest.raises(CadError, match="one name per centre"):
        ring_brep_bodies(body, ("a", "b"), offsets)
    with pytest.raises(CadError, match="unique"):
        ring_brep_bodies(body, ("a", "b", "a"), offsets)
    with pytest.raises(CadError, match="offsets"):
        ring_brep_bodies(body, (), ())
