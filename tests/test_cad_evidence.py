# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — B-rep body evidence tests

"""The evidence refuses at construction, and a wrong answer trips it.

Every negative case here is built from raw measures rather than from an
injected error scalar. That is the point of the module: the record's
bounds are compared against values recomputed from its own measures, so
a test that merely overwrote an error field would prove that the
overwriting was noticed, not that the geometry was checked.

The synthetic measures are deliberately large and unequal so that a
one-ulp perturbation is representable and no test can pass by symmetry.
They describe no device.
"""

from __future__ import annotations

import dataclasses
import math
from typing import Any

import pytest

from cad_fixtures import (
    CYLINDER_EXTENT_M,
    CYLINDER_RADIUS_M,
    PRISM_EXTENT_M,
    PRISM_SIDES_M,
    TUBE_EXTENT_M,
    TUBE_RADII_M,
    cylinder,
    prism,
    tube,
)
from scpn_reactor_kernels.cad import (
    MEASURE_TOLERANCE,
    BodyEvidence,
    assembly_evidence,
    body_evidence,
    facet_body,
)
from scpn_reactor_kernels.cad.evidence import facet_bounds
from scpn_reactor_kernels.cad.facet import PLANAR_FACETING_TOLERANCE
from scpn_reactor_kernels.errors import CadError
from scpn_reactor_kernels.geometry import (
    TriangleMesh,
    annular_tube,
    cylinder_solid,
    rectangular_prism,
)

LINEAR_DEFLECTION_M = 1.0e-4
ANGULAR_DEFLECTION_RAD = 0.1
SEGMENTS = 64

ANALYTIC_VOLUME_M3 = 1.0e9
BREP_VOLUME_M3 = 1.0e9 + 0.5
ANALYTIC_AREA_M2 = 1.0e9
BREP_AREA_M2 = 1.0e9 + 0.5
FACETED_VOLUME_M3 = 1.0e9 - 1.0e6
REFERENCE_VOLUME_M3 = 1.0e9 - 2.0e6
DEFICIT_BOUND = 2.0e-3
DIFFERENCE_BOUND = 2.0e-3

MEASURE_NAMES = (
    "analytic_volume_m3",
    "brep_volume_m3",
    "analytic_surface_area_m2",
    "brep_surface_area_m2",
    "faceted_volume_m3",
    "reference_mesh_volume_m3",
)
MAGNITUDE_NAMES = (
    "volume_relative_error",
    "surface_area_relative_error",
    "faceted_volume_deficit_bound",
    "mesh_volume_relative_difference",
    "mesh_volume_difference_bound",
)
DERIVED_NAMES = (
    "volume_relative_error",
    "surface_area_relative_error",
    "faceted_volume_relative_deficit",
    "mesh_volume_relative_difference",
)
NUMERIC_NAMES = (*MEASURE_NAMES, *MAGNITUDE_NAMES, "faceted_volume_relative_deficit")
NON_FINITE = (math.nan, math.inf, -math.inf)


def ratio(numerator: float, denominator: float) -> float:
    """Return a ratio, or zero where the denominator forbids one.

    Parameters
    ----------
    numerator, denominator
        The two operands.

    Returns
    -------
    float
        ``numerator / denominator``, or ``0.0`` when the denominator is
        zero. The zero-denominator cases exist to test that the record
        refuses such a measure, and the helper must be able to build one
        rather than raising while constructing the case.
    """
    try:
        return numerator / denominator
    except ZeroDivisionError:
        return 0.0


def measured_fields(**overrides: Any) -> dict[str, Any]:
    """Return a self-consistent field mapping, with overrides applied.

    Parameters
    ----------
    **overrides
        Field values to replace. A raw measure is replaced before the
        derived quantities are computed from it, so the mapping stays
        self-consistent; a derived field named here is replaced
        afterwards, which is how an inconsistent record is built on
        purpose.

    Returns
    -------
    dict[str, Any]
        Every field of :class:`BodyEvidence`.
    """
    fields: dict[str, Any] = {
        "name": "body",
        "role": "plasma",
        "material_identifier": "declared",
        "analytic_volume_m3": ANALYTIC_VOLUME_M3,
        "brep_volume_m3": BREP_VOLUME_M3,
        "analytic_surface_area_m2": ANALYTIC_AREA_M2,
        "brep_surface_area_m2": BREP_AREA_M2,
        "faceted_volume_m3": FACETED_VOLUME_M3,
        "reference_mesh_volume_m3": REFERENCE_VOLUME_M3,
        "faceted_volume_deficit_bound": DEFICIT_BOUND,
        "mesh_volume_difference_bound": DIFFERENCE_BOUND,
    }
    fields.update(overrides)
    fields["volume_relative_error"] = ratio(
        abs(fields["brep_volume_m3"] - fields["analytic_volume_m3"]),
        fields["analytic_volume_m3"],
    )
    fields["surface_area_relative_error"] = ratio(
        abs(fields["brep_surface_area_m2"] - fields["analytic_surface_area_m2"]),
        fields["analytic_surface_area_m2"],
    )
    fields["faceted_volume_relative_deficit"] = ratio(
        fields["analytic_volume_m3"] - fields["faceted_volume_m3"],
        fields["analytic_volume_m3"],
    )
    fields["mesh_volume_relative_difference"] = ratio(
        abs(fields["faceted_volume_m3"] - fields["reference_mesh_volume_m3"]),
        fields["analytic_volume_m3"],
    )
    fields.update(overrides)
    return fields


def measured_evidence(**overrides: Any) -> BodyEvidence:
    """Construct evidence from self-consistent synthetic measures.

    Parameters
    ----------
    **overrides
        Passed to :func:`measured_fields`.

    Returns
    -------
    BodyEvidence
        The constructed record.
    """
    return BodyEvidence(**measured_fields(**overrides))


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
    vertices, faces = annular_tube(*TUBE_RADII_M, *TUBE_EXTENT_M, SEGMENTS)
    return TriangleMesh(
        name="outer",
        role="wall",
        material_identifier="steel",
        vertices=vertices,
        faces=faces,
    )


def reference_prism() -> TriangleMesh:
    """Return the tier-G1 mesh of the fixture prism."""
    vertices, faces = rectangular_prism(*PRISM_SIDES_M, *PRISM_EXTENT_M)
    return TriangleMesh(
        name="slab",
        role="target",
        material_identifier="fuel",
        vertices=vertices,
        faces=faces,
    )


def faceted_of(body: Any) -> TriangleMesh:
    """Return the faceting of a body at the module's deflections."""
    return facet_body(body, LINEAR_DEFLECTION_M, ANGULAR_DEFLECTION_RAD)


def test_evidence_of_a_body_carries_every_bound_next_to_its_measure() -> None:
    """The record states each measured value and the bound it is under."""
    body = cylinder()
    evidence = body_evidence(
        body,
        CYLINDER_RADIUS_M,
        faceted_of(body),
        reference_cylinder(),
        LINEAR_DEFLECTION_M,
        SEGMENTS,
    )
    assert evidence.name == "inner"
    assert evidence.volume_relative_error <= MEASURE_TOLERANCE
    assert evidence.surface_area_relative_error <= MEASURE_TOLERANCE
    assert (
        abs(evidence.faceted_volume_relative_deficit)
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


def test_a_body_without_curvature_passes_under_the_round_off_bound() -> None:
    """The planar regime is a real case, not a branch nothing exercises."""
    body = prism()
    evidence = body_evidence(
        body,
        None,
        faceted_of(body),
        reference_prism(),
        LINEAR_DEFLECTION_M,
        SEGMENTS,
    )
    assert evidence.faceted_volume_deficit_bound == PLANAR_FACETING_TOLERANCE
    assert evidence.mesh_volume_difference_bound == PLANAR_FACETING_TOLERANCE
    assert abs(evidence.faceted_volume_relative_deficit) <= PLANAR_FACETING_TOLERANCE


def test_the_two_faceting_regimes_are_orders_apart() -> None:
    """A curved body's bounds are nothing like a planar body's."""
    curved = facet_bounds(CYLINDER_RADIUS_M, LINEAR_DEFLECTION_M, SEGMENTS)
    planar = facet_bounds(None, LINEAR_DEFLECTION_M, SEGMENTS)
    assert planar == (PLANAR_FACETING_TOLERANCE, PLANAR_FACETING_TOLERANCE)
    assert curved[0] > planar[0] * 1.0e6
    assert curved[1] > planar[1] * 1.0e6


def test_assembly_evidence_keeps_the_body_order_across_a_mixed_assembly() -> None:
    """Curved and planar bodies are checked together, in order."""
    bodies = (cylinder(), tube(), prism())
    evidence = assembly_evidence(
        bodies,
        (CYLINDER_RADIUS_M, TUBE_RADII_M[0], None),
        tuple(faceted_of(body) for body in bodies),
        (reference_cylinder(), reference_tube(), reference_prism()),
        LINEAR_DEFLECTION_M,
        SEGMENTS,
    )
    assert tuple(item.name for item in evidence) == ("inner", "outer", "slab")
    assert evidence[2].faceted_volume_deficit_bound == PLANAR_FACETING_TOLERANCE


def test_assembly_evidence_refuses_ragged_input() -> None:
    """A missing radius, mesh or reference is named, never silently zipped."""
    bodies = (cylinder(), tube())
    with pytest.raises(CadError, match="same length"):
        assembly_evidence(
            bodies,
            (CYLINDER_RADIUS_M,),
            tuple(faceted_of(body) for body in bodies),
            (reference_cylinder(), reference_tube()),
            LINEAR_DEFLECTION_M,
            SEGMENTS,
        )


def test_evidence_is_a_plain_frozen_record() -> None:
    """The evidence cannot be mutated after it has been checked."""
    evidence = measured_evidence()
    assert isinstance(evidence, BodyEvidence)
    frozen_field = "name"
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(evidence, frozen_field, "other")


@pytest.mark.parametrize("field_name", NUMERIC_NAMES)
@pytest.mark.parametrize("value", NON_FINITE)
def test_every_numeric_field_refuses_a_non_finite_value(
    field_name: str, value: float
) -> None:
    """A NaN or an infinity is refused before any comparison runs.

    This is the case the previous contract failed on: a NaN compares
    ``False`` against a bound and against its negation, so it satisfied
    every check at once.
    """
    with pytest.raises(CadError, match=f"{field_name}: must be finite"):
        measured_evidence(**{field_name: value})


@pytest.mark.parametrize("field_name", MEASURE_NAMES)
@pytest.mark.parametrize("value", [0.0, -1.0])
def test_every_measure_refuses_zero_or_less(field_name: str, value: float) -> None:
    """A measure a ratio is taken against must be strictly positive."""
    with pytest.raises(CadError, match=f"{field_name}: must be strictly positive"):
        measured_evidence(**{field_name: value})


@pytest.mark.parametrize("field_name", MAGNITUDE_NAMES)
def test_every_magnitude_refuses_a_negative_value(field_name: str) -> None:
    """A negative magnitude would pass every bound whatever happened."""
    with pytest.raises(CadError, match=f"{field_name}: must not be negative"):
        measured_evidence(**{field_name: -1.0})


@pytest.mark.parametrize("field_name", ["name", "role", "material_identifier"])
def test_every_identity_refuses_an_empty_value(field_name: str) -> None:
    """An unnamed body cannot be named in its own refusal."""
    with pytest.raises(CadError, match=f"{field_name}: must be non-empty"):
        measured_evidence(**{field_name: ""})


def test_a_claimed_zero_error_beside_contradicting_measures_is_refused() -> None:
    """The original counterexample: volume 1 against 100, error zero."""
    fields = measured_fields(
        analytic_volume_m3=1.0,
        brep_volume_m3=100.0,
        faceted_volume_m3=1.0,
        reference_mesh_volume_m3=1.0,
    )
    fields["volume_relative_error"] = 0.0
    with pytest.raises(CadError, match="volume_relative_error: must equal"):
        BodyEvidence(**fields)


@pytest.mark.parametrize("field_name", DERIVED_NAMES)
def test_every_derived_field_must_be_what_its_measures_give(field_name: str) -> None:
    """One ulp away from the measured value is already a wrong claim."""
    sound = measured_evidence()
    drifted = math.nextafter(getattr(sound, field_name), math.inf)
    with pytest.raises(CadError, match=f"{field_name}: must equal"):
        measured_evidence(**{field_name: drifted})


def test_the_volume_tolerance_is_exact_at_the_bound_and_one_ulp_either_side() -> None:
    """The nearest failing case is a representable neighbour of the bound."""
    at_bound = ANALYTIC_VOLUME_M3 + 1.0
    assert abs(at_bound - ANALYTIC_VOLUME_M3) / ANALYTIC_VOLUME_M3 == MEASURE_TOLERANCE
    accepted = measured_evidence(brep_volume_m3=at_bound)
    assert accepted.volume_relative_error == MEASURE_TOLERANCE
    below = math.nextafter(at_bound, -math.inf)
    assert measured_evidence(brep_volume_m3=below).volume_relative_error < (
        MEASURE_TOLERANCE
    )
    above = math.nextafter(at_bound, math.inf)
    with pytest.raises(CadError, match="volume_relative_error"):
        measured_evidence(brep_volume_m3=above)


def test_the_area_tolerance_is_exact_at_the_bound_and_one_ulp_either_side() -> None:
    """The area is checked on its own measures, not on the volume's."""
    at_bound = ANALYTIC_AREA_M2 + 1.0
    assert abs(at_bound - ANALYTIC_AREA_M2) / ANALYTIC_AREA_M2 == MEASURE_TOLERANCE
    accepted = measured_evidence(brep_surface_area_m2=at_bound)
    assert accepted.surface_area_relative_error == MEASURE_TOLERANCE
    above = math.nextafter(at_bound, math.inf)
    with pytest.raises(CadError, match="surface_area_relative_error"):
        measured_evidence(brep_surface_area_m2=above)


def test_the_faceting_bound_is_exact_and_refuses_one_ulp_beyond() -> None:
    """The deficit bound is tested against a deficit built from volumes."""
    sound = measured_evidence()
    magnitude = abs(sound.faceted_volume_relative_deficit)
    accepted = measured_evidence(faceted_volume_deficit_bound=magnitude)
    assert accepted.faceted_volume_deficit_bound == magnitude
    below = math.nextafter(magnitude, -math.inf)
    with pytest.raises(CadError, match="faceted_volume_relative_deficit"):
        measured_evidence(faceted_volume_deficit_bound=below)


def test_the_mesh_difference_bound_is_exact_and_refuses_one_ulp_beyond() -> None:
    """The mesh difference is bounded by the polygon deficit, exactly."""
    sound = measured_evidence()
    magnitude = sound.mesh_volume_relative_difference
    accepted = measured_evidence(mesh_volume_difference_bound=magnitude)
    assert accepted.mesh_volume_difference_bound == magnitude
    below = math.nextafter(magnitude, -math.inf)
    with pytest.raises(CadError, match="mesh_volume_relative_difference"):
        measured_evidence(mesh_volume_difference_bound=below)


def test_a_faceted_volume_that_overshoots_is_refused_like_one_that_undershoots() -> (
    None
):
    """The deficit is signed, and both signs are checked in magnitude."""
    overshoot = ANALYTIC_VOLUME_M3 + 1.0e6
    accepted = measured_evidence(
        faceted_volume_m3=overshoot, reference_mesh_volume_m3=overshoot
    )
    assert accepted.faceted_volume_relative_deficit < 0.0
    assert abs(accepted.faceted_volume_relative_deficit) <= DEFICIT_BOUND
    far = ANALYTIC_VOLUME_M3 + 1.0e7
    with pytest.raises(CadError, match="faceted_volume_relative_deficit"):
        measured_evidence(faceted_volume_m3=far, reference_mesh_volume_m3=far)


def test_a_recomputed_ratio_that_overflows_is_refused() -> None:
    """Finite measures and a positive denominator still allow an infinity.

    The supplied error is a finite zero here, so it passes every check on
    the fields themselves. Only the recomputation overflows, and it is
    the recomputed value the bounds are compared against, so an
    unchecked infinity there would have satisfied the tolerance.
    """
    with pytest.raises(CadError, match="recomputed: must be finite"):
        measured_evidence(
            analytic_volume_m3=5.0e-324,
            brep_volume_m3=1.0e308,
            faceted_volume_m3=5.0e-324,
            reference_mesh_volume_m3=5.0e-324,
            volume_relative_error=0.0,
        )


@pytest.mark.parametrize("field_name", ["name", "role", "material_identifier"])
@pytest.mark.parametrize("which", ["faceted", "reference"])
def test_body_evidence_refuses_a_mesh_of_another_body(
    field_name: str, which: str
) -> None:
    """Matching measures do not make two bodies the same body."""
    body = cylinder()
    meshes = {"faceted": faceted_of(body), "reference": reference_cylinder()}
    changes: dict[str, Any] = {field_name: "elsewhere"}
    meshes[which] = dataclasses.replace(meshes[which], **changes)
    with pytest.raises(CadError, match=f"{field_name}: the B-rep body"):
        body_evidence(
            body,
            CYLINDER_RADIUS_M,
            meshes["faceted"],
            meshes["reference"],
            LINEAR_DEFLECTION_M,
            SEGMENTS,
        )


def test_assembly_evidence_refuses_reference_meshes_in_the_wrong_order() -> None:
    """The zip is where a body meets its neighbour's mesh, so it is tested."""
    bodies = (cylinder(), tube())
    with pytest.raises(CadError, match="the B-rep body"):
        assembly_evidence(
            bodies,
            (CYLINDER_RADIUS_M, TUBE_RADII_M[0]),
            tuple(faceted_of(body) for body in bodies),
            (reference_tube(), reference_cylinder()),
            LINEAR_DEFLECTION_M,
            SEGMENTS,
        )
