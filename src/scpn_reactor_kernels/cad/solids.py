# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — B-rep solids of the analytic primitives

"""B-rep solids (CadQuery/OCP) of the same primitives as the tier-G1 meshes.

Every constructor takes the argument list of its tessellating twin in
:mod:`scpn_reactor_kernels.geometry.primitives` (radius or radii, axial
extent) plus the body identity (name, role, material token) and returns a
:class:`BrepBody` whose OpenCASCADE shape is an exact solid of revolution.
The body carries the analytic volume and surface area of the primitive
(``pi r^2 h`` and ``2 pi r h + 2 pi r^2`` for the cylinder;
``pi (r_o^2 - r_i^2) h`` and ``2 pi (r_i + r_o) h + 2 pi (r_o^2 - r_i^2)``
for the tube) so the B-rep kernel's own measures can be checked against
them. OpenCASCADE is a pinned third-party kernel: its measures are checked
against the analytic forms within a declared relative tolerance, never
claimed bit-exact. Nothing here describes a device.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Final

from scpn_reactor_kernels.cad._backend import load_backend
from scpn_reactor_kernels.errors import CadError
from scpn_reactor_kernels.validation import require_finite, require_positive

#: Declared relative tolerance between the B-rep measures and the analytic forms.
MEASURE_TOLERANCE: Final = 1.0e-9

Bounds = tuple[tuple[float, float, float], tuple[float, float, float]]


def require_extent(z_low_m: float, z_high_m: float) -> tuple[float, float]:
    """Return the axial extent when finite and increasing.

    Parameters
    ----------
    z_low_m, z_high_m
        Axial extent.

    Returns
    -------
    (float, float)
        The validated extent.

    Raises
    ------
    CadError
        If either bound is non-finite or ``z_high_m <= z_low_m``.
    """
    try:
        require_finite("z_low_m", z_low_m)
        require_finite("z_high_m", z_high_m)
    except ValueError as exc:
        raise CadError(str(exc)) from exc
    if z_high_m <= z_low_m:
        raise CadError(
            f"z_high_m: must exceed z_low_m, got {z_high_m!r} <= {z_low_m!r}"
        )
    return z_low_m, z_high_m


def require_radius(name: str, value: float) -> float:
    """Return a radius when finite and strictly positive.

    Parameters
    ----------
    name
        Field name reported in the rejection message.
    value
        Radius under validation.

    Returns
    -------
    float
        The validated radius.

    Raises
    ------
    CadError
        If the radius is non-finite or not strictly positive.
    """
    try:
        return require_positive(name, value)
    except ValueError as exc:
        raise CadError(str(exc)) from exc


@dataclass(frozen=True)
class BrepBody:
    """One named B-rep solid with its analytic reference measures.

    Parameters
    ----------
    name
        Node name of the body; non-empty.
    role
        Declared role token of the body.
    material_identifier
        Declared material token; no material property is carried.
    shape
        The CadQuery ``Shape`` (an OpenCASCADE solid).
    analytic_volume_m3
        Volume of the primitive in closed form.
    analytic_surface_area_m2
        Surface area of the primitive in closed form.

    Raises
    ------
    CadError
        If a name is empty.
    """

    name: str
    role: str
    material_identifier: str
    shape: Any
    analytic_volume_m3: float
    analytic_surface_area_m2: float

    def __post_init__(self) -> None:
        """Validate the body identity.

        Raises
        ------
        CadError
            If a name is empty.
        """
        for field_name, value in (
            ("name", self.name),
            ("role", self.role),
            ("material_identifier", self.material_identifier),
        ):
            if not value:
                raise CadError(f"{field_name}: must be non-empty")

    @property
    def volume_m3(self) -> float:
        """Volume measured by the B-rep kernel."""
        return float(self.shape.Volume())

    @property
    def surface_area_m2(self) -> float:
        """Surface area measured by the B-rep kernel."""
        return float(self.shape.Area())

    def bounding_box_m(self) -> Bounds:
        """Axis-aligned bounding box measured by the B-rep kernel.

        Returns
        -------
        Bounds
            Component-wise minimum and maximum.
        """
        box = self.shape.BoundingBox()
        return (
            (float(box.xmin), float(box.ymin), float(box.zmin)),
            (float(box.xmax), float(box.ymax), float(box.zmax)),
        )

    def volume_relative_error(self) -> float:
        """Relative difference between the measured and the analytic volume.

        Returns
        -------
        float
            ``|V_brep - V_analytic| / V_analytic``.
        """
        return abs(self.volume_m3 - self.analytic_volume_m3) / self.analytic_volume_m3

    def surface_area_relative_error(self) -> float:
        """Relative difference between the measured and the analytic area.

        Returns
        -------
        float
            ``|A_brep - A_analytic| / A_analytic``.
        """
        return (
            abs(self.surface_area_m2 - self.analytic_surface_area_m2)
            / self.analytic_surface_area_m2
        )

    def summary_record(self) -> dict[str, Any]:
        """Project the body summary to a JSON-serialisable record.

        Returns
        -------
        dict[str, Any]
            Identity, measures, analytic references, relative errors and
            the bounding box.
        """
        low, high = self.bounding_box_m()
        return {
            "name": self.name,
            "role": self.role,
            "material_identifier": self.material_identifier,
            "volume_m3": self.volume_m3,
            "surface_area_m2": self.surface_area_m2,
            "analytic_volume_m3": self.analytic_volume_m3,
            "analytic_surface_area_m2": self.analytic_surface_area_m2,
            "volume_relative_error": self.volume_relative_error(),
            "surface_area_relative_error": self.surface_area_relative_error(),
            "bounding_box_min_m": list(low),
            "bounding_box_max_m": list(high),
        }


def _workplane(z_low_m: float) -> Any:
    cadquery = load_backend("cadquery")
    return cadquery.Workplane("XY").workplane(offset=z_low_m)


def cylinder_solid_brep(
    radius_m: float,
    z_low_m: float,
    z_high_m: float,
    name: str,
    role: str,
    material_identifier: str,
) -> BrepBody:
    """Build a closed solid cylinder on the ``z`` axis.

    Parameters
    ----------
    radius_m
        Cylinder radius; strictly positive.
    z_low_m, z_high_m
        Axial extent; ``z_high_m > z_low_m``.
    name, role, material_identifier
        Body identity.

    Returns
    -------
    BrepBody
        The solid with its analytic volume ``pi r^2 h`` and area
        ``2 pi r h + 2 pi r^2``.

    Raises
    ------
    CadError
        If an argument is invalid; :class:`CadUnavailableError` if the
        back-end is absent.
    """
    radius = require_radius("radius_m", radius_m)
    low, high = require_extent(z_low_m, z_high_m)
    height = high - low
    shape = _workplane(low).circle(radius).extrude(height).val()
    return BrepBody(
        name=name,
        role=role,
        material_identifier=material_identifier,
        shape=shape,
        analytic_volume_m3=math.pi * radius * radius * height,
        analytic_surface_area_m2=2.0 * math.pi * radius * height
        + 2.0 * math.pi * radius * radius,
    )


def annular_tube_brep(
    inner_radius_m: float,
    outer_radius_m: float,
    z_low_m: float,
    z_high_m: float,
    name: str,
    role: str,
    material_identifier: str,
) -> BrepBody:
    """Build a closed annular tube (hollow cylinder) on the ``z`` axis.

    Parameters
    ----------
    inner_radius_m, outer_radius_m
        Bore and outer radii; both strictly positive with
        ``outer_radius_m > inner_radius_m``.
    z_low_m, z_high_m
        Axial extent; ``z_high_m > z_low_m``.
    name, role, material_identifier
        Body identity.

    Returns
    -------
    BrepBody
        The solid with its analytic volume ``pi (r_o^2 - r_i^2) h`` and
        area ``2 pi (r_i + r_o) h + 2 pi (r_o^2 - r_i^2)``.

    Raises
    ------
    CadError
        If an argument is invalid; :class:`CadUnavailableError` if the
        back-end is absent.
    """
    inner = require_radius("inner_radius_m", inner_radius_m)
    outer = require_radius("outer_radius_m", outer_radius_m)
    if outer <= inner:
        raise CadError(
            f"outer_radius_m: must exceed inner_radius_m, got {outer!r} <= {inner!r}"
        )
    low, high = require_extent(z_low_m, z_high_m)
    height = high - low
    shape = _workplane(low).circle(outer).circle(inner).extrude(height).val()
    ring = outer * outer - inner * inner
    return BrepBody(
        name=name,
        role=role,
        material_identifier=material_identifier,
        shape=shape,
        analytic_volume_m3=math.pi * ring * height,
        analytic_surface_area_m2=2.0 * math.pi * (inner + outer) * height
        + 2.0 * math.pi * ring,
    )
