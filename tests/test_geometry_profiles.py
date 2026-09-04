# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — axial profile primitive tests

"""Profiled bodies close, orient outward, generalise exactly, and refuse."""

from __future__ import annotations

import math
from typing import Any

import pytest

from scpn_reactor_kernels.errors import GeometryError
from scpn_reactor_kernels.geometry import (
    TriangleMesh,
    annular_tube,
    cylinder_solid,
)
from scpn_reactor_kernels.geometry.profiles import (
    MIN_PROFILE_SAMPLES,
    closed_profiled_solid,
    profile_lateral_area_m2,
    profile_volume_m3,
    profiled_solid,
    profiled_tube,
    require_aligned_profiles,
    require_closed_profile,
    require_profile,
    require_revolution_profile,
)

#: A narrow-wide-narrow profile of the shape a confined flux tube takes.
WAIST = (
    (0.0, 0.0225),
    (0.5, 0.06),
    (0.98, 0.1),
    (1.46, 0.06),
    (1.96, 0.0225),
)


def polygon_area_ratio(segments: int) -> float:
    """Return the inscribed regular polygon area ratio of a segment count."""
    return (segments / (2.0 * math.pi)) * math.sin(2.0 * math.pi / segments)


def mesh_of(vertices: Any, faces: Any, name: str = "body") -> TriangleMesh:
    """Wrap raw streams in the closed-mesh contract."""
    return TriangleMesh(
        name=name,
        role="plasma",
        material_identifier="plasma",
        vertices=vertices,
        faces=faces,
    )


def test_a_two_sample_constant_profile_is_the_cylinder_bit_for_bit() -> None:
    """The generalisation keeps the existing primitive's exact streams.

    A consumer that moves a body from a constant radius to a profile of
    the same shape must not see a single bit move, or every pinned digest
    in the group would change for a shape that did not.
    """
    for segments in (8, 16, 64, 256):
        assert profiled_solid(((0.0, 0.05), (0.3, 0.05)), segments) == cylinder_solid(
            0.05, 0.0, 0.3, segments
        )


def test_a_pair_of_constant_profiles_is_the_annular_tube_bit_for_bit() -> None:
    """The same exactness holds for the hollow body."""
    for segments in (8, 16, 64):
        assert profiled_tube(
            ((-0.1, 0.08), (0.4, 0.08)), ((-0.1, 0.1), (0.4, 0.1)), segments
        ) == annular_tube(0.08, 0.1, -0.1, 0.4, segments)


def test_a_varying_profile_is_closed_and_outward_oriented() -> None:
    """A genuinely varying body satisfies the closed-mesh contract."""
    vertices, faces = profiled_solid(WAIST, 64)
    body = mesh_of(vertices, faces)
    assert body.signed_volume_m3() > 0.0
    assert body.vertex_count == len(WAIST) * 64 + 2
    assert body.face_count == (2 * (len(WAIST) - 1) + 2) * 64
    low, high = body.bounding_box()
    assert math.isclose(low[2], WAIST[0][0], abs_tol=1.0e-15)
    assert math.isclose(high[2], WAIST[-1][0], abs_tol=1.0e-15)
    assert math.isclose(high[0], max(radius for _, radius in WAIST), abs_tol=1.0e-15)


def test_a_varying_tube_is_closed_and_outward_oriented() -> None:
    """The hollow profiled body closes over both surfaces and both annuli."""
    inner = ((0.0, 0.05), (1.0, 0.08), (2.0, 0.05))
    outer = ((0.0, 0.06), (1.0, 0.09), (2.0, 0.06))
    vertices, faces = profiled_tube(inner, outer, 64)
    body = mesh_of(vertices, faces, "tube")
    assert body.signed_volume_m3() > 0.0
    assert body.vertex_count == 2 * len(inner) * 64
    assert body.face_count == (4 * (len(inner) - 1) + 4) * 64
    exact = profile_volume_m3(outer) - profile_volume_m3(inner)
    assert abs(body.signed_volume_m3() - exact) / exact < 2.0e-3


def test_the_tessellated_volume_approaches_the_closed_form() -> None:
    """The deficit is the inscribed-polygon deficit, not an error.

    The closed form is exact for the frustum stack a linear profile is;
    the tessellation is the approximation, and its deficit is the exact
    polygon deficit of the segment count, the same bound every other
    primitive in the group carries.
    """
    exact = profile_volume_m3(WAIST)
    for segments in (8, 64, 512):
        vertices, faces = profiled_solid(WAIST, segments)
        volume = mesh_of(vertices, faces).signed_volume_m3()
        deficit = (exact - volume) / exact
        bound = 1.0 - polygon_area_ratio(segments)
        assert 0.0 < deficit <= bound
        assert math.isclose(deficit, bound, rel_tol=1.0e-9)


def test_the_closed_forms_are_the_elementary_frustum_sums() -> None:
    """Volume and lateral area agree with the textbook frustum forms."""
    cone = ((0.0, 1.0), (3.0, 2.0))
    assert math.isclose(
        profile_volume_m3(cone),
        (math.pi / 3.0) * (1.0 + 2.0 + 4.0) * 3.0,
        rel_tol=1.0e-15,
    )
    slant = math.sqrt(1.0 + 9.0)
    assert math.isclose(
        profile_lateral_area_m2(cone), math.pi * 3.0 * slant, rel_tol=1.0e-15
    )
    cylinder = ((0.0, 0.05), (0.3, 0.05))
    assert math.isclose(
        profile_volume_m3(cylinder), math.pi * 0.05 * 0.05 * 0.3, rel_tol=1.0e-15
    )
    assert math.isclose(
        profile_lateral_area_m2(cylinder),
        2.0 * math.pi * 0.05 * 0.3,
        rel_tol=1.0e-15,
    )


def test_the_closed_forms_are_additive_over_a_subdivision() -> None:
    """Splitting a segment in two at the line does not change the forms.

    The profile is linear between samples, so a sample inserted on that
    line is not new information and must not change the body.
    """
    coarse = ((0.0, 1.0), (2.0, 3.0))
    fine = ((0.0, 1.0), (1.0, 2.0), (2.0, 3.0))
    assert math.isclose(
        profile_volume_m3(coarse), profile_volume_m3(fine), rel_tol=1.0e-15
    )
    assert math.isclose(
        profile_lateral_area_m2(coarse),
        profile_lateral_area_m2(fine),
        rel_tol=1.0e-15,
    )


def test_a_profile_must_carry_at_least_two_samples() -> None:
    """One sample is not a body."""
    assert MIN_PROFILE_SAMPLES == 2
    with pytest.raises(GeometryError, match="at least 2 samples"):
        require_profile("profile", ((0.0, 1.0),))
    with pytest.raises(GeometryError, match="at least 2 samples"):
        profiled_solid((), 8)


def test_a_profile_refuses_a_bad_sample_and_names_its_index() -> None:
    """Every rejection points at the row a caller has to fix."""
    with pytest.raises(GeometryError, match=r"profile\[1\]\.radius"):
        require_profile("profile", ((0.0, 1.0), (1.0, 0.0)))
    with pytest.raises(GeometryError, match=r"profile\[1\]\.radius"):
        require_profile("profile", ((0.0, 1.0), (1.0, -2.0)))
    with pytest.raises(GeometryError, match=r"profile\[1\]\.z"):
        require_profile("profile", ((0.0, 1.0), (math.nan, 2.0)))
    with pytest.raises(GeometryError, match=r"profile\[2\]\.z: must exceed"):
        require_profile("profile", ((0.0, 1.0), (1.0, 2.0), (1.0, 3.0)))
    with pytest.raises(GeometryError, match=r"profile\[1\]\.z: must exceed"):
        require_profile("profile", ((0.0, 1.0), (-1.0, 2.0)))
    with pytest.raises(GeometryError, match=r"profile\[0\]: must be a \(z, radius\)"):
        require_profile("profile", ((0.0, 1.0, 2.0), (1.0, 2.0)))  # type: ignore[arg-type]


def test_two_profiles_must_form_a_well_defined_annulus() -> None:
    """Different lengths, different heights or a crossing are refused."""
    inner = ((0.0, 1.0), (1.0, 2.0))
    with pytest.raises(GeometryError, match="same number of samples"):
        require_aligned_profiles("inner_profile", inner, "outer_profile", ((0.0, 2.0),))
    with pytest.raises(GeometryError, match=r"outer_profile\[1\]\.z"):
        require_aligned_profiles(
            "inner_profile", inner, "outer_profile", ((0.0, 2.0), (1.5, 3.0))
        )
    with pytest.raises(GeometryError, match=r"outer_profile\[1\]\.radius"):
        require_aligned_profiles(
            "inner_profile", inner, "outer_profile", ((0.0, 2.0), (1.0, 2.0))
        )
    with pytest.raises(GeometryError, match=r"outer_profile\[0\]\.radius"):
        profiled_tube(inner, ((0.0, 0.5), (1.0, 3.0)), 8)


def test_the_segment_rule_still_governs_the_rings() -> None:
    """A profiled body is tessellated by the same circle as everything else."""
    with pytest.raises(GeometryError, match="multiple"):
        profiled_solid(WAIST, 20)
    with pytest.raises(GeometryError, match="multiple"):
        profiled_tube(((0.0, 1.0), (1.0, 1.0)), ((0.0, 2.0), (1.0, 2.0)), 20)


def test_the_closed_forms_validate_their_input() -> None:
    """Neither closed form accepts a profile the primitives would refuse."""
    with pytest.raises(GeometryError, match="at least 2 samples"):
        profile_volume_m3(((0.0, 1.0),))
    with pytest.raises(GeometryError, match="at least 2 samples"):
        profile_lateral_area_m2(((0.0, 1.0),))


#: The separatrix of a compact toroid, closed on the axis at both poles:
#: ``r(z) = a sqrt(1 - |z / b|^m)`` sampled at nine heights with ``m = 2``,
#: which is the ellipse the shape index takes as its reference.
SEPARATRIX = (
    (-0.15, 0.0),
    (-0.1125, 0.02 * math.sqrt(1.0 - 0.75**2)),
    (-0.075, 0.02 * math.sqrt(1.0 - 0.5**2)),
    (-0.0375, 0.02 * math.sqrt(1.0 - 0.25**2)),
    (0.0, 0.02),
    (0.0375, 0.02 * math.sqrt(1.0 - 0.25**2)),
    (0.075, 0.02 * math.sqrt(1.0 - 0.5**2)),
    (0.1125, 0.02 * math.sqrt(1.0 - 0.75**2)),
    (0.15, 0.0),
)

#: A cone standing on its tip: closed at one pole, a disc at the other.
CONE = ((0.0, 0.0), (1.0, 0.5))

#: The same cone the other way up: a disc at the bottom, the pole on top.
INVERTED_CONE = ((0.0, 0.5), (1.0, 0.0))


def test_a_closed_profile_is_closed_and_outward_oriented() -> None:
    """A body that comes to a point at both poles satisfies the contract."""
    vertices, faces = closed_profiled_solid(SEPARATRIX, 64)
    body = mesh_of(vertices, faces, "separatrix")
    assert body.signed_volume_m3() > 0.0
    assert body.vertex_count == (len(SEPARATRIX) - 2) * 64 + 2
    assert body.face_count == (len(SEPARATRIX) - 3) * 2 * 64 + 2 * 64
    low, high = body.bounding_box()
    assert math.isclose(low[2], SEPARATRIX[0][0], abs_tol=1.0e-15)
    assert math.isclose(high[2], SEPARATRIX[-1][0], abs_tol=1.0e-15)
    assert math.isclose(high[0], 0.02, abs_tol=1.0e-15)


def test_a_pole_is_one_apex_vertex_and_not_a_ring() -> None:
    """The axis carries a single point per pole, not a ring of them.

    A ring of zero radius would place ``segments`` identical vertices on
    the axis and give every face touching it zero area. The count is the
    evidence: two poles cost two vertices, not two rings.
    """
    vertices, _ = closed_profiled_solid(SEPARATRIX, 64)
    on_axis = [v for v in vertices if v[0] == 0.0 and v[1] == 0.0]
    assert len(on_axis) == 2
    assert {v[2] for v in on_axis} == {SEPARATRIX[0][0], SEPARATRIX[-1][0]}


def test_a_cone_closes_with_one_fan_and_one_disc() -> None:
    """One pole and one positive end give a fan and a disc."""
    vertices, faces = closed_profiled_solid(CONE, 64)
    body = mesh_of(vertices, faces, "cone")
    assert body.signed_volume_m3() > 0.0
    assert body.vertex_count == 1 + 64 + 1
    assert body.face_count == 2 * 64


def test_a_cone_closes_the_same_way_when_its_pole_is_on_top() -> None:
    """Either end may be the pole, and the body closes either way.

    The two cones are the same solid reflected, so their volumes agree
    exactly and neither orientation is a special case in the kernel.
    """
    vertices, faces = closed_profiled_solid(INVERTED_CONE, 64)
    body = mesh_of(vertices, faces, "inverted_cone")
    assert body.signed_volume_m3() > 0.0
    assert body.vertex_count == 1 + 64 + 1
    assert body.face_count == 2 * 64
    on_axis = [v for v in vertices if v[0] == 0.0 and v[1] == 0.0]
    assert sorted(v[2] for v in on_axis) == [0.0, 1.0]
    assert profile_volume_m3(INVERTED_CONE) == profile_volume_m3(CONE)


def test_the_cone_volume_falls_out_of_the_frustum_sum_exactly() -> None:
    """A zero end radius turns the frustum term into the cone term.

    No separate closed form is added for a closed profile because none is
    needed, and this is the proof: the general sum reproduces
    ``pi r^2 h / 3`` bit for bit.
    """
    assert profile_volume_m3(CONE) == math.pi * 0.5 * 0.5 * 1.0 / 3.0


def test_the_cone_lateral_area_falls_out_of_the_slant_sum_exactly() -> None:
    """The same holds for the lateral area, which becomes ``pi r l``."""
    slant = math.sqrt(0.5 * 0.5 + 1.0)
    assert profile_lateral_area_m2(CONE) == math.pi * 0.5 * slant


def test_a_closed_body_carries_the_same_polygon_deficit_as_every_other() -> None:
    """The tessellated volume is the exact one times the polygon ratio.

    Stated as a ratio rather than as a deficit on purpose. The two are the
    same statement in exact arithmetic, but the deficit form computes
    ``1 - ratio`` and ``(exact - volume) / exact``, and both cancel: at 512
    segments the deficit is 2.5e-5, so five digits are lost on each side
    and the agreement degrades to 2.6e-9 for reasons that have nothing to
    do with the geometry. The ratio form cancels nothing and holds to
    6.6e-14 over the same range, which is what the bodies actually agree
    to.
    """
    exact = profile_volume_m3(SEPARATRIX)
    for segments in (8, 64, 512):
        vertices, faces = closed_profiled_solid(SEPARATRIX, segments)
        volume = mesh_of(vertices, faces, "separatrix").signed_volume_m3()
        assert math.isclose(
            volume / exact, polygon_area_ratio(segments), rel_tol=1.0e-12
        )


def test_an_open_profile_is_refused_by_the_closed_contract() -> None:
    """A profile positive at both ends belongs to the open contract."""
    with pytest.raises(GeometryError, match="at least one end radius"):
        require_closed_profile("profile", ((0.0, 0.1), (1.0, 0.2)))


def test_a_bipolar_profile_needs_a_ring_between_its_poles() -> None:
    """Two poles and nothing between them is not a body."""
    with pytest.raises(GeometryError, match="at least 3 samples"):
        require_closed_profile("profile", ((0.0, 0.0), (1.0, 0.0)))


@pytest.mark.parametrize(
    ("profile", "message"),
    [
        (((0.0, 0.0),), "at least 2 samples"),
        (((0.0, 0.0), (1.0, 0.1, 2.0)), r"profile\[1\]: must be a \(z, radius\) pair"),
        (((0.0, 0.0), (math.inf, 0.1)), r"profile\[1\]\.z"),
        (((0.0, 0.0), (1.0, math.nan)), r"profile\[1\]\.radius"),
        (((0.0, -1.0), (1.0, 0.1)), "pole radius must not be negative"),
        (((0.0, 0.0), (1.0, 0.0), (2.0, 0.1)), r"profile\[1\]\.radius"),
        (((0.0, 0.0), (0.0, 0.1)), r"profile\[1\]\.z: must exceed"),
    ],
)
def test_the_closed_contract_refuses_and_names_the_sample(
    profile: Any, message: str
) -> None:
    """Every refusal names the field and, where it has one, the index."""
    with pytest.raises(GeometryError, match=message):
        require_closed_profile("profile", profile)


def test_the_closed_solid_still_obeys_the_segment_rule() -> None:
    """The circumferential contract is unchanged for a closed body."""
    with pytest.raises(GeometryError, match="segments"):
        closed_profiled_solid(SEPARATRIX, 12)


def test_the_dispatching_contract_routes_by_the_end_radii() -> None:
    """A zero end radius selects the closed contract, anything else open."""
    assert require_revolution_profile("profile", SEPARATRIX) is SEPARATRIX
    assert require_revolution_profile("profile", CONE) is CONE
    assert require_revolution_profile("profile", WAIST) is WAIST
    with pytest.raises(GeometryError, match=r"profile\[1\]\.radius"):
        require_revolution_profile("profile", ((0.0, 0.0), (1.0, 0.0), (2.0, 0.1)))
    with pytest.raises(GeometryError, match=r"profile\[0\]\.radius"):
        require_revolution_profile("profile", ((0.0, -0.1), (1.0, 0.2)))
