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

**Both containers store positions in float32, and that is a range, not a
formality.** A float32 holds about seven decimal digits, so what survives
storage is not a body's size but the ratio between its coordinates and its
smallest feature. A one-centimetre wall modelled at the origin is exact to
seven digits; the same wall on a site grid a hundred metres away has only
five digits left, and a kilometre away it has four. The damage arrives long
before anything looks broken: measured on this library's own tube, a
hundred-metre offset already costs a thousandth of a facet's area, ten
kilometres costs a tenth of it, and only past two hundred kilometres does a
triangle finally collapse to a line. A writer that checks nothing emits all
three cases as ordinary bytes.

Both writers therefore measure the geometry they are about to store, and
refuse to write one that has lost more than :data:`EXPORT_AREA_TOLERANCE`
of any facet's area, or that has collapsed a facet, or that carries a
coordinate outside the float32 range. The two containers then differ in
what they can offer instead:

- **GLB has a node transform.** When a body does not survive storage in
  absolute coordinates, its positions are stored relative to the midpoint
  of its own bounding box and that midpoint is written to the node's
  ``translation``. The body's place in the world is unchanged, because a
  glTF node's translation composes with its mesh; nothing is moved
  silently. The translation is written at full double precision in the
  JSON text. A consumer that keeps node translations in float32 places the
  body to float32 resolution, which is all a float32 pipeline can express
  anyway, and **the body's own shape is unaffected either way** since
  every vertex moves together.
- **Binary STL has no transform of any kind.** Rebasing an STL really does
  move the device, so the writer never does it on its own: it refuses, and
  names the translation that would work. A caller that wants it passes
  ``translation_m`` explicitly and is then responsible for recording the
  value, because the file cannot.

A body whose own shape is too fine for float32 even about its own centre
is refused by both writers. The midpoint is a tested rebase heuristic;
refusal does not prove that
every possible translation would fail.
"""

from __future__ import annotations

import json
import math
import struct
from pathlib import Path
from typing import Any, Final

from scpn_reactor_kernels.errors import GeometryError
from scpn_reactor_kernels.geometry.mesh import (
    TriangleMesh,
    Vertex,
    face_normal_and_area,
)

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

ORIGIN: Final[Vertex] = (0.0, 0.0, 0.0)
"""The translation that stores absolute coordinates: no rebase at all."""

LARGEST_FLOAT32: Final = 3.4028234663852886e38
"""Largest finite float32; a coordinate above it has no representation.

Measured with :func:`struct.pack`, not quoted: above this the standard
library raises :class:`OverflowError` rather than storing an infinity, and
that exception is not part of this module's contract, so the range is
checked here and refused as a :class:`GeometryError` naming the body.
"""

EXPORT_AREA_TOLERANCE: Final = 1.0e-3
"""Largest relative area change float32 storage may inflict on any facet.

**Chosen from measurement of the bodies that exist, not from the format.**
Across the fifty bodies of the six device families that use these writers
the worst measured value is ``5.61e-6``, and this library's own fixtures
sit at ``7.7e-7``; the bound is therefore about a hundred and eighty times
above anything real, and no export that works today is refused by it.

Below it the guarantee is worth stating: every triangle in the file has the
area it has in the mesh, to one part in a thousand. Above it the file is
not a record of the body any more. The corresponding limit on a body is a
ratio: coordinates may reach roughly ``1.7e4`` times the smallest feature,
since float32 resolves about ``6e-8`` of a coordinate. The worst ratio
among the real bodies is ``3.6e3``.

The bound cannot be tightened much further. A rebased body is no better
than the same body at the origin, and this library's tube is already at
``7.2e-7`` there, so a bound near that value would refuse bodies no
translation could rescue.
"""

EXPORT_STORAGE_CONTRACT: Final = (
    "float32 positions, 2.0.0: every stored coordinate is inside the "
    "float32 range, no facet collapses, and no facet's area changes by "
    "more than EXPORT_AREA_TOLERANCE; a GLB body that needs it is stored "
    "about the midpoint of its bounding box with that midpoint in the "
    "node translation, and binary STL refuses instead, since it has no "
    "transform to record one in"
)
"""The storage contract both writers enforce, named and versioned.

The contract is versioned here rather than in :data:`STL_HEADER` or
:data:`GLTF_GENERATOR`, because those strings are in every byte stream the
library has ever produced and changing them would rewrite every export to
distinguish a corpus of older files that measurably does not exist: no
``.stl``, ``.glb`` or ``.gltf`` is committed in this repository or in any
of the six device repositories that use these writers, and no consumer
records a digest of export bytes. A file that needs the new behaviour says
so itself, in its node translation.
"""


def _float32(value: float) -> float:
    """Round a double to the nearest float32 and return it as a float.

    Parameters
    ----------
    value
        A double whose magnitude is at most :data:`LARGEST_FLOAT32`; the
        callers check that first, so this never has to refuse.

    Returns
    -------
    float
        The nearest float32, as a double.
    """
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


def _require_translation(translation_m: Vertex) -> Vertex:
    """Refuse a translation that is not three finite doubles.

    Parameters
    ----------
    translation_m
        The caller's requested rebase.

    Returns
    -------
    Vertex
        The translation, unchanged.

    Raises
    ------
    GeometryError
        If it is not three components or any component is not finite.
    """
    if len(translation_m) != 3:
        raise GeometryError(
            f"translation_m: three components required, got {translation_m!r}"
        )
    for axis, value in enumerate(translation_m):
        if not math.isfinite(value):
            raise GeometryError(f"translation_m[{axis}]: must be finite, got {value!r}")
    return translation_m


def recommended_translation_m(meshes: tuple[TriangleMesh, ...]) -> Vertex:
    """Return the midpoint rebase evaluated for these bodies.

    Parameters
    ----------
    meshes
        The bodies that would share one coordinate system.

    Returns
    -------
    Vertex
        The midpoint of the bodies' shared bounding box, at full double
        precision.

    Raises
    ------
    GeometryError
        If the body list is empty or names repeat.

    Notes
    -----
    The midpoint was measured against three other rules on this library's
    bodies translated from the origin to ``1e12`` m, and it is the only one
    that leaves a rebased body as accurate as the same body at the origin
    (worst relative facet-area error ``7.17e-7`` at every offset). The
    body's first vertex is close behind at ``8.34e-7`` because a body
    reaches further from a corner than from its centre.

    **The two rules that would make the subtraction cheaper are both far
    worse, and the measurement is the reason they are not used here.**
    Rounding the midpoint to a float32 first costs ``8.0e-2`` at ``1e12``,
    because a float32 cannot name that midpoint closely enough and the
    residual is what gets stored. Snapping it down to a power of two is
    worse still and collapses facets from ``1e6`` upwards, since the
    residual can be as large as the coordinate itself. The translation is
    therefore kept as an ordinary double.
    """
    _require_bodies(meshes)
    return (
        _axis_midpoint(meshes, 0),
        _axis_midpoint(meshes, 1),
        _axis_midpoint(meshes, 2),
    )


def _axis_midpoint(meshes: tuple[TriangleMesh, ...], axis: int) -> float:
    """Midpoint of the bodies' shared extent along one axis."""
    lowest = min(vertex[axis] for mesh in meshes for vertex in mesh.vertices)
    highest = max(vertex[axis] for mesh in meshes for vertex in mesh.vertices)
    return 0.5 * lowest + 0.5 * highest


def _local_vertices(mesh: TriangleMesh, translation: Vertex) -> tuple[Vertex, ...]:
    """Return the mesh's vertices relative to a translation, in doubles."""
    return tuple(
        (
            vertex[0] - translation[0],
            vertex[1] - translation[1],
            vertex[2] - translation[2],
        )
        for vertex in mesh.vertices
    )


def _stored_vertices(local: tuple[Vertex, ...]) -> tuple[Vertex, ...]:
    """Return exactly what the container will hold: the float32 positions."""
    return tuple(
        (_float32(vertex[0]), _float32(vertex[1]), _float32(vertex[2]))
        for vertex in local
    )


def _area_or_none(v0: Vertex, v1: Vertex, v2: Vertex) -> float | None:
    """Area of a triangle, or ``None`` when its three corners are collinear.

    The library's own face measure is used rather than a local formula, so
    that the areas compared here are the areas the rest of the library
    reports, at every coordinate scale it can hold.
    """
    try:
        return face_normal_and_area(v0, v1, v2)[1]
    except GeometryError:
        return None


def _storage_failure(mesh: TriangleMesh, local: tuple[Vertex, ...]) -> str | None:
    """Return why this body does not survive float32 storage, or ``None``.

    Parameters
    ----------
    mesh
        The body, whose own float64 vertices are the reference the stored
        geometry is scored against.
    local
        Its vertices relative to the chosen translation, in doubles.

    Returns
    -------
    str or None
        A sentence naming the body and what went wrong, or ``None`` when
        the stored geometry meets :data:`EXPORT_STORAGE_CONTRACT`.

    Notes
    -----
    **The range is checked before anything is converted**, because
    :func:`struct.pack` raises :class:`OverflowError` on a coordinate above
    the float32 range rather than storing an infinity, and that exception
    would leave this module without ever naming the body. The first draft
    of this repair converted first and the reproducer caught it.
    """
    for index, vertex in enumerate(local):
        for axis, value in enumerate(vertex):
            if abs(value) > LARGEST_FLOAT32:
                return (
                    f"{mesh.name}: vertices[{index}][{axis}] is {value!r}, "
                    f"outside the float32 range of {LARGEST_FLOAT32!r}"
                )
    stored = _stored_vertices(local)
    for index, face in enumerate(mesh.faces):
        reference = face_normal_and_area(*(mesh.vertices[corner] for corner in face))[1]
        if _area_or_none(*(local[corner] for corner in face)) is None:
            return (
                f"{mesh.name}: faces[{index}] is degenerate after the "
                "requested translation, before any float32 rounding"
            )
        kept = _area_or_none(*(stored[corner] for corner in face))
        if kept is None:
            return (
                f"{mesh.name}: faces[{index}] collapses to a line or a point "
                "when its corners are stored as float32"
            )
        error = abs(kept - reference) / reference
        if error > EXPORT_AREA_TOLERANCE:
            return (
                f"{mesh.name}: faces[{index}] loses a relative area of "
                f"{error!r} when stored as float32, above the "
                f"{EXPORT_AREA_TOLERANCE!r} this writer guarantees"
            )
    return None


def _fitting_translation(mesh: TriangleMesh) -> Vertex:
    """Return the translation a GLB node needs, preferring none at all.

    A body that survives storage in absolute coordinates keeps them, so a
    document that never needed a rebase is byte-for-byte the document this
    writer produced before it could rebase at all.
    """
    absolute = _local_vertices(mesh, ORIGIN)
    if _storage_failure(mesh, absolute) is None:
        return ORIGIN
    return recommended_translation_m((mesh,))


def _stl_remedy(meshes: tuple[TriangleMesh, ...], suggestion: Vertex) -> str:
    """Name the way out of an STL refusal, but only one that would work.

    Parameters
    ----------
    meshes
        Every body of the refused document; a binary STL has one coordinate
        system, so a rebase has to serve all of them at once.
    suggestion
        The translation :func:`recommended_translation_m` returns for them.

    Returns
    -------
    str
        The clause appended to the refusal.

    Notes
    -----
    **A remedy is only offered once it has been measured on the bodies that
    were refused.** Naming a translation that would fail as well reads as
    advice and costs the caller a second refusal to discover it is not.
    """
    rebased_fails = any(
        _storage_failure(mesh, _local_vertices(mesh, suggestion)) is not None
        for mesh in meshes
    )
    if rebased_fails:
        return (
            "the recommended shared translation does not recover these bodies; "
            "use a higher-precision format or review the geometry and its "
            "precision requirements"
        )
    return (
        "binary STL has no node transform, so this writer will not rebase "
        f"on its own; pass translation_m={suggestion!r} to store the "
        "bodies about that point and record the value yourself, or export "
        "GLB, which carries the translation in the file"
    )


def _require_storage(
    mesh: TriangleMesh, local: tuple[Vertex, ...], remedy: str
) -> None:
    """Refuse a body the container cannot hold.

    Raises
    ------
    GeometryError
        With the body, the face and the measured loss, then the remedy.
    """
    failure = _storage_failure(mesh, local)
    if failure is not None:
        raise GeometryError(f"{failure}; {remedy}")


def stl_bytes(
    meshes: tuple[TriangleMesh, ...], *, translation_m: Vertex = ORIGIN
) -> bytes:
    """Serialise meshes as one binary STL document.

    Parameters
    ----------
    meshes
        Validated meshes; all bodies are concatenated in order.
    translation_m
        Coordinate rebase applied to every body before storage, in metres.
        The default stores absolute coordinates and moves nothing. **A
        non-default value moves the device**, and binary STL has nowhere to
        record that it did, so the caller owns the value and must carry it
        in its own provenance; :func:`recommended_translation_m` returns
        the one that stores these bodies most accurately.

    Returns
    -------
    bytes
        The binary STL document.

    Raises
    ------
    GeometryError
        If the body list is empty, names repeat, the translation is not
        three finite doubles, or a body does not survive float32 storage
        under :data:`EXPORT_STORAGE_CONTRACT`.
    """
    _require_bodies(meshes)
    translation = _require_translation(translation_m)
    parts = [STL_HEADER, struct.pack("<I", sum(mesh.face_count for mesh in meshes))]
    for mesh in meshes:
        local = _local_vertices(mesh, translation)
        failure = _storage_failure(mesh, local)
        if failure is not None:
            remedy = _stl_remedy(meshes, recommended_translation_m(meshes))
            raise GeometryError(f"{failure}; {remedy}")
        for face in mesh.faces:
            v0, v1, v2 = (local[corner] for corner in face)
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
        If the body list is empty, names repeat, the extras cannot be
        serialised, or a body does not survive float32 storage even about
        the midpoint of its own bounding box.

    Notes
    -----
    A body that needs it is stored in its own local coordinates with the
    rebase in the node's ``translation``, which composes with the mesh and
    leaves the body where it was. A body that does not need one keeps
    absolute coordinates and no ``translation`` key, so documents that were
    already right are byte-for-byte unchanged.
    """
    _require_bodies(meshes)
    binary = bytearray()
    buffer_views: list[dict[str, Any]] = []
    accessors: list[dict[str, Any]] = []
    mesh_records: list[dict[str, Any]] = []
    nodes: list[dict[str, Any]] = []
    for index, mesh in enumerate(meshes):
        translation = _fitting_translation(mesh)
        local = _local_vertices(mesh, translation)
        _require_storage(
            mesh,
            local,
            "the body's own shape is finer than float32 can hold about its "
            "own centre, so no node translation recovers it; coarsen the "
            "body or model it in units that give its features more digits",
        )
        stored = _stored_vertices(local)
        positions = b"".join(struct.pack("<3f", *vertex) for vertex in local)
        lows = [min(vertex[axis] for vertex in stored) for axis in range(3)]
        highs = [max(vertex[axis] for vertex in stored) for axis in range(3)]
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
        node: dict[str, Any] = {
            "name": mesh.name,
            "mesh": index,
            "extras": {
                "role": mesh.role,
                "material_identifier": mesh.material_identifier,
                "mesh_sha256": mesh.digest_sha256(),
            },
        }
        if translation != ORIGIN:
            node["translation"] = list(translation)
        nodes.append(node)
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


def write_stl(
    path: Path, meshes: tuple[TriangleMesh, ...], *, translation_m: Vertex = ORIGIN
) -> int:
    """Write a binary STL document.

    Parameters
    ----------
    path
        Destination file.
    meshes
        Validated meshes.
    translation_m
        Coordinate rebase, see :func:`stl_bytes`; the default moves nothing.

    Returns
    -------
    int
        Number of bytes written.

    Raises
    ------
    GeometryError
        For every reason :func:`stl_bytes` refuses; nothing is written when
        it does.
    """
    return path.write_bytes(stl_bytes(meshes, translation_m=translation_m))


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

    Raises
    ------
    GeometryError
        For every reason :func:`glb_bytes` refuses; nothing is written when
        it does.
    """
    return path.write_bytes(glb_bytes(meshes, extras))
