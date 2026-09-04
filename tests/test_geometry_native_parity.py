# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — native geometry parity tests

"""Bit-exact parity of the geometry kernels between Python and Rust.

Skipped hermetically when the optional native module is absent; when
present, every vertex coordinate, face index and measure is compared by
float64 bit pattern, never by tolerance. All inputs are synthetic.
"""

from __future__ import annotations

import math

import pytest

from geometry_fixtures import bits, sample_bodies, stream_bits
from scpn_reactor_kernels.geometry import (
    annular_tube,
    circle_points,
    closed_profiled_solid,
    cylinder_solid,
    profile_lateral_area_m2,
    profile_volume_m3,
    profiled_solid,
    profiled_tube,
    ring_offsets,
    ring_separation_m,
    translate,
    unit_circle,
)
from scpn_reactor_kernels.geometry.spheres import (
    sphere_profile,
    sphere_solid,
    spherical_shell,
)

native = pytest.importorskip("scpn_reactor_kernels_native")


@pytest.mark.parametrize("segments", [8, 16, 24, 64, 1024])
def test_unit_circle_is_bit_exact(segments: int) -> None:
    """The flat cos/sin stream agrees bit for bit."""
    floor = [component for point in unit_circle(segments) for component in point]
    assert stream_bits(floor) == stream_bits(native.unit_circle(segments))


@pytest.mark.parametrize(
    ("radius", "low", "high"), [(0.05, 0.0, 1.0), (0.123, -0.5, 1.75)]
)
@pytest.mark.parametrize("segments", [8, 32])
def test_cylinder_is_bit_exact(
    radius: float, low: float, high: float, segments: int
) -> None:
    """Vertices and faces of the solid cylinder agree exactly."""
    vertices, faces = cylinder_solid(radius, low, high, segments)
    got_vertices, got_faces = native.tessellate_cylinder(radius, low, high, segments)
    assert stream_bits([c for v in vertices for c in v]) == stream_bits(got_vertices)
    assert [i for f in faces for i in f] == got_faces


@pytest.mark.parametrize(("inner", "outer"), [(0.1, 0.11), (0.3, 0.55)])
@pytest.mark.parametrize("segments", [8, 32])
def test_tube_is_bit_exact(inner: float, outer: float, segments: int) -> None:
    """Vertices and faces of the annular tube agree exactly."""
    vertices, faces = annular_tube(inner, outer, 0.0, 1.6, segments)
    got_vertices, got_faces = native.tessellate_annular_tube(
        inner, outer, 0.0, 1.6, segments
    )
    assert stream_bits([c for v in vertices for c in v]) == stream_bits(got_vertices)
    assert [i for f in faces for i in f] == got_faces


def test_measures_of_every_body_are_bit_exact() -> None:
    """Volume and area of the synthetic bodies agree bit for bit."""
    for mesh in sample_bodies(64):
        vertices = [c for v in mesh.vertices for c in v]
        faces = [i for f in mesh.faces for i in f]
        assert bits(native.mesh_volume(vertices, faces)) == bits(
            mesh.signed_volume_m3()
        )
        assert bits(native.mesh_area(vertices, faces)) == bits(mesh.surface_area_m2())


def test_native_refusals_mirror_the_floor() -> None:
    """Invalid segment counts and malformed streams raise ValueError."""
    with pytest.raises(ValueError, match="multiple of 8"):
        native.unit_circle(12)
    with pytest.raises(ValueError, match="at least 8"):
        native.tessellate_cylinder(1.0, 0.0, 1.0, 4)
    with pytest.raises(ValueError, match="at least 8"):
        native.tessellate_annular_tube(0.5, 1.0, 0.0, 1.0, 4)
    with pytest.raises(ValueError, match="flat streams of triples"):
        native.mesh_volume([0.0, 0.0], [0, 1, 2])
    with pytest.raises(ValueError, match="out of range"):
        native.mesh_area([0.0] * 9, [0, 1, 7])


@pytest.mark.parametrize("count", [3, 6, 8, 12, 13, 64, 257])
def test_circle_points_and_ring_placement_are_bit_exact(count: int) -> None:
    """Arbitrary circle counts, ring offsets and the separation agree bit for bit."""
    radius = 0.0517
    floor_points = [c for point in circle_points(count) for c in point]
    assert stream_bits(floor_points) == stream_bits(list(native.circle_points(count)))
    floor_offsets = [c for point in ring_offsets(count, radius) for c in point]
    assert stream_bits(floor_offsets) == stream_bits(
        list(native.ring_offsets(count, radius))
    )
    assert bits(ring_separation_m(count, radius)) == bits(
        native.ring_separation(count, radius)
    )


def test_translation_of_a_body_is_bit_exact() -> None:
    """A translated tessellated body agrees coordinate for coordinate."""
    vertices, _ = cylinder_solid(0.006, 0.0, 0.16, 32)
    floor = [c for v in translate(vertices, 0.0517, -0.013, 0.25) for c in v]
    flat = [c for v in vertices for c in v]
    assert stream_bits(floor) == stream_bits(
        list(native.translate(flat, 0.0517, -0.013, 0.25))
    )


def test_native_placement_refusals_mirror_the_floor() -> None:
    """The native bindings refuse the same inputs as the floor."""
    with pytest.raises(ValueError, match="at least 3"):
        native.circle_points(2)
    with pytest.raises(ValueError, match="at least 3"):
        native.ring_offsets(2, 0.05)
    with pytest.raises(ValueError, match="at least 3"):
        native.ring_separation(2, 0.05)
    with pytest.raises(ValueError, match="multiple of three"):
        native.translate([0.0, 1.0], 0.0, 0.0, 0.0)


#: A narrow-wide-narrow profile and its aligned outer surface.
WAIST = (
    (0.0, 0.0225),
    (0.5, 0.06),
    (0.98, 0.1),
    (1.46, 0.06),
    (1.96, 0.0225),
)
WAIST_OUTER = tuple((z, radius + 0.004) for z, radius in WAIST)

#: A compact-toroid separatrix, closed on the axis at both poles, and a
#: cone, closed at one. Both are shapes the open profile cannot express.
SEPARATRIX = (
    (-0.15, 0.0),
    (-0.1125, 0.02 * math.sqrt(1.0 - 0.75**2)),
    (-0.075, 0.02 * math.sqrt(1.0 - 0.5**2)),
    (0.0, 0.02),
    (0.075, 0.02 * math.sqrt(1.0 - 0.5**2)),
    (0.1125, 0.02 * math.sqrt(1.0 - 0.75**2)),
    (0.15, 0.0),
)
CONE = ((0.0, 0.0), (1.0, 0.5))


@pytest.mark.parametrize("segments", [8, 32, 64])
def test_profiled_solid_is_bit_exact(segments: int) -> None:
    """Every vertex of a varying body agrees bit for bit."""
    vertices, faces = profiled_solid(WAIST, segments)
    flat = [value for sample in WAIST for value in sample]
    got_vertices, got_faces = native.tessellate_profiled_solid(flat, segments)
    assert stream_bits([c for v in vertices for c in v]) == stream_bits(got_vertices)
    assert [i for f in faces for i in f] == got_faces


@pytest.mark.parametrize("segments", [8, 32, 64])
@pytest.mark.parametrize(("profile", "label"), [(SEPARATRIX, "poles"), (CONE, "cone")])
def test_closed_profiled_solid_is_bit_exact(
    profile: tuple[tuple[float, float], ...], label: str, segments: int
) -> None:
    """A body that closes on the axis agrees bit for bit, either way up."""
    vertices, faces = closed_profiled_solid(profile, segments)
    flat = [value for sample in profile for value in sample]
    got_vertices, got_faces = native.tessellate_closed_profiled_solid(flat, segments)
    assert stream_bits([c for v in vertices for c in v]) == stream_bits(got_vertices)
    assert [i for f in faces for i in f] == got_faces
    assert label in {"poles", "cone"}


def test_closed_profile_closed_forms_are_bit_exact() -> None:
    """The same sums serve a closed profile, and agree bit for bit."""
    flat = [value for sample in SEPARATRIX for value in sample]
    assert bits(profile_volume_m3(SEPARATRIX)) == bits(native.profile_volume(flat))
    assert bits(profile_lateral_area_m2(SEPARATRIX)) == bits(
        native.profile_lateral_area(flat)
    )


@pytest.mark.parametrize("segments", [8, 32])
def test_profiled_tube_is_bit_exact(segments: int) -> None:
    """The hollow varying body agrees bit for bit on both surfaces."""
    vertices, faces = profiled_tube(WAIST, WAIST_OUTER, segments)
    inner_flat = [value for sample in WAIST for value in sample]
    outer_flat = [value for sample in WAIST_OUTER for value in sample]
    got_vertices, got_faces = native.tessellate_profiled_tube(
        inner_flat, outer_flat, segments
    )
    assert stream_bits([c for v in vertices for c in v]) == stream_bits(got_vertices)
    assert [i for f in faces for i in f] == got_faces


def test_profile_closed_forms_are_bit_exact() -> None:
    """The frustum-stack volume and lateral area agree bit for bit."""
    flat = [value for sample in WAIST for value in sample]
    assert bits(profile_volume_m3(WAIST)) == bits(native.profile_volume(flat))
    assert bits(profile_lateral_area_m2(WAIST)) == bits(
        native.profile_lateral_area(flat)
    )


def test_native_profile_refusals_mirror_the_floor() -> None:
    """The native binding refuses a ragged stream and a bad segment count."""
    flat = [value for sample in WAIST for value in sample]
    with pytest.raises(ValueError, match="multiple"):
        native.tessellate_profiled_solid(flat, 20)
    with pytest.raises(ValueError, match="even number of values"):
        native.tessellate_profiled_solid([0.0, 1.0, 2.0], 8)
    with pytest.raises(ValueError, match="even number of values"):
        native.profile_volume([0.0, 1.0, 2.0])


@pytest.mark.parametrize("rings", [2, 3, 8, 64, 512])
@pytest.mark.parametrize(("radius", "centre"), [(1.0, 0.0), (0.0375, -2.25)])
def test_sphere_profile_is_bit_exact(radius: float, centre: float, rings: int) -> None:
    """The polar sampling agrees bit for bit, poles and equator included.

    Both sides read the same vendored polynomial trigonometry at the same
    indices of the same circle, so this is an equality on the bits and not
    a tolerance on the values.
    """
    floor = [
        value for sample in sphere_profile(radius, centre, rings) for value in sample
    ]
    assert stream_bits(floor) == stream_bits(
        native.sphere_profile(radius, centre, rings)
    )


@pytest.mark.parametrize("segments", [8, 64])
@pytest.mark.parametrize("rings", [2, 16])
def test_sphere_solid_is_bit_exact(rings: int, segments: int) -> None:
    """A sphere is its profile revolved, so parity follows from both kernels."""
    vertices, faces = sphere_solid(1.0, 0.0, segments, rings)
    flat = [value for sample in sphere_profile(1.0, 0.0, rings) for value in sample]
    got_vertices, got_faces = native.tessellate_closed_profiled_solid(flat, segments)
    assert stream_bits([c for v in vertices for c in v]) == stream_bits(got_vertices)
    assert [i for f in faces for i in f] == got_faces


@pytest.mark.parametrize("segments", [8, 64])
@pytest.mark.parametrize("rings", [2, 16])
def test_spherical_shell_is_bit_exact(rings: int, segments: int) -> None:
    """Both surfaces, the index offset and the reversed winding all agree."""
    vertices, faces = spherical_shell(0.6, 1.0, 0.0, segments, rings)
    outer = [v for s in sphere_profile(1.0, 0.0, rings) for v in s]
    inner = [v for s in sphere_profile(0.6, 0.0, rings) for v in s]
    got_vertices, got_faces = native.tessellate_spherical_shell(outer, inner, segments)
    assert stream_bits([c for v in vertices for c in v]) == stream_bits(got_vertices)
    assert [i for f in faces for i in f] == got_faces
