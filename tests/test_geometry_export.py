# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — open-format export tests

"""Binary STL and GLB layouts read back with minimal spec-level readers."""

from __future__ import annotations

import json
import math
import struct
from pathlib import Path
from typing import Any

import pytest

from geometry_fixtures import sample_bodies, sample_extras
from scpn_reactor_kernels.errors import GeometryError
from scpn_reactor_kernels.geometry import (
    GLTF_GENERATOR,
    STL_HEADER,
    glb_bytes,
    stl_bytes,
    write_glb,
    write_stl,
)


def read_glb(data: bytes) -> tuple[dict[str, Any], bytes]:
    """Parse a GLB container per the glTF 2.0 binary layout."""
    magic, version, total = struct.unpack_from("<III", data, 0)
    assert magic == 0x46546C67
    assert version == 2
    assert total == len(data)
    json_length, json_type = struct.unpack_from("<II", data, 12)
    assert json_type == 0x4E4F534A
    assert json_length % 4 == 0
    document = json.loads(data[20 : 20 + json_length].decode("utf-8"))
    offset = 20 + json_length
    bin_length, bin_type = struct.unpack_from("<II", data, offset)
    assert bin_type == 0x004E4942
    assert bin_length % 4 == 0
    binary = data[offset + 8 : offset + 8 + bin_length]
    assert offset + 8 + bin_length == total
    return document, binary


@pytest.mark.parametrize("segments", [8, 16, 24, 32])
def test_glb_layout_nodes_and_accessors(segments: int) -> None:
    """Every body is one named node with aligned position and index accessors."""
    bodies = sample_bodies(segments)
    document, binary = read_glb(glb_bytes(bodies, sample_extras()))
    assert document["asset"] == {"version": "2.0", "generator": GLTF_GENERATOR}
    assert document["scenes"] == [{"nodes": [0, 1, 2]}]
    assert [node["name"] for node in document["nodes"]] == [m.name for m in bodies]
    assert document["buffers"][0]["byteLength"] <= len(binary)
    assert document["extras"] == sample_extras()
    for index, mesh in enumerate(bodies):
        node = document["nodes"][index]
        assert node["mesh"] == index
        assert node["extras"] == {
            "role": mesh.role,
            "material_identifier": mesh.material_identifier,
            "mesh_sha256": mesh.digest_sha256(),
        }
        primitive = document["meshes"][index]["primitives"][0]
        assert primitive["mode"] == 4
        positions = document["accessors"][primitive["attributes"]["POSITION"]]
        indices = document["accessors"][primitive["indices"]]
        assert positions["count"] == mesh.vertex_count
        assert positions["type"] == "VEC3"
        assert indices["count"] == 3 * mesh.face_count
        assert indices["componentType"] == 5125
        view = document["bufferViews"][positions["bufferView"]]
        assert view["byteOffset"] % 4 == 0
        assert view["byteLength"] == 12 * mesh.vertex_count
        first = struct.unpack_from("<3f", binary, view["byteOffset"])
        expected = struct.unpack("<3f", struct.pack("<3f", *mesh.vertices[0]))
        assert first == expected
        assert positions["min"] == [
            min(
                struct.unpack("<f", struct.pack("<f", v[axis]))[0]
                for v in mesh.vertices
            )
            for axis in range(3)
        ]
        index_view = document["bufferViews"][indices["bufferView"]]
        stream = struct.unpack_from(
            f"<{3 * mesh.face_count}I", binary, index_view["byteOffset"]
        )
        assert stream[:3] == mesh.faces[0]


def test_glb_is_deterministic() -> None:
    """The same bodies and extras yield identical bytes."""
    bodies = sample_bodies(8)
    assert glb_bytes(bodies, sample_extras()) == glb_bytes(bodies, sample_extras())


def test_empty_or_duplicate_bodies_are_refused() -> None:
    """Both exporters refuse an empty list and repeated node names."""
    with pytest.raises(GeometryError, match="at least one body"):
        stl_bytes(())
    with pytest.raises(GeometryError, match="at least one body"):
        glb_bytes((), sample_extras())
    body = sample_bodies(8)[0]
    with pytest.raises(GeometryError, match="must be unique"):
        stl_bytes((body, body))


def test_non_serialisable_extras_are_refused() -> None:
    """Extras with NaN or non-JSON values fail closed."""
    bodies = sample_bodies(8)
    with pytest.raises(GeometryError, match="not JSON-serialisable"):
        glb_bytes(bodies, {"value": math.nan})
    with pytest.raises(GeometryError, match="not JSON-serialisable"):
        glb_bytes(bodies, {"value": object()})


def test_stl_layout() -> None:
    """The binary STL carries every face with a unit normal and zero attribute."""
    bodies = sample_bodies(8)
    data = stl_bytes(bodies)
    assert data[:80] == STL_HEADER
    assert not data.startswith(b"solid")
    count = struct.unpack_from("<I", data, 80)[0]
    assert count == sum(mesh.face_count for mesh in bodies)
    assert len(data) == 84 + 50 * count
    offset = 84
    for mesh in bodies:
        for face in mesh.faces:
            normal = struct.unpack_from("<3f", data, offset)
            length = sum(component * component for component in normal)
            assert abs(length - 1.0) <= 1.0e-6
            vertices = struct.unpack_from("<9f", data, offset + 12)
            expected = struct.unpack(
                "<9f",
                struct.pack(
                    "<9f", *(c for corner in face for c in mesh.vertices[corner])
                ),
            )
            assert vertices == expected
            assert struct.unpack_from("<H", data, offset + 48)[0] == 0
            offset += 50


def test_writers_create_files(tmp_path: Path) -> None:
    """The file writers persist exactly the serialised bytes."""
    bodies = sample_bodies(8)
    stl_path = tmp_path / "bodies.stl"
    glb_path = tmp_path / "bodies.glb"
    assert write_stl(stl_path, bodies) == len(stl_bytes(bodies))
    assert write_glb(glb_path, bodies, sample_extras()) == len(
        glb_bytes(bodies, sample_extras())
    )
    assert stl_path.read_bytes() == stl_bytes(bodies)
    assert glb_path.read_bytes() == glb_bytes(bodies, sample_extras())
