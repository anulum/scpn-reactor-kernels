# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — tessellation primitive tests

"""Closure, orientation, exact identities and convergence of the primitives."""

from __future__ import annotations

import math

import pytest

from scpn_reactor_kernels.errors import GeometryError
from scpn_reactor_kernels.geometry import (
    TriangleMesh,
    annular_tube,
    cylinder_solid,
    unit_circle,
)


def as_mesh(vertices: object, faces: object) -> TriangleMesh:
    """Wrap raw streams into the validated mesh contract."""
    return TriangleMesh(
        name="body",
        role="test",
        material_identifier="none",
        vertices=vertices,  # type: ignore[arg-type]
        faces=faces,  # type: ignore[arg-type]
    )


def polygon_area(radius: float, segments: int) -> float:
    """Inscribed regular polygon area from the same circle points."""
    points = unit_circle(segments)
    total = 0.0
    for index, (x0, y0) in enumerate(points):
        x1, y1 = points[(index + 1) % segments]
        total += x0 * y1 - x1 * y0
    return radius * radius * total / 2.0


@pytest.mark.parametrize("segments", [8, 16, 64])
def test_cylinder_is_closed_outward_and_exact(segments: int) -> None:
    """Counts, closure, outward orientation and the polygon-prism identity."""
    vertices, faces = cylinder_solid(0.25, -0.5, 1.5, segments)
    assert len(vertices) == 2 * segments + 2
    assert len(faces) == 4 * segments
    mesh = as_mesh(vertices, faces)
    volume = mesh.signed_volume_m3()
    assert volume > 0.0
    expected = polygon_area(0.25, segments) * 2.0
    assert abs(volume - expected) <= 1.0e-14 * expected
    assert mesh.bounding_box() == ((-0.25, -0.25, -0.5), (0.25, 0.25, 1.5))


def test_cylinder_volume_converges_quadratically() -> None:
    """The relative volume error falls by ~4 per doubling of segments."""
    exact = math.pi * 0.3 * 0.3 * 2.0

    def error(segments: int) -> float:
        vertices, faces = cylinder_solid(0.3, 0.0, 2.0, segments)
        return (exact - as_mesh(vertices, faces).signed_volume_m3()) / exact

    coarse, fine = error(64), error(128)
    assert coarse > fine > 0.0
    assert abs(coarse / fine - 4.0) < 0.05


def test_cylinder_area_converges_to_the_closed_form() -> None:
    """Side plus caps area approaches 2 pi r h + 2 pi r^2."""
    exact = 2.0 * math.pi * 0.3 * 2.0 + 2.0 * math.pi * 0.3 * 0.3
    vertices, faces = cylinder_solid(0.3, 0.0, 2.0, 1024)
    area = as_mesh(vertices, faces).surface_area_m2()
    assert 0.0 < (exact - area) / exact < 1.0e-5


@pytest.mark.parametrize("segments", [8, 32])
def test_tube_is_closed_and_equals_outer_minus_inner(segments: int) -> None:
    """The tube volume is the difference of the two cylinder volumes."""
    vertices, faces = annular_tube(0.3, 0.5, 0.0, 1.0, segments)
    assert len(vertices) == 4 * segments
    assert len(faces) == 8 * segments
    tube = as_mesh(vertices, faces)
    outer = as_mesh(*cylinder_solid(0.5, 0.0, 1.0, segments))
    inner = as_mesh(*cylinder_solid(0.3, 0.0, 1.0, segments))
    expected = outer.signed_volume_m3() - inner.signed_volume_m3()
    assert abs(tube.signed_volume_m3() - expected) <= 1.0e-14 * expected
    assert tube.bounding_box() == ((-0.5, -0.5, 0.0), (0.5, 0.5, 1.0))


def test_tube_area_converges_to_the_closed_form() -> None:
    """Both sides plus both annuli approach the analytic area."""
    exact = 2.0 * math.pi * (0.3 + 0.5) * 1.0 + 2.0 * math.pi * (0.5**2 - 0.3**2)
    vertices, faces = annular_tube(0.3, 0.5, 0.0, 1.0, 1024)
    area = as_mesh(vertices, faces).surface_area_m2()
    assert 0.0 < (exact - area) / exact < 1.0e-5


@pytest.mark.parametrize("radius", [0.0, -1.0, math.nan, math.inf])
def test_invalid_radius_is_refused(radius: float) -> None:
    """Radii must be finite and strictly positive."""
    with pytest.raises(GeometryError, match="radius_m"):
        cylinder_solid(radius, 0.0, 1.0, 8)


def test_invalid_extent_is_refused() -> None:
    """Non-finite bounds and non-positive extents fail closed."""
    with pytest.raises(GeometryError, match="z_low: must be finite"):
        cylinder_solid(1.0, math.nan, 1.0, 8)
    with pytest.raises(GeometryError, match="z_high: must exceed z_low"):
        cylinder_solid(1.0, 1.0, 1.0, 8)
    with pytest.raises(GeometryError, match="z_high: must exceed z_low"):
        annular_tube(0.5, 1.0, 2.0, 1.0, 8)


def test_tube_radii_must_be_ordered() -> None:
    """The bore must be strictly inside the outer surface."""
    with pytest.raises(GeometryError, match="outer_radius_m: must exceed"):
        annular_tube(1.0, 1.0, 0.0, 1.0, 8)
    with pytest.raises(GeometryError, match="inner_radius_m"):
        annular_tube(0.0, 1.0, 0.0, 1.0, 8)


def test_invalid_segments_propagate() -> None:
    """The segment rule of the unit circle applies to every primitive."""
    with pytest.raises(GeometryError, match="multiple"):
        cylinder_solid(1.0, 0.0, 1.0, 12)
    with pytest.raises(GeometryError, match="at least"):
        annular_tube(0.5, 1.0, 0.0, 1.0, 4)
