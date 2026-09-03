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

import pytest

from geometry_fixtures import bits, sample_bodies, stream_bits
from scpn_reactor_kernels.geometry import (
    annular_tube,
    circle_points,
    cylinder_solid,
    ring_offsets,
    ring_separation_m,
    translate,
    unit_circle,
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
