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
from scpn_reactor_kernels.geometry.placement import (
    ring_offsets,
    ring_separation_m,
    translate,
)
from scpn_reactor_kernels.geometry.primitives import annular_tube, cylinder_solid
from scpn_reactor_kernels.geometry.profiles import (
    MIN_BIPOLAR_PROFILE_SAMPLES,
    MIN_CLOSED_PROFILE_SAMPLES,
    MIN_PROFILE_SAMPLES,
    Profile,
    ProfileSample,
    closed_profiled_solid,
    profile_lateral_area_m2,
    profile_volume_m3,
    profiled_solid,
    profiled_tube,
    require_aligned_profiles,
    require_closed_profile,
    require_profile,
    require_revolution_profile,
)
from scpn_reactor_kernels.geometry.spheres import (
    MIN_SPHERE_RINGS,
    require_rings,
    sphere_profile,
    sphere_solid,
    spherical_shell,
)
from scpn_reactor_kernels.geometry.trig import (
    MIN_CIRCLE_POINTS,
    MIN_SEGMENTS,
    SEGMENT_MULTIPLE,
    circle_points,
    cosine_polynomial,
    require_circle_points,
    require_segments,
    sine_polynomial,
    unit_circle,
)

__all__ = [
    "GLTF_GENERATOR",
    "MESH_BYTES_LAYOUT",
    "MIN_BIPOLAR_PROFILE_SAMPLES",
    "MIN_CIRCLE_POINTS",
    "MIN_CLOSED_PROFILE_SAMPLES",
    "MIN_PROFILE_SAMPLES",
    "MIN_SEGMENTS",
    "MIN_SPHERE_RINGS",
    "SEGMENT_MULTIPLE",
    "STL_HEADER",
    "Face",
    "Profile",
    "ProfileSample",
    "TriangleMesh",
    "Vertex",
    "annular_tube",
    "circle_points",
    "closed_profiled_solid",
    "cosine_polynomial",
    "cylinder_solid",
    "face_normal_and_area",
    "glb_bytes",
    "profile_lateral_area_m2",
    "profile_volume_m3",
    "profiled_solid",
    "profiled_tube",
    "require_aligned_profiles",
    "require_circle_points",
    "require_closed_profile",
    "require_profile",
    "require_revolution_profile",
    "require_rings",
    "require_segments",
    "ring_offsets",
    "ring_separation_m",
    "sine_polynomial",
    "sphere_profile",
    "sphere_solid",
    "spherical_shell",
    "stl_bytes",
    "translate",
    "unit_circle",
    "write_glb",
    "write_stl",
]
