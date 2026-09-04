# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — shared validation helper tests

"""Every branch of the shared fail-closed scalar validation."""

from __future__ import annotations

import math

import pytest

from scpn_reactor_kernels import (
    GeometryError,
    KernelInputError,
    __version__,
    require_finite,
    require_non_negative,
    require_positive,
)


def test_valid_values_pass_through() -> None:
    """Valid inputs are returned unchanged."""
    assert require_finite("x", 1.5) == 1.5
    assert require_positive("x", 2.0) == 2.0
    assert require_non_negative("x", 0.0) == 0.0
    assert __version__ == "1.0.0.dev0"


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_non_finite_is_refused_everywhere(value: float) -> None:
    """NaN and infinities fail closed in every helper."""
    for helper in (require_finite, require_positive, require_non_negative):
        with pytest.raises(KernelInputError, match="x: must be finite"):
            helper("x", value)


def test_sign_rules() -> None:
    """Zero and negatives are refused where the rule demands."""
    with pytest.raises(KernelInputError, match="strictly positive"):
        require_positive("x", 0.0)
    with pytest.raises(KernelInputError, match="non-negative"):
        require_non_negative("x", -1.0)


def test_caller_error_class_is_honoured() -> None:
    """A kernel passes its own error subclass and receives it back."""
    with pytest.raises(GeometryError, match="r: must be strictly positive"):
        require_positive("r", -1.0, GeometryError)
    assert issubclass(GeometryError, KernelInputError)
