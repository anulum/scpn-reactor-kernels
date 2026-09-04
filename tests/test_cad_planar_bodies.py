# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — bodies with no curved surface

"""A body with no curved surface is faceted exactly, and bounded as such."""

from __future__ import annotations

import math

import pytest

from cad_fixtures import PRISM_EXTENT_M, PRISM_SIDES_M, cylinder, prism
from scpn_reactor_kernels.cad import (
    MEASURE_TOLERANCE,
    PLANAR_FACETING_TOLERANCE,
    body_evidence,
    facet_body,
    facet_bounds,
    rectangular_prism_brep,
)
from scpn_reactor_kernels.errors import CadError
from scpn_reactor_kernels.geometry import TriangleMesh, rectangular_prism

LINEAR_DEFLECTION_M = 2.0e-7
ANGULAR_DEFLECTION_RAD = 0.1
SEGMENTS = 64
#: Worst relative deviation measured over nine prisms spanning 1 um to
#: 10 m and aspect ratios to 1000:1, at every deflection the back-end
#: accepts. The declared tolerance sits four orders above it.
MEASURED_WORST_DEVIATION = 2.581e-16


def reference_prism() -> TriangleMesh:
    """Return the tier-G1 mesh of the fixture prism."""
    vertices, faces = rectangular_prism(*PRISM_SIDES_M, *PRISM_EXTENT_M)
    return TriangleMesh(
        name="slab",
        role="target",
        material_identifier="fuel",
        vertices=vertices,
        faces=faces,
    )


def test_the_two_tiers_of_the_prism_agree_on_every_measure() -> None:
    """The B-rep prism and its tessellating twin are the same body."""
    body = prism()
    mesh = reference_prism()
    assert body.analytic_volume_m3 == pytest.approx(
        mesh.signed_volume_m3(), rel=PLANAR_FACETING_TOLERANCE
    )
    assert body.analytic_surface_area_m2 == pytest.approx(
        mesh.surface_area_m2(), rel=PLANAR_FACETING_TOLERANCE
    )
    assert body.volume_relative_error() <= MEASURE_TOLERANCE
    assert body.surface_area_relative_error() <= MEASURE_TOLERANCE


def test_the_prism_is_faceted_exactly_and_the_deflection_does_not_matter() -> None:
    """The mesher returns the body itself at every deflection it accepts.

    Measured across seven orders of linear deflection: the facet count
    never leaves 8 vertices and 12 triangles and the volume never moves.
    That is why this body's evidence is not bounded by a chord deficit —
    there is no chord.
    """
    body = prism()
    volumes = []
    for deflection in (1.0e-7, 1.0e-5, 1.0e-3, 1.0e-1):
        faceted = facet_body(body, deflection, ANGULAR_DEFLECTION_RAD)
        assert len(faceted.vertices) == 8
        assert len(faceted.faces) == 12
        volumes.append(faceted.signed_volume_m3())
    assert len(set(volumes)) == 1
    assert volumes[0] == pytest.approx(
        body.analytic_volume_m3, rel=PLANAR_FACETING_TOLERANCE
    )


def test_the_angular_deflection_does_not_matter_either() -> None:
    """A body with no curvature has no normals for the angle to bound."""
    body = prism()
    volumes = {
        facet_body(body, LINEAR_DEFLECTION_M, angular).signed_volume_m3()
        for angular in (0.01, 0.1, 0.5, 1.0)
    }
    assert len(volumes) == 1


def test_a_body_without_curvature_declares_the_round_off_bounds() -> None:
    """``None`` selects the planar regime for both faceting bounds."""
    assert facet_bounds(None, LINEAR_DEFLECTION_M, SEGMENTS) == (
        PLANAR_FACETING_TOLERANCE,
        PLANAR_FACETING_TOLERANCE,
    )


def test_a_body_with_curvature_still_declares_the_chord_and_polygon_bounds() -> None:
    """A stated radius selects the curved regime, unchanged."""
    deficit, difference = facet_bounds(0.05, LINEAR_DEFLECTION_M, SEGMENTS)
    assert deficit == pytest.approx(2.0 * LINEAR_DEFLECTION_M / 0.05)
    assert 0.0 < difference < 1.0


def test_the_circular_bound_would_have_been_decorative_on_a_prism() -> None:
    """The reason the planar regime exists, stated as a measurement.

    At the fixture prism's own scale the chord bound is eleven orders
    above the deviation the prism actually shows, and the prism's
    deviation is negative as often as positive. A check against that
    bound would have passed whatever the mesher did.
    """
    body = prism()
    faceted = facet_body(body, LINEAR_DEFLECTION_M, ANGULAR_DEFLECTION_RAD)
    deviation = (
        body.analytic_volume_m3 - faceted.signed_volume_m3()
    ) / body.analytic_volume_m3
    circular_bound, _ = facet_bounds(
        min(PRISM_SIDES_M) / 2.0, LINEAR_DEFLECTION_M, SEGMENTS
    )
    assert abs(deviation) <= MEASURED_WORST_DEVIATION
    assert circular_bound / PLANAR_FACETING_TOLERANCE > 1.0e6


def test_the_evidence_of_a_prism_passes_the_round_off_bounds() -> None:
    """The composed evidence carries the planar bounds and is accepted."""
    body = prism()
    faceted = facet_body(body, LINEAR_DEFLECTION_M, ANGULAR_DEFLECTION_RAD)
    evidence = body_evidence(
        body,
        None,
        faceted,
        reference_prism(),
        LINEAR_DEFLECTION_M,
        SEGMENTS,
    )
    assert evidence.faceted_volume_deficit_bound == PLANAR_FACETING_TOLERANCE
    assert evidence.mesh_volume_difference_bound == PLANAR_FACETING_TOLERANCE
    assert abs(evidence.faceted_volume_relative_deficit) <= MEASURED_WORST_DEVIATION
    assert evidence.mesh_volume_relative_difference <= MEASURED_WORST_DEVIATION
    assert evidence.name == "slab"
    assert evidence.role == "target"


def test_the_prism_evidence_refuses_a_body_that_is_not_the_prism() -> None:
    """The round-off bound is tight enough to catch a real defect.

    A tolerance that no wrong body could violate would be decorative in
    the other direction. Here the reference mesh is a prism one part in
    ten thousand too wide, which is far below anything a reader would
    notice by eye and far above the declared bound.
    """
    body = prism()
    width, depth = PRISM_SIDES_M
    vertices, faces = rectangular_prism(width * 1.0001, depth, *PRISM_EXTENT_M)
    wrong = TriangleMesh(
        name="slab",
        role="target",
        material_identifier="fuel",
        vertices=vertices,
        faces=faces,
    )
    with pytest.raises(CadError, match="mesh_volume_relative_difference"):
        body_evidence(
            body,
            None,
            facet_body(body, LINEAR_DEFLECTION_M, ANGULAR_DEFLECTION_RAD),
            wrong,
            LINEAR_DEFLECTION_M,
            SEGMENTS,
        )


def test_a_faceted_volume_that_overshoots_is_refused_in_magnitude() -> None:
    """The deficit is checked in magnitude, not one-sidedly.

    Before this the check was ``deficit > bound``, so a faceted volume
    *above* the analytic one passed at any size. A prism's deviation is
    negative about as often as positive, which is what surfaced it.
    """
    body = prism()
    oversized = rectangular_prism_brep(
        PRISM_SIDES_M[0] * 1.01,
        PRISM_SIDES_M[1],
        *PRISM_EXTENT_M,
        "slab",
        "target",
        "fuel",
    )
    faceted = facet_body(oversized, LINEAR_DEFLECTION_M, ANGULAR_DEFLECTION_RAD)
    assert faceted.signed_volume_m3() > body.analytic_volume_m3
    with pytest.raises(CadError, match="faceted_volume_relative_deficit"):
        body_evidence(
            body,
            None,
            faceted,
            reference_prism(),
            LINEAR_DEFLECTION_M,
            SEGMENTS,
        )


def test_an_assembly_may_mix_a_curved_body_and_a_planar_one() -> None:
    """Each body carries its own regime, in the assembly's order."""
    from cad_fixtures import CYLINDER_EXTENT_M, CYLINDER_RADIUS_M
    from scpn_reactor_kernels.cad import assembly_evidence
    from scpn_reactor_kernels.geometry import cylinder_solid

    round_body = cylinder()
    vertices, faces = cylinder_solid(CYLINDER_RADIUS_M, *CYLINDER_EXTENT_M, SEGMENTS)
    round_reference = TriangleMesh(
        name="inner",
        role="electrode",
        material_identifier="conductor",
        vertices=vertices,
        faces=faces,
    )
    deflection = 1.0e-4
    evidence = assembly_evidence(
        (round_body, prism()),
        (CYLINDER_RADIUS_M, None),
        (
            facet_body(round_body, deflection, ANGULAR_DEFLECTION_RAD),
            facet_body(prism(), deflection, ANGULAR_DEFLECTION_RAD),
        ),
        (round_reference, reference_prism()),
        deflection,
        SEGMENTS,
    )
    assert evidence[0].faceted_volume_deficit_bound == pytest.approx(
        2.0 * deflection / CYLINDER_RADIUS_M
    )
    assert evidence[1].faceted_volume_deficit_bound == PLANAR_FACETING_TOLERANCE
    assert evidence[0].faceted_volume_relative_deficit > 0.0


@pytest.mark.parametrize(
    ("width", "depth", "field"),
    [
        (0.0, 0.09, "width_x_m"),
        (-0.06, 0.09, "width_x_m"),
        (math.nan, 0.09, "width_x_m"),
        (0.06, 0.0, "depth_y_m"),
        (0.06, math.inf, "depth_y_m"),
    ],
)
def test_the_brep_prism_refuses_an_unusable_side(
    width: float, depth: float, field: str
) -> None:
    """Every side length is refused by name."""
    with pytest.raises(CadError, match=field):
        rectangular_prism_brep(width, depth, *PRISM_EXTENT_M, "slab", "target", "fuel")


def test_the_brep_prism_refuses_an_extent_that_does_not_increase() -> None:
    """A prism of zero or negative height is refused."""
    with pytest.raises(CadError, match="z_high_m"):
        rectangular_prism_brep(*PRISM_SIDES_M, 0.1, 0.1, "slab", "target", "fuel")
