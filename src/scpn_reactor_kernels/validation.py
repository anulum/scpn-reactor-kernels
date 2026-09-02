# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — shared input validation

"""Fail-closed scalar validation shared by every kernel.

Each helper returns the validated value so it can be used inline, and
raises :class:`~scpn_reactor_kernels.errors.KernelInputError` (or the
subclass the caller passes) naming the field and the violated bound.
"""

from __future__ import annotations

import math

from scpn_reactor_kernels.errors import KernelInputError


def require_finite(
    name: str, value: float, error: type[KernelInputError] = KernelInputError
) -> float:
    """Return ``value`` when finite, otherwise fail closed.

    Parameters
    ----------
    name
        Field name reported in the rejection message.
    value
        Value under validation.
    error
        Error class to raise; a kernel passes its own subclass.

    Returns
    -------
    float
        The validated value.

    Raises
    ------
    KernelInputError
        If ``value`` is NaN or infinite.
    """
    if not math.isfinite(value):
        raise error(f"{name}: must be finite, got {value!r}")
    return value


def require_positive(
    name: str, value: float, error: type[KernelInputError] = KernelInputError
) -> float:
    """Return ``value`` when finite and strictly positive.

    Parameters
    ----------
    name
        Field name reported in the rejection message.
    value
        Value under validation.
    error
        Error class to raise; a kernel passes its own subclass.

    Returns
    -------
    float
        The validated value.

    Raises
    ------
    KernelInputError
        If ``value`` is non-finite or not strictly positive.
    """
    require_finite(name, value, error)
    if value <= 0.0:
        raise error(f"{name}: must be strictly positive, got {value!r}")
    return value


def require_non_negative(
    name: str, value: float, error: type[KernelInputError] = KernelInputError
) -> float:
    """Return ``value`` when finite and non-negative.

    Parameters
    ----------
    name
        Field name reported in the rejection message.
    value
        Value under validation.
    error
        Error class to raise; a kernel passes its own subclass.

    Returns
    -------
    float
        The validated value.

    Raises
    ------
    KernelInputError
        If ``value`` is non-finite or negative.
    """
    require_finite(name, value, error)
    if value < 0.0:
        raise error(f"{name}: must be non-negative, got {value!r}")
    return value
