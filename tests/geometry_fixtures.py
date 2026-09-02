# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — shared synthetic fixtures of the geometry tests

"""Synthetic bodies and bit-pattern helpers shared by the geometry tests.

Every value is a test fixture; none describes a real machine.
"""

from __future__ import annotations

import struct

from scpn_reactor_kernels.geometry import TriangleMesh, annular_tube, cylinder_solid


def sample_bodies(segments: int) -> tuple[TriangleMesh, ...]:
    """Return three validated synthetic bodies: two cylinders and a tube."""
    inner = cylinder_solid(0.05, 0.0, 1.0, segments)
    tube = annular_tube(0.1, 0.11, 0.0, 1.6, segments)
    column = cylinder_solid(0.01, 1.0, 1.5, segments)
    return (
        TriangleMesh(
            name="inner_cylinder",
            role="conductor",
            material_identifier="conductor",
            vertices=inner[0],
            faces=inner[1],
        ),
        TriangleMesh(
            name="tube",
            role="conductor",
            material_identifier="conductor",
            vertices=tube[0],
            faces=tube[1],
        ),
        TriangleMesh(
            name="column",
            role="plasma",
            material_identifier="plasma",
            vertices=column[0],
            faces=column[1],
        ),
    )


def sample_extras() -> dict[str, object]:
    """Return a consumer-style provenance record for the GLB extras."""
    return {
        "schema": "scpn.test-3d-model.v1",
        "schema_version": "1.0.0",
        "units": {"length": "metre"},
        "non_claims": ["synthetic test bodies"],
    }


def bits(value: float) -> bytes:
    """Return the IEEE-754 double bit pattern of a value."""
    return struct.pack("<d", value)


def stream_bits(values: list[float]) -> bytes:
    """Return the concatenated bit patterns of a float stream."""
    return b"".join(bits(value) for value in values)
