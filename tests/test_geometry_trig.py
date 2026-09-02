# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — deterministic trigonometry tests

"""Accuracy, exact symmetry and refusal paths of the vendored unit circle."""

from __future__ import annotations

import math

import pytest

from scpn_reactor_kernels.errors import GeometryError
from scpn_reactor_kernels.geometry import (
    MIN_SEGMENTS,
    SEGMENT_MULTIPLE,
    cosine_polynomial,
    require_segments,
    sine_polynomial,
    unit_circle,
)

LIBM_TOLERANCE = 1.0e-15


@pytest.mark.parametrize("segments", [8, 16, 24, 64, 1024, 4096])
def test_unit_circle_tracks_libm_within_tolerance(segments: int) -> None:
    """Every point agrees with math.cos/math.sin to the stated tolerance."""
    points = unit_circle(segments)
    assert len(points) == segments
    for index, (cosine, sine) in enumerate(points):
        angle = 2.0 * math.pi * index / segments
        assert abs(cosine - math.cos(angle)) <= LIBM_TOLERANCE
        assert abs(sine - math.sin(angle)) <= LIBM_TOLERANCE
        assert abs(cosine * cosine + sine * sine - 1.0) <= 4.0e-16


@pytest.mark.parametrize("segments", [8, 16, 32])
def test_quadrant_points_are_exact(segments: int) -> None:
    """Points at multiples of pi/2 are exactly 0 and ±1 by symmetry."""
    points = unit_circle(segments)
    quarter = segments // 4
    assert points[0] == (1.0, 0.0)
    assert points[quarter] == (0.0, 1.0)
    assert points[2 * quarter] == (-1.0, 0.0)
    assert points[3 * quarter] == (0.0, -1.0)
    eighth = segments // 8
    cosine, sine = points[eighth]
    assert abs(cosine - sine) <= 2.0e-16


def test_symmetry_is_exact_across_quadrants() -> None:
    """Every quadrant is a sign/swap image of the first, bit for bit."""
    points = unit_circle(64)
    quarter = 16
    for index in range(quarter):
        cosine, sine = points[index]
        assert points[index + quarter] == (0.0 - sine, cosine)
        assert points[index + 2 * quarter] == (0.0 - cosine, 0.0 - sine)
        assert points[index + 3 * quarter] == (sine, 0.0 - cosine)


def test_no_negative_zero_is_emitted() -> None:
    """Zeros are positive so canonical bytes carry one representation."""
    for cosine, sine in unit_circle(8):
        if cosine == 0.0:
            assert math.copysign(1.0, cosine) == 1.0
        if sine == 0.0:
            assert math.copysign(1.0, sine) == 1.0


def test_polynomials_on_the_reduced_interval() -> None:
    """The polynomials match libm on [0, pi/4] and are exact at zero."""
    assert sine_polynomial(0.0) == 0.0
    assert cosine_polynomial(0.0) == 1.0
    for step in range(65):
        angle = math.pi / 4.0 * step / 64.0
        assert abs(sine_polynomial(angle) - math.sin(angle)) <= LIBM_TOLERANCE
        assert abs(cosine_polynomial(angle) - math.cos(angle)) <= LIBM_TOLERANCE


@pytest.mark.parametrize("segments", [0, 4, 7, -8])
def test_too_few_segments_are_refused(segments: int) -> None:
    """Counts below the minimum fail closed."""
    with pytest.raises(GeometryError, match="at least"):
        unit_circle(segments)


@pytest.mark.parametrize("segments", [12, 20, 9])
def test_non_multiples_are_refused(segments: int) -> None:
    """Counts that are not multiples of eight fail closed."""
    with pytest.raises(GeometryError, match="multiple"):
        require_segments(segments)


def test_boolean_is_refused() -> None:
    """A boolean is not a segment count."""
    with pytest.raises(GeometryError, match="at least"):
        require_segments(True)


def test_constants_are_consistent() -> None:
    """The minimum count is itself an admissible multiple."""
    assert MIN_SEGMENTS % SEGMENT_MULTIPLE == 0
    assert require_segments(MIN_SEGMENTS) == MIN_SEGMENTS
