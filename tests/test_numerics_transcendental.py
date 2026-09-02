# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — transcendental kernel tests

"""Accuracy, exactness, identities and refusals of the vendored ``ln``/``exp``.

The accuracy bounds are the evidence record quoted in ``VALIDATION.md``;
the platform ``math`` module is the reference. Every value is synthetic.
"""

from __future__ import annotations

import math
import random
import sys
from fractions import Fraction

import pytest

from scpn_reactor_kernels import NumericsError
from scpn_reactor_kernels.numerics import (
    EXP_MAX,
    EXP_MIN,
    INV_LN2,
    LN2,
    LN2_HI,
    LN2_LO,
    MIN_NORMAL,
    SQRT_HALF,
    atanh_series,
    binary_decompose,
    exponential,
    exponential_series,
    natural_log,
    power,
    require_positive_normal,
)

LN_TOLERANCE = 1.0e-15
EXP_TOLERANCE = 1.0e-15
POW_TOLERANCE = 1.0e-13


def relative_gap(got: float, want: float) -> float:
    """Relative difference with the reference's magnitude as the scale."""
    return abs(got - want) / max(abs(want), MIN_NORMAL)


def test_constants_are_the_documented_doubles() -> None:
    """Every literal is the correctly rounded value it claims to be."""
    assert math.log(2.0) == LN2
    assert INV_LN2 == 1.0 / LN2
    assert math.sqrt(0.5) == SQRT_HALF
    assert sys.float_info.min == MIN_NORMAL
    assert LN2_HI + LN2_LO == LN2
    assert LN2_HI.hex().endswith("00000p-1")
    for k in range(-1100, 1101):
        assert Fraction(float(k) * LN2_HI) == Fraction(k) * Fraction(LN2_HI)


@pytest.mark.parametrize(
    "x", [1.0, 1.5, 3.0, 0.3, 1e-300, 1e300, MIN_NORMAL, sys.float_info.max]
)
def test_decomposition_is_exact_and_windowed(x: float) -> None:
    """``x = m 2^k`` exactly with ``m`` in ``[sqrt(1/2), sqrt(2))``."""
    mantissa, exponent = binary_decompose(x)
    assert SQRT_HALF <= mantissa < 2.0 * SQRT_HALF
    assert Fraction(mantissa) * Fraction(2) ** exponent == Fraction(x)


def test_exact_points() -> None:
    """Powers of two, unity and zero are reproduced exactly."""
    assert natural_log(1.0) == 0.0
    assert natural_log(2.0) == LN2
    assert natural_log(0.5) == -LN2
    for k in range(-1022, 1024):
        assert natural_log(math.ldexp(1.0, k)) == float(k) * LN2
    assert exponential(0.0) == 1.0
    assert power(7.5, 0.0) == 1.0
    assert power(2.0, 10.0) == 1024.0


def test_series_pieces_agree_with_math() -> None:
    """The two series match the reference on their reduced intervals."""
    for i in range(-100, 101):
        s = 0.1716 * i / 100.0
        assert relative_gap(atanh_series(s), 2.0 * math.atanh(s)) <= 2e-15 or s == 0.0
        r = 0.35 * i / 100.0
        assert relative_gap(exponential_series(r), math.exp(r)) <= 1e-15


def test_logarithm_agrees_with_math_over_the_normal_range() -> None:
    """Deterministic sweep of the whole normal range against ``math.log``."""
    generator = random.Random(20260902)
    for _ in range(50000):
        x = math.exp(generator.uniform(-708.0, 709.0))
        assert relative_gap(natural_log(x), math.log(x)) <= LN_TOLERANCE, x
    for _ in range(50000):
        x = generator.uniform(0.5, 2.0)
        if x != 1.0:
            assert relative_gap(natural_log(x), math.log(x)) <= LN_TOLERANCE, x
    assert relative_gap(natural_log(sys.float_info.max), 709.782712893384) <= 1e-15
    assert relative_gap(natural_log(MIN_NORMAL), -708.3964185322641) <= 1e-15


def test_exponential_agrees_with_math_over_the_admissible_range() -> None:
    """Deterministic sweep of ``[EXP_MIN, EXP_MAX]`` against ``math.exp``."""
    generator = random.Random(20260902)
    for _ in range(50000):
        y = generator.uniform(EXP_MIN, EXP_MAX)
        assert relative_gap(exponential(y), math.exp(y)) <= EXP_TOLERANCE, y
    for _ in range(50000):
        y = generator.uniform(-1.0, 1.0)
        assert relative_gap(exponential(y), math.exp(y)) <= EXP_TOLERANCE, y
    assert exponential(EXP_MAX) == pytest.approx(math.exp(EXP_MAX), rel=1e-15)
    assert exponential(EXP_MIN) == pytest.approx(math.exp(EXP_MIN), rel=1e-15)
    assert exponential(EXP_MIN) >= MIN_NORMAL


def test_power_agrees_with_math_with_the_documented_growth() -> None:
    """``pow`` error stays within the bound quoted for ``|y ln x| <= 100``."""
    generator = random.Random(20260902)
    for _ in range(50000):
        base = math.exp(generator.uniform(-20.0, 20.0))
        exponent = generator.uniform(-5.0, 5.0)
        assert relative_gap(power(base, exponent), math.pow(base, exponent)) <= (
            POW_TOLERANCE
        ), (base, exponent)
    assert power(0.5, 3.8) == pytest.approx(0.5**3.8, rel=1e-15)
    assert power(10.0, 0.5) == pytest.approx(math.sqrt(10.0), rel=1e-15)


def test_inverse_identities() -> None:
    """``exp(ln x) = x`` and ``ln(exp y) = y`` to the series accuracy."""
    generator = random.Random(1)
    for _ in range(20000):
        x = math.exp(generator.uniform(-700.0, 700.0))
        assert relative_gap(exponential(natural_log(x)), x) <= 2e-13
        y = generator.uniform(-700.0, 700.0)
        assert abs(natural_log(exponential(y)) - y) <= 2e-13 * max(1.0, abs(y))


def test_monotonicity_on_a_dense_grid() -> None:
    """Both kernels are non-decreasing on dense grids (no series glitch)."""
    previous = natural_log(0.25)
    for i in range(1, 40001):
        current = natural_log(0.25 + i * 1e-4)
        assert current >= previous
        previous = current
    previous = exponential(-5.0)
    for i in range(1, 100001):
        current = exponential(-5.0 + i * 1e-4)
        assert current >= previous
        previous = current


@pytest.mark.parametrize(
    ("value", "match"),
    [
        (math.nan, "must be finite"),
        (math.inf, "must be finite"),
        (0.0, "positive normal"),
        (-1.0, "positive normal"),
        (5e-324, "positive normal"),
        (MIN_NORMAL / 2.0, "positive normal"),
    ],
)
def test_logarithm_refusals(value: float, match: str) -> None:
    """Non-finite, non-positive and subnormal arguments are refused."""
    with pytest.raises(NumericsError, match=match):
        natural_log(value)
    with pytest.raises(NumericsError, match=match):
        require_positive_normal("x", value)


@pytest.mark.parametrize(
    ("value", "match"),
    [
        (math.nan, "must be finite"),
        (-math.inf, "must be finite"),
        (EXP_MAX + 1e-9, "normal number"),
        (EXP_MIN - 1e-9, "normal number"),
        (1000.0, "normal number"),
    ],
)
def test_exponential_refusals(value: float, match: str) -> None:
    """Arguments whose result is not a normal double are refused."""
    with pytest.raises(NumericsError, match=match):
        exponential(value)


def test_power_refusals() -> None:
    """Invalid bases, non-finite exponents and out-of-range results refuse."""
    with pytest.raises(NumericsError, match="base: must be a positive normal"):
        power(0.0, 1.0)
    with pytest.raises(NumericsError, match="base: must be finite"):
        power(math.inf, 1.0)
    with pytest.raises(NumericsError, match="exponent: must be finite"):
        power(2.0, math.nan)
    with pytest.raises(NumericsError, match="would not be a normal number"):
        power(10.0, 400.0)
    with pytest.raises(NumericsError, match="would not be a normal number"):
        power(1e-300, 3.0)


def test_numerics_error_is_a_kernel_input_error() -> None:
    """The refusal type sits in the library's error hierarchy."""
    from scpn_reactor_kernels import KernelInputError

    assert issubclass(NumericsError, KernelInputError)
    assert issubclass(NumericsError, ValueError)
