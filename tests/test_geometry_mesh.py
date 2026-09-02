# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — triangle mesh contract tests

"""Every validation branch, measure and serialisation of TriangleMesh."""

from __future__ import annotations

import hashlib
import math
import struct

import pytest

from scpn_reactor_kernels.errors import GeometryError
from scpn_reactor_kernels.geometry import (
    MESH_BYTES_LAYOUT,
    Face,
    TriangleMesh,
    Vertex,
    face_normal_and_area,
)

TETRA_VERTICES: tuple[Vertex, ...] = (
    (0.0, 0.0, 0.0),
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
)
TETRA_FACES: tuple[Face, ...] = ((0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3))


def tetrahedron(**overrides: object) -> TriangleMesh:
    """Build the unit tetrahedron with optional field overrides."""
    fields: dict[str, object] = {
        "name": "tetra",
        "role": "test",
        "material_identifier": "none",
        "vertices": TETRA_VERTICES,
        "faces": TETRA_FACES,
    }
    fields.update(overrides)
    return TriangleMesh(**fields)  # type: ignore[arg-type]


def test_measures_of_the_unit_tetrahedron() -> None:
    """Volume, area and bounding box match the closed forms."""
    mesh = tetrahedron()
    assert mesh.vertex_count == 4
    assert mesh.face_count == 4
    assert abs(mesh.signed_volume_m3() - 1.0 / 6.0) <= 1.0e-16
    expected_area = 1.5 + math.sqrt(3.0) / 2.0
    assert abs(mesh.surface_area_m2() - expected_area) <= 1.0e-15
    assert mesh.bounding_box() == ((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))


def test_face_normal_and_area() -> None:
    """The oblique face has the unit normal (1,1,1)/sqrt(3) and area sqrt(3)/2."""
    normal, area = face_normal_and_area(
        TETRA_VERTICES[1], TETRA_VERTICES[2], TETRA_VERTICES[3]
    )
    root = 1.0 / math.sqrt(3.0)
    assert all(abs(component - root) <= 1.0e-16 for component in normal)
    assert abs(area - math.sqrt(3.0) / 2.0) <= 1.0e-16
    with pytest.raises(GeometryError, match="degenerate"):
        face_normal_and_area((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (2.0, 0.0, 0.0))


def test_canonical_bytes_layout_and_digest() -> None:
    """The byte layout is the documented little-endian stream."""
    mesh = tetrahedron()
    data = mesh.canonical_bytes()
    assert struct.unpack_from("<II", data, 0) == (4, 4)
    offset = 8
    for vertex in TETRA_VERTICES:
        assert struct.unpack_from("<ddd", data, offset) == vertex
        offset += 24
    for face in TETRA_FACES:
        assert struct.unpack_from("<III", data, offset) == face
        offset += 12
    assert offset == len(data)
    assert mesh.digest_sha256() == hashlib.sha256(data).hexdigest()
    assert "little-endian" in MESH_BYTES_LAYOUT


def test_summary_record_carries_every_field() -> None:
    """The summary is the JSON projection used by the model record."""
    record = tetrahedron().summary_record()
    assert record["name"] == "tetra"
    assert record["role"] == "test"
    assert record["material_identifier"] == "none"
    assert record["vertex_count"] == 4
    assert record["face_count"] == 4
    assert record["bounding_box_min_m"] == [0.0, 0.0, 0.0]
    assert record["bounding_box_max_m"] == [1.0, 1.0, 1.0]
    assert len(record["mesh_sha256"]) == 64


@pytest.mark.parametrize("field", ["name", "role", "material_identifier"])
def test_empty_identity_is_refused(field: str) -> None:
    """Every identity token must be non-empty."""
    with pytest.raises(GeometryError, match=f"{field}: must be non-empty"):
        tetrahedron(**{field: ""})


def test_too_few_vertices_is_refused() -> None:
    """A closed surface needs at least four vertices."""
    with pytest.raises(GeometryError, match="vertices: at least 4"):
        tetrahedron(vertices=TETRA_VERTICES[:3])


def test_non_finite_vertex_is_refused() -> None:
    """NaN coordinates fail closed."""
    bad = ((math.nan, 0.0, 0.0), *TETRA_VERTICES[1:])
    with pytest.raises(GeometryError, match=r"vertices\[0\]: must be finite"):
        tetrahedron(vertices=bad)


def test_too_few_faces_is_refused() -> None:
    """A closed surface needs at least four faces."""
    with pytest.raises(GeometryError, match="faces: at least 4"):
        tetrahedron(faces=TETRA_FACES[:3])


@pytest.mark.parametrize("corner", [4, -1, True])
def test_index_out_of_range_is_refused(corner: int) -> None:
    """Indices outside [0, count) and booleans fail closed."""
    faces = ((corner, 2, 1), *TETRA_FACES[1:])
    with pytest.raises(GeometryError, match="out of range"):
        tetrahedron(faces=faces)


def test_repeated_index_is_refused() -> None:
    """A face must reference three distinct vertices."""
    faces = ((0, 0, 1), *TETRA_FACES[1:])
    with pytest.raises(GeometryError, match="repeated vertex index"):
        tetrahedron(faces=faces)


def test_degenerate_face_is_refused() -> None:
    """Three distinct but collinear vertices have zero area."""
    vertices = (*TETRA_VERTICES, (2.0, 0.0, 0.0))
    faces = ((0, 1, 4), *TETRA_FACES[1:])
    with pytest.raises(GeometryError, match=r"faces\[0\]: face: degenerate"):
        tetrahedron(vertices=vertices, faces=faces)


def test_duplicate_directed_edge_is_refused() -> None:
    """A duplicated face (same orientation) repeats its directed edges."""
    faces = (*TETRA_FACES, TETRA_FACES[0])
    with pytest.raises(GeometryError, match="appears twice"):
        tetrahedron(faces=faces)


def test_open_surface_is_refused() -> None:
    """Dropping one face of a five-face closed surface leaves unmatched edges."""
    vertices = (*TETRA_VERTICES, (1.0, 1.0, 1.0))
    faces: tuple[Face, ...] = (
        (0, 2, 1),
        (0, 1, 3),
        (0, 3, 2),
        (1, 2, 4),
        (2, 3, 4),
        (3, 1, 4),
    )
    TriangleMesh(
        name="hexa", role="t", material_identifier="m", vertices=vertices, faces=faces
    )
    with pytest.raises(GeometryError, match="has no reverse"):
        tetrahedron(vertices=vertices, faces=faces[:5])


def test_inconsistent_orientation_is_refused() -> None:
    """Flipping one face duplicates a directed edge of its neighbour."""
    faces = ((0, 1, 2), *TETRA_FACES[1:])
    with pytest.raises(GeometryError, match="appears twice"):
        tetrahedron(faces=faces)
