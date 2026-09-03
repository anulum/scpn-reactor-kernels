# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — bodies whose radius varies along the axis

"""Surfaces of revolution through a sampled axial radius profile.

The primitives of :mod:`scpn_reactor_kernels.geometry.primitives` build
bodies of constant radius. Not every part of a machine is one. A magnetic
flux tube is widest where the field is weakest and narrowest where it is
strongest; a tapered liner, a horn, a conical transition and a bellows
envelope are all bodies whose radius is a function of ``z``. A device
repository must never re-implement geometry to draw them, so they are
here.

A *profile* is an ordered sequence of ``(z, radius)`` samples: at least
two, strictly increasing in ``z``, every radius strictly positive, every
value finite. The body is the surface of revolution through exactly those
samples, closed with end discs, and **linear between them**. That is the
whole contract, and it is deliberately narrow: this kernel interpolates
nothing beyond the straight line between two samples it was given, so a
record built on it can say what the surface is without appealing to a
smoothing rule nobody declared. A caller who wants a finer surface passes
finer samples.

The rings are the same deterministic circle points every other primitive
uses, in the same vertex and face order, so the native kernel reproduces
every coordinate bit for bit. The generalisation is exact in a second
sense as well: a two-sample profile of constant radius produces the
identical vertex and face streams as
:func:`~scpn_reactor_kernels.geometry.primitives.cylinder_solid`, and a
pair of such profiles the identical streams as
:func:`~scpn_reactor_kernels.geometry.primitives.annular_tube` — asserted
in the test suite, so a consumer that moves from a constant radius to a
profile keeps its digests when the shape is genuinely unchanged.

The closed forms of the resulting solid are elementary and exact, because
a linear profile makes the body a stack of conical frusta: the volume is
``sum (pi / 3) (r_i^2 + r_i r_{i+1} + r_{i+1}^2) (z_{i+1} - z_i)`` and the
lateral area is ``sum pi (r_i + r_{i+1}) l_i`` with the slant
``l_i = sqrt((r_{i+1} - r_i)^2 + (z_{i+1} - z_i)^2)``. They are provided
here so the tier-G2 evidence can check a B-rep of the same profile
against them exactly as it checks a cylinder or a tube.

Nothing here describes a device: the kernel knows a list of radii and a
list of heights.
"""

from __future__ import annotations

import math
from itertools import pairwise
from typing import Final

from scpn_reactor_kernels.errors import GeometryError
from scpn_reactor_kernels.geometry.mesh import Face, Vertex
from scpn_reactor_kernels.geometry.trig import unit_circle
from scpn_reactor_kernels.validation import require_finite, require_positive

#: Fewest samples a profile may carry: two, which is a frustum.
MIN_PROFILE_SAMPLES: Final = 2

#: One ``(z, radius)`` sample of an axial profile.
ProfileSample = tuple[float, float]
#: An ordered axial radius profile.
Profile = tuple[ProfileSample, ...]


def require_profile(name: str, profile: Profile) -> Profile:
    """Return an axial radius profile when it satisfies the contract.

    Parameters
    ----------
    name
        Field name reported in the rejection message.
    profile
        Candidate ``(z, radius)`` samples.

    Returns
    -------
    Profile
        The validated profile, unchanged.

    Raises
    ------
    GeometryError
        If the profile carries fewer than two samples, if any value is
        non-finite, if any radius is not strictly positive, or if the
        heights do not strictly increase. The rejection names the sample
        index so a caller can find the offending row.
    """
    if len(profile) < MIN_PROFILE_SAMPLES:
        raise GeometryError(
            f"{name}: must carry at least {MIN_PROFILE_SAMPLES} samples, got "
            f"{len(profile)!r}"
        )
    previous_z: float | None = None
    for index, sample in enumerate(profile):
        if len(sample) != 2:
            raise GeometryError(
                f"{name}[{index}]: must be a (z, radius) pair, got {sample!r}"
            )
        height, radius = sample
        require_finite(f"{name}[{index}].z", height, GeometryError)
        require_positive(f"{name}[{index}].radius", radius, GeometryError)
        if previous_z is not None and not height > previous_z:
            raise GeometryError(
                f"{name}[{index}].z: must exceed the previous sample, got "
                f"{height!r} after {previous_z!r}"
            )
        previous_z = height
    return profile


def require_aligned_profiles(
    inner_name: str, inner: Profile, outer_name: str, outer: Profile
) -> None:
    """Validate that two profiles form a well-defined annulus.

    Parameters
    ----------
    inner_name, outer_name
        Field names reported in the rejection messages.
    inner, outer
        Validated profiles of the bore and of the outer surface.

    Raises
    ------
    GeometryError
        If the two profiles do not carry the same number of samples, if a
        pair of samples does not sit at the same height, or if an outer
        radius does not exceed its inner radius. Sampling the two surfaces
        at different heights would leave the annulus undefined between
        them, so it is refused rather than interpolated.
    """
    if len(inner) != len(outer):
        raise GeometryError(
            f"{outer_name}: must carry the same number of samples as "
            f"{inner_name}, got {len(outer)!r} against {len(inner)!r}"
        )
    for index, (inner_sample, outer_sample) in enumerate(
        zip(inner, outer, strict=True)
    ):
        inner_z, inner_radius = inner_sample
        outer_z, outer_radius = outer_sample
        if inner_z != outer_z:
            raise GeometryError(
                f"{outer_name}[{index}].z: must equal {inner_name}[{index}].z, got "
                f"{outer_z!r} against {inner_z!r}"
            )
        if outer_radius <= inner_radius:
            raise GeometryError(
                f"{outer_name}[{index}].radius: must exceed "
                f"{inner_name}[{index}].radius, got {outer_radius!r} <= "
                f"{inner_radius!r}"
            )


def _ring(
    radius: float, height: float, circle: tuple[tuple[float, float], ...]
) -> list[Vertex]:
    """Scale the unit circle to one ring of vertices at a height."""
    return [(radius * cosine, radius * sine, height) for cosine, sine in circle]


def _side_faces(lower: int, upper: int, count: int) -> list[Face]:
    """Return the outward-oriented quads between two rings, split in two."""
    faces: list[Face] = []
    for index in range(count):
        following = (index + 1) % count
        faces.append((lower + index, lower + following, upper + following))
        faces.append((lower + index, upper + following, upper + index))
    return faces


def profiled_solid(
    profile: Profile, segments: int
) -> tuple[tuple[Vertex, ...], tuple[Face, ...]]:
    """Tessellate a closed solid of revolution through an axial profile.

    Parameters
    ----------
    profile
        Ordered ``(z, radius)`` samples; at least two, strictly increasing
        in ``z``, radii strictly positive.
    segments
        Circumferential segments; at least 8 and a multiple of 8.

    Returns
    -------
    (vertices, faces)
        ``samples * segments + 2`` vertices (one ring per sample in
        profile order, then the bottom and top disc centres) and
        ``(2 * (samples - 1) + 2) * segments`` outward-oriented faces
        (the side bands in profile order, then the bottom and top fans).

    Raises
    ------
    GeometryError
        If the profile or the segment count is invalid.
    """
    require_profile("profile", profile)
    circle = unit_circle(segments)
    count = len(circle)
    vertices: list[Vertex] = []
    for height, radius in profile:
        vertices.extend(_ring(radius, height, circle))
    vertices.append((0.0, 0.0, profile[0][0]))
    vertices.append((0.0, 0.0, profile[-1][0]))
    bottom_centre = len(profile) * count
    top_centre = bottom_centre + 1
    last_ring = (len(profile) - 1) * count
    faces: list[Face] = []
    for band in range(len(profile) - 1):
        faces.extend(_side_faces(band * count, (band + 1) * count, count))
    for index in range(count):
        following = (index + 1) % count
        faces.append((bottom_centre, following, index))
    for index in range(count):
        following = (index + 1) % count
        faces.append((top_centre, last_ring + index, last_ring + following))
    return tuple(vertices), tuple(faces)


def profiled_tube(
    inner_profile: Profile, outer_profile: Profile, segments: int
) -> tuple[tuple[Vertex, ...], tuple[Face, ...]]:
    """Tessellate a closed tube of revolution between two axial profiles.

    Parameters
    ----------
    inner_profile, outer_profile
        Ordered ``(z, radius)`` samples of the bore and of the outer
        surface; same length, pairwise at the same heights, every outer
        radius strictly larger than its inner radius.
    segments
        Circumferential segments; at least 8 and a multiple of 8.

    Returns
    -------
    (vertices, faces)
        ``2 * samples * segments`` vertices (the outer rings in profile
        order, then the inner rings) and
        ``(4 * (samples - 1) + 4) * segments`` outward-oriented faces (the
        outer bands, the inner bands facing the bore, then the bottom and
        top annuli).

    Raises
    ------
    GeometryError
        If either profile, their alignment, or the segment count is
        invalid.
    """
    require_profile("inner_profile", inner_profile)
    require_profile("outer_profile", outer_profile)
    require_aligned_profiles(
        "inner_profile", inner_profile, "outer_profile", outer_profile
    )
    circle = unit_circle(segments)
    count = len(circle)
    samples = len(inner_profile)
    vertices: list[Vertex] = []
    for height, radius in outer_profile:
        vertices.extend(_ring(radius, height, circle))
    for height, radius in inner_profile:
        vertices.extend(_ring(radius, height, circle))
    inner_base = samples * count
    outer_last = (samples - 1) * count
    inner_last = inner_base + outer_last
    faces: list[Face] = []
    for band in range(samples - 1):
        faces.extend(_side_faces(band * count, (band + 1) * count, count))
    for band in range(samples - 1):
        lower = inner_base + band * count
        upper = inner_base + (band + 1) * count
        for index in range(count):
            following = (index + 1) % count
            faces.append((lower + index, upper + following, lower + following))
            faces.append((lower + index, upper + index, upper + following))
    for index in range(count):
        following = (index + 1) % count
        faces.append((index, inner_base + index, inner_base + following))
        faces.append((index, inner_base + following, following))
    for index in range(count):
        following = (index + 1) % count
        faces.append(
            (outer_last + index, outer_last + following, inner_last + following)
        )
        faces.append((outer_last + index, inner_last + following, inner_last + index))
    return tuple(vertices), tuple(faces)


def profile_volume_m3(profile: Profile) -> float:
    """Return the exact volume of the solid of revolution of a profile.

    Parameters
    ----------
    profile
        Validated ``(z, radius)`` samples.

    Returns
    -------
    float
        ``sum (pi / 3) (r_i^2 + r_i r_{i+1} + r_{i+1}^2) (z_{i+1} - z_i)``
        — the closed form of a stack of conical frusta, which is exactly
        what a linear profile is. Not an approximation of the tessellated
        body: the tessellation approximates this.

    Raises
    ------
    GeometryError
        If the profile is invalid.
    """
    require_profile("profile", profile)
    total = 0.0
    for (low_z, low_radius), (high_z, high_radius) in pairwise(profile):
        total += (
            (math.pi / 3.0)
            * (
                low_radius * low_radius
                + low_radius * high_radius
                + high_radius * high_radius
            )
            * (high_z - low_z)
        )
    return total


def profile_lateral_area_m2(profile: Profile) -> float:
    """Return the exact lateral area of the surface of revolution.

    Parameters
    ----------
    profile
        Validated ``(z, radius)`` samples.

    Returns
    -------
    float
        ``sum pi (r_i + r_{i+1}) l_i`` with the slant
        ``l_i = sqrt((r_{i+1} - r_i)^2 + (z_{i+1} - z_i)^2)``; the end
        discs are not included, so a caller composes the closed area as
        it needs it.

    Raises
    ------
    GeometryError
        If the profile is invalid.
    """
    require_profile("profile", profile)
    total = 0.0
    for (low_z, low_radius), (high_z, high_radius) in pairwise(profile):
        delta_radius = high_radius - low_radius
        delta_z = high_z - low_z
        slant = math.sqrt(delta_radius * delta_radius + delta_z * delta_z)
        total += math.pi * (low_radius + high_radius) * slant
    return total
