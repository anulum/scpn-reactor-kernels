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
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from geometry_fixtures import sample_bodies, sample_extras
from scpn_reactor_kernels.errors import GeometryError
from scpn_reactor_kernels.geometry import (
    GLTF_GENERATOR,
    STL_HEADER,
    TriangleMesh,
    glb_bytes,
    stl_bytes,
    write_glb,
    write_stl,
)
from scpn_reactor_kernels.geometry.export import (
    EXPORT_AREA_TOLERANCE,
    EXPORT_STORAGE_CONTRACT,
    LARGEST_FLOAT32,
    recommended_translation_m,
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


# --- what float32 storage does to the geometry -------------------------------

UNIT_TETRAHEDRON_FACES = ((0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3))
UNIT_TETRAHEDRON_VERTICES = (
    (0.0, 0.0, 0.0),
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
)

LARGEST_ACCEPTED_TETRAHEDRON_OFFSET_M = 16484177.499999998
"""Largest offset at which a one-metre tetrahedron is still written.

Bisected over float64 bit ordinals against the writer itself, so the value
below it and the one above are adjacent doubles and the refusal test can
assert the nearest failing case.
"""

LARGEST_ACCEPTED_SAMPLE_BODY_OFFSET_M = 63.99925751495179
"""Largest offset at which the fixture bodies still meet the tolerance.

The tube's wall is one centimetre; past sixty-four metres of offset float32
can no longer hold it to one part in a thousand. Bisected the same way.
"""

WORST_MEASURED_FIXTURE_AREA_ERROR = 7.7e-7
"""Worst relative facet-area error the fixtures suffer at the origin.

Measured at 7.682642722556756e-07 on the tube at 32 segments, which is the
floor no rebase can improve on and the reason the tolerance is not set
anywhere near it.
"""


def tetrahedron(
    offset: float = 0.0, edge: float = 1.0, name: str = "probe"
) -> TriangleMesh:
    """Return a closed four-face body at a chosen scale and offset."""
    return TriangleMesh(
        name=name,
        role="plasma",
        material_identifier="declared",
        vertices=tuple(
            (
                vertex[0] * edge + offset,
                vertex[1] * edge + offset,
                vertex[2] * edge + offset,
            )
            for vertex in UNIT_TETRAHEDRON_VERTICES
        ),
        faces=UNIT_TETRAHEDRON_FACES,
    )


def moved(mesh: TriangleMesh, offset: float) -> TriangleMesh:
    """Return the same body translated along the diagonal."""
    return TriangleMesh(
        name=mesh.name,
        role=mesh.role,
        material_identifier=mesh.material_identifier,
        vertices=tuple(
            (vertex[0] + offset, vertex[1] + offset, vertex[2] + offset)
            for vertex in mesh.vertices
        ),
        faces=mesh.faces,
    )


def triangle_area(a: Any, b: Any, c: Any) -> float:
    """Area of a triangle from three corners, zero when they are collinear.

    Written out here rather than taken from the library, so that what the
    tests measure on decoded bytes does not depend on the same code the
    exporter uses to decide.
    """
    u = tuple(b[axis] - a[axis] for axis in range(3))
    v = tuple(c[axis] - a[axis] for axis in range(3))
    cross = (
        u[1] * v[2] - u[2] * v[1],
        u[2] * v[0] - u[0] * v[2],
        u[0] * v[1] - u[1] * v[0],
    )
    return 0.5 * math.sqrt(sum(component * component for component in cross))


def decode_stl_triangles(data: bytes) -> list[tuple[Any, Any, Any]]:
    """Every triangle of a binary STL, read back as three float32 corners."""
    count = struct.unpack_from("<I", data, 80)[0]
    triangles = []
    for index in range(count):
        values = struct.unpack_from("<12f", data, 84 + index * 50)
        triangles.append((values[3:6], values[6:9], values[9:12]))
    return triangles


def decode_glb_body(
    document: dict[str, Any], binary: bytes, index: int
) -> tuple[list[tuple[float, ...]], list[tuple[int, int, int]], tuple[float, ...]]:
    """Read one GLB node back the way the specification says to.

    Returns the node's stored positions, its triangles as index triples and
    the node's translation, defaulting to the origin when the node carries
    none. Composing the translation with the positions is what a conformant
    consumer does, and it is what places the body in the world.
    """
    node = document["nodes"][index]
    primitive = document["meshes"][node["mesh"]]["primitives"][0]
    position_accessor = document["accessors"][primitive["attributes"]["POSITION"]]
    index_accessor = document["accessors"][primitive["indices"]]
    position_view = document["bufferViews"][position_accessor["bufferView"]]
    index_view = document["bufferViews"][index_accessor["bufferView"]]
    raw = binary[
        position_view["byteOffset"] : position_view["byteOffset"]
        + position_view["byteLength"]
    ]
    positions = [
        struct.unpack_from("<3f", raw, corner * 12)
        for corner in range(position_accessor["count"])
    ]
    raw = binary[
        index_view["byteOffset"] : index_view["byteOffset"] + index_view["byteLength"]
    ]
    faces = [
        struct.unpack_from("<3I", raw, face * 12)
        for face in range(index_accessor["count"] // 3)
    ]
    translation = tuple(node.get("translation", (0.0, 0.0, 0.0)))
    return positions, faces, translation


def test_the_stored_triangles_are_the_body_within_the_declared_tolerance() -> None:
    """Decoded bytes, not written bytes, are what a consumer receives.

    Both containers are read back with the readers above and every triangle
    is measured again from the decoded float32 corners. A test that checked
    only the header, the length or repeatability would have passed on every
    version of this module, including the one that stored four distinct
    corners as one point.
    """
    bodies = sample_bodies(32)
    triangles = decode_stl_triangles(stl_bytes(bodies))
    document, binary = read_glb(glb_bytes(bodies, sample_extras()))
    stl_worst = 0.0
    glb_worst = 0.0
    position = 0
    for index, mesh in enumerate(bodies):
        positions, faces, translation = decode_glb_body(document, binary, index)
        assert translation == (0.0, 0.0, 0.0)
        assert faces == [tuple(face) for face in mesh.faces]
        for face in mesh.faces:
            reference = triangle_area(*(mesh.vertices[corner] for corner in face))
            assert reference > 0.0
            stl_worst = max(
                stl_worst,
                abs(triangle_area(*triangles[position]) - reference) / reference,
            )
            glb_worst = max(
                glb_worst,
                abs(triangle_area(*(positions[corner] for corner in face)) - reference)
                / reference,
            )
            position += 1
    assert position == len(triangles)
    assert stl_worst <= EXPORT_AREA_TOLERANCE
    assert glb_worst <= EXPORT_AREA_TOLERANCE
    assert stl_worst <= WORST_MEASURED_FIXTURE_AREA_ERROR
    assert glb_worst <= WORST_MEASURED_FIXTURE_AREA_ERROR


def test_the_reported_collapse_is_refused_by_binary_stl() -> None:
    """Four distinct corners becoming one point is not a file, it is a loss."""
    with pytest.raises(GeometryError, match="collapses to a line or a point"):
        stl_bytes((tetrahedron(offset=1.0e8),))


def test_binary_stl_accepts_the_last_offset_that_survives_and_refuses_the_next() -> (
    None
):
    """The refusal is asserted at the nearest failing case, not a decade above.

    The two offsets are adjacent doubles: there is no value between them at
    which the writer could be doing something else.
    """
    largest = LARGEST_ACCEPTED_TETRAHEDRON_OFFSET_M
    smallest_refused = math.nextafter(largest, math.inf)
    assert stl_bytes((tetrahedron(offset=largest),))
    with pytest.raises(GeometryError, match="collapses to a line or a point"):
        stl_bytes((tetrahedron(offset=smallest_refused),))


def test_the_fixture_bodies_are_refused_at_the_nearest_offset_that_loses_them() -> None:
    """The tolerance, not the collapse, is what stops an ordinary body.

    A one-centimetre wall sixty-four metres from the origin has lost a
    thousandth of its facets' area while every triangle is still a triangle,
    which is exactly the damage the collapse check alone cannot see.
    """
    largest = LARGEST_ACCEPTED_SAMPLE_BODY_OFFSET_M
    accepted = tuple(moved(mesh, largest) for mesh in sample_bodies(16))
    refused = tuple(
        moved(mesh, math.nextafter(largest, math.inf)) for mesh in sample_bodies(16)
    )
    assert stl_bytes(accepted)
    with pytest.raises(GeometryError, match="loses a relative area of"):
        stl_bytes(refused)


def test_glb_carries_the_far_body_in_a_node_translation() -> None:
    """The device is not moved; the coordinate system it is stored in is.

    The decoded positions are local, the node translation puts them back,
    and every triangle keeps its area. This is the whole reason GLB does not
    have to refuse where STL does.
    """
    body = tetrahedron(offset=1.0e12)
    document, binary = read_glb(glb_bytes((body,), sample_extras()))
    positions, faces, translation = decode_glb_body(document, binary, 0)
    assert translation != (0.0, 0.0, 0.0)
    assert faces == [tuple(face) for face in body.faces]
    assert len(set(positions)) == len(body.vertices)
    for face in body.faces:
        reference = triangle_area(*(body.vertices[corner] for corner in face))
        stored = triangle_area(*(positions[corner] for corner in face))
        assert abs(stored - reference) / reference <= EXPORT_AREA_TOLERANCE
    world = [
        tuple(position[axis] + translation[axis] for axis in range(3))
        for position in positions
    ]
    for placed, original in zip(world, body.vertices, strict=True):
        for axis in range(3):
            assert abs(placed[axis] - original[axis]) <= abs(original[axis]) * 1.0e-7


def test_the_node_translation_is_written_at_full_double_precision() -> None:
    """A float32 translation was measured to be eighty times worse.

    The JSON text carries the exact double, so a consumer that wants the
    placement can have it; one that keeps translations in float32 places the
    body to float32 resolution and still gets its shape exactly.
    """
    body = tetrahedron(offset=1.0e12)
    document, _ = read_glb(glb_bytes((body,), sample_extras()))
    translation = document["nodes"][0]["translation"]
    assert translation == [1.0000000000005e12] * 3
    assert any(
        value != struct.unpack("<f", struct.pack("<f", value))[0]
        for value in translation
    )


def test_a_body_that_needs_no_rebase_carries_no_translation_key() -> None:
    """Documents that were already right keep the bytes they always had."""
    document, _ = read_glb(glb_bytes(sample_bodies(8), sample_extras()))
    assert all("translation" not in node for node in document["nodes"])


def test_an_explicit_translation_lets_binary_stl_carry_the_far_body() -> None:
    """The caller asks for the rebase, and owns the value afterwards."""
    body = tetrahedron(offset=1.0e12)
    translation = recommended_translation_m((body,))
    triangles = decode_stl_triangles(stl_bytes((body,), translation_m=translation))
    for face, triangle in zip(body.faces, triangles, strict=True):
        reference = triangle_area(*(body.vertices[corner] for corner in face))
        assert abs(triangle_area(*triangle) - reference) / reference <= (
            EXPORT_AREA_TOLERANCE
        )
    written = write_stl(
        Path(tempfile.mkdtemp()) / "far.stl", (body,), translation_m=translation
    )
    assert written == len(stl_bytes((body,), translation_m=translation))


def test_the_recommended_translation_is_the_midpoint_of_the_shared_extent() -> None:
    """One translation serves every body of a binary STL, since it has one frame."""
    bodies = sample_bodies(8)
    translation = recommended_translation_m(bodies)
    for axis in range(3):
        lowest = min(vertex[axis] for mesh in bodies for vertex in mesh.vertices)
        highest = max(vertex[axis] for mesh in bodies for vertex in mesh.vertices)
        assert translation[axis] == 0.5 * (lowest + highest)


@pytest.mark.parametrize("container", ["stl", "glb"])
def test_a_coordinate_beyond_the_float32_range_is_named_not_an_overflow(
    container: str,
) -> None:
    """The container's own limit is refused as a geometry error.

    Packing such a coordinate raises OverflowError from the standard
    library, which is not in either writer's documented contract and names
    neither the body nor the vertex.
    """
    body = tetrahedron(edge=1.0e39, name="huge")
    write: Callable[[], bytes] = (
        (lambda: stl_bytes((body,)))
        if container == "stl"
        else (lambda: glb_bytes((body,), sample_extras()))
    )
    with pytest.raises(GeometryError, match="outside the float32 range"):
        write()


def test_the_largest_float32_coordinate_is_accepted_and_the_next_double_is_not() -> (
    None
):
    """The range check is asserted at the boundary itself."""
    assert stl_bytes((tetrahedron(edge=LARGEST_FLOAT32, name="edge"),))
    with pytest.raises(GeometryError, match="outside the float32 range"):
        stl_bytes(
            (tetrahedron(edge=math.nextafter(LARGEST_FLOAT32, math.inf), name="edge"),)
        )


def test_the_remedy_is_offered_only_when_it_would_work() -> None:
    """Naming a translation that fails as well is advice, not a refusal.

    A body that is merely far away is told which translation to pass. A body
    which the midpoint cannot rescue gets no unverified promise that some
    other translation or change of units will help.
    """
    with pytest.raises(GeometryError, match="pass translation_m="):
        stl_bytes((tetrahedron(offset=1.0e8),))
    with pytest.raises(
        GeometryError, match="recommended shared translation does not recover"
    ):
        stl_bytes((tetrahedron(edge=1.0e39, name="huge"),))


def test_glb_refuses_a_body_its_own_centre_cannot_rescue() -> None:
    """What float32 cannot hold is a fine feature far from the body's middle.

    A micrometre feature at the end of a metre-long body loses three
    quarters of a per cent of a facet's area even about the body's own
    centre, and no translation helps, because the coordinate it sits on is
    still half a metre from wherever the centre is put. The refusal says so
    instead of writing the file.
    """
    body = TriangleMesh(
        name="sliver",
        role="plasma",
        material_identifier="declared",
        vertices=(
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (1.0 + 1.0e-6, 1.0e-6, 0.0),
            (0.5, 0.0, 1.0),
        ),
        faces=UNIT_TETRAHEDRON_FACES,
    )
    with pytest.raises(GeometryError, match="no node translation recovers it"):
        glb_bytes((body,), sample_extras())


def test_a_fine_feature_at_the_origin_is_stored_and_a_far_one_is_not() -> None:
    """The size of a feature is not what decides; where it sits is.

    Both bodies below have a feature far below float32's seven digits. The
    first keeps it, because a small coordinate is stored with all of those
    digits to itself. The second loses it, because the same difference has
    to share the digits of a coordinate half a metre from the centre. A
    writer that gated on feature size alone would get both wrong.
    """
    near = TriangleMesh(
        name="near",
        role="plasma",
        material_identifier="declared",
        vertices=(
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (0.0, 1.0e-9, 0.0),
            (0.0, 0.0, 1.0e-9),
        ),
        faces=UNIT_TETRAHEDRON_FACES,
    )
    far = TriangleMesh(
        name="far",
        role="plasma",
        material_identifier="declared",
        vertices=(
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (1.0 + 1.0e-9, 1.0e-9, 0.0),
            (0.5, 0.0, 1.0),
        ),
        faces=UNIT_TETRAHEDRON_FACES,
    )
    assert glb_bytes((near,), sample_extras())
    with pytest.raises(GeometryError, match="loses a relative area of"):
        glb_bytes((far,), sample_extras())


def test_a_translation_that_destroys_the_body_in_doubles_is_refused() -> None:
    """The float64 grid gives out before float32 does, and says which one did."""
    tiny = tetrahedron(edge=1.0e-30, name="tiny")
    with pytest.raises(GeometryError, match="before any float32 rounding"):
        stl_bytes((tiny,), translation_m=(1.0e8, 1.0e8, 1.0e8))


@pytest.mark.parametrize(
    "translation",
    [
        (0.0, 0.0),
        (0.0, 0.0, 0.0, 0.0),
        (math.nan, 0.0, 0.0),
        (0.0, math.inf, 0.0),
    ],
)
def test_a_translation_that_is_not_three_finite_numbers_is_refused(
    translation: Any,
) -> None:
    """Every component is validated, and the arity before them."""
    with pytest.raises(GeometryError, match="translation_m"):
        stl_bytes(sample_bodies(8), translation_m=translation)


def test_the_storage_contract_names_what_both_writers_enforce() -> None:
    """The contract is versioned in a readable constant, not in every byte.

    Changing the header strings would have rewritten every export in order
    to distinguish a corpus of older files that does not exist; measured,
    no export artefact is committed in this repository or in any consumer.
    """
    assert "2.0.0" in EXPORT_STORAGE_CONTRACT
    expected_header = b"SCPN Reactor Kernels geometry_exports 1.0.0 binary STL"
    assert expected_header.ljust(80, b" ") == STL_HEADER
    assert GLTF_GENERATOR == "scpn-reactor-kernels geometry_exports 1.0.0"
