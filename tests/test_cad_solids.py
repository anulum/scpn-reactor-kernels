# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — B-rep solid and assembly tests

"""The B-rep measures agree with the analytic forms; identity and refusals."""

from __future__ import annotations

import json
import math

import pytest

from cad_fixtures import (
    CYLINDER_EXTENT_M,
    CYLINDER_RADIUS_M,
    TUBE_EXTENT_M,
    TUBE_RADII_M,
    assembly,
    cylinder,
    tube,
)
from scpn_reactor_kernels.cad import (
    MANIFEST_SCHEMA,
    MANIFEST_SCHEMA_VERSION,
    MEASURE_TOLERANCE,
    BrepAssembly,
    BrepBody,
    annular_tube_brep,
    cylinder_solid_brep,
    require_extent,
    require_radius,
)
from scpn_reactor_kernels.errors import CadError


def test_cylinder_measures_agree_with_the_analytic_forms() -> None:
    """Volume pi r^2 h and area 2 pi r h + 2 pi r^2 within the declared tolerance."""
    body = cylinder()
    height = CYLINDER_EXTENT_M[1] - CYLINDER_EXTENT_M[0]
    assert body.analytic_volume_m3 == math.pi * CYLINDER_RADIUS_M**2 * height
    assert body.volume_relative_error() <= MEASURE_TOLERANCE
    assert body.surface_area_relative_error() <= MEASURE_TOLERANCE
    low, high = body.bounding_box_m()
    assert math.isclose(low[2], CYLINDER_EXTENT_M[0], abs_tol=1.0e-7)
    assert math.isclose(high[2], CYLINDER_EXTENT_M[1], abs_tol=1.0e-7)
    assert math.isclose(high[0], CYLINDER_RADIUS_M, abs_tol=1.0e-7)
    record = body.summary_record()
    assert record["name"] == "inner"
    assert record["volume_relative_error"] <= MEASURE_TOLERANCE
    assert set(record) == {
        "name",
        "role",
        "material_identifier",
        "volume_m3",
        "surface_area_m2",
        "analytic_volume_m3",
        "analytic_surface_area_m2",
        "volume_relative_error",
        "surface_area_relative_error",
        "bounding_box_min_m",
        "bounding_box_max_m",
    }


def test_tube_measures_agree_with_the_analytic_forms() -> None:
    """Volume pi (ro^2 - ri^2) h and the tube area within the declared tolerance."""
    body = tube()
    inner, outer = TUBE_RADII_M
    height = TUBE_EXTENT_M[1] - TUBE_EXTENT_M[0]
    assert body.analytic_volume_m3 == math.pi * (outer**2 - inner**2) * height
    assert body.volume_relative_error() <= MEASURE_TOLERANCE
    assert body.surface_area_relative_error() <= MEASURE_TOLERANCE
    assert body.volume_m3 < cylinder().volume_m3 * 3.0


@pytest.mark.parametrize(
    ("call", "fragment"),
    [
        (lambda: cylinder_solid_brep(0.0, 0.0, 1.0, "a", "b", "c"), "radius_m"),
        (lambda: cylinder_solid_brep(math.nan, 0.0, 1.0, "a", "b", "c"), "radius_m"),
        (lambda: cylinder_solid_brep(1.0, 1.0, 1.0, "a", "b", "c"), "z_high_m"),
        (lambda: cylinder_solid_brep(1.0, 0.0, math.inf, "a", "b", "c"), "z_high_m"),
        (lambda: cylinder_solid_brep(1.0, 0.0, 1.0, "", "b", "c"), "name"),
        (
            lambda: annular_tube_brep(1.0, 1.0, 0.0, 1.0, "a", "b", "c"),
            "outer_radius_m",
        ),
        (
            lambda: annular_tube_brep(-1.0, 2.0, 0.0, 1.0, "a", "b", "c"),
            "inner_radius_m",
        ),
        (lambda: annular_tube_brep(1.0, 2.0, 0.0, 1.0, "a", "", "c"), "role"),
        (lambda: annular_tube_brep(1.0, 2.0, 0.0, 1.0, "a", "b", ""), "material"),
    ],
)
def test_invalid_arguments_are_refused(call: object, fragment: str) -> None:
    """Every argument is validated before the back-end is asked for a shape."""
    assert callable(call)
    with pytest.raises(CadError, match=fragment):
        call()
    assert require_radius("r", 0.5) == 0.5
    assert require_extent(0.0, 1.0) == (0.0, 1.0)


def test_assembly_manifest_is_canonical_and_ordered() -> None:
    """The manifest lists the bodies in order with a stable digest."""
    built = assembly()
    manifest = built.manifest()
    assert manifest["schema"] == MANIFEST_SCHEMA
    assert manifest["schema_version"] == MANIFEST_SCHEMA_VERSION
    assert manifest["body_count"] == 2
    assert [body["name"] for body in manifest["bodies"]] == ["inner", "outer"]
    data = built.manifest_bytes()
    assert data.endswith(b"\n")
    assert json.loads(data) == manifest
    assert built.manifest_sha256() == assembly().manifest_sha256()
    cad_assembly = built.to_cadquery("device")
    assert [child.name for child in cad_assembly.children] == ["inner", "outer"]


def test_assembly_refusals() -> None:
    """An empty assembly and duplicate names are refused."""
    with pytest.raises(CadError, match="at least one body"):
        BrepAssembly(())
    with pytest.raises(CadError, match="unique"):
        BrepAssembly((cylinder(), cylinder()))
    assert isinstance(cylinder(), BrepBody)
