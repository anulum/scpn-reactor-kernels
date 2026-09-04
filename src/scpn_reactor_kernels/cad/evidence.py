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
declared tolerance, and the faceted volume against both its analytic form
and the tier-G1 mesh of the same body. None of that is device knowledge,
so it lives here rather than once per device repository: a family owns
its schema identity, its body composition and its non-claims, and
consumes the evidence.

**The faceting bounds depend on whether the body is curved, and the
caller must say which.** A body with a curved surface is faceted by
inscribed chords, so its faceted volume falls below the analytic one by a
deficit bounded by ``2 d / r`` at the body's smallest circular radius,
and its tier-G1 twin is an inscribed polygon prism bounded by the exact
polygon-deficit ratio. A body with **no** curved surface has neither
bound and needs neither: the mesher returns the body itself, so the only
deviation is round-off, it can fall on either side of the analytic value,
and it is bounded by
:data:`~scpn_reactor_kernels.cad.facet.PLANAR_FACETING_TOLERANCE`.
Callers state which regime a body is in by passing its smallest circular
radius, or ``None`` where there is none. Reusing the circular bound for a
prism would not merely be loose — the prism's deviation is negative as
often as positive and is 14 orders below ``2 d / r``, so the check would
pass whatever happened, and the evidence would be decorative (ADR 0015).

The evidence object refuses at construction. A bound that is violated
raises :class:`~scpn_reactor_kernels.errors.CadError` naming the body and
the bound, so a model cannot be built around a body that failed a check
and a caller cannot forget to look. Nothing here describes a device.

**A bound is only a check if a wrong answer can fail it, and a bare
comparison is not one.** Every field is therefore proved to be a finite
number before it is compared, because a NaN compares ``False`` in both
directions and would satisfy a bound and its negation at once; every
measure a ratio is taken against is proved strictly positive; every
magnitude is proved not to be negative, because a negative one passes a
``must not exceed`` test whatever the geometry did; and **every supplied
error is recomputed from the record's own raw measures and must equal
what they give**, so a claimed error of zero cannot stand next to a
B-rep volume a hundred times its analytic form. The bounds are then
compared against the recomputed values rather than the supplied ones,
which means the record cannot certify itself: the caller's arithmetic is
evidence, not authority. The identity of the three bodies compared is
checked before any of their measures are, because measures do not carry
identity and a mesh paired with the wrong body would produce a small
difference and certify nothing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Final

from scpn_reactor_kernels.cad.facet import (
    PLANAR_FACETING_TOLERANCE,
    deflection_volume_bound,
    inscribed_polygon_area_ratio,
)
from scpn_reactor_kernels.cad.solids import MEASURE_TOLERANCE, BrepBody
from scpn_reactor_kernels.errors import CadError
from scpn_reactor_kernels.geometry.mesh import TriangleMesh

IDENTITY_FIELDS: Final = ("name", "role", "material_identifier")
"""Fields that must agree across the B-rep, faceted and reference bodies."""

_MEASURE_FIELDS: Final = (
    "analytic_volume_m3",
    "brep_volume_m3",
    "analytic_surface_area_m2",
    "brep_surface_area_m2",
    "faceted_volume_m3",
    "reference_mesh_volume_m3",
)
_MAGNITUDE_FIELDS: Final = (
    "volume_relative_error",
    "surface_area_relative_error",
    "faceted_volume_deficit_bound",
    "mesh_volume_relative_difference",
    "mesh_volume_difference_bound",
)
_SIGNED_FIELDS: Final = ("faceted_volume_relative_deficit",)


def _require_finite(body_name: str, field_name: str, value: float) -> float:
    """Return the value if it is a finite number, and refuse it otherwise.

    Parameters
    ----------
    body_name
        Name of the body the field belongs to, so the refusal says which.
    field_name
        Name of the field being checked.
    value
        The value.

    Returns
    -------
    float
        The value, unchanged.

    Raises
    ------
    CadError
        If the value is a NaN or an infinity.

    Notes
    -----
    This is the check the rest of the module rests on. Every bound here
    is a comparison, and a NaN compares ``False`` against everything, so
    a single NaN reaching a bound would satisfy it in both directions and
    the evidence would be admitted without a check ever having run.
    """
    if not math.isfinite(value):
        raise CadError(f"{body_name}.{field_name}: must be finite, got {value!r}")
    return value


def _require_positive(body_name: str, field_name: str, value: float) -> float:
    """Return the value if it is strictly positive, and refuse it otherwise.

    Parameters
    ----------
    body_name
        Name of the body the field belongs to.
    field_name
        Name of the field being checked.
    value
        The value.

    Returns
    -------
    float
        The value, unchanged.

    Raises
    ------
    CadError
        If the value is zero or negative.

    Notes
    -----
    Applied to the measures a relative error is formed from. A zero
    analytic measure makes every ratio a division by zero, and a negative
    one silently flips the sign of every error taken against it. The
    faceted and reference volumes are signed volumes of closed meshes, so
    a negative value there is an inward-oriented mesh rather than a small
    body.
    """
    if value <= 0.0:
        raise CadError(
            f"{body_name}.{field_name}: must be strictly positive, got {value!r}"
        )
    return value


def _require_non_negative(body_name: str, field_name: str, value: float) -> float:
    """Return the value if it is not negative, and refuse it otherwise.

    Parameters
    ----------
    body_name
        Name of the body the field belongs to.
    field_name
        Name of the field being checked.
    value
        The value.

    Returns
    -------
    float
        The value, unchanged.

    Raises
    ------
    CadError
        If the value is negative.

    Notes
    -----
    Applied to the magnitudes: an absolute relative error and a declared
    bound. A negative magnitude passes every ``must not exceed`` test
    whatever the geometry did, which is how a supplied error of ``-1.0``
    was formerly admitted.
    """
    if value < 0.0:
        raise CadError(f"{body_name}.{field_name}: must not be negative, got {value!r}")
    return value


def _require_recomputed(
    body_name: str, field_name: str, supplied: float, recomputed: float
) -> None:
    """Refuse a supplied error that its own measures do not produce.

    Parameters
    ----------
    body_name
        Name of the body the field belongs to.
    field_name
        Name of the field being checked.
    supplied
        The value the caller supplied.
    recomputed
        The value recomputed from the record's own raw measures.

    Raises
    ------
    CadError
        If the two differ at all.

    Notes
    -----
    **Equality here is exact, and that is a measurement rather than a
    preference.** The recomputation uses the same expressions in the same
    arithmetic order as
    :meth:`~scpn_reactor_kernels.cad.solids.BrepBody.volume_relative_error`
    and :func:`body_evidence`, and operates on the record's own stored
    measures, so on the real curved and planar bodies of this library it
    reproduces every supplied value bit for bit. No allowance is needed,
    and any allowance would be room for a claimed error to drift from the
    geometry it claims to describe.
    """
    if supplied != recomputed:
        raise CadError(
            f"{body_name}.{field_name}: must equal the value its own measures "
            f"give, {recomputed!r}, got {supplied!r}"
        )


def _require_within(
    body_name: str, field_name: str, value: float, bound: float, description: str
) -> None:
    """Refuse a measured value that exceeds its declared bound.

    Parameters
    ----------
    body_name
        Name of the body the field belongs to.
    field_name
        Name of the field being checked.
    value
        The recomputed value, never the supplied one.
    bound
        The declared bound.
    description
        How the bound is named in the refusal.

    Raises
    ------
    CadError
        If the value exceeds the bound.
    """
    if value > bound:
        raise CadError(
            f"{body_name}.{field_name}: {value!r} exceeds {description}, {bound!r}"
        )


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
        Checked **in magnitude**: a faceted volume that overshoots the
        analytic one is as much a defect as one that undershoots, and a
        one-sided check would have admitted the first without comment.
    faceted_volume_deficit_bound
        Declared bound of that magnitude. For a curved body it is
        ``2 d / r`` at the body's smallest circular radius ``r`` and the
        linear deflection ``d``; for a body with no curved surface it is
        :data:`~scpn_reactor_kernels.cad.facet.PLANAR_FACETING_TOLERANCE`.
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
        If an identity is empty, a numeric field is not finite, a measure
        is not strictly positive, a magnitude is negative, a supplied
        error is not the value its own measures give, or a recomputed
        value exceeds its declared bound.

    Notes
    -----
    ``analytic_volume_m3``, ``brep_volume_m3``,
    ``analytic_surface_area_m2``, ``brep_surface_area_m2``,
    ``faceted_volume_m3`` and ``reference_mesh_volume_m3`` are measures
    and must be strictly positive; the last two are signed volumes of
    closed meshes, so a negative value is an inward-oriented mesh rather
    than a small body. The relative errors, the mesh difference and both
    bounds are magnitudes and must not be negative. Only
    ``faceted_volume_relative_deficit`` is signed, and it is checked in
    magnitude.
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
        """Refuse evidence that is not a valid, self-consistent record.

        The checks run in one order and it matters: a field is proved
        finite before it is compared, proved to have the right sign
        before it is divided by, proved to be the value its own measures
        give before it is trusted, and only then compared against its
        bound.

        Raises
        ------
        CadError
            If an identity is empty, a numeric field is not finite, a
            measure is not strictly positive, a magnitude is negative, a
            supplied error is not the one its own measures give, or a
            recomputed value exceeds its declared bound.
        """
        for field_name in IDENTITY_FIELDS:
            if not getattr(self, field_name):
                raise CadError(f"{field_name}: must be non-empty")
        for field_name in (*_MEASURE_FIELDS, *_MAGNITUDE_FIELDS, *_SIGNED_FIELDS):
            _require_finite(self.name, field_name, getattr(self, field_name))
        for field_name in _MEASURE_FIELDS:
            _require_positive(self.name, field_name, getattr(self, field_name))
        for field_name in _MAGNITUDE_FIELDS:
            _require_non_negative(self.name, field_name, getattr(self, field_name))
        recomputed = self._recompute_from_measures()
        for field_name, value in recomputed.items():
            _require_recomputed(self.name, field_name, getattr(self, field_name), value)
        _require_within(
            self.name,
            "volume_relative_error",
            recomputed["volume_relative_error"],
            MEASURE_TOLERANCE,
            "the measure tolerance",
        )
        _require_within(
            self.name,
            "surface_area_relative_error",
            recomputed["surface_area_relative_error"],
            MEASURE_TOLERANCE,
            "the measure tolerance",
        )
        _require_within(
            self.name,
            "faceted_volume_relative_deficit",
            abs(recomputed["faceted_volume_relative_deficit"]),
            self.faceted_volume_deficit_bound,
            "its declared bound in magnitude",
        )
        _require_within(
            self.name,
            "mesh_volume_relative_difference",
            recomputed["mesh_volume_relative_difference"],
            self.mesh_volume_difference_bound,
            "the polygon-deficit bound",
        )

    def _recompute_from_measures(self) -> dict[str, float]:
        """Return the four derived quantities, taken from the measures.

        Returns
        -------
        dict[str, float]
            Each derived field name against the value the record's own
            raw measures produce, in the arithmetic order the library
            computes it in.

        Raises
        ------
        CadError
            If a recomputed ratio is not finite. Finite measures with a
            positive denominator can still overflow, and a ratio that
            does would satisfy every bound below it.
        """
        recomputed = {
            "volume_relative_error": abs(self.brep_volume_m3 - self.analytic_volume_m3)
            / self.analytic_volume_m3,
            "surface_area_relative_error": abs(
                self.brep_surface_area_m2 - self.analytic_surface_area_m2
            )
            / self.analytic_surface_area_m2,
            "faceted_volume_relative_deficit": (
                self.analytic_volume_m3 - self.faceted_volume_m3
            )
            / self.analytic_volume_m3,
            "mesh_volume_relative_difference": abs(
                self.faceted_volume_m3 - self.reference_mesh_volume_m3
            )
            / self.analytic_volume_m3,
        }
        for field_name, value in recomputed.items():
            _require_finite(self.name, f"{field_name} recomputed", value)
        return recomputed

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


def facet_bounds(
    smallest_radius_m: float | None, linear_deflection_m: float, segments: int
) -> tuple[float, float]:
    """Return the two faceting bounds of one body, by its curvature.

    Parameters
    ----------
    smallest_radius_m
        The body's smallest circular radius, or ``None`` where the body
        has no curved surface.
    linear_deflection_m
        The mesher's linear deflection.
    segments
        The reference mesh segment count.

    Returns
    -------
    (faceted_volume_deficit_bound, mesh_volume_difference_bound)
        The chord-deficit and polygon-deficit bounds for a curved body;
        :data:`~scpn_reactor_kernels.cad.facet.PLANAR_FACETING_TOLERANCE`
        twice for a body with no curved surface.

    Notes
    -----
    Neither argument of the curved branch means anything for a body
    without curvature. A prism has no circular radius to bound a chord
    against and no inscribed polygon to compare against, and its
    tessellation does not change with the segment count because there is
    nothing to refine. Returning the round-off tolerance for it is not a
    relaxation: measured, it is thirteen orders **tighter** than the
    chord bound the same deflection would have produced.
    """
    if smallest_radius_m is None:
        return PLANAR_FACETING_TOLERANCE, PLANAR_FACETING_TOLERANCE
    return (
        deflection_volume_bound(smallest_radius_m, linear_deflection_m),
        1.0 - inscribed_polygon_area_ratio(segments),
    )


def _require_matching_identity(
    body: BrepBody, faceted: TriangleMesh, reference_mesh: TriangleMesh
) -> None:
    """Refuse three bodies that are not the same body.

    Parameters
    ----------
    body
        The B-rep body.
    faceted
        The faceted mesh said to be of that body.
    reference_mesh
        The tier-G1 mesh said to be of that body.

    Raises
    ------
    CadError
        If a name, role or material identifier disagrees.

    Notes
    -----
    Every number below this check is a comparison of measures, and
    measures do not carry identity: two bodies of a device can have equal
    volumes and be different shapes in different places, so a reference
    mesh handed in against the wrong body would produce a small
    difference and an evidence record that certifies nothing. The
    assembly form zips four sequences in one fixed order, which is
    exactly where a body can be paired with its neighbour's mesh, so the
    check belongs here rather than in the constructor: the constructor
    sees one identity and cannot know it is the wrong one.
    """
    for other in (faceted, reference_mesh):
        for field_name in IDENTITY_FIELDS:
            expected = getattr(body, field_name)
            found = getattr(other, field_name)
            if expected != found:
                raise CadError(
                    f"{body.name}.{field_name}: the B-rep body and the mesh "
                    f"compared against it must be the same body, got "
                    f"{expected!r} and {found!r}"
                )


def body_evidence(
    body: BrepBody,
    smallest_radius_m: float | None,
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
        The body's smallest circular radius, which is the radius the
        chord deficit of the faceting is bounded at, or **``None`` where
        the body has no curved surface at all**. The caller must state
        which: a body with no curvature is faceted exactly, and bounding
        it by a chord deficit it does not have would make the check pass
        whatever happened.
    faceted
        The faceted closed mesh of the body.
    reference_mesh
        The tier-G1 mesh of the same body at the reference segment count.
    linear_deflection_m
        The mesher's linear deflection. Ignored when the body has no
        curved surface, because its faceting does not depend on it.
    segments
        The reference mesh segment count. Ignored likewise.

    Returns
    -------
    BodyEvidence
        The checked evidence.

    Raises
    ------
    CadError
        If the three bodies are not the same body, if a declared bound is
        violated, or if an argument of a bound is invalid.
    """
    _require_matching_identity(body, faceted, reference_mesh)
    faceted_volume = faceted.signed_volume_m3()
    reference_volume = reference_mesh.signed_volume_m3()
    analytic_volume = body.analytic_volume_m3
    deficit_bound, difference_bound = facet_bounds(
        smallest_radius_m, linear_deflection_m, segments
    )
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
        faceted_volume_deficit_bound=deficit_bound,
        reference_mesh_volume_m3=reference_volume,
        mesh_volume_relative_difference=abs(faceted_volume - reference_volume)
        / analytic_volume,
        mesh_volume_difference_bound=difference_bound,
    )


def assembly_evidence(
    bodies: tuple[BrepBody, ...],
    smallest_radii: tuple[float | None, ...],
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
        The smallest circular radius of each body, in the same order,
        with ``None`` for any body that has no curved surface. An
        assembly may mix the two.
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
