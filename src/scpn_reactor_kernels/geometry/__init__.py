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
    ROTATION_TOLERANCE,
    Direction,
    Rotation,
    aim_rotation,
    axis_direction,
    centre_separation_m,
    inward_aim,
    require_rotation,
    ring_azimuths,
    ring_offsets,
    ring_separation_m,
    rotate,
    sphere_ring_offsets,
    translate,
)
from scpn_reactor_kernels.geometry.primitives import (
    annular_tube,
    cylinder_solid,
    rectangular_prism,
)
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
    DEGREES_PER_HALF_TURN,
    MAX_ANGLE_RAD,
    MAX_QUADRANT_INDEX,
    MIN_CIRCLE_POINTS,
    MIN_SEGMENTS,
    SEGMENT_MULTIPLE,
    UNIT_POINT_TOLERANCE,
    CirclePoint,
    circle_point,
    circle_points,
    cosine,
    cosine_polynomial,
    opposite_point,
    quadrant_reduction,
    radians_from_degrees,
    require_circle_point,
    require_circle_points,
    require_reducible_angle,
    require_segments,
    sine,
    sine_polynomial,
    supplementary_point,
    unit_circle,
)

__all__ = [
    "DEGREES_PER_HALF_TURN",
    "GLTF_GENERATOR",
    "MAX_ANGLE_RAD",
    "MAX_QUADRANT_INDEX",
    "MESH_BYTES_LAYOUT",
    "MIN_BIPOLAR_PROFILE_SAMPLES",
    "MIN_CIRCLE_POINTS",
    "MIN_CLOSED_PROFILE_SAMPLES",
    "MIN_PROFILE_SAMPLES",
    "MIN_SEGMENTS",
    "MIN_SPHERE_RINGS",
    "ROTATION_TOLERANCE",
    "SEGMENT_MULTIPLE",
    "STL_HEADER",
    "UNIT_POINT_TOLERANCE",
    "CirclePoint",
    "Direction",
    "Face",
    "Profile",
    "ProfileSample",
    "Rotation",
    "TriangleMesh",
    "Vertex",
    "aim_rotation",
    "annular_tube",
    "axis_direction",
    "centre_separation_m",
    "circle_point",
    "circle_points",
    "closed_profiled_solid",
    "cosine",
    "cosine_polynomial",
    "cylinder_solid",
    "face_normal_and_area",
    "glb_bytes",
    "inward_aim",
    "opposite_point",
    "profile_lateral_area_m2",
    "profile_volume_m3",
    "profiled_solid",
    "profiled_tube",
    "quadrant_reduction",
    "radians_from_degrees",
    "rectangular_prism",
    "require_aligned_profiles",
    "require_circle_point",
    "require_circle_points",
    "require_closed_profile",
    "require_profile",
    "require_reducible_angle",
    "require_revolution_profile",
    "require_rings",
    "require_rotation",
    "require_segments",
    "ring_azimuths",
    "ring_offsets",
    "ring_separation_m",
    "rotate",
    "sine",
    "sine_polynomial",
    "sphere_profile",
    "sphere_ring_offsets",
    "sphere_solid",
    "spherical_shell",
    "stl_bytes",
    "supplementary_point",
    "translate",
    "unit_circle",
    "write_glb",
    "write_stl",
]
