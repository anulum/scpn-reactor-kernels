# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — numerics kernel group

"""Numerical substrate kernels shared by the physics kernels.

Implemented: the vendored deterministic natural logarithm, exponential and
real power (:mod:`scpn_reactor_kernels.numerics.transcendental`) and the
Bessel functions ``J0`` and ``J1`` with their first zeros
(:mod:`scpn_reactor_kernels.numerics.bessel`). Nothing here describes a
device.
"""

from __future__ import annotations

from scpn_reactor_kernels.numerics.bessel import (
    BESSEL_DOMAIN,
    BESSEL_J0_FIRST_ZERO,
    BESSEL_J1_FIRST_ZERO,
    BESSEL_TERMS,
    bessel_j0,
    bessel_j0_series,
    bessel_j1,
    bessel_j1_series,
    require_bessel_argument,
)
from scpn_reactor_kernels.numerics.transcendental import (
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

__all__ = [
    "BESSEL_DOMAIN",
    "BESSEL_J0_FIRST_ZERO",
    "BESSEL_J1_FIRST_ZERO",
    "BESSEL_TERMS",
    "EXP_MAX",
    "EXP_MIN",
    "INV_LN2",
    "LN2",
    "LN2_HI",
    "LN2_LO",
    "MIN_NORMAL",
    "SQRT_HALF",
    "atanh_series",
    "bessel_j0",
    "bessel_j0_series",
    "bessel_j1",
    "bessel_j1_series",
    "binary_decompose",
    "exponential",
    "exponential_series",
    "natural_log",
    "power",
    "require_bessel_argument",
    "require_positive_normal",
]
