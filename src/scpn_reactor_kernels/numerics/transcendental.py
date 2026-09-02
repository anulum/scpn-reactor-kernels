# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — deterministic natural logarithm, exponential and power

"""Vendored deterministic ``ln``, ``exp`` and real power for bit-exact kernels.

Physics closed forms carry logarithms (coaxial inductances ``ln(b/a)``,
Coulomb logarithms), exponentials (reactivity parametrisations,
self-absorption factors) and real powers (empirical scaling laws). Platform
``libm`` implementations of these functions are not guaranteed to be
correctly rounded and differ between languages and libraries, so a native
kernel could not reproduce the Python floor bit for bit if either side
called them. Both sides therefore evaluate the same series with the same
operation order:

- ``ln(x) = k ln 2 + 2 atanh(s)`` with ``x = m 2^k``, ``m`` in
  ``[sqrt(1/2), sqrt(2))`` obtained by exact binary decomposition, and
  ``s = (m - 1)/(m + 1)`` (so ``|s| <= 3 - 2 sqrt(2) < 0.1716``); the
  odd series of ``atanh`` is truncated after ``s^25`` (truncation below
  ``1e-20`` relative) and evaluated in Horner form in ``s^2`` with the
  reciprocal odd integers as exact quotients;
- ``exp(y) = 2^k exp(r)`` with ``k = floor(y / ln 2 + 1/2)`` and
  ``r = (y - k ln2_hi) - k ln2_lo`` (Cody–Waite split of ``ln 2``, the
  high part carrying trailing zero bits so ``k ln2_hi`` is exact); the
  Taylor series of ``exp(r)`` on ``|r| <= ln(2)/2`` is truncated after
  ``r^17`` (truncation below ``1e-24``) and evaluated in Horner form with
  the reciprocal factorials as exact quotients; the scaling by ``2^k`` is
  exact;
- ``pow(x, y) = exp(y ln x)`` for positive normal ``x``.

Accuracy, bounded by the tests against the platform ``math`` module: the
logarithm and the exponential agree to a few units in the last place; the
power inherits the logarithm error multiplied by ``|y ln x|``, so its
relative error grows with the magnitude of the exponent of the result
(about ``1e-13`` at ``|y ln x| = 100``). Inputs outside the normal range
are refused, never clamped: the logarithm needs a positive normal number,
the exponential an argument whose result is a normal number. Nothing here
describes a device; it is the numerical substrate of the physics kernels.
"""

from __future__ import annotations

import math
from typing import Final

from scpn_reactor_kernels.errors import NumericsError

#: Smallest positive normal double; the logarithm's lower admissible bound.
MIN_NORMAL: Final = 2.2250738585072014e-308
#: Correctly rounded ``ln 2``.
LN2: Final = 0.6931471805599453
#: High part of the Cody–Waite split of ``ln 2`` (trailing zero bits, so
#: integer multiples up to ``2^21`` are exact).
LN2_HI: Final = 6.93147180369123816490e-01
#: Low part of the Cody–Waite split of ``ln 2`` (``LN2_HI + LN2_LO == LN2``).
LN2_LO: Final = 1.90821492927058770002e-10
#: Correctly rounded ``1 / ln 2``; equals the exact quotient ``1.0 / LN2``.
INV_LN2: Final = 1.4426950408889634
#: Correctly rounded ``sqrt(1/2)``; the lower edge of the mantissa window.
SQRT_HALF: Final = 0.7071067811865476
#: Largest admissible exponential argument (the result stays a normal number).
EXP_MAX: Final = 709.0
#: Smallest admissible exponential argument (the result stays a normal number).
EXP_MIN: Final = -708.0

# Reciprocal odd integers of the atanh series as exact quotients.
_A3: Final = 1.0 / 3.0
_A5: Final = 1.0 / 5.0
_A7: Final = 1.0 / 7.0
_A9: Final = 1.0 / 9.0
_A11: Final = 1.0 / 11.0
_A13: Final = 1.0 / 13.0
_A15: Final = 1.0 / 15.0
_A17: Final = 1.0 / 17.0
_A19: Final = 1.0 / 19.0
_A21: Final = 1.0 / 21.0
_A23: Final = 1.0 / 23.0
_A25: Final = 1.0 / 25.0

# Reciprocal factorials of the exponential series as exact quotients (every
# factorial below 18! is exactly representable).
_F2: Final = 1.0 / 2.0
_F3: Final = 1.0 / 6.0
_F4: Final = 1.0 / 24.0
_F5: Final = 1.0 / 120.0
_F6: Final = 1.0 / 720.0
_F7: Final = 1.0 / 5040.0
_F8: Final = 1.0 / 40320.0
_F9: Final = 1.0 / 362880.0
_F10: Final = 1.0 / 3628800.0
_F11: Final = 1.0 / 39916800.0
_F12: Final = 1.0 / 479001600.0
_F13: Final = 1.0 / 6227020800.0
_F14: Final = 1.0 / 87178291200.0
_F15: Final = 1.0 / 1307674368000.0
_F16: Final = 1.0 / 20922789888000.0
_F17: Final = 1.0 / 355687428096000.0


def require_positive_normal(name: str, value: float) -> float:
    """Return ``value`` when it is a finite, positive, normal double.

    Parameters
    ----------
    name
        Field name reported in the rejection message.
    value
        Value under validation.

    Returns
    -------
    float
        The validated value.

    Raises
    ------
    NumericsError
        If ``value`` is NaN, infinite, zero, negative or subnormal.
    """
    if not math.isfinite(value):
        raise NumericsError(f"{name}: must be finite, got {value!r}")
    if value < MIN_NORMAL:
        raise NumericsError(
            f"{name}: must be a positive normal number (at least "
            f"{MIN_NORMAL!r}), got {value!r}"
        )
    return value


def binary_decompose(x: float) -> tuple[float, int]:
    """Split a positive normal ``x`` into ``m 2^k`` with ``m`` in the window.

    Parameters
    ----------
    x
        Positive normal double (validated by the caller).

    Returns
    -------
    (float, int)
        Mantissa ``m`` in ``[sqrt(1/2), sqrt(2))`` and integer exponent ``k``
        with ``x == m * 2**k`` exactly; both operations (the binary split
        and the doubling) are exact, so every backend obtains the same pair.
    """
    mantissa, exponent = math.frexp(x)
    if mantissa < SQRT_HALF:
        mantissa = mantissa * 2.0
        exponent = exponent - 1
    return mantissa, exponent


def atanh_series(s: float) -> float:
    """Evaluate ``2 atanh(s)`` by its odd series truncated after ``s^25``.

    Parameters
    ----------
    s
        Series argument; intended for ``|s| < 0.1716``.

    Returns
    -------
    float
        ``2 (s + s^3/3 + ... + s^25/25)`` in Horner form in ``s^2`` with the
        fixed operation order shared by the native kernel.
    """
    square = s * s
    polynomial = _A25
    polynomial = polynomial * square + _A23
    polynomial = polynomial * square + _A21
    polynomial = polynomial * square + _A19
    polynomial = polynomial * square + _A17
    polynomial = polynomial * square + _A15
    polynomial = polynomial * square + _A13
    polynomial = polynomial * square + _A11
    polynomial = polynomial * square + _A9
    polynomial = polynomial * square + _A7
    polynomial = polynomial * square + _A5
    polynomial = polynomial * square + _A3
    polynomial = polynomial * square + 1.0
    return (2.0 * s) * polynomial


def exponential_series(r: float) -> float:
    """Evaluate ``exp(r)`` by its Taylor series truncated after ``r^17``.

    Parameters
    ----------
    r
        Reduced argument; intended for ``|r| <= ln(2)/2``.

    Returns
    -------
    float
        ``1 + r + r^2/2! + ... + r^17/17!`` in Horner form with the fixed
        operation order shared by the native kernel.
    """
    polynomial = _F17
    polynomial = polynomial * r + _F16
    polynomial = polynomial * r + _F15
    polynomial = polynomial * r + _F14
    polynomial = polynomial * r + _F13
    polynomial = polynomial * r + _F12
    polynomial = polynomial * r + _F11
    polynomial = polynomial * r + _F10
    polynomial = polynomial * r + _F9
    polynomial = polynomial * r + _F8
    polynomial = polynomial * r + _F7
    polynomial = polynomial * r + _F6
    polynomial = polynomial * r + _F5
    polynomial = polynomial * r + _F4
    polynomial = polynomial * r + _F3
    polynomial = polynomial * r + _F2
    polynomial = polynomial * r + 1.0
    return polynomial * r + 1.0


def natural_log(x: float) -> float:
    """Return the natural logarithm of a positive normal double.

    Parameters
    ----------
    x
        Argument; must be finite, positive and normal.

    Returns
    -------
    float
        ``k ln 2 + 2 atanh((m - 1)/(m + 1))`` for ``x = m 2^k``; exactly
        ``0.0`` at ``x = 1`` and exactly ``k * LN2`` at every power of two.

    Raises
    ------
    NumericsError
        If ``x`` is non-finite, zero, negative or subnormal.
    """
    require_positive_normal("x", x)
    mantissa, exponent = binary_decompose(x)
    s = (mantissa - 1.0) / (mantissa + 1.0)
    return float(exponent) * LN2 + atanh_series(s)


def exponential(y: float) -> float:
    """Return ``exp(y)`` for arguments whose result is a normal double.

    Parameters
    ----------
    y
        Argument; must be finite and within ``[EXP_MIN, EXP_MAX]``.

    Returns
    -------
    float
        ``2^k exp(r)`` with the Cody–Waite reduction; exactly ``1.0`` at
        ``y = 0``.

    Raises
    ------
    NumericsError
        If ``y`` is non-finite or outside ``[EXP_MIN, EXP_MAX]``.
    """
    if not math.isfinite(y):
        raise NumericsError(f"y: must be finite, got {y!r}")
    if y < EXP_MIN or y > EXP_MAX:
        raise NumericsError(
            f"y: must lie within [{EXP_MIN!r}, {EXP_MAX!r}] so that the "
            f"result is a normal number, got {y!r}"
        )
    k = math.floor(y * INV_LN2 + 0.5)
    r = (y - float(k) * LN2_HI) - float(k) * LN2_LO
    return exponential_series(r) * math.ldexp(1.0, k)


def power(base: float, exponent: float) -> float:
    """Return ``base ** exponent`` as ``exp(exponent ln base)``.

    Parameters
    ----------
    base
        Positive normal double.
    exponent
        Finite real exponent.

    Returns
    -------
    float
        The power; exactly ``1.0`` when ``exponent`` is ``0`` and exactly
        ``base`` reproduced to the accuracy of the two series when
        ``exponent`` is ``1``.

    Raises
    ------
    NumericsError
        If ``base`` is not a positive normal number, ``exponent`` is
        non-finite, or ``exponent ln base`` leaves the admissible
        exponential range (the result would overflow or be subnormal).
    """
    require_positive_normal("base", base)
    if not math.isfinite(exponent):
        raise NumericsError(f"exponent: must be finite, got {exponent!r}")
    product = exponent * natural_log(base)
    if product < EXP_MIN or product > EXP_MAX:
        raise NumericsError(
            f"power: exponent * ln(base) = {product!r} leaves "
            f"[{EXP_MIN!r}, {EXP_MAX!r}]; the result would not be a normal number"
        )
    return exponential(product)
