# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — B-rep axial profile tests

"""Revolved profiles agree with the closed forms and with their G1 twin."""

from __future__ import annotations

import math

import pytest

from cad_fixtures import CYLINDER_EXTENT_M, CYLINDER_RADIUS_M
from scpn_reactor_kernels.cad import (
    MEASURE_TOLERANCE,
    BrepAssembly,
    BrepBody,
    annular_tube_brep,
    closed_profiled_solid_brep,
    cylinder_solid_brep,
    facet_body,
    profiled_solid_brep,
    profiled_tube_brep,
)
from scpn_reactor_kernels.errors import CadError
from scpn_reactor_kernels.geometry import (
    TriangleMesh,
    closed_profiled_solid,
    profile_lateral_area_m2,
    profile_volume_m3,
    profiled_solid,
)

#: A narrow-wide-narrow profile of the shape a confined flux tube takes.
WAIST = (
    (0.0, 0.0225),
    (0.5, 0.06),
    (0.98, 0.1),
    (1.46, 0.06),
    (1.96, 0.0225),
)
WAIST_OUTER = tuple((height, radius + 0.004) for height, radius in WAIST)


def solid() -> BrepBody:
    """Return the revolved profiled solid of these tests."""
    return profiled_solid_brep(WAIST, "flux_tube", "plasma", "plasma")


def test_the_revolved_solid_agrees_with_the_frustum_stack_forms() -> None:
    """Volume and area match the closed forms inside the declared tolerance."""
    body = solid()
    assert body.analytic_volume_m3 == profile_volume_m3(WAIST)
    assert body.volume_relative_error() <= MEASURE_TOLERANCE
    assert body.surface_area_relative_error() <= MEASURE_TOLERANCE
    low, high = body.bounding_box_m()
    assert math.isclose(low[2], WAIST[0][0], abs_tol=1.0e-12)
    assert math.isclose(high[2], WAIST[-1][0], abs_tol=1.0e-12)
    assert math.isclose(high[0], max(r for _, r in WAIST), abs_tol=1.0e-12)


def test_the_revolved_tube_agrees_with_the_difference_of_the_forms() -> None:
    """The hollow body's references are the exact difference and sum."""
    body = profiled_tube_brep(WAIST, WAIST_OUTER, "vessel", "wall", "steel")
    assert body.analytic_volume_m3 == profile_volume_m3(
        WAIST_OUTER
    ) - profile_volume_m3(WAIST)
    assert body.volume_relative_error() <= MEASURE_TOLERANCE
    assert body.surface_area_relative_error() <= MEASURE_TOLERANCE


def test_a_constant_profile_reproduces_the_cylinder_measures() -> None:
    """A two-sample constant profile is the cylinder, to the last bit.

    The tessellating tier proves this on the vertex streams. Here the
    claim is what the B-rep tier can honestly make: the analytic
    references are identical values, and the back-end measures both
    bodies inside the declared tolerance of them.
    """
    profile = (
        (CYLINDER_EXTENT_M[0], CYLINDER_RADIUS_M),
        (CYLINDER_EXTENT_M[1], CYLINDER_RADIUS_M),
    )
    revolved = profiled_solid_brep(profile, "inner", "electrode", "conductor")
    extruded = cylinder_solid_brep(
        CYLINDER_RADIUS_M, *CYLINDER_EXTENT_M, "inner", "electrode", "conductor"
    )
    assert revolved.analytic_volume_m3 == extruded.analytic_volume_m3
    assert math.isclose(
        revolved.analytic_surface_area_m2,
        extruded.analytic_surface_area_m2,
        rel_tol=1.0e-15,
    )
    assert revolved.volume_relative_error() <= MEASURE_TOLERANCE
    assert extruded.volume_relative_error() <= MEASURE_TOLERANCE


def test_a_pair_of_constant_profiles_reproduces_the_tube_measures() -> None:
    """The same holds for the hollow body against the annular tube."""
    inner = ((0.0, 0.08), (0.4, 0.08))
    outer = ((0.0, 0.1), (0.4, 0.1))
    revolved = profiled_tube_brep(inner, outer, "outer", "wall", "steel")
    extruded = annular_tube_brep(0.08, 0.1, 0.0, 0.4, "outer", "wall", "steel")
    assert math.isclose(
        revolved.analytic_volume_m3, extruded.analytic_volume_m3, rel_tol=1.0e-15
    )
    assert math.isclose(
        revolved.analytic_surface_area_m2,
        extruded.analytic_surface_area_m2,
        rel_tol=1.0e-15,
    )


def test_the_faceted_solid_tracks_its_tessellated_twin() -> None:
    """Faceting the B-rep agrees in volume with the tier-G1 mesh.

    Both tiers describe one body, so the two volumes must agree within
    the polygon deficit of the reference tessellation; if the revolve and
    the tessellation had disagreed about the shape, this is where it
    would show.
    """
    body = solid()
    faceted = facet_body(body, 1.0e-4, 0.1)
    vertices, faces = profiled_solid(WAIST, 64)
    reference = TriangleMesh(
        name="flux_tube",
        role="plasma",
        material_identifier="plasma",
        vertices=vertices,
        faces=faces,
    )
    analytic = body.analytic_volume_m3
    bound = 1.0 - (64.0 / (2.0 * math.pi)) * math.sin(2.0 * math.pi / 64.0)
    difference = abs(faceted.signed_volume_m3() - reference.signed_volume_m3())
    assert difference / analytic <= bound
    assert faceted.signed_volume_m3() > 0.0


def test_a_profiled_body_assembles_and_exports() -> None:
    """The body is an ordinary member of an assembly manifest."""
    manifest = BrepAssembly((solid(),)).manifest()
    assert manifest["body_count"] == 1
    record = manifest["bodies"][0]
    assert record["name"] == "flux_tube"
    assert record["volume_relative_error"] <= MEASURE_TOLERANCE


def test_the_profile_contract_is_the_geometry_contract() -> None:
    """Refusals carry the geometry group's message under the CAD type."""
    with pytest.raises(CadError, match="at least 2 samples"):
        profiled_solid_brep(((0.0, 1.0),), "b", "r", "m")
    with pytest.raises(CadError, match=r"profile\[1\]\.radius"):
        profiled_solid_brep(((0.0, 1.0), (1.0, -1.0)), "b", "r", "m")
    with pytest.raises(CadError, match=r"profile\[1\]\.z: must exceed"):
        profiled_solid_brep(((0.0, 1.0), (0.0, 2.0)), "b", "r", "m")
    with pytest.raises(CadError, match="same number of samples"):
        profiled_tube_brep(
            ((0.0, 1.0), (1.0, 1.0)),
            ((0.0, 2.0), (0.5, 2.0), (1.0, 2.0)),
            "b",
            "r",
            "m",
        )
    with pytest.raises(CadError, match=r"outer_profile\[0\]\.radius"):
        profiled_tube_brep(
            ((0.0, 1.0), (1.0, 1.0)), ((0.0, 0.5), (1.0, 2.0)), "b", "r", "m"
        )
    with pytest.raises(CadError, match=r"outer_profile\[1\]\.z: must equal"):
        profiled_tube_brep(
            ((0.0, 1.0), (1.0, 1.0)), ((0.0, 2.0), (1.5, 2.0)), "b", "r", "m"
        )
    with pytest.raises(CadError, match="inner_profile: must carry at least"):
        profiled_tube_brep((), ((0.0, 2.0), (1.0, 3.0)), "b", "r", "m")


#: A compact-toroid separatrix, closed on the axis at both poles.
SEPARATRIX = (
    (-0.15, 0.0),
    (-0.1125, 0.02 * math.sqrt(1.0 - 0.75**2)),
    (-0.075, 0.02 * math.sqrt(1.0 - 0.5**2)),
    (0.0, 0.02),
    (0.075, 0.02 * math.sqrt(1.0 - 0.5**2)),
    (0.1125, 0.02 * math.sqrt(1.0 - 0.75**2)),
    (0.15, 0.0),
)

#: A cone standing on its tip: one pole, one disc.
CONE = ((0.0, 0.0), (1.0, 0.5))

#: The same cone the other way up: the disc at the bottom, the pole on top.
INVERTED_CONE = ((0.0, 0.5), (1.0, 0.0))


def test_the_revolved_separatrix_agrees_with_the_same_closed_forms() -> None:
    """A body closed at both poles needs no new closed form.

    The frustum-stack volume reduces to the cone volume at each pole, and
    a pole carries no disc, so the references are the same two sums the
    open body uses.
    """
    body = closed_profiled_solid_brep(SEPARATRIX, "separatrix", "plasma", "plasma")
    assert body.analytic_volume_m3 == profile_volume_m3(SEPARATRIX)
    assert body.analytic_surface_area_m2 == profile_lateral_area_m2(SEPARATRIX)
    assert body.volume_relative_error() <= MEASURE_TOLERANCE
    assert body.surface_area_relative_error() <= MEASURE_TOLERANCE
    low, high = body.bounding_box_m()
    assert math.isclose(low[2], SEPARATRIX[0][0], abs_tol=1.0e-12)
    assert math.isclose(high[2], SEPARATRIX[-1][0], abs_tol=1.0e-12)
    assert math.isclose(high[0], 0.02, abs_tol=1.0e-12)


def test_the_revolved_cone_keeps_the_disc_of_its_positive_end() -> None:
    """One pole and one disc: the area carries exactly one disc term."""
    body = closed_profiled_solid_brep(CONE, "cone", "structure", "steel")
    assert body.analytic_volume_m3 == math.pi * 0.5 * 0.5 * 1.0 / 3.0
    assert body.analytic_surface_area_m2 == (
        profile_lateral_area_m2(CONE) + math.pi * 0.5 * 0.5
    )
    assert body.volume_relative_error() <= MEASURE_TOLERANCE
    assert body.surface_area_relative_error() <= MEASURE_TOLERANCE


def test_the_faceted_separatrix_tracks_its_tessellated_twin() -> None:
    """The B-rep and the tier-G1 mesh of the same profile agree."""
    body = closed_profiled_solid_brep(SEPARATRIX, "separatrix", "plasma", "plasma")
    vertices, faces = closed_profiled_solid(SEPARATRIX, 64)
    reference = TriangleMesh(
        name="separatrix",
        role="plasma",
        material_identifier="plasma",
        vertices=vertices,
        faces=faces,
    )
    faceted = facet_body(body, 1.0e-4, 0.1)
    assert faceted.signed_volume_m3() > 0.0
    assert abs(faceted.signed_volume_m3() - body.analytic_volume_m3) < 2.0e-3 * (
        body.analytic_volume_m3
    )
    assert reference.signed_volume_m3() < body.analytic_volume_m3


def test_the_closed_profile_contract_is_the_geometry_contract() -> None:
    """The CAD twin refuses exactly what the geometry contract refuses."""
    with pytest.raises(CadError, match="at least one end radius"):
        closed_profiled_solid_brep(
            ((0.0, 0.1), (1.0, 0.2)), "body", "structure", "steel"
        )
    with pytest.raises(CadError, match=r"profile\[1\]\.radius"):
        closed_profiled_solid_brep(
            ((0.0, 0.0), (1.0, 0.0), (2.0, 0.1)), "body", "structure", "steel"
        )


def test_the_revolved_cone_is_the_same_solid_either_way_up() -> None:
    """Which end carries the pole is not a special case.

    The generating polyline returns along the axis only at the end that
    has a disc, so the two orientations exercise different branches and
    must still describe the same solid.
    """
    upright = closed_profiled_solid_brep(CONE, "cone", "structure", "steel")
    inverted = closed_profiled_solid_brep(
        INVERTED_CONE, "inverted_cone", "structure", "steel"
    )
    assert inverted.analytic_volume_m3 == upright.analytic_volume_m3
    assert inverted.analytic_surface_area_m2 == upright.analytic_surface_area_m2
    assert inverted.volume_relative_error() <= MEASURE_TOLERANCE
    assert inverted.surface_area_relative_error() <= MEASURE_TOLERANCE
    low, high = inverted.bounding_box_m()
    assert math.isclose(low[2], 0.0, abs_tol=1.0e-12)
    assert math.isclose(high[2], 1.0, abs_tol=1.0e-12)
