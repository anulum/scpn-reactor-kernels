# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — B-rep body evidence tests

"""The evidence checks every declared bound and refuses at construction."""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest

from cad_fixtures import CYLINDER_EXTENT_M, CYLINDER_RADIUS_M, cylinder, tube
from scpn_reactor_kernels.cad import (
    MEASURE_TOLERANCE,
    BodyEvidence,
    assembly_evidence,
    body_evidence,
    facet_body,
)
from scpn_reactor_kernels.errors import CadError
from scpn_reactor_kernels.geometry import TriangleMesh, annular_tube, cylinder_solid

LINEAR_DEFLECTION_M = 1.0e-4
ANGULAR_DEFLECTION_RAD = 0.1
SEGMENTS = 64


def reference_cylinder() -> TriangleMesh:
    """Return the tier-G1 mesh of the fixture cylinder."""
    vertices, faces = cylinder_solid(CYLINDER_RADIUS_M, *CYLINDER_EXTENT_M, SEGMENTS)
    return TriangleMesh(
        name="inner",
        role="electrode",
        material_identifier="conductor",
        vertices=vertices,
        faces=faces,
    )


def reference_tube() -> TriangleMesh:
    """Return the tier-G1 mesh of the fixture tube."""
    from cad_fixtures import TUBE_EXTENT_M, TUBE_RADII_M

    vertices, faces = annular_tube(*TUBE_RADII_M, *TUBE_EXTENT_M, SEGMENTS)
    return TriangleMesh(
        name="outer",
        role="wall",
        material_identifier="steel",
        vertices=vertices,
        faces=faces,
    )


def test_evidence_of_a_body_carries_every_bound_next_to_its_measure() -> None:
    """The record states each measured value and the bound it is under."""
    body = cylinder()
    evidence = body_evidence(
        body,
        CYLINDER_RADIUS_M,
        facet_body(body, LINEAR_DEFLECTION_M, ANGULAR_DEFLECTION_RAD),
        reference_cylinder(),
        LINEAR_DEFLECTION_M,
        SEGMENTS,
    )
    assert evidence.name == "inner"
    assert evidence.volume_relative_error <= MEASURE_TOLERANCE
    assert evidence.surface_area_relative_error <= MEASURE_TOLERANCE
    assert (
        evidence.faceted_volume_relative_deficit
        <= evidence.faceted_volume_deficit_bound
    )
    assert (
        evidence.mesh_volume_relative_difference
        <= evidence.mesh_volume_difference_bound
    )
    record = evidence.to_record()
    assert set(record) == {
        "name",
        "role",
        "material_identifier",
        "analytic_volume_m3",
        "brep_volume_m3",
        "volume_relative_error",
        "analytic_surface_area_m2",
        "brep_surface_area_m2",
        "surface_area_relative_error",
        "faceted_volume_m3",
        "faceted_volume_relative_deficit",
        "faceted_volume_deficit_bound",
        "reference_mesh_volume_m3",
        "mesh_volume_relative_difference",
        "mesh_volume_difference_bound",
    }


def test_assembly_evidence_keeps_the_body_order() -> None:
    """Every body of an assembly is checked, in the assembly's order."""
    bodies = (cylinder(), tube())
    faceted = tuple(
        facet_body(body, LINEAR_DEFLECTION_M, ANGULAR_DEFLECTION_RAD) for body in bodies
    )
    evidence = assembly_evidence(
        bodies,
        (CYLINDER_RADIUS_M, 0.08),
        faceted,
        (reference_cylinder(), reference_tube()),
        LINEAR_DEFLECTION_M,
        SEGMENTS,
    )
    assert tuple(item.name for item in evidence) == ("inner", "outer")


def test_assembly_evidence_refuses_ragged_input() -> None:
    """A missing radius, mesh or reference is named, never silently zipped."""
    bodies = (cylinder(), tube())
    faceted = tuple(
        facet_body(body, LINEAR_DEFLECTION_M, ANGULAR_DEFLECTION_RAD) for body in bodies
    )
    with pytest.raises(CadError, match="same length"):
        assembly_evidence(
            bodies,
            (CYLINDER_RADIUS_M,),
            faceted,
            (reference_cylinder(), reference_tube()),
            LINEAR_DEFLECTION_M,
            SEGMENTS,
        )


def test_evidence_refuses_every_violated_bound() -> None:
    """Each of the four bounds refuses at construction, naming the body."""
    body = cylinder()
    sound = body_evidence(
        body,
        CYLINDER_RADIUS_M,
        facet_body(body, LINEAR_DEFLECTION_M, ANGULAR_DEFLECTION_RAD),
        reference_cylinder(),
        LINEAR_DEFLECTION_M,
        SEGMENTS,
    )
    for field_name, value, message in (
        ("volume_relative_error", 1.0e-6, "volume_relative_error"),
        ("surface_area_relative_error", 1.0e-6, "surface_area_relative_error"),
        (
            "faceted_volume_relative_deficit",
            sound.faceted_volume_deficit_bound * 2.0,
            "faceted_volume_relative_deficit",
        ),
        (
            "mesh_volume_relative_difference",
            sound.mesh_volume_difference_bound * 2.0,
            "mesh_volume_relative_difference",
        ),
    ):
        changes: dict[str, Any] = {field_name: value}
        with pytest.raises(CadError, match=message):
            dataclasses.replace(sound, **changes)


def test_evidence_is_a_plain_frozen_record() -> None:
    """The evidence cannot be mutated after it has been checked."""
    body = cylinder()
    evidence = body_evidence(
        body,
        CYLINDER_RADIUS_M,
        facet_body(body, LINEAR_DEFLECTION_M, ANGULAR_DEFLECTION_RAD),
        reference_cylinder(),
        LINEAR_DEFLECTION_M,
        SEGMENTS,
    )
    assert isinstance(evidence, BodyEvidence)
    with pytest.raises(dataclasses.FrozenInstanceError):
        evidence.name = "other"  # type: ignore[misc]
