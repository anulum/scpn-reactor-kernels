# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — open-format mesh exports

"""Deterministic binary STL and glTF 2.0 (GLB) exports of validated meshes.

Both writers are pure serialisations of validated meshes: the same bodies
always yield the same bytes. Binary STL concatenates every body (80-byte
header, triangle count, per triangle a float32 unit normal, three float32
vertices and a zero attribute word). GLB follows the glTF 2.0 specification
(The Khronos Group): a 12-byte header, one JSON chunk and one binary chunk;
every body becomes one mesh with a float32 ``POSITION`` accessor (with the
required min/max) and a uint32 index accessor, attached to one named node
whose extras carry the body's role, material token and mesh digest; the
document ``extras`` are supplied by the caller (a consumer places its
record schema, digests, units and non-claims there). Coordinates are stored
in metres; float32 storage is a constraint of both containers, and the
canonical digests are taken on the float64 mesh bytes, never on the
exports.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Any, Final

from scpn_reactor_kernels.errors import GeometryError
from scpn_reactor_kernels.geometry.mesh import TriangleMesh, face_normal_and_area

STL_HEADER: Final = b"SCPN Reactor Kernels geometry_exports 1.0.0 binary STL".ljust(
    80, b" "
)
GLB_MAGIC: Final = 0x46546C67
GLB_VERSION: Final = 2
GLB_CHUNK_JSON: Final = 0x4E4F534A
GLB_CHUNK_BIN: Final = 0x004E4942
GLTF_GENERATOR: Final = "scpn-reactor-kernels geometry_exports 1.0.0"
_ARRAY_BUFFER: Final = 34962
_ELEMENT_ARRAY_BUFFER: Final = 34963
_FLOAT: Final = 5126
_UNSIGNED_INT: Final = 5125
_TRIANGLES: Final = 4


def _float32(value: float) -> float:
    """Round a double to the nearest float32 and return it as a float."""
    return float(struct.unpack("<f", struct.pack("<f", value))[0])


def _require_bodies(meshes: tuple[TriangleMesh, ...]) -> None:
    """Refuse an empty body list or duplicate node names.

    Raises
    ------
    GeometryError
        If no body is given or two bodies share a name.
    """
    if not meshes:
        raise GeometryError("meshes: at least one body is required")
    names = [mesh.name for mesh in meshes]
    if len(names) != len(set(names)):
        raise GeometryError(f"meshes: body names must be unique, got {names!r}")


def stl_bytes(meshes: tuple[TriangleMesh, ...]) -> bytes:
    """Serialise meshes as one binary STL document.

    Parameters
    ----------
    meshes
        Validated meshes; all bodies are concatenated in order.

    Returns
    -------
    bytes
        The binary STL document.

    Raises
    ------
    GeometryError
        If the body list is empty or names repeat.
    """
    _require_bodies(meshes)
    parts = [STL_HEADER, struct.pack("<I", sum(mesh.face_count for mesh in meshes))]
    for mesh in meshes:
        for face in mesh.faces:
            v0, v1, v2 = (mesh.vertices[corner] for corner in face)
            normal, _ = face_normal_and_area(v0, v1, v2)
            parts.append(struct.pack("<3f", *normal))
            parts.append(struct.pack("<9f", *v0, *v1, *v2))
            parts.append(struct.pack("<H", 0))
    return b"".join(parts)


def _padded(data: bytes, pad: bytes) -> bytes:
    """Pad a chunk payload to a multiple of four bytes."""
    return data + pad * ((4 - len(data) % 4) % 4)


def glb_bytes(meshes: tuple[TriangleMesh, ...], extras: dict[str, Any]) -> bytes:
    """Serialise meshes as one glTF 2.0 binary document.

    Parameters
    ----------
    meshes
        Validated meshes, one named node each.
    extras
        Document-level ``extras``: the consumer's provenance record (schema,
        digests, units, non-claims); must be JSON-serialisable with string
        keys and without NaN or infinity.

    Returns
    -------
    bytes
        The GLB document: header, JSON chunk, binary chunk.

    Raises
    ------
    GeometryError
        If the body list is empty, names repeat, or the extras cannot be
        serialised.
    """
    _require_bodies(meshes)
    binary = bytearray()
    buffer_views: list[dict[str, Any]] = []
    accessors: list[dict[str, Any]] = []
    mesh_records: list[dict[str, Any]] = []
    nodes: list[dict[str, Any]] = []
    for index, mesh in enumerate(meshes):
        positions = b"".join(struct.pack("<3f", *vertex) for vertex in mesh.vertices)
        lows = [
            min(_float32(vertex[axis]) for vertex in mesh.vertices) for axis in range(3)
        ]
        highs = [
            max(_float32(vertex[axis]) for vertex in mesh.vertices) for axis in range(3)
        ]
        position_view = len(buffer_views)
        buffer_views.append(
            {
                "buffer": 0,
                "byteOffset": len(binary),
                "byteLength": len(positions),
                "target": _ARRAY_BUFFER,
            }
        )
        binary.extend(positions)
        indices = b"".join(struct.pack("<3I", *face) for face in mesh.faces)
        index_view = len(buffer_views)
        buffer_views.append(
            {
                "buffer": 0,
                "byteOffset": len(binary),
                "byteLength": len(indices),
                "target": _ELEMENT_ARRAY_BUFFER,
            }
        )
        binary.extend(indices)
        position_accessor = len(accessors)
        accessors.append(
            {
                "bufferView": position_view,
                "componentType": _FLOAT,
                "count": mesh.vertex_count,
                "type": "VEC3",
                "min": lows,
                "max": highs,
            }
        )
        index_accessor = len(accessors)
        accessors.append(
            {
                "bufferView": index_view,
                "componentType": _UNSIGNED_INT,
                "count": 3 * mesh.face_count,
                "type": "SCALAR",
            }
        )
        mesh_records.append(
            {
                "name": mesh.name,
                "primitives": [
                    {
                        "attributes": {"POSITION": position_accessor},
                        "indices": index_accessor,
                        "mode": _TRIANGLES,
                    }
                ],
            }
        )
        nodes.append(
            {
                "name": mesh.name,
                "mesh": index,
                "extras": {
                    "role": mesh.role,
                    "material_identifier": mesh.material_identifier,
                    "mesh_sha256": mesh.digest_sha256(),
                },
            }
        )
    document = {
        "asset": {"version": "2.0", "generator": GLTF_GENERATOR},
        "scene": 0,
        "scenes": [{"nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": mesh_records,
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(binary)}],
        "extras": extras,
    }
    try:
        text = json.dumps(
            document, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
    except (TypeError, ValueError) as exc:
        raise GeometryError(f"extras: not JSON-serialisable: {exc}") from exc
    json_chunk = _padded(text.encode("utf-8"), b" ")
    binary_chunk = _padded(bytes(binary), b"\x00")
    total = 12 + 8 + len(json_chunk) + 8 + len(binary_chunk)
    return b"".join(
        (
            struct.pack("<III", GLB_MAGIC, GLB_VERSION, total),
            struct.pack("<II", len(json_chunk), GLB_CHUNK_JSON),
            json_chunk,
            struct.pack("<II", len(binary_chunk), GLB_CHUNK_BIN),
            binary_chunk,
        )
    )


def write_stl(path: Path, meshes: tuple[TriangleMesh, ...]) -> int:
    """Write a binary STL document.

    Parameters
    ----------
    path
        Destination file.
    meshes
        Validated meshes.

    Returns
    -------
    int
        Number of bytes written.
    """
    return path.write_bytes(stl_bytes(meshes))


def write_glb(
    path: Path, meshes: tuple[TriangleMesh, ...], extras: dict[str, Any]
) -> int:
    """Write a glTF 2.0 binary document.

    Parameters
    ----------
    path
        Destination file.
    meshes
        Validated meshes.
    extras
        Document-level extras, see :func:`glb_bytes`.

    Returns
    -------
    int
        Number of bytes written.
    """
    return path.write_bytes(glb_bytes(meshes, extras))
