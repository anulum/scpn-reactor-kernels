# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — kernel error surface

"""Error surface of the kernel library.

Every kernel refuses an invalid input with one of these errors, naming the
offending field and the violated bound; nothing is clamped, defaulted or
silently corrected, and no kernel returns a non-finite value.
"""

from __future__ import annotations


class KernelInputError(ValueError):
    """Raised when a kernel input violates its declared domain."""


class GeometryError(KernelInputError):
    """Raised when a geometry parameter or a mesh violates a model invariant."""
