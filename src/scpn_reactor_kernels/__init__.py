# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — shared kernel library

"""Shared physics and geometry kernels of the SCPN Reactor Systems group.

Public surface of the implemented kernel groups at
``computational_prototype`` maturity: the geometry kernels (deterministic
unit circle, closed-mesh contract, cylinder and tube tessellation, STL and
glTF exports) and the shared fail-closed validation helpers. Every kernel
is a computational prototype of a cited closed form or a standard method;
no value describes any real machine.
"""

from __future__ import annotations

from typing import Final

from scpn_reactor_kernels.errors import GeometryError, KernelInputError
from scpn_reactor_kernels.geometry import (
    GLTF_GENERATOR,
    MESH_BYTES_LAYOUT,
    MIN_SEGMENTS,
    SEGMENT_MULTIPLE,
    STL_HEADER,
    Face,
    TriangleMesh,
    Vertex,
    annular_tube,
    cosine_polynomial,
    cylinder_solid,
    face_normal_and_area,
    glb_bytes,
    require_segments,
    sine_polynomial,
    stl_bytes,
    unit_circle,
    write_glb,
    write_stl,
)
from scpn_reactor_kernels.validation import (
    require_finite,
    require_non_negative,
    require_positive,
)

__version__: Final = "0.1.0.dev0"

__all__ = [
    "GLTF_GENERATOR",
    "MESH_BYTES_LAYOUT",
    "MIN_SEGMENTS",
    "SEGMENT_MULTIPLE",
    "STL_HEADER",
    "Face",
    "GeometryError",
    "KernelInputError",
    "TriangleMesh",
    "Vertex",
    "__version__",
    "annular_tube",
    "cosine_polynomial",
    "cylinder_solid",
    "face_normal_and_area",
    "glb_bytes",
    "require_finite",
    "require_non_negative",
    "require_positive",
    "require_segments",
    "sine_polynomial",
    "stl_bytes",
    "unit_circle",
    "write_glb",
    "write_stl",
]
