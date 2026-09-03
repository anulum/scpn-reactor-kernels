# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — placement kernel tests

"""Translation, ring offsets and neighbour separation of the placement kernel."""

from __future__ import annotations

import math

import pytest

from scpn_reactor_kernels.errors import GeometryError
from scpn_reactor_kernels.geometry import (
    circle_points,
    cylinder_solid,
    ring_offsets,
    ring_separation_m,
    translate,
)


def test_translation_adds_each_component_once() -> None:
    """Each coordinate is one addition of the corresponding offset."""
    vertices = ((1.0, 2.0, 3.0), (-0.5, 0.25, 7.5))
    moved = translate(vertices, 0.1, -0.2, 0.3)
    assert moved == (
        (1.0 + 0.1, 2.0 + -0.2, 3.0 + 0.3),
        (-0.5 + 0.1, 0.25 + -0.2, 7.5 + 0.3),
    )


def test_translation_of_a_tessellated_body_moves_it_rigidly() -> None:
    """A translated cylinder keeps its face stream and shifts its extent."""
    vertices, faces = cylinder_solid(0.01, 0.0, 0.2, 8)
    moved = translate(vertices, 0.05, 0.0, 0.0)
    assert len(moved) == len(vertices)
    # the face stream belongs to the body, not to its position: translating
    # the vertices must leave the topology of the source body untouched
    assert faces == cylinder_solid(0.01, 0.0, 0.2, 8)[1]
    assert min(v[0] for v in moved) == pytest.approx(min(v[0] for v in vertices) + 0.05)
    assert [v[2] for v in moved] == [v[2] for v in vertices]


def test_translation_refuses_an_empty_stream_and_non_finite_offsets() -> None:
    """The kernel fails closed on an empty stream and on non-finite offsets."""
    with pytest.raises(GeometryError, match="vertices: must not be empty"):
        translate((), 0.0, 0.0, 0.0)
    for offset in ((math.nan, 0.0, 0.0), (0.0, math.inf, 0.0), (0.0, 0.0, math.nan)):
        with pytest.raises(GeometryError, match="offset_"):
            translate(((0.0, 0.0, 0.0),), *offset)


@pytest.mark.parametrize("count", [3, 4, 6, 8, 12, 13])
def test_ring_offsets_are_the_scaled_circle_points(count: int) -> None:
    """Every centre is the circle point scaled by the radius."""
    radius = 0.0517
    offsets = ring_offsets(count, radius)
    assert len(offsets) == count
    assert offsets == tuple(
        (radius * cosine, radius * sine) for cosine, sine in circle_points(count)
    )
    assert offsets[0] == (radius, 0.0)


@pytest.mark.parametrize("count", [3, 4, 6, 12, 13, 24])
def test_ring_separation_is_the_chord_between_neighbours(count: int) -> None:
    """The separation equals the analytic chord 2 R sin(pi / count)."""
    radius = 0.0517
    separation = ring_separation_m(count, radius)
    chord = 2.0 * radius * math.sin(math.pi / count)
    assert abs(separation - chord) <= 1.0e-15
    offsets = ring_offsets(count, radius)
    for index in range(count):
        first = offsets[index]
        second = offsets[(index + 1) % count]
        distance = math.hypot(second[0] - first[0], second[1] - first[1])
        assert abs(distance - separation) <= 1.0e-15


def test_ring_refuses_too_few_bodies_and_a_non_positive_radius() -> None:
    """Fewer than three bodies or a non-positive radius fail closed."""
    for count in (2, 1, 0):
        with pytest.raises(GeometryError, match="count: must be at least 3"):
            ring_offsets(count, 0.05)
    with pytest.raises(GeometryError, match="count: must be at least 3"):
        ring_separation_m(2, 0.05)
    for radius in (0.0, -0.05, math.nan, math.inf):
        with pytest.raises(GeometryError, match="radius_m"):
            ring_offsets(6, radius)
