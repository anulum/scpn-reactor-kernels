# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — spherical bodies

"""Spherical bodies as profiles of revolution about ``z``.

A sphere is a body that closes on the axis at both poles, which is
exactly what
:func:`~scpn_reactor_kernels.geometry.profiles.closed_profiled_solid`
already tessellates. So this module adds no tessellation kernel for the
solid sphere: it adds the **profile**, and the one body a profile cannot
express — the spherical shell, whose cross-section changes from an
annulus to a full disc at the inner sphere's poles and is therefore not a
tube between two aligned profiles.

**The profile is sampled uniformly in polar angle, not in height.** Both
converge, but only the angular sampling converges cleanly: measured, its
volume deficit falls as the square of the ring count, the ratio between
successive halvings running 3.990, 3.998, 3.999, 4.000. Uniform sampling
in ``z`` crowds the samples where the surface is flat and starves them
where it turns fastest, and its deficit falls more slowly and less
regularly.

The angles come from
:func:`~scpn_reactor_kernels.geometry.trig.circle_points`, the same
deterministic kernel the unit circle uses, evaluated on twice the ring
count and read over its first half turn. That is not a convenience: it is
what makes the poles land on exactly ``±radius`` with a radius of exactly
zero, the equator on exactly the centre with a radius of exactly the
sphere's, and every value bit-identical to the native kernel.
"""

from __future__ import annotations

from typing import Final

from scpn_reactor_kernels.errors import GeometryError
from scpn_reactor_kernels.geometry.mesh import Face, Vertex
from scpn_reactor_kernels.geometry.profiles import Profile, closed_profiled_solid
from scpn_reactor_kernels.geometry.trig import circle_points
from scpn_reactor_kernels.validation import require_finite, require_positive

#: Fewest polar steps a sphere may carry. Two gives a profile of three
#: samples — the two poles and the equator — which is the fewest a body
#: closed at both ends can have, and tessellates to a bipyramid.
MIN_SPHERE_RINGS: Final = 2


def require_rings(rings: int) -> int:
    """Validate a polar step count.

    Parameters
    ----------
    rings
        Number of polar steps from one pole to the other.

    Returns
    -------
    int
        The validated count.

    Raises
    ------
    GeometryError
        If the count is below :data:`MIN_SPHERE_RINGS`. A count of one
        would put the two poles adjacent with no ring of positive radius
        between them, which is a segment and not a body.
    """
    if rings < MIN_SPHERE_RINGS:
        raise GeometryError(
            f"rings: must be at least {MIN_SPHERE_RINGS}, got {rings!r}"
        )
    return rings


def sphere_profile(radius_m: float, centre_z_m: float, rings: int) -> Profile:
    """Return the axial profile of a sphere, sampled in polar angle.

    Parameters
    ----------
    radius_m
        Sphere radius; strictly positive.
    centre_z_m
        Height of the sphere's centre on the axis; finite.
    rings
        Polar steps from pole to pole; at least
        :data:`MIN_SPHERE_RINGS`.

    Returns
    -------
    Profile
        ``rings + 1`` samples of strictly increasing height, the first at
        ``centre_z_m - radius_m`` and the last at ``centre_z_m +
        radius_m``, both with a radius of exactly zero.

    Raises
    ------
    GeometryError
        If the radius is non-finite or not positive, the centre is
        non-finite, or the ring count is below the minimum.
    """
    require_positive("radius_m", radius_m, GeometryError)
    require_finite("centre_z_m", centre_z_m, GeometryError)
    require_rings(rings)
    points = circle_points(2 * rings)
    profile = [
        (centre_z_m - radius_m * cosine, radius_m * sine)
        for cosine, sine in points[:rings]
    ]
    profile.append((centre_z_m + radius_m, 0.0))
    return tuple(profile)


def sphere_solid(
    radius_m: float, centre_z_m: float, segments: int, rings: int
) -> tuple[tuple[Vertex, ...], tuple[Face, ...]]:
    """Tessellate a closed sphere on the ``z`` axis.

    The profile of :func:`sphere_profile` revolved by
    :func:`~scpn_reactor_kernels.geometry.profiles.closed_profiled_solid`,
    which places one apex vertex at each pole rather than a degenerate
    ring.

    Parameters
    ----------
    radius_m
        Sphere radius; strictly positive.
    centre_z_m
        Height of the centre on the axis; finite.
    segments
        Circumferential segments; at least 8 and a multiple of 8.
    rings
        Polar steps from pole to pole; at least
        :data:`MIN_SPHERE_RINGS`.

    Returns
    -------
    (vertices, faces)
        ``(rings - 1) * segments + 2`` vertices and
        ``2 * (rings - 1) * segments`` outward-oriented faces.

    Raises
    ------
    GeometryError
        If any parameter is invalid.
    """
    return closed_profiled_solid(sphere_profile(radius_m, centre_z_m, rings), segments)


def spherical_shell(
    inner_radius_m: float,
    outer_radius_m: float,
    centre_z_m: float,
    segments: int,
    rings: int,
) -> tuple[tuple[Vertex, ...], tuple[Face, ...]]:
    """Tessellate the closed shell between two concentric spheres.

    The shell is **not** a tube between two aligned profiles, and cannot
    be built as one: below the inner sphere's poles its cross-section is
    an annulus, and above them a full disc, so the two surfaces do not
    stand over one another sample for sample. It is instead two closed
    surfaces — the outer sphere as built, and the inner sphere with every
    triangle reversed so that it faces the cavity.

    Parameters
    ----------
    inner_radius_m, outer_radius_m
        Cavity and outer radii; both strictly positive with
        ``outer_radius_m > inner_radius_m``.
    centre_z_m
        Height of the common centre on the axis; finite.
    segments
        Circumferential segments; at least 8 and a multiple of 8.
    rings
        Polar steps from pole to pole, used for both surfaces; at least
        :data:`MIN_SPHERE_RINGS`.

    Returns
    -------
    (vertices, faces)
        The outer surface's vertices then the inner surface's, and the
        outer faces then the inner faces reversed. Twice the counts of
        :func:`sphere_solid`.

    Raises
    ------
    GeometryError
        If either radius is invalid, the outer does not exceed the inner,
        or the centre, segment or ring counts are invalid.
    """
    require_positive("inner_radius_m", inner_radius_m, GeometryError)
    require_positive("outer_radius_m", outer_radius_m, GeometryError)
    if outer_radius_m <= inner_radius_m:
        raise GeometryError(
            "outer_radius_m: must exceed inner_radius_m, got "
            f"inner={inner_radius_m!r} outer={outer_radius_m!r}"
        )
    outer_vertices, outer_faces = sphere_solid(
        outer_radius_m, centre_z_m, segments, rings
    )
    inner_vertices, inner_faces = sphere_solid(
        inner_radius_m, centre_z_m, segments, rings
    )
    offset = len(outer_vertices)
    reversed_faces = tuple(
        (first + offset, third + offset, second + offset)
        for first, second, third in inner_faces
    )
    return outer_vertices + inner_vertices, outer_faces + reversed_faces
