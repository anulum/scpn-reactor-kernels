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

import itertools
import math

import pytest

from geometry_fixtures import bits, sample_bodies, stream_bits
from scpn_reactor_kernels.geometry import (
    aim_rotation,
    annular_tube,
    axis_direction,
    centre_separation_m,
    circle_points,
    closed_profiled_solid,
    cylinder_solid,
    inward_aim,
    profile_lateral_area_m2,
    profile_volume_m3,
    profiled_solid,
    profiled_tube,
    rectangular_prism,
    ring_azimuths,
    ring_offsets,
    ring_separation_m,
    rotate,
    sphere_ring_offsets,
    translate,
    unit_circle,
)
from scpn_reactor_kernels.geometry.spheres import (
    sphere_profile,
    sphere_solid,
    spherical_shell,
)
from scpn_reactor_kernels.geometry.trig import (
    MAX_ANGLE_RAD,
    circle_point,
    radians_from_degrees,
)

native = pytest.importorskip("scpn_reactor_kernels_native")


@pytest.mark.parametrize("segments", [8, 16, 24, 64, 1024])
def test_unit_circle_is_bit_exact(segments: int) -> None:
    """The flat cos/sin stream agrees bit for bit."""
    floor = [component for point in unit_circle(segments) for component in point]
    assert stream_bits(floor) == stream_bits(native.unit_circle(segments))


PRINTED_RINGS = ((5, 20.1), (10, 59.0), (10, 121.0), (5, 159.9))


def _polar(degrees: float) -> tuple[float, float]:
    """Return the circle point of a printed latitude in degrees."""
    return circle_point(radians_from_degrees(degrees))


def test_the_aiming_rotation_is_bit_exact() -> None:
    """Every entry of the matrix agrees, for outward and inward aims alike."""
    for count, degrees in PRINTED_RINGS:
        polar = _polar(degrees)
        for azimuth in ring_azimuths(count, (1.0, 0.0)):
            for floor_call, native_call in (
                (aim_rotation, native.aim_rotation),
                (inward_aim, native.inward_aim),
            ):
                floor = [entry for row in floor_call(polar, azimuth) for entry in row]
                assert stream_bits(floor) == stream_bits(
                    native_call(list(polar), list(azimuth))
                )


def test_the_axis_direction_is_bit_exact() -> None:
    """The direction and the matrix column come from the same products."""
    for count, degrees in PRINTED_RINGS:
        polar = _polar(degrees)
        for azimuth in ring_azimuths(count, (1.0, 0.0)):
            floor = list(axis_direction(polar, azimuth))
            assert stream_bits(floor) == stream_bits(
                native.axis_direction(list(polar), list(azimuth))
            )


@pytest.mark.parametrize("count", [3, 5, 10, 12])
def test_the_twisted_ring_azimuths_are_bit_exact(count: int) -> None:
    """Both the identity twist and a real one agree bit for bit."""
    for offset in ((1.0, 0.0), circle_point(radians_from_degrees(36.0))):
        floor = [
            component for point in ring_azimuths(count, offset) for component in point
        ]
        assert stream_bits(floor) == stream_bits(
            native.ring_azimuths(count, list(offset))
        )


@pytest.mark.parametrize(("count", "degrees"), PRINTED_RINGS)
def test_the_sphere_ring_centres_are_bit_exact(count: int, degrees: float) -> None:
    """Every centre of every printed latitude agrees bit for bit."""
    polar = _polar(degrees)
    floor = [
        component
        for centre in sphere_ring_offsets(count, 1.5, polar, (1.0, 0.0))
        for component in centre
    ]
    assert stream_bits(floor) == stream_bits(
        native.sphere_ring_offsets(count, 1.5, list(polar), [1.0, 0.0])
    )


@pytest.mark.parametrize("segments", [8, 32])
def test_a_rotated_body_is_bit_exact(segments: int) -> None:
    """The rotated vertex stream of a real body agrees coordinate by coordinate."""
    vertices, _ = cylinder_solid(0.05, 0.0, 0.30, segments)
    polar = _polar(20.1)
    azimuth = ring_azimuths(5, (1.0, 0.0))[1]
    rotation = inward_aim(polar, azimuth)
    floor = [c for v in rotate(vertices, rotation) for c in v]
    flat_rotation = [entry for row in rotation for entry in row]
    assert stream_bits(floor) == stream_bits(
        native.rotate([c for v in vertices for c in v], flat_rotation)
    )


def test_the_centre_separation_is_bit_exact() -> None:
    """The distance agrees to the bit, not to a tolerance."""
    polar = _polar(59.0)
    centres = sphere_ring_offsets(10, 1.5, polar, (1.0, 0.0))
    for first, second in itertools.pairwise(centres):
        assert bits(centre_separation_m(first, second)) == bits(
            native.centre_separation(list(first), list(second))
        )


def test_the_arbitrary_angle_circle_point_is_bit_exact() -> None:
    """Every angle of a wide scan agrees bit for bit, not to a tolerance.

    The scan carries the quarter turns, the printed latitudes of a node
    set on a sphere, both edges of the declared domain and a sweep across
    it, so all four quadrant branches and both signs are compared.
    """
    angles = [step * 0.03125 for step in range(-2001, 2002)]
    angles += [radians_from_degrees(deg) for deg in (20.1, 43.4, 59.0, 159.9)]
    angles += [
        0.0,
        math.pi / 2.0,
        math.pi,
        3.0 * math.pi / 2.0,
        2.0 * math.pi,
        MAX_ANGLE_RAD,
        0.0 - MAX_ANGLE_RAD,
        3290522.209527707,
    ]
    floor = [component for angle in angles for component in circle_point(angle)]
    assert stream_bits(floor) == stream_bits(native.circle_point_stream(angles))


@pytest.mark.parametrize("angle_rad", [0.0, 0.35081118059122317, -12.5, 1.0e5])
def test_the_single_angle_binding_is_bit_exact(angle_rad: float) -> None:
    """The scalar entry point agrees with the stream one and with the floor."""
    floor = list(circle_point(angle_rad))
    assert stream_bits(floor) == stream_bits(native.circle_point(angle_rad))


@pytest.mark.parametrize("degrees", [0.0, 20.1, 180.0, -359.99, 1.0e5])
def test_the_degree_conversion_is_bit_exact(degrees: float) -> None:
    """One multiplication and one division, in the same order on both sides."""
    assert bits(radians_from_degrees(degrees)) == bits(
        native.radians_from_degrees(degrees)
    )


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


@pytest.mark.parametrize(
    ("width", "depth", "low", "high"),
    [
        (0.06, 0.09, -0.02, 0.14),
        (0.01, 0.01, -0.005, 0.005),
        (1.0, 1.0e-3, 0.0, 1.0e-3),
        (0.0123456789, 0.0987654321, -0.31, 0.0031415927),
    ],
)
def test_prism_is_bit_exact(
    width: float, depth: float, low: float, high: float
) -> None:
    """Vertices and faces of the rectangular prism agree exactly.

    This kernel is declared ``native_parity: true`` in the inventory, and
    that declaration covers every function in it. The prism has no
    circle behind it, so unlike its siblings its parity rests on the
    halving and the negation alone.
    """
    vertices, faces = rectangular_prism(width, depth, low, high)
    got_vertices, got_faces = native.tessellate_rectangular_prism(
        width, depth, low, high
    )
    assert stream_bits([c for v in vertices for c in v]) == stream_bits(got_vertices)
    assert [i for f in faces for i in f] == got_faces


def test_the_native_prism_takes_no_segment_count() -> None:
    """The absence of a resolution argument crosses the boundary too.

    A native twin that accepted a segment count would invite a caller to
    pass one and believe it did something.
    """
    with pytest.raises(TypeError):
        native.tessellate_rectangular_prism(0.06, 0.09, -0.02, 0.14, 8)


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
