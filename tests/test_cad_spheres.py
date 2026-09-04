# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — B-rep spherical body tests

"""Every branch of the B-rep spherical bodies.

Skipped hermetically when the optional CAD back-end is absent, which is
how every other tier-G2 suite in this library behaves.
"""

from __future__ import annotations

import functools
import math

import pytest

from scpn_reactor_kernels.cad.solids import MEASURE_TOLERANCE, BrepBody
from scpn_reactor_kernels.cad.spheres import sphere_brep, spherical_shell_brep
from scpn_reactor_kernels.errors import GeometryError
from scpn_reactor_kernels.geometry import profile_volume_m3
from scpn_reactor_kernels.geometry.spheres import sphere_profile

pytest.importorskip("cadquery")

RINGS = 16


@functools.cache
def sphere() -> BrepBody:
    """Build and cache a reference sphere body."""
    return sphere_brep(1.0, 0.0, RINGS, "sphere", "shell", "steel")


@functools.cache
def shell() -> BrepBody:
    """Build and cache a reference spherical shell body."""
    return spherical_shell_brep(0.6, 1.0, 0.0, RINGS, "shell", "shell", "steel")


def test_the_sphere_matches_its_analytic_references() -> None:
    """The revolve reproduces the frustum stack of the profile it was built from.

    Measured, the volume and area errors are zero at this ring count and
    of order 1e-16 at sixty-four, both far inside the library's declared
    tolerance.
    """
    body = sphere()
    assert body.volume_relative_error() < MEASURE_TOLERANCE
    assert body.surface_area_relative_error() < MEASURE_TOLERANCE
    assert body.analytic_volume_m3 == profile_volume_m3(sphere_profile(1.0, 0.0, RINGS))


def test_the_sphere_carries_no_disc_at_either_pole() -> None:
    """A pole is a point, so the closed-profile builder appends no axis return.

    The analytic area is therefore the lateral sum alone, which is what
    makes it equal to the tessellated body's own surface.
    """
    profile = sphere_profile(1.0, 0.0, RINGS)
    assert profile[0][1] == 0.0
    assert profile[-1][1] == 0.0
    assert sphere().analytic_surface_area_m2 > 0.0


def test_the_shell_matches_its_analytic_references() -> None:
    """The two on-axis segments of its polyline sweep nothing, and it shows.

    The shell's generating polyline runs up the outer profile and back
    down the inner one, joined along the axis at both ends. The back-end
    was measured to revolve that exactly: the volume equals the difference
    of the two frustum stacks with no allowance for the construction.
    """
    body = shell()
    assert body.volume_relative_error() < MEASURE_TOLERANCE
    assert body.surface_area_relative_error() < MEASURE_TOLERANCE
    assert body.analytic_volume_m3 == pytest.approx(
        profile_volume_m3(sphere_profile(1.0, 0.0, RINGS))
        - profile_volume_m3(sphere_profile(0.6, 0.0, RINGS))
    )


def test_the_shell_encloses_less_than_the_sphere_that_contains_it() -> None:
    """A cavity removes volume and adds surface."""
    assert shell().volume_m3 < sphere().volume_m3
    assert shell().surface_area_m2 > sphere().surface_area_m2


def test_a_shell_of_a_vanishing_cavity_approaches_the_solid_sphere() -> None:
    """The cavity is the only difference between the two bodies.

    Measured across three shrinking cavities, the shell's volume rises
    towards the sphere's and the gap falls as the cube of the cavity
    radius, which is what a sphere's volume does.
    """
    solid = sphere().analytic_volume_m3
    previous = None
    for cavity in (0.4, 0.2, 0.1):
        gap = (
            solid
            - spherical_shell_brep(
                cavity, 1.0, 0.0, RINGS, "s", "shell", "steel"
            ).analytic_volume_m3
        )
        assert 0.0 < gap < solid
        if previous is not None:
            assert previous / gap == pytest.approx(8.0, rel=1e-9)
        previous = gap


@pytest.mark.parametrize(
    ("radius", "centre", "rings", "match"),
    [
        (0.0, 0.0, RINGS, "radius_m"),
        (-1.0, 0.0, RINGS, "radius_m"),
        (1.0, math.inf, RINGS, "centre_z_m"),
        (1.0, 0.0, 1, "rings"),
    ],
)
def test_the_sphere_refuses_by_name(
    radius: float, centre: float, rings: int, match: str
) -> None:
    """The geometry guards run before any back-end call."""
    with pytest.raises(GeometryError, match=match):
        sphere_brep(radius, centre, rings, "s", "shell", "steel")


@pytest.mark.parametrize(
    ("inner", "outer", "rings", "match"),
    [
        (0.0, 1.0, RINGS, "inner_radius_m"),
        (1.0, 0.0, RINGS, "outer_radius_m"),
        (1.0, 1.0, RINGS, "must exceed"),
        (1.5, 1.0, RINGS, "must exceed"),
        (0.5, 1.0, 1, "rings"),
    ],
)
def test_the_shell_refuses_by_name(
    inner: float, outer: float, rings: int, match: str
) -> None:
    """Radii that do not nest are refused before the revolve is attempted."""
    with pytest.raises(GeometryError, match=match):
        spherical_shell_brep(inner, outer, 0.0, rings, "s", "shell", "steel")


def test_the_bodies_carry_their_declared_identity() -> None:
    """Name, role and material token pass through unchanged."""
    body = spherical_shell_brep(0.5, 1.0, 2.0, RINGS, "capsule", "ablator", "plastic")
    assert (body.name, body.role, body.material_identifier) == (
        "capsule",
        "ablator",
        "plastic",
    )
