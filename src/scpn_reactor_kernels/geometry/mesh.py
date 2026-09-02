# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — triangle mesh contract

"""Closed triangle meshes with canonical bytes, digests and measures.

A :class:`TriangleMesh` is the unit of every device 3D model: a named,
material-tagged, closed and consistently oriented triangle surface with
fixed vertex and face order. Validation is fail-closed (index range,
degenerate faces, open or inconsistently oriented surfaces are rejected).
The signed volume follows the divergence theorem and the surface area the
cross-product identity, both with the fixed summation order shared by the
native kernel. Canonical bytes are little-endian: vertex count, face
count, every vertex as three doubles, every face as three unsigned
32-bit indices; the SHA-256 of those bytes identifies the exact mesh.
"""

from __future__ import annotations

import hashlib
import math
import struct
from dataclasses import dataclass
from typing import Any, Final

from scpn_reactor_kernels.errors import GeometryError

Vertex = tuple[float, float, float]
Face = tuple[int, int, int]

MIN_VERTICES: Final = 4
MIN_FACES: Final = 4
MESH_BYTES_LAYOUT: Final = (
    "little-endian: uint32 vertex_count, uint32 face_count, "
    "float64 x y z per vertex, uint32 i j k per face"
)


def _cross(a: Vertex, b: Vertex) -> Vertex:
    """Cross product with the fixed component order of the native kernel."""
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _subtract(a: Vertex, b: Vertex) -> Vertex:
    """Component-wise difference ``a - b``."""
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def face_normal_and_area(v0: Vertex, v1: Vertex, v2: Vertex) -> tuple[Vertex, float]:
    """Compute the unit normal and the area of one triangle.

    Parameters
    ----------
    v0, v1, v2
        Triangle vertices in face order.

    Returns
    -------
    (Vertex, float)
        The unit normal ``(v1 - v0) x (v2 - v0) / |...|`` and the area
        ``|...| / 2``.

    Raises
    ------
    GeometryError
        If the triangle is degenerate (zero area).
    """
    cross = _cross(_subtract(v1, v0), _subtract(v2, v0))
    norm = math.sqrt(cross[0] * cross[0] + cross[1] * cross[1] + cross[2] * cross[2])
    if norm == 0.0:
        raise GeometryError("face: degenerate triangle with zero area")
    return (cross[0] / norm, cross[1] / norm, cross[2] / norm), norm / 2.0


@dataclass(frozen=True, slots=True)
class TriangleMesh:
    """One closed, consistently oriented triangle mesh.

    Parameters
    ----------
    name
        Node name of the body; non-empty.
    role
        Declared role token of the body (for example ``electrode``).
    material_identifier
        Declared material token; no material property is carried.
    vertices
        Vertex coordinates in metres; at least four, all finite.
    faces
        Triangles as vertex index triples, outward oriented; at least four.

    Raises
    ------
    GeometryError
        If any invariant fails: empty names, non-finite coordinates, an
        index out of range, a degenerate face, or a surface that is not a
        closed manifold with consistent orientation (every directed edge
        must appear exactly once, together with its reverse).
    """

    name: str
    role: str
    material_identifier: str
    vertices: tuple[Vertex, ...]
    faces: tuple[Face, ...]

    def __post_init__(self) -> None:
        """Validate the mesh invariants.

        Raises
        ------
        GeometryError
            If any invariant fails.
        """
        for field_name, value in (
            ("name", self.name),
            ("role", self.role),
            ("material_identifier", self.material_identifier),
        ):
            if not value:
                raise GeometryError(f"{field_name}: must be non-empty")
        if len(self.vertices) < MIN_VERTICES:
            raise GeometryError(
                f"vertices: at least {MIN_VERTICES} required, got {len(self.vertices)}"
            )
        for index, vertex in enumerate(self.vertices):
            for coordinate in vertex:
                if not math.isfinite(coordinate):
                    raise GeometryError(
                        f"vertices[{index}]: must be finite, got {vertex!r}"
                    )
        if len(self.faces) < MIN_FACES:
            raise GeometryError(
                f"faces: at least {MIN_FACES} required, got {len(self.faces)}"
            )
        count = len(self.vertices)
        edges: set[tuple[int, int]] = set()
        for index, face in enumerate(self.faces):
            for corner in face:
                if isinstance(corner, bool) or not 0 <= corner < count:
                    raise GeometryError(
                        f"faces[{index}]: index {corner!r} out of range [0, {count})"
                    )
            if len(set(face)) != 3:
                raise GeometryError(
                    f"faces[{index}]: repeated vertex index in {face!r}"
                )
            try:
                face_normal_and_area(*(self.vertices[corner] for corner in face))
            except GeometryError as exc:
                raise GeometryError(f"faces[{index}]: {exc}") from exc
            for start, end in (
                (face[0], face[1]),
                (face[1], face[2]),
                (face[2], face[0]),
            ):
                if (start, end) in edges:
                    raise GeometryError(
                        f"faces[{index}]: directed edge {(start, end)!r} appears "
                        "twice (inconsistent orientation or duplicate face)"
                    )
                edges.add((start, end))
        for start, end in edges:
            if (end, start) not in edges:
                raise GeometryError(
                    f"faces: edge {(start, end)!r} has no reverse; the surface "
                    "is not closed"
                )

    @property
    def vertex_count(self) -> int:
        """Number of vertices."""
        return len(self.vertices)

    @property
    def face_count(self) -> int:
        """Number of triangles."""
        return len(self.faces)

    def signed_volume_m3(self) -> float:
        """Enclosed volume by the divergence theorem.

        Returns
        -------
        float
            ``sum(v0 . (v1 x v2)) / 6`` over the faces in order; positive
            for outward orientation.
        """
        total = 0.0
        for face in self.faces:
            v0 = self.vertices[face[0]]
            cross = _cross(self.vertices[face[1]], self.vertices[face[2]])
            total += v0[0] * cross[0] + v0[1] * cross[1] + v0[2] * cross[2]
        return total / 6.0

    def surface_area_m2(self) -> float:
        """Total surface area.

        Returns
        -------
        float
            Sum of ``|(v1 - v0) x (v2 - v0)|`` over the faces in order,
            divided by two.
        """
        total = 0.0
        for face in self.faces:
            v0 = self.vertices[face[0]]
            cross = _cross(
                _subtract(self.vertices[face[1]], v0),
                _subtract(self.vertices[face[2]], v0),
            )
            total += math.sqrt(
                cross[0] * cross[0] + cross[1] * cross[1] + cross[2] * cross[2]
            )
        return total / 2.0

    def bounding_box(self) -> tuple[Vertex, Vertex]:
        """Axis-aligned bounding box.

        Returns
        -------
        (Vertex, Vertex)
            Component-wise minimum and maximum over the vertices.
        """
        xs = [vertex[0] for vertex in self.vertices]
        ys = [vertex[1] for vertex in self.vertices]
        zs = [vertex[2] for vertex in self.vertices]
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))

    def canonical_bytes(self) -> bytes:
        """Serialise the mesh in the fixed binary layout.

        Returns
        -------
        bytes
            See :data:`MESH_BYTES_LAYOUT`.
        """
        parts = [struct.pack("<II", len(self.vertices), len(self.faces))]
        parts.extend(struct.pack("<ddd", *vertex) for vertex in self.vertices)
        parts.extend(struct.pack("<III", *face) for face in self.faces)
        return b"".join(parts)

    def digest_sha256(self) -> str:
        """Identify the exact mesh.

        Returns
        -------
        str
            SHA-256 of :meth:`canonical_bytes` as lowercase hex.
        """
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

    def summary_record(self) -> dict[str, Any]:
        """Project the mesh summary to a JSON-serialisable record.

        Returns
        -------
        dict[str, Any]
            Identity, counts, measures, bounding box and digest; the vertex
            and face streams themselves stay in the binary exports.
        """
        low, high = self.bounding_box()
        return {
            "name": self.name,
            "role": self.role,
            "material_identifier": self.material_identifier,
            "vertex_count": self.vertex_count,
            "face_count": self.face_count,
            "volume_m3": self.signed_volume_m3(),
            "surface_area_m2": self.surface_area_m2(),
            "bounding_box_min_m": list(low),
            "bounding_box_max_m": list(high),
            "mesh_sha256": self.digest_sha256(),
        }
