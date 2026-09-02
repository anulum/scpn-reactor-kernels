# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — native transcendental parity tests

"""Bit-exact parity of the transcendental and Bessel kernels between Python and Rust.

Skipped hermetically when the optional native module is absent; when
present, every result is compared by float64 bit pattern, never by
tolerance. All inputs are synthetic.
"""

from __future__ import annotations

import math
import random

import pytest

from geometry_fixtures import bits, stream_bits
from scpn_reactor_kernels.numerics import (
    BESSEL_J0_FIRST_ZERO,
    BESSEL_J1_FIRST_ZERO,
    EXP_MAX,
    EXP_MIN,
    MIN_NORMAL,
    bessel_j0,
    bessel_j1,
    exponential,
    natural_log,
    power,
)

native = pytest.importorskip("scpn_reactor_kernels_native")


def logarithm_arguments() -> list[float]:
    """Deterministic arguments spanning the normal range and the unit window."""
    generator = random.Random(9)
    values = [1.0, 2.0, 0.5, MIN_NORMAL, 1.7976931348623157e308, 0.75, 1.5]
    values += [math.exp(generator.uniform(-708.0, 709.0)) for _ in range(5000)]
    values += [generator.uniform(0.5, 2.0) for _ in range(5000)]
    return values


def exponential_arguments() -> list[float]:
    """Deterministic arguments spanning the admissible exponential range."""
    generator = random.Random(11)
    values = [0.0, 1.0, -1.0, EXP_MIN, EXP_MAX, 0.3465, -0.3466]
    values += [generator.uniform(EXP_MIN, EXP_MAX) for _ in range(5000)]
    values += [generator.uniform(-1.0, 1.0) for _ in range(5000)]
    return values


def test_logarithm_is_bit_exact() -> None:
    """Scalar and stream bindings agree bit for bit with the floor."""
    arguments = logarithm_arguments()
    floor = [natural_log(x) for x in arguments]
    assert stream_bits(floor) == stream_bits(native.natural_log_stream(arguments))
    for x, want in zip(arguments[:64], floor[:64], strict=True):
        assert bits(native.natural_log(x)) == bits(want)


def test_exponential_is_bit_exact() -> None:
    """Scalar and stream bindings agree bit for bit with the floor."""
    arguments = exponential_arguments()
    floor = [exponential(y) for y in arguments]
    assert stream_bits(floor) == stream_bits(native.exponential_stream(arguments))
    for y, want in zip(arguments[:64], floor[:64], strict=True):
        assert bits(native.exponential(y)) == bits(want)


def test_power_is_bit_exact() -> None:
    """Scalar and stream bindings agree bit for bit with the floor."""
    generator = random.Random(13)
    bases = [math.exp(generator.uniform(-20.0, 20.0)) for _ in range(5000)]
    exponents = [generator.uniform(-5.0, 5.0) for _ in range(5000)]
    floor = [power(b, e) for b, e in zip(bases, exponents, strict=True)]
    assert stream_bits(floor) == stream_bits(native.power_stream(bases, exponents))
    for b, e, want in zip(bases[:64], exponents[:64], floor[:64], strict=True):
        assert bits(native.power(b, e)) == bits(want)


def test_native_refusals_mirror_the_floor() -> None:
    """Every refusal of the floor is a ValueError of the binding."""
    with pytest.raises(ValueError, match="positive normal"):
        native.natural_log(0.0)
    with pytest.raises(ValueError, match="must be finite"):
        native.natural_log(math.nan)
    with pytest.raises(ValueError, match="normal number"):
        native.exponential(EXP_MAX + 1.0)
    with pytest.raises(ValueError, match="must be finite"):
        native.exponential(math.inf)
    with pytest.raises(ValueError, match="would not be a normal number"):
        native.power(10.0, 400.0)
    with pytest.raises(ValueError, match="exponent: must be finite"):
        native.power(2.0, math.nan)
    with pytest.raises(ValueError, match="positive normal"):
        native.natural_log_stream([1.0, -1.0])
    with pytest.raises(ValueError, match="normal number"):
        native.exponential_stream([0.0, 1000.0])
    with pytest.raises(ValueError, match="same length"):
        native.power_stream([1.0, 2.0], [1.0])
    with pytest.raises(ValueError, match="positive normal"):
        native.power_stream([0.0], [1.0])


def test_bessel_kernels_are_bit_exact() -> None:
    """``J0`` and ``J1`` agree bit for bit on a domain grid and at the zeros."""
    generator = random.Random(17)
    arguments = [0.0, 8.0, -8.0, BESSEL_J0_FIRST_ZERO, BESSEL_J1_FIRST_ZERO]
    arguments += [generator.uniform(-8.0, 8.0) for _ in range(5000)]
    floor_j0 = [bessel_j0(x) for x in arguments]
    floor_j1 = [bessel_j1(x) for x in arguments]
    assert stream_bits(floor_j0) == stream_bits(native.bessel_j0_stream(arguments))
    assert stream_bits(floor_j1) == stream_bits(native.bessel_j1_stream(arguments))
    for x, j0, j1 in zip(arguments[:64], floor_j0[:64], floor_j1[:64], strict=True):
        assert bits(native.bessel_j0(x)) == bits(j0)
        assert bits(native.bessel_j1(x)) == bits(j1)
    with pytest.raises(ValueError, match=r"<= 8\.0"):
        native.bessel_j0(8.5)
    with pytest.raises(ValueError, match="must be finite"):
        native.bessel_j1_stream([1.0, math.nan])
