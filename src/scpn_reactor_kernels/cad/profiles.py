# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — B-rep bodies whose radius varies along the axis

"""B-rep solids of revolution through a sampled axial radius profile.

The tier-G2 twin of :mod:`scpn_reactor_kernels.geometry.profiles`. The
profile contract is that module's, unchanged: an ordered sequence of
``(z, radius)`` samples, at least two, strictly increasing in ``z``, radii
strictly positive, and the surface linear between samples. The B-rep is
built by revolving the polyline through those samples about the axis, so
the two tiers describe the same body — the tessellation is the inscribed
approximation of exactly this solid.

The analytic closed forms carried by the body are the geometry group's
frustum-stack sums, which are exact for a linear profile, plus the end
discs. They are not an approximation of anything: they are what the
evidence kernel checks the pinned third-party B-rep kernel against, at
the same declared relative tolerance the cylinder and the tube use.

Nothing here describes a device.
"""

from __future__ import annotations

from typing import Any

from scpn_reactor_kernels.cad._backend import load_backend
from scpn_reactor_kernels.cad.solids import BrepBody
from scpn_reactor_kernels.errors import CadError, GeometryError
from scpn_reactor_kernels.geometry.profiles import (
    Profile,
    profile_lateral_area_m2,
    profile_volume_m3,
    require_aligned_profiles,
    require_closed_profile,
    require_profile,
)

#: Full turn of the revolution, in degrees.
FULL_TURN_DEGREES = 360.0


def _validated(name: str, profile: Profile) -> Profile:
    """Return a profile validated under the CAD error type.

    Parameters
    ----------
    name
        Field name reported in the rejection message.
    profile
        Candidate samples.

    Returns
    -------
    Profile
        The validated profile.

    Raises
    ------
    CadError
        Carrying the geometry group's message, so a caller sees one
        contract stated once.
    """
    try:
        return require_profile(name, profile)
    except GeometryError as exc:
        raise CadError(str(exc)) from exc


def _validated_closed(name: str, profile: Profile) -> Profile:
    """Return a closed profile validated under the CAD error type.

    Parameters
    ----------
    name
        Field name reported in the rejection message.
    profile
        Candidate samples.

    Returns
    -------
    Profile
        The validated profile.

    Raises
    ------
    CadError
        Carrying the geometry group's message, so a caller sees one
        contract stated once.
    """
    try:
        return require_closed_profile(name, profile)
    except GeometryError as exc:
        raise CadError(str(exc)) from exc


def _disc_area(radius: float) -> float:
    """Return the area of a disc of a given radius."""
    return 3.141592653589793 * radius * radius


def revolved(points: list[tuple[float, float]]) -> Any:
    """Revolve a closed polyline in the ``xz`` plane about the ``z`` axis.

    Shared with :mod:`scpn_reactor_kernels.cad.spheres`, which needs a
    polyline no profile can express. It carries no leading underscore for
    that reason and is still not part of the package's public surface.

    Parameters
    ----------
    points
        ``(radius, z)`` vertices of the generating polyline, in order; the
        polyline is closed by the constructor.

    Returns
    -------
    Any
        The CadQuery ``Shape`` of the resulting solid.
    """
    cadquery = load_backend("cadquery")
    return (
        cadquery.Workplane("XZ")
        .polyline(points)
        .close()
        .revolve(FULL_TURN_DEGREES, (0, 0, 0), (0, 1, 0))
        .val()
    )


def profiled_solid_brep(
    profile: Profile,
    name: str,
    role: str,
    material_identifier: str,
) -> BrepBody:
    """Build a closed B-rep solid of revolution through an axial profile.

    Parameters
    ----------
    profile
        Ordered ``(z, radius)`` samples; at least two, strictly increasing
        in ``z``, radii strictly positive.
    name, role, material_identifier
        Body identity.

    Returns
    -------
    BrepBody
        The solid with the exact frustum-stack volume and the exact area
        (lateral sum plus the two end discs) as its analytic references.

    Raises
    ------
    CadError
        If the profile is invalid;
        :class:`~scpn_reactor_kernels.errors.CadUnavailableError` if the
        back-end is absent.
    """
    samples = _validated("profile", profile)
    points = [(radius, height) for height, radius in samples]
    points.append((0.0, samples[-1][0]))
    points.append((0.0, samples[0][0]))
    return BrepBody(
        name=name,
        role=role,
        material_identifier=material_identifier,
        shape=revolved(points),
        analytic_volume_m3=profile_volume_m3(samples),
        analytic_surface_area_m2=profile_lateral_area_m2(samples)
        + _disc_area(samples[0][1])
        + _disc_area(samples[-1][1]),
    )


def closed_profiled_solid_brep(
    profile: Profile,
    name: str,
    role: str,
    material_identifier: str,
) -> BrepBody:
    """Build a B-rep solid of revolution that closes on the axis at a pole.

    The generating polyline is the profile itself. Where an end already
    sits on the axis there is nothing to return along, so no axis point is
    appended there: appending one would repeat a vertex and leave the
    polyline with a zero-length segment. An end of positive radius keeps
    its return point and therefore its disc.

    The analytic references need no special case. The frustum-stack volume
    reduces to the cone volume at a pole on its own, and a pole's disc has
    zero radius and therefore zero area, so the same two sums serve both
    kinds of body.

    Parameters
    ----------
    profile
        Ordered ``(z, radius)`` samples; strictly increasing in ``z``, at
        least one end radius exactly zero, every interior radius strictly
        positive.
    name, role, material_identifier
        Body identity.

    Returns
    -------
    BrepBody
        The solid with the exact frustum-stack volume and the exact area
        (lateral sum plus the disc of each end that has one) as its
        analytic references.

    Raises
    ------
    CadError
        If the profile is invalid;
        :class:`~scpn_reactor_kernels.errors.CadUnavailableError` if the
        back-end is absent.
    """
    samples = _validated_closed("profile", profile)
    points = [(radius, height) for height, radius in samples]
    if samples[-1][1] != 0.0:
        points.append((0.0, samples[-1][0]))
    if samples[0][1] != 0.0:
        points.append((0.0, samples[0][0]))
    return BrepBody(
        name=name,
        role=role,
        material_identifier=material_identifier,
        shape=revolved(points),
        analytic_volume_m3=profile_volume_m3(samples),
        analytic_surface_area_m2=profile_lateral_area_m2(samples)
        + _disc_area(samples[0][1])
        + _disc_area(samples[-1][1]),
    )


def profiled_tube_brep(
    inner_profile: Profile,
    outer_profile: Profile,
    name: str,
    role: str,
    material_identifier: str,
) -> BrepBody:
    """Build a closed B-rep tube of revolution between two axial profiles.

    Parameters
    ----------
    inner_profile, outer_profile
        Ordered ``(z, radius)`` samples of the bore and of the outer
        surface; same length, pairwise at the same heights, every outer
        radius strictly larger than its inner radius.
    name, role, material_identifier
        Body identity.

    Returns
    -------
    BrepBody
        The solid with the exact difference of the two frustum-stack
        volumes and the exact area (both lateral sums plus the two end
        annuli) as its analytic references.

    Raises
    ------
    CadError
        If either profile or their alignment is invalid;
        :class:`~scpn_reactor_kernels.errors.CadUnavailableError` if the
        back-end is absent.
    """
    inner = _validated("inner_profile", inner_profile)
    outer = _validated("outer_profile", outer_profile)
    try:
        require_aligned_profiles("inner_profile", inner, "outer_profile", outer)
    except GeometryError as exc:
        raise CadError(str(exc)) from exc
    points = [(radius, height) for height, radius in outer]
    points.extend((radius, height) for height, radius in reversed(inner))
    first_annulus = _disc_area(outer[0][1]) - _disc_area(inner[0][1])
    last_annulus = _disc_area(outer[-1][1]) - _disc_area(inner[-1][1])
    return BrepBody(
        name=name,
        role=role,
        material_identifier=material_identifier,
        shape=revolved(points),
        analytic_volume_m3=profile_volume_m3(outer) - profile_volume_m3(inner),
        analytic_surface_area_m2=profile_lateral_area_m2(outer)
        + profile_lateral_area_m2(inner)
        + first_annulus
        + last_annulus,
    )
