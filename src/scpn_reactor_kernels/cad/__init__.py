# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — CAD kernel group (tier G2)

"""CAD kernels (tier G2): B-rep solids, assemblies, STEP, faceting, volume mesh.

Optional group behind the ``cad`` extra (CadQuery/OCP and gmsh). The
B-rep solids are the same primitives as the tier-G1 meshes, built by the
pinned OpenCASCADE kernel and checked against the analytic closed forms;
the assembly manifest is the record, the normalised STEP file its
deterministic export; the faceting returns the G1 closed-mesh contract;
the gmsh volume mesh is the entry point of the simulation lanes. Nothing
here describes a device. Design record: ADR 0006.
"""

from __future__ import annotations

from scpn_reactor_kernels.cad._backend import INSTALL_HINT, backend_versions
from scpn_reactor_kernels.cad.assembly import (
    MANIFEST_SCHEMA,
    MANIFEST_SCHEMA_VERSION,
    BrepAssembly,
)
from scpn_reactor_kernels.cad.evidence import (
    BodyEvidence,
    assembly_evidence,
    body_evidence,
)
from scpn_reactor_kernels.cad.facet import (
    DEFLECTION_DEFICIT_FACTOR,
    deflection_volume_bound,
    facet_assembly,
    facet_body,
    inscribed_polygon_area_ratio,
    require_deflection,
    weld,
)
from scpn_reactor_kernels.cad.placement import (
    ring_brep_bodies,
    translate_brep,
)
from scpn_reactor_kernels.cad.profiles import (
    FULL_TURN_DEGREES,
    profiled_solid_brep,
    profiled_tube_brep,
)
from scpn_reactor_kernels.cad.solids import (
    MEASURE_TOLERANCE,
    BrepBody,
    annular_tube_brep,
    cylinder_solid_brep,
    require_extent,
    require_radius,
)
from scpn_reactor_kernels.cad.step import (
    STEP_FILE_NAME,
    STEP_FIXED_TIMESTAMP,
    STEP_GENERATOR,
    normalise_step_text,
    step_bytes,
    step_sha256,
    write_step,
)
from scpn_reactor_kernels.cad.volume_mesh import (
    GMSH_OPTIONS,
    MSH_FORMAT,
    VolumeEntity,
    VolumeMesh,
    gmsh_volume_mesh,
    tetrahedron_volume,
)

__all__ = [
    "DEFLECTION_DEFICIT_FACTOR",
    "FULL_TURN_DEGREES",
    "GMSH_OPTIONS",
    "INSTALL_HINT",
    "MANIFEST_SCHEMA",
    "MANIFEST_SCHEMA_VERSION",
    "MEASURE_TOLERANCE",
    "MSH_FORMAT",
    "STEP_FILE_NAME",
    "STEP_FIXED_TIMESTAMP",
    "STEP_GENERATOR",
    "BodyEvidence",
    "BrepAssembly",
    "BrepBody",
    "VolumeEntity",
    "VolumeMesh",
    "annular_tube_brep",
    "assembly_evidence",
    "backend_versions",
    "body_evidence",
    "cylinder_solid_brep",
    "deflection_volume_bound",
    "facet_assembly",
    "facet_body",
    "gmsh_volume_mesh",
    "inscribed_polygon_area_ratio",
    "normalise_step_text",
    "profiled_solid_brep",
    "profiled_tube_brep",
    "require_deflection",
    "require_extent",
    "require_radius",
    "ring_brep_bodies",
    "step_bytes",
    "step_sha256",
    "tetrahedron_volume",
    "translate_brep",
    "weld",
    "write_step",
]
