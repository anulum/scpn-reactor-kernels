# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — geometry kernels package

"""Geometry kernels shared by every device 3D model.

A vendored bit-exact unit circle, the closed-mesh contract with canonical
bytes and digests, deterministic tessellation of analytic bodies, and
open-format exports (binary STL, glTF 2.0 binary). Every body is an
analytic surface of declared parameters; nothing here is a CAD solid, an
equilibrium boundary or an engineering model. Design record: ADR 0002.
"""

from __future__ import annotations

from scpn_reactor_kernels.geometry.export import (
    GLTF_GENERATOR,
    STL_HEADER,
    glb_bytes,
    stl_bytes,
    write_glb,
    write_stl,
)
from scpn_reactor_kernels.geometry.mesh import (
    MESH_BYTES_LAYOUT,
    Face,
    TriangleMesh,
    Vertex,
    face_normal_and_area,
)
from scpn_reactor_kernels.geometry.primitives import annular_tube, cylinder_solid
from scpn_reactor_kernels.geometry.trig import (
    MIN_SEGMENTS,
    SEGMENT_MULTIPLE,
    cosine_polynomial,
    require_segments,
    sine_polynomial,
    unit_circle,
)

__all__ = [
    "GLTF_GENERATOR",
    "MESH_BYTES_LAYOUT",
    "MIN_SEGMENTS",
    "SEGMENT_MULTIPLE",
    "STL_HEADER",
    "Face",
    "TriangleMesh",
    "Vertex",
    "annular_tube",
    "cosine_polynomial",
    "cylinder_solid",
    "face_normal_and_area",
    "glb_bytes",
    "require_segments",
    "sine_polynomial",
    "stl_bytes",
    "unit_circle",
    "write_glb",
    "write_stl",
]
