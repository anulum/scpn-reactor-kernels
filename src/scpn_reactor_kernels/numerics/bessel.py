# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — Bessel functions of the first kind, orders zero and one

"""Deterministic Bessel functions ``J0`` and ``J1`` and their first zeros.

The relaxed (force-free) states of the reversed-field pinch and the
spheromak are Bessel-function profiles; their reversal and eigenvalue
conditions sit at the first zeros of ``J0`` and ``J1``. Platform special
functions are not part of the bit-exact rule, so both orders are evaluated
from the ascending series of NIST DLMF 10.2.2,
``J_nu(x) = (x/2)^nu sum_k (-1)^k (x^2/4)^k / (k! (k + nu)!)``, in Horner
form on ``t = x^2 / 4`` with the coefficient ratios ``-t / k^2`` (order 0)
and ``-t / (k (k + 1))`` (order 1) evaluated as exact quotients of small
integers, truncated after ``t^30`` and with the same operation order on
both sides. The declared domain is ``|x| <= 8``: beyond it the alternating
series loses digits (its largest term grows like ``e^|x|``); an argument
outside the domain or non-finite is refused, never clamped. The tests
bound the error against an exact rational evaluation of the same series
(``2e-14`` absolute on the domain) and check the zeros, the parity in
``x`` and the derivative identity ``J0' = -J1``. The first zeros are the
correctly rounded doubles of OEIS A115368 (``j_{0,1}``) and A115369
(``j_{1,1}``); DLMF 10.21 lists them. Nothing here describes a device.
"""

from __future__ import annotations

import math
from typing import Final

from scpn_reactor_kernels.errors import NumericsError

#: First positive zero of ``J0`` (OEIS A115368), correctly rounded.
BESSEL_J0_FIRST_ZERO: Final = 2.404825557695773
#: First positive zero of ``J1`` (OEIS A115369), correctly rounded.
BESSEL_J1_FIRST_ZERO: Final = 3.8317059702075125
#: Largest admissible ``|x|`` of the series evaluation.
BESSEL_DOMAIN: Final = 8.0
#: Number of series terms after the leading one (``t^30``).
BESSEL_TERMS: Final = 30


def require_bessel_argument(name: str, value: float) -> float:
    """Return ``value`` when finite and inside ``[-8, 8]``.

    Parameters
    ----------
    name
        Field name reported in the rejection message.
    value
        Argument under validation.

    Returns
    -------
    float
        The validated argument.

    Raises
    ------
    NumericsError
        If ``value`` is non-finite or ``|value| > 8``.
    """
    if not math.isfinite(value):
        raise NumericsError(f"{name}: must be finite, got {value!r}")
    if value < -BESSEL_DOMAIN or value > BESSEL_DOMAIN:
        raise NumericsError(
            f"{name}: the Bessel series is evaluated on |x| <= {BESSEL_DOMAIN!r}, "
            f"got {value!r}"
        )
    return value


def bessel_j0_series(t: float) -> float:
    """Evaluate ``sum_k (-t)^k / (k!)^2`` by Horner recursion in ``t``.

    Parameters
    ----------
    t
        ``x^2 / 4``; non-negative.

    Returns
    -------
    float
        The truncated series.
    """
    acc = 1.0
    for k in range(BESSEL_TERMS, 0, -1):
        acc = 1.0 - t * acc / float(k * k)
    return acc


def bessel_j1_series(t: float) -> float:
    """Evaluate ``sum_k (-t)^k / (k! (k + 1)!)`` by Horner recursion in ``t``.

    Parameters
    ----------
    t
        ``x^2 / 4``; non-negative.

    Returns
    -------
    float
        The truncated series (without the leading ``x / 2`` factor).
    """
    acc = 1.0
    for k in range(BESSEL_TERMS, 0, -1):
        acc = 1.0 - t * acc / float(k * (k + 1))
    return acc


def bessel_j0(x: float) -> float:
    """Return ``J0(x)`` on the declared domain.

    Parameters
    ----------
    x
        Argument with ``|x| <= 8``.

    Returns
    -------
    float
        ``J0(x)``; exactly ``1.0`` at ``x = 0`` and an even function of
        ``x`` by construction.

    Raises
    ------
    NumericsError
        If ``x`` is non-finite or outside the domain.
    """
    require_bessel_argument("x", x)
    return bessel_j0_series(x * x / 4.0)


def bessel_j1(x: float) -> float:
    """Return ``J1(x)`` on the declared domain.

    Parameters
    ----------
    x
        Argument with ``|x| <= 8``.

    Returns
    -------
    float
        ``J1(x)``; exactly ``0.0`` at ``x = 0`` and an odd function of
        ``x`` by construction.

    Raises
    ------
    NumericsError
        If ``x`` is non-finite or outside the domain.
    """
    require_bessel_argument("x", x)
    return (x / 2.0) * bessel_j1_series(x * x / 4.0)
