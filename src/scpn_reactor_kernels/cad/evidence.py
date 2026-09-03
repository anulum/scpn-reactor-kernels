# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — fail-closed evidence of one B-rep body

"""Fail-closed evidence of a B-rep body against its analytic closed form.

A tier-G2 device model is only worth its record if every body in it is
checked, and the check is the same for every family: the B-rep kernel's
volume and area against the analytic closed forms within the group's
declared tolerance, the faceted volume against the declared chord-deficit
bound of the mesher's linear deflection, and the faceted volume against
the tier-G1 mesh of the same body within the exact inscribed-polygon
deficit bound of the reference tessellation. None of that is device
knowledge, so it lives here rather than once per device repository: a
family owns its schema identity, its body composition and its non-claims,
and consumes the evidence.

The evidence object refuses at construction. A bound that is violated
raises :class:`~scpn_reactor_kernels.errors.CadError` naming the body and
the bound, so a model cannot be built around a body that failed a check
and a caller cannot forget to look. Nothing here describes a device.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from scpn_reactor_kernels.cad.facet import (
    deflection_volume_bound,
    inscribed_polygon_area_ratio,
)
from scpn_reactor_kernels.cad.solids import MEASURE_TOLERANCE, BrepBody
from scpn_reactor_kernels.errors import CadError
from scpn_reactor_kernels.geometry.mesh import TriangleMesh


@dataclass(frozen=True, slots=True)
class BodyEvidence:
    """One B-rep body checked against its analytic form and its G1 mesh.

    Parameters
    ----------
    name, role, material_identifier
        Body identity, identical to the tier-G1 body of the same name.
    analytic_volume_m3, brep_volume_m3
        Closed-form volume and the B-rep kernel's measure.
    volume_relative_error
        ``|V_brep - V_analytic| / V_analytic``; must not exceed the
        declared measure tolerance
        :data:`~scpn_reactor_kernels.cad.solids.MEASURE_TOLERANCE`.
    analytic_surface_area_m2, brep_surface_area_m2
        Closed-form surface area and the B-rep kernel's measure.
    surface_area_relative_error
        ``|A_brep - A_analytic| / A_analytic``; same tolerance.
    faceted_volume_m3
        Signed volume of the faceted B-rep (a closed mesh).
    faceted_volume_relative_deficit
        ``(V_analytic - V_faceted) / V_analytic`` of the faceted body.
    faceted_volume_deficit_bound
        Declared bound ``2 d / r`` of the chord deficit at the body's
        smallest circular radius ``r`` and the linear deflection ``d``.
    reference_mesh_volume_m3
        Signed volume of the tier-G1 mesh at the reference segment count.
    mesh_volume_relative_difference
        ``|V_faceted - V_reference| / V_analytic``.
    mesh_volume_difference_bound
        Exact polygon-deficit bound ``1 - (n / (2 pi)) sin(2 pi / n)`` of
        the reference segment count ``n``.

    Raises
    ------
    CadError
        If a declared bound is violated.
    """

    name: str
    role: str
    material_identifier: str
    analytic_volume_m3: float
    brep_volume_m3: float
    volume_relative_error: float
    analytic_surface_area_m2: float
    brep_surface_area_m2: float
    surface_area_relative_error: float
    faceted_volume_m3: float
    faceted_volume_relative_deficit: float
    faceted_volume_deficit_bound: float
    reference_mesh_volume_m3: float
    mesh_volume_relative_difference: float
    mesh_volume_difference_bound: float

    def __post_init__(self) -> None:
        """Refuse evidence that violates a declared bound.

        Raises
        ------
        CadError
            If a relative error exceeds the measure tolerance or a deficit
            exceeds its declared bound.
        """
        if self.volume_relative_error > MEASURE_TOLERANCE:
            raise CadError(
                f"{self.name}.volume_relative_error: must not exceed "
                f"{MEASURE_TOLERANCE!r}, got {self.volume_relative_error!r}"
            )
        if self.surface_area_relative_error > MEASURE_TOLERANCE:
            raise CadError(
                f"{self.name}.surface_area_relative_error: must not exceed "
                f"{MEASURE_TOLERANCE!r}, got {self.surface_area_relative_error!r}"
            )
        if self.faceted_volume_relative_deficit > self.faceted_volume_deficit_bound:
            raise CadError(
                f"{self.name}.faceted_volume_relative_deficit: must not exceed "
                f"the declared bound {self.faceted_volume_deficit_bound!r}, got "
                f"{self.faceted_volume_relative_deficit!r}"
            )
        if self.mesh_volume_relative_difference > self.mesh_volume_difference_bound:
            raise CadError(
                f"{self.name}.mesh_volume_relative_difference: must not exceed "
                f"the polygon-deficit bound {self.mesh_volume_difference_bound!r}, "
                f"got {self.mesh_volume_relative_difference!r}"
            )

    def to_record(self) -> dict[str, Any]:
        """Project the evidence to a JSON-serialisable record.

        Returns
        -------
        dict[str, Any]
            Identity, analytic and measured values, and every declared
            bound with the measured value next to it.
        """
        return {
            "name": self.name,
            "role": self.role,
            "material_identifier": self.material_identifier,
            "analytic_volume_m3": self.analytic_volume_m3,
            "brep_volume_m3": self.brep_volume_m3,
            "volume_relative_error": self.volume_relative_error,
            "analytic_surface_area_m2": self.analytic_surface_area_m2,
            "brep_surface_area_m2": self.brep_surface_area_m2,
            "surface_area_relative_error": self.surface_area_relative_error,
            "faceted_volume_m3": self.faceted_volume_m3,
            "faceted_volume_relative_deficit": self.faceted_volume_relative_deficit,
            "faceted_volume_deficit_bound": self.faceted_volume_deficit_bound,
            "reference_mesh_volume_m3": self.reference_mesh_volume_m3,
            "mesh_volume_relative_difference": self.mesh_volume_relative_difference,
            "mesh_volume_difference_bound": self.mesh_volume_difference_bound,
        }


def body_evidence(
    body: BrepBody,
    smallest_radius_m: float,
    faceted: TriangleMesh,
    reference_mesh: TriangleMesh,
    linear_deflection_m: float,
    segments: int,
) -> BodyEvidence:
    """Compute the fail-closed evidence of one body.

    Parameters
    ----------
    body
        The B-rep body.
    smallest_radius_m
        The body's smallest circular radius, which is the radius the chord
        deficit of the faceting is bounded at.
    faceted
        The faceted closed mesh of the body.
    reference_mesh
        The tier-G1 mesh of the same body at the reference segment count.
    linear_deflection_m
        The mesher's linear deflection.
    segments
        The reference mesh segment count.

    Returns
    -------
    BodyEvidence
        The checked evidence.

    Raises
    ------
    CadError
        If a declared bound is violated, or if an argument of a bound is
        invalid.
    """
    faceted_volume = faceted.signed_volume_m3()
    reference_volume = reference_mesh.signed_volume_m3()
    analytic_volume = body.analytic_volume_m3
    return BodyEvidence(
        name=body.name,
        role=body.role,
        material_identifier=body.material_identifier,
        analytic_volume_m3=analytic_volume,
        brep_volume_m3=body.volume_m3,
        volume_relative_error=body.volume_relative_error(),
        analytic_surface_area_m2=body.analytic_surface_area_m2,
        brep_surface_area_m2=body.surface_area_m2,
        surface_area_relative_error=body.surface_area_relative_error(),
        faceted_volume_m3=faceted_volume,
        faceted_volume_relative_deficit=(analytic_volume - faceted_volume)
        / analytic_volume,
        faceted_volume_deficit_bound=deflection_volume_bound(
            smallest_radius_m, linear_deflection_m
        ),
        reference_mesh_volume_m3=reference_volume,
        mesh_volume_relative_difference=abs(faceted_volume - reference_volume)
        / analytic_volume,
        mesh_volume_difference_bound=1.0 - inscribed_polygon_area_ratio(segments),
    )


def assembly_evidence(
    bodies: tuple[BrepBody, ...],
    smallest_radii: tuple[float, ...],
    faceted: tuple[TriangleMesh, ...],
    reference_meshes: tuple[TriangleMesh, ...],
    linear_deflection_m: float,
    segments: int,
) -> tuple[BodyEvidence, ...]:
    """Compute the evidence of every body of an assembly, in order.

    Parameters
    ----------
    bodies
        The B-rep bodies in the assembly's fixed order.
    smallest_radii
        The smallest circular radius of each body, in the same order.
    faceted
        The faceted meshes of the bodies, in the same order.
    reference_meshes
        The tier-G1 meshes of the same bodies, in the same order.
    linear_deflection_m
        The mesher's linear deflection.
    segments
        The reference mesh segment count.

    Returns
    -------
    tuple of BodyEvidence
        The checked evidence in the assembly's order.

    Raises
    ------
    CadError
        If the four sequences do not have the same length, or if any body
        violates a declared bound.
    """
    lengths = {
        len(bodies),
        len(smallest_radii),
        len(faceted),
        len(reference_meshes),
    }
    if len(lengths) != 1:
        raise CadError(
            "bodies, smallest_radii, faceted and reference_meshes: must have the "
            f"same length, got {len(bodies)!r}, {len(smallest_radii)!r}, "
            f"{len(faceted)!r} and {len(reference_meshes)!r}"
        )
    return tuple(
        body_evidence(body, radius, mesh, reference, linear_deflection_m, segments)
        for body, radius, mesh, reference in zip(
            bodies, smallest_radii, faceted, reference_meshes, strict=True
        )
    )
