# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — shared fixtures of the CAD kernel tests

"""Synthetic B-rep bodies shared by the CAD kernel tests (no device described)."""

from __future__ import annotations

import pytest

pytest.importorskip("cadquery")

from scpn_reactor_kernels.cad import (
    BrepAssembly,
    BrepBody,
    annular_tube_brep,
    cylinder_solid_brep,
)

CYLINDER_RADIUS_M = 0.05
CYLINDER_EXTENT_M = (0.0, 0.3)
TUBE_RADII_M = (0.08, 0.1)
TUBE_EXTENT_M = (-0.1, 0.4)


def cylinder() -> BrepBody:
    """Return the synthetic solid cylinder."""
    return cylinder_solid_brep(
        CYLINDER_RADIUS_M, *CYLINDER_EXTENT_M, "inner", "electrode", "conductor"
    )


def tube() -> BrepBody:
    """Return the synthetic annular tube."""
    return annular_tube_brep(*TUBE_RADII_M, *TUBE_EXTENT_M, "outer", "wall", "steel")


def assembly() -> BrepAssembly:
    """Return the two-body assembly."""
    return BrepAssembly((cylinder(), tube()))
