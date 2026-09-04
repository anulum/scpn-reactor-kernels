# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — spherical body tests

"""Every branch of the spherical bodies, and what makes their sampling right."""

from __future__ import annotations

import math
from itertools import pairwise

import pytest

from scpn_reactor_kernels.errors import GeometryError
from scpn_reactor_kernels.geometry import (
    Face,
    TriangleMesh,
    Vertex,
    profile_lateral_area_m2,
    profile_volume_m3,
    require_revolution_profile,
)
from scpn_reactor_kernels.geometry.spheres import (
    MIN_SPHERE_RINGS,
    require_rings,
    sphere_profile,
    sphere_solid,
    spherical_shell,
)

SEGMENTS = 64


def built(vertices: tuple[Vertex, ...], faces: tuple[Face, ...]) -> TriangleMesh:
    """Wrap a vertex and face stream in a validated mesh."""
    return TriangleMesh(
        name="body",
        role="role",
        material_identifier="material",
        vertices=vertices,
        faces=faces,
    )


@pytest.mark.parametrize("rings", [1, 0, -4])
def test_too_few_rings_are_refused(rings: int) -> None:
    """One polar step puts the poles adjacent, which is a segment not a body."""
    with pytest.raises(GeometryError, match="rings"):
        require_rings(rings)


def test_the_minimum_ring_count_is_admitted() -> None:
    """Two steps give three samples: two poles and one equator ring."""
    assert require_rings(MIN_SPHERE_RINGS) == MIN_SPHERE_RINGS
    assert len(sphere_profile(1.0, 0.0, MIN_SPHERE_RINGS)) == 3


@pytest.mark.parametrize(
    ("radius", "centre", "rings", "match"),
    [
        (0.0, 0.0, 8, "radius_m"),
        (-1.0, 0.0, 8, "radius_m"),
        (math.nan, 0.0, 8, "radius_m"),
        (1.0, math.inf, 8, "centre_z_m"),
        (1.0, math.nan, 8, "centre_z_m"),
        (1.0, 0.0, 1, "rings"),
    ],
)
def test_the_profile_refuses_by_name(
    radius: float, centre: float, rings: int, match: str
) -> None:
    """Each guard names the field it rejected."""
    with pytest.raises(GeometryError, match=match):
        sphere_profile(radius, centre, rings)


@pytest.mark.parametrize("rings", [2, 3, 8, 64, 256])
def test_the_poles_are_exact_and_the_profile_is_a_valid_revolution(
    rings: int,
) -> None:
    """Both ends sit on the axis at exactly one radius from the centre.

    Asserted as equalities rather than tolerances: the angles come from
    the deterministic circle kernel, which returns exactly ``(1, 0)`` at
    zero and exactly ``(-1, 0)`` at half a turn, so neither pole is the
    result of an approximation.
    """
    centre, radius = 3.0, 2.0
    profile = sphere_profile(radius, centre, rings)
    assert len(profile) == rings + 1
    assert profile[0] == (centre - radius, 0.0)
    assert profile[-1] == (centre + radius, 0.0)
    require_revolution_profile("sphere", profile)


@pytest.mark.parametrize("rings", [2, 4, 8, 64])
def test_an_even_ring_count_puts_a_sample_exactly_on_the_equator(
    rings: int,
) -> None:
    """The widest ring is exactly the sphere's radius, at exactly its centre."""
    centre, radius = -1.5, 0.75
    profile = sphere_profile(radius, centre, rings)
    assert profile[rings // 2] == (centre, radius)


@pytest.mark.parametrize("rings", [2, 8, 64, 256, 1024])
def test_the_heights_increase_strictly_at_every_ring_count(rings: int) -> None:
    """A profile of revolution must, and the poles crowd as the count rises.

    At 1024 rings the smallest step is still 5e-6 of the radius, which is
    far above anything a double loses.
    """
    heights = [height for height, _ in sphere_profile(1.0, 0.0, rings)]
    assert all(later > earlier for earlier, later in pairwise(heights))


def test_the_volume_deficit_falls_as_the_square_of_the_ring_count() -> None:
    """The reason the profile is sampled in angle and not in height.

    A polyhedron inscribed in a sphere loses volume as the square of its
    polar step, so halving the step should quarter the deficit. Measured,
    the ratio between successive doublings runs 3.990, 3.998, 3.999,
    4.000 — which is the convergence a uniform sampling in ``z`` does not
    give, because it starves the poles where the surface turns fastest.
    """
    exact = 4.0 / 3.0 * math.pi
    deficits = [
        1.0 - profile_volume_m3(sphere_profile(1.0, 0.0, rings)) / exact
        for rings in (16, 32, 64, 128, 256)
    ]
    for coarse, fine in pairwise(deficits):
        assert coarse / fine == pytest.approx(4.0, abs=0.02)


@pytest.mark.parametrize("rings", [2, 8, 64])
def test_the_sphere_carries_the_documented_vertex_and_face_counts(
    rings: int,
) -> None:
    """One apex per pole, one ring per interior sample, two faces per band."""
    vertices, faces = sphere_solid(1.0, 0.0, SEGMENTS, rings)
    assert len(vertices) == (rings - 1) * SEGMENTS + 2
    assert len(faces) == 2 * (rings - 1) * SEGMENTS


@pytest.mark.parametrize("rings", [2, 8, 64])
def test_the_sphere_mesh_volume_is_its_profile_volume_times_the_polygon_ratio(
    rings: int,
) -> None:
    """The tessellation loses the inscribed polygon and nothing else.

    The ratio is the same at every ring count, which is what shows the
    two resolutions are independent: the polar sampling sets the profile
    volume and the circumferential one sets what the mesh keeps of it.
    """
    ratio = SEGMENTS * math.sin(2.0 * math.pi / SEGMENTS) / (2.0 * math.pi)
    mesh = built(*sphere_solid(1.0, 0.0, SEGMENTS, rings))
    assert math.isclose(
        mesh.signed_volume_m3() / profile_volume_m3(sphere_profile(1.0, 0.0, rings)),
        ratio,
        rel_tol=1e-12,
    )


def test_a_sphere_off_the_origin_is_the_same_body_moved() -> None:
    """The centre enters only as a translation along the axis."""
    at_origin = built(*sphere_solid(1.0, 0.0, SEGMENTS, 16))
    moved = built(*sphere_solid(1.0, 5.0, SEGMENTS, 16))
    assert moved.signed_volume_m3() == pytest.approx(at_origin.signed_volume_m3())
    assert moved.surface_area_m2() == pytest.approx(at_origin.surface_area_m2())


@pytest.mark.parametrize(
    ("inner", "outer", "match"),
    [
        (0.0, 1.0, "inner_radius_m"),
        (-1.0, 1.0, "inner_radius_m"),
        (1.0, 0.0, "outer_radius_m"),
        (1.0, 1.0, "must exceed"),
        (1.5, 1.0, "must exceed"),
    ],
)
def test_the_shell_refuses_radii_that_do_not_nest(
    inner: float, outer: float, match: str
) -> None:
    """A cavity at least as large as the body is refused, not reordered."""
    with pytest.raises(GeometryError, match=match):
        spherical_shell(inner, outer, 0.0, SEGMENTS, 8)


@pytest.mark.parametrize("rings", [2, 8, 32])
def test_the_shell_carries_both_surfaces_and_nothing_else(rings: int) -> None:
    """Exactly twice a sphere's vertices and faces: no caps, no seams."""
    vertices, faces = spherical_shell(0.6, 1.0, 0.0, SEGMENTS, rings)
    sphere_vertices, sphere_faces = sphere_solid(1.0, 0.0, SEGMENTS, rings)
    assert len(vertices) == 2 * len(sphere_vertices)
    assert len(faces) == 2 * len(sphere_faces)


@pytest.mark.parametrize("rings", [8, 32])
def test_the_shell_volume_is_the_difference_of_the_two_spheres(rings: int) -> None:
    """The inner surface is reversed, so it subtracts rather than adds.

    Asserted within a relative tolerance rather than as an equality: the
    shell's volume is one sum over both surfaces and the difference is
    two sums subtracted, so they part in the last places. Measured, by
    213 units in the last place at 8 rings and 357 at 32, which is about
    1e-13 relative.
    """
    shell = built(*spherical_shell(0.6, 1.0, 0.0, SEGMENTS, rings))
    outer = built(*sphere_solid(1.0, 0.0, SEGMENTS, rings))
    inner = built(*sphere_solid(0.6, 0.0, SEGMENTS, rings))
    assert math.isclose(
        shell.signed_volume_m3(),
        outer.signed_volume_m3() - inner.signed_volume_m3(),
        rel_tol=1e-12,
    )


def test_the_shell_area_is_the_sum_of_both_surfaces() -> None:
    """A cavity has a wall, and it is counted."""
    shell = built(*spherical_shell(0.6, 1.0, 0.0, SEGMENTS, 16))
    outer = built(*sphere_solid(1.0, 0.0, SEGMENTS, 16))
    inner = built(*sphere_solid(0.6, 0.0, SEGMENTS, 16))
    assert shell.surface_area_m2() == pytest.approx(
        outer.surface_area_m2() + inner.surface_area_m2()
    )


def test_the_profile_lateral_area_ignores_the_poles() -> None:
    """A pole is a point, so it adds no lateral area and no disc."""
    profile = sphere_profile(1.0, 0.0, 32)
    assert profile_lateral_area_m2(profile) > 0.0
    assert profile[0][1] == 0.0
    assert profile[-1][1] == 0.0
