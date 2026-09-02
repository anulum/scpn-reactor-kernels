# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — faceting tests

"""Faceted solids satisfy the closed-mesh contract and the deficit bounds."""

from __future__ import annotations

import math

import pytest

from cad_fixtures import CYLINDER_RADIUS_M, TUBE_RADII_M, assembly, cylinder, tube
from scpn_reactor_kernels.cad import (
    DEFLECTION_DEFICIT_FACTOR,
    deflection_volume_bound,
    facet_assembly,
    facet_body,
    inscribed_polygon_area_ratio,
    require_deflection,
    weld,
)
from scpn_reactor_kernels.errors import CadError
from scpn_reactor_kernels.geometry import TriangleMesh, cylinder_solid, stl_bytes

LINEAR_M = 1.0e-4
ANGULAR_RAD = 0.1


def test_faceted_cylinder_is_closed_outward_and_within_the_deficit_bound() -> None:
    """The mesh validates, its volume is below the exact one within 2 d / r."""
    body = cylinder()
    mesh = facet_body(body, LINEAR_M, ANGULAR_RAD)
    assert isinstance(mesh, TriangleMesh)
    assert mesh.name == "inner"
    assert mesh.role == "electrode"
    volume = mesh.signed_volume_m3()
    assert 0.0 < volume < body.analytic_volume_m3
    deficit = 1.0 - volume / body.analytic_volume_m3
    assert deficit <= deflection_volume_bound(CYLINDER_RADIUS_M, LINEAR_M)
    assert (
        deflection_volume_bound(0.05, 1.0e-4)
        == DEFLECTION_DEFICIT_FACTOR * 1.0e-4 / 0.05
    )
    assert stl_bytes((mesh,))[:80].startswith(b"SCPN")


def test_faceted_tube_is_closed_and_its_area_near_the_analytic_value() -> None:
    """The tube facets to one closed manifold; area within 1 % of the analytic."""
    body = tube()
    mesh = facet_body(body, LINEAR_M, ANGULAR_RAD)
    assert mesh.signed_volume_m3() > 0.0
    assert math.isclose(
        mesh.surface_area_m2(), body.analytic_surface_area_m2, rel_tol=1.0e-2
    )
    inner_bound = deflection_volume_bound(TUBE_RADII_M[0], LINEAR_M)
    assert abs(mesh.signed_volume_m3() / body.analytic_volume_m3 - 1.0) <= inner_bound


def test_assembly_facets_in_order() -> None:
    """Every body facets in the assembly order with its name."""
    meshes = facet_assembly(assembly(), LINEAR_M, ANGULAR_RAD)
    assert [mesh.name for mesh in meshes] == ["inner", "outer"]


def test_inscribed_polygon_ratio_matches_the_g1_tessellation() -> None:
    """The exact ratio (n / 2 pi) sin(2 pi / n) equals the G1 prism volume ratio."""
    for segments in (8, 16, 64):
        ratio = inscribed_polygon_area_ratio(segments)
        assert math.isclose(
            ratio, segments / (2.0 * math.pi) * math.sin(2.0 * math.pi / segments)
        )
        vertices, faces = cylinder_solid(0.05, 0.0, 0.3, segments)
        g1 = TriangleMesh("g1", "r", "m", vertices, faces)
        analytic = math.pi * 0.05**2 * 0.3
        assert math.isclose(g1.signed_volume_m3(), analytic * ratio, rel_tol=1.0e-12)


def test_weld_merges_exact_duplicates_only() -> None:
    """Welding keeps first-occurrence order and merges exact coordinates."""

    class Point:
        def __init__(self, x: float, y: float, z: float) -> None:
            self.x, self.y, self.z = x, y, z

    stream, faces = weld(
        [Point(0, 0, 0), Point(1, 0, 0), Point(0, 1, 0), Point(1, 0, 0)],
        [(0, 1, 2), (2, 3, 0)],
    )
    assert stream == ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    assert faces == ((0, 1, 2), (2, 1, 0))


@pytest.mark.parametrize("value", [0.0, -1.0, math.nan])
def test_invalid_deflections_are_refused(value: float) -> None:
    """Both deflections are strictly positive."""
    with pytest.raises(CadError, match="linear_deflection_m"):
        facet_body(cylinder(), value, ANGULAR_RAD)
    with pytest.raises(CadError, match="angular_deflection_rad"):
        facet_body(cylinder(), LINEAR_M, value)
    with pytest.raises(CadError, match="d"):
        require_deflection("d", value)
