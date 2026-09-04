# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — B-rep spherical bodies

"""Exact solids of the spherical bodies.

The tier-G1 module explains why a sphere needs no tessellation kernel of
its own and a shell does. The same split holds here: the solid sphere is
its profile handed to
:func:`~scpn_reactor_kernels.cad.profiles.closed_profiled_solid_brep`,
and the shell is a revolve of a polyline this library did not have a
shape for.

**The shell's generating polyline touches the axis along two segments.**
It runs up the outer sphere's profile from pole to pole, then back down
the inner sphere's, and the two ends are joined along the axis because
that is where the cavity's poles sit inside the outer body. Those
segments sweep nothing, and the back-end was measured to accept them: the
revolved volume equals the difference of the two frustum stacks exactly,
not approximately, so the analytic references need no allowance for the
construction.

Both bodies are polyhedra of revolution, not ideal spheres, and their
analytic references are the frustum stacks of the profiles actually
built. A caller comparing either to ``4/3 pi r^3`` would be comparing two
different solids.
"""

from __future__ import annotations

from scpn_reactor_kernels.cad.profiles import (
    closed_profiled_solid_brep,
    revolved,
)
from scpn_reactor_kernels.cad.solids import BrepBody
from scpn_reactor_kernels.errors import GeometryError
from scpn_reactor_kernels.geometry.profiles import (
    profile_lateral_area_m2,
    profile_volume_m3,
)
from scpn_reactor_kernels.geometry.spheres import sphere_profile
from scpn_reactor_kernels.validation import require_positive


def sphere_brep(
    radius_m: float,
    centre_z_m: float,
    rings: int,
    name: str,
    role: str,
    material_identifier: str,
) -> BrepBody:
    """Build the exact solid of a sphere's profile of revolution.

    Parameters
    ----------
    radius_m
        Sphere radius; strictly positive.
    centre_z_m
        Height of the centre on the axis; finite.
    rings
        Polar steps from pole to pole; at least
        :data:`~scpn_reactor_kernels.geometry.spheres.MIN_SPHERE_RINGS`.
    name, role, material_identifier
        Body identity.

    Returns
    -------
    BrepBody
        The solid with the frustum-stack volume and lateral area of its
        profile as its analytic references. Both poles sit on the axis,
        so neither end carries a disc.

    Raises
    ------
    GeometryError
        If the radius, the centre or the ring count is invalid.
    CadError
        If the back-end refuses the revolve;
        :class:`~scpn_reactor_kernels.errors.CadUnavailableError` if the
        back-end is absent.
    """
    return closed_profiled_solid_brep(
        sphere_profile(radius_m, centre_z_m, rings), name, role, material_identifier
    )


def spherical_shell_brep(
    inner_radius_m: float,
    outer_radius_m: float,
    centre_z_m: float,
    rings: int,
    name: str,
    role: str,
    material_identifier: str,
) -> BrepBody:
    """Build the exact solid between two concentric spheres.

    Parameters
    ----------
    inner_radius_m, outer_radius_m
        Cavity and outer radii; both strictly positive with
        ``outer_radius_m > inner_radius_m``.
    centre_z_m
        Height of the common centre on the axis; finite.
    rings
        Polar steps from pole to pole, used for both surfaces; at least
        :data:`~scpn_reactor_kernels.geometry.spheres.MIN_SPHERE_RINGS`.
    name, role, material_identifier
        Body identity.

    Returns
    -------
    BrepBody
        The solid whose analytic volume is the difference of the two
        frustum stacks and whose analytic area is the sum of their
        lateral areas. Neither surface carries a disc: all four poles sit
        on the axis.

    Raises
    ------
    GeometryError
        If either radius, the centre or the ring count is invalid, or the
        outer radius does not exceed the inner. The radii are validated
        here by their own names rather than left to the profile builder,
        which would report both of them as ``radius_m`` and make the two
        tiers refuse the same input differently.
    CadError
        If the back-end refuses the revolve;
        :class:`~scpn_reactor_kernels.errors.CadUnavailableError` if the
        back-end is absent.
    """
    require_positive("inner_radius_m", inner_radius_m, GeometryError)
    require_positive("outer_radius_m", outer_radius_m, GeometryError)
    if outer_radius_m <= inner_radius_m:
        raise GeometryError(
            "outer_radius_m: must exceed inner_radius_m, got "
            f"inner={inner_radius_m!r} outer={outer_radius_m!r}"
        )
    outer = sphere_profile(outer_radius_m, centre_z_m, rings)
    inner = sphere_profile(inner_radius_m, centre_z_m, rings)
    points = [(radius, height) for height, radius in outer]
    points.extend((radius, height) for height, radius in reversed(inner))
    return BrepBody(
        name=name,
        role=role,
        material_identifier=material_identifier,
        shape=revolved(points),
        analytic_volume_m3=profile_volume_m3(outer) - profile_volume_m3(inner),
        analytic_surface_area_m2=profile_lateral_area_m2(outer)
        + profile_lateral_area_m2(inner),
    )
