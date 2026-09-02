# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — Bessel kernel tests

"""Accuracy, exactness, identities, zeros and refusals of ``J0`` and ``J1``.

The reference is an exact rational evaluation of the same DLMF 10.2.2
series to sixty terms (``fractions.Fraction`` on the exact binary value of
the argument), which isolates the rounding of the float evaluation; the
zeros are the OEIS decimal expansions. Every value is synthetic.
"""

from __future__ import annotations

import math
from decimal import Decimal
from fractions import Fraction

import pytest

from scpn_reactor_kernels import NumericsError
from scpn_reactor_kernels.numerics import (
    BESSEL_DOMAIN,
    BESSEL_J0_FIRST_ZERO,
    BESSEL_J1_FIRST_ZERO,
    BESSEL_TERMS,
    bessel_j0,
    bessel_j1,
    require_bessel_argument,
)

ABSOLUTE_TOLERANCE = 2.0e-14
OEIS_A115368 = "2.4048255576957727686216318793264546431242449091459"
OEIS_A115369 = "3.8317059702075123156144358863081607665645452742878"


def reference(order: int, x: float, terms: int = 60) -> Fraction:
    """Exact rational partial sum of the DLMF 10.2.2 series."""
    t = Fraction(x) * Fraction(x) / 4
    total = Fraction(0)
    for k in range(terms + 1):
        total += (-t) ** k / (math.factorial(k) * math.factorial(k + order))
    return (Fraction(x) / 2) ** order * total


def grid() -> list[float]:
    """Deterministic arguments over the domain, denser near the zeros."""
    values = [-8.0, -5.0, -1.0, -0.001, 0.0, 0.001, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0]
    values += [-8.0 + 16.0 * i / 400.0 for i in range(401)]
    values += [BESSEL_J0_FIRST_ZERO + d for d in (-1e-3, 0.0, 1e-3)]
    values += [BESSEL_J1_FIRST_ZERO + d for d in (-1e-3, 0.0, 1e-3)]
    return values


def test_zero_constants_are_the_oeis_doubles() -> None:
    """The constants are the correctly rounded OEIS expansions."""
    assert float(Decimal(OEIS_A115368)) == BESSEL_J0_FIRST_ZERO
    assert float(Decimal(OEIS_A115369)) == BESSEL_J1_FIRST_ZERO
    assert BESSEL_TERMS == 30
    assert BESSEL_DOMAIN == 8.0


@pytest.mark.parametrize("x", grid())
def test_series_matches_the_exact_rational_reference(x: float) -> None:
    """Both orders agree with the exact series to the declared bound."""
    assert abs(bessel_j0(x) - float(reference(0, x))) <= ABSOLUTE_TOLERANCE
    assert abs(bessel_j1(x) - float(reference(1, x))) <= ABSOLUTE_TOLERANCE


def test_truncation_is_below_rounding_on_the_domain() -> None:
    """Thirty terms versus sixty exact terms differ by less than the bound."""
    for x in (8.0, 7.5, 6.0):
        thirty = float(reference(0, x, BESSEL_TERMS))
        sixty = float(reference(0, x, 60))
        assert abs(thirty - sixty) <= 1.0e-15
        assert (
            abs(float(reference(1, x, BESSEL_TERMS)) - float(reference(1, x))) <= 1e-15
        )


def test_origin_and_zeros() -> None:
    """Exact values at the origin; the OEIS zeros are zeros of the series."""
    assert bessel_j0(0.0) == 1.0
    assert bessel_j1(0.0) == 0.0
    assert abs(bessel_j0(BESSEL_J0_FIRST_ZERO)) <= 1.0e-14
    assert abs(bessel_j1(BESSEL_J1_FIRST_ZERO)) <= 1.0e-14
    assert (
        bessel_j0(BESSEL_J0_FIRST_ZERO - 0.01)
        > 0.0
        > bessel_j0(BESSEL_J0_FIRST_ZERO + 0.01)
    )
    assert (
        bessel_j1(BESSEL_J1_FIRST_ZERO - 0.01)
        > 0.0
        > bessel_j1(BESSEL_J1_FIRST_ZERO + 0.01)
    )


@pytest.mark.parametrize("x", [0.3, 1.7, 2.9, 4.4, 6.1, 7.9])
def test_parity_and_derivative_identity(x: float) -> None:
    """``J0`` is even and ``J1`` odd bit for bit; ``J0' = -J1``."""
    assert bessel_j0(-x) == bessel_j0(x)
    assert bessel_j1(-x) == -bessel_j1(x)
    h = 1.0e-5
    derivative = (bessel_j0(x + h) - bessel_j0(x - h)) / (2.0 * h)
    assert abs(derivative + bessel_j1(x)) <= 1.0e-9


@pytest.mark.parametrize(
    ("value", "match"),
    [
        (math.nan, "must be finite"),
        (math.inf, "must be finite"),
        (8.000001, r"\|x\| <= 8\.0"),
        (-8.000001, r"\|x\| <= 8\.0"),
        (25.0, r"\|x\| <= 8\.0"),
    ],
)
def test_refusals(value: float, match: str) -> None:
    """Non-finite and out-of-domain arguments are refused, never clamped."""
    with pytest.raises(NumericsError, match=match):
        bessel_j0(value)
    with pytest.raises(NumericsError, match=match):
        bessel_j1(value)
    with pytest.raises(NumericsError, match=match):
        require_bessel_argument("x", value)


def test_domain_edges_are_admitted() -> None:
    """Exactly ``±8`` are inside the domain."""
    assert bessel_j0(8.0) == bessel_j0(-8.0)
    assert bessel_j1(8.0) == -bessel_j1(-8.0)
