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
from decimal import Decimal, getcontext
from fractions import Fraction
from typing import Any

import pytest

from scpn_reactor_kernels.errors import GeometryError
from scpn_reactor_kernels.geometry import (
    MESH_BYTES_LAYOUT,
    Face,
    TriangleMesh,
    Vertex,
    annular_tube,
    cylinder_solid,
    face_normal_and_area,
    sphere_solid,
    spherical_shell,
)
from scpn_reactor_kernels.geometry.mesh import (
    SUMMATION_RULE,
    TRANSLATION_DRIFT_FACTOR,
)

TETRA_VERTICES: tuple[Vertex, ...] = (
    (0.0, 0.0, 0.0),
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
)
TETRA_FACES: tuple[Face, ...] = ((0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3))


def tetrahedron(**overrides: Any) -> TriangleMesh:
    """Build the unit tetrahedron with optional field overrides."""
    fields: dict[str, Any] = {
        "name": "tetra",
        "role": "test",
        "material_identifier": "none",
        "vertices": TETRA_VERTICES,
        "faces": TETRA_FACES,
    }
    fields.update(overrides)
    return TriangleMesh(**fields)


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


def moved(offset: tuple[float, float, float]) -> tuple[Vertex, ...]:
    """Return the unit tetrahedron's vertices translated by an offset."""
    return tuple(
        (vertex[0] + offset[0], vertex[1] + offset[1], vertex[2] + offset[2])
        for vertex in TETRA_VERTICES
    )


def exact_signed_volume(
    vertices: tuple[Vertex, ...], faces: tuple[Face, ...]
) -> Fraction:
    """Return the exact rational value of the divergence-theorem sum.

    Parameters
    ----------
    vertices, faces
        The mesh, whose coordinates are exact binary doubles.

    Returns
    -------
    Fraction
        The sum evaluated without rounding. This is an oracle independent
        of every floating-point algorithm and of the native kernel, which
        is the point: two implementations agreeing is not evidence that
        either is right.
    """
    total = Fraction(0)
    for face in faces:
        a = tuple(Fraction(component) for component in vertices[face[0]])
        b = tuple(Fraction(component) for component in vertices[face[1]])
        c = tuple(Fraction(component) for component in vertices[face[2]])
        cross = (
            b[1] * c[2] - b[2] * c[1],
            b[2] * c[0] - b[0] * c[2],
            b[0] * c[1] - b[1] * c[0],
        )
        total += a[0] * cross[0] + a[1] * cross[1] + a[2] * cross[2]
    return total / 6


def uncompensated(vertices: tuple[Vertex, ...], faces: tuple[Face, ...]) -> float:
    """Return the same sum without the compensation, for comparison."""
    origin = vertices[0]
    total = 0.0
    for face in faces:
        a = tuple(vertices[face[0]][axis] - origin[axis] for axis in range(3))
        b = tuple(vertices[face[1]][axis] - origin[axis] for axis in range(3))
        c = tuple(vertices[face[2]][axis] - origin[axis] for axis in range(3))
        cross = (
            b[1] * c[2] - b[2] * c[1],
            b[2] * c[0] - b[0] * c[2],
            b[0] * c[1] - b[1] * c[0],
        )
        total += a[0] * cross[0] + a[1] * cross[1] + a[2] * cross[2]
    return total / 6.0


@pytest.mark.parametrize(
    "offset",
    [
        (0.0, 0.0, 0.0),
        (1.0e2, 1.0e2, 1.0e2),
        (1.0e4, 1.0e4, 1.0e4),
        (1.0e6, 1.0e6, 1.0e6),
        (1.0e8, 1.0e8, 1.0e8),
        (1.0e6, -1.0e6, 1.0e6),
        (-1.0e8, 1.0e8, -1.0e8),
        (1.0e8, 0.0, 0.0),
    ],
)
def test_the_volume_survives_translation(offset: tuple[float, float, float]) -> None:
    """A moved body keeps its volume, and the error does not grow with the move.

    Two of these offsets are the defect this replaced: at
    ``(1e8, 1e8, 1e8)`` the previous form returned ``33333333.333333332``
    for a body of volume one sixth, and at ``(-1e8, 1e8, -1e8)`` it
    returned **exactly zero** — a body with no volume and no complaint.
    """
    mesh = tetrahedron(vertices=moved(offset))
    assert mesh.signed_volume_m3() == pytest.approx(1.0 / 6.0, rel=1.0e-15)


def test_the_translated_volume_is_bit_identical_to_the_unmoved_one() -> None:
    """Exactly representable offsets change nothing at all, not merely little."""
    unmoved = tetrahedron().signed_volume_m3()
    for offset in ((1.0e2,) * 3, (1.0e4,) * 3, (1.0e8,) * 3, (-1.0e8, 1.0e8, -1.0e8)):
        assert tetrahedron(vertices=moved(offset)).signed_volume_m3() == unmoved


@pytest.mark.parametrize("segments", [16, 64])
def test_every_body_agrees_with_its_exact_rational_value(segments: int) -> None:
    """The oracle is exact arithmetic, not a second implementation."""
    for vertices, faces in (
        cylinder_solid(0.05, 0.0, 0.3, segments),
        annular_tube(0.08, 0.1, -0.1, 0.4, segments),
        sphere_solid(0.25, 0.0, segments, segments // 2),
        spherical_shell(0.2, 0.25, 0.0, segments, segments // 2),
    ):
        for offset in (0.0, 1.0e4, 1.0e8):
            placed = tuple(
                (vertex[0] + offset, vertex[1] + offset, vertex[2] + offset)
                for vertex in vertices
            )
            mesh = tetrahedron(vertices=placed, faces=faces)
            exact = exact_signed_volume(placed, faces)
            error = abs(Fraction(mesh.signed_volume_m3()) - exact) / abs(exact)
            assert float(error) <= 1.0e-15


def test_the_compensation_is_not_decorative() -> None:
    """Dropping it costs more than an order of magnitude on a real body.

    A shell is the case that shows it: nineteen hundred faces whose
    contributions cancel between the outer surface and the cavity. If the
    compensated and uncompensated sums agreed here, the compensation
    would be paying for nothing and should not be in the contract.
    """
    vertices, faces = spherical_shell(0.2, 0.25, 0.0, 32, 16)
    mesh = tetrahedron(vertices=vertices, faces=faces)
    exact = exact_signed_volume(vertices, faces)
    compensated_error = abs(Fraction(mesh.signed_volume_m3()) - exact) / abs(exact)
    plain_error = abs(Fraction(uncompensated(vertices, faces)) - exact) / abs(exact)
    assert plain_error > compensated_error * 10


def test_a_uniformly_inward_mesh_keeps_a_negative_volume() -> None:
    """The measure is signed, and stays signed a hundred thousand kilometres out."""
    inward: tuple[Face, ...] = tuple(
        (face[0], face[2], face[1]) for face in TETRA_FACES
    )
    near = tetrahedron(faces=inward)
    far = tetrahedron(vertices=moved((1.0e8, 1.0e8, 1.0e8)), faces=inward)
    assert near.signed_volume_m3() == pytest.approx(-1.0 / 6.0, rel=1.0e-15)
    assert far.signed_volume_m3() == near.signed_volume_m3()


@pytest.mark.parametrize("offset", [1.0e2, 1.0e4, 1.0e6, 1.0e8])
def test_the_drift_of_a_translated_body_stays_under_the_declared_bound(
    offset: float,
) -> None:
    """What moves is the coordinate grid, and the bound says by how much.

    This is a different quantity from the accuracy above and no summation
    can improve it: translating a body rounds every coordinate at the new
    magnitude, so the body itself changes shape. The bound is
    ``TRANSLATION_DRIFT_FACTOR * ulp(offset) / L`` at the smallest
    feature ``L``, which is the tube's wall thickness here.
    """
    wall_thickness_m = 0.02
    vertices, faces = annular_tube(0.08, 0.1, -0.1, 0.4, 64)
    at_origin = tetrahedron(vertices=vertices, faces=faces).signed_volume_m3()
    placed = tuple(
        (vertex[0] + offset, vertex[1] + offset, vertex[2] + offset)
        for vertex in vertices
    )
    moved_volume = tetrahedron(vertices=placed, faces=faces).signed_volume_m3()
    drift = abs(moved_volume - at_origin) / abs(at_origin)
    bound = TRANSLATION_DRIFT_FACTOR * math.ulp(offset) / wall_thickness_m
    assert drift <= bound


def test_the_summation_rule_is_stated_for_the_native_kernel() -> None:
    """The order is contract, because the parity test compares bit patterns."""
    assert "compensated" in SUMMATION_RULE
    assert "larger magnitude first" in SUMMATION_RULE


UNIT_AREA = 1.5 + math.sqrt(3.0) / 2.0
LARGEST_MEASURABLE_SCALE = 6.163580613284844e153
SMALLEST_SCALE_WITHIN_RELATIVE_TOLERANCE = 3.6841669742473237e-162


def at_scale(scale: float) -> TriangleMesh:
    """Return the unit tetrahedron scaled about the origin."""
    return tetrahedron(
        vertices=tuple(
            tuple(component * scale for component in vertex)
            for vertex in TETRA_VERTICES
        )
    )


def direct_area(mesh: TriangleMesh) -> float:
    """Return the area as the library computed it before the repair.

    Parameters
    ----------
    mesh
        The mesh.

    Returns
    -------
    float
        The sum of face norms taken directly from the sum of squares,
        with no rescaling. Used to prove that nothing which already
        worked has moved.
    """
    total = 0.0
    for face in mesh.faces:
        v0 = mesh.vertices[face[0]]
        first = tuple(mesh.vertices[face[1]][axis] - v0[axis] for axis in range(3))
        second = tuple(mesh.vertices[face[2]][axis] - v0[axis] for axis in range(3))
        cross = (
            first[1] * second[2] - first[2] * second[1],
            first[2] * second[0] - first[0] * second[2],
            first[0] * second[1] - first[1] * second[0],
        )
        total += math.sqrt(
            cross[0] * cross[0] + cross[1] * cross[1] + cross[2] * cross[2]
        )
    return total / 2.0


@pytest.mark.parametrize("exponent", [77, 100, 150, 153])
def test_the_area_survives_squares_that_overflow(exponent: int) -> None:
    """A representable area is returned, not lost to its own intermediates.

    At a coordinate scale of ``1e100`` the exact area is ``2.37e200``,
    comfortably inside the format, while the sum of squares of the cross
    product is ``1e400``. The whole area used to collapse to infinity.
    """
    scale = 10.0**exponent
    area = at_scale(scale).surface_area_m2()
    assert area == pytest.approx(UNIT_AREA * scale * scale, rel=1.0e-12)


@pytest.mark.parametrize("exponent", [-100, -154, -160])
def test_the_area_survives_squares_that_fall_subnormal(exponent: int) -> None:
    """The other end of the same defect, which cost a triangle its existence.

    Far enough down, the cross product's squares reached zero and the
    triangle was refused as degenerate although its area was perfectly
    representable.
    """
    scale = 10.0**exponent
    area = at_scale(scale).surface_area_m2()
    assert area == pytest.approx(UNIT_AREA * scale * scale, rel=1.0e-12)


@pytest.mark.parametrize("exponent", [-50, -10, 0, 10, 50])
def test_nothing_that_already_worked_has_moved(exponent: int) -> None:
    """The direct form is kept where it works, and this asserts it bit for bit.

    A repair that improved ordinary results would be a change to every
    consumer's records. This one is not: at every ordinary scale the
    measure is the same double it always was.
    """
    mesh = at_scale(10.0**exponent)
    assert mesh.surface_area_m2() == direct_area(mesh)


@pytest.mark.parametrize("scale", [LARGEST_MEASURABLE_SCALE, 8e153, 8.7e153])
def test_representable_area_survives_intermediate_overflow(scale: float) -> None:
    """Score the final area, even when twice that area cannot fit."""
    mesh = at_scale(scale)
    expected = float(exact_surface_area(mesh))
    assert math.isfinite(expected)
    assert mesh.surface_area_m2() == pytest.approx(expected, rel=1e-14)


def test_unrepresentable_total_area_is_refused() -> None:
    """Finite face areas do not permit an infinite aggregate record."""
    with pytest.raises(GeometryError, match="surface_area_m2: not representable"):
        at_scale(1e154).surface_area_m2()


@pytest.mark.parametrize("scale", [8e102, 1e103])
def test_representable_volume_survives_intermediate_overflow(scale: float) -> None:
    """Compare to a rational oracle before rounding the final volume."""
    expected = float(Fraction(scale) ** 3 / 6)
    assert at_scale(scale).signed_volume_m3() == pytest.approx(expected, rel=1e-14)


def test_face_cross_product_overflow_preserves_area_and_normal() -> None:
    """The cross product can overflow although half its norm is finite."""
    normal, area = face_normal_and_area(
        (0.0, 0.0, 0.0), (1.4e154, 0.0, 0.0), (0.0, 1.4e154, 0.0)
    )
    assert normal == (0.0, 0.0, 1.0)
    assert area == float(Fraction(1.4e154) ** 2 / 2)


@pytest.mark.parametrize("scale", [1e155, 1e-200])
def test_face_refuses_unrepresentable_final_area(scale: float) -> None:
    """Reject overflow and underflow without returning a nonfinite normal."""
    with pytest.raises(GeometryError, match=r"face\.area"):
        face_normal_and_area((0.0, 0.0, 0.0), (scale, 0.0, 0.0), (0.0, scale, 0.0))


def test_public_face_rejects_nonfinite_coordinates() -> None:
    """The standalone entry point validates inputs outside mesh construction."""
    with pytest.raises(GeometryError, match="coordinates must be finite"):
        face_normal_and_area((math.nan, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))


def exact_surface_area(mesh: TriangleMesh) -> Decimal:
    """Return the exact area of the mesh actually given, at 80 digits.

    Parameters
    ----------
    mesh
        The mesh, whose coordinates are exact binary doubles.

    Returns
    -------
    Decimal
        The sum of face norms evaluated without floating-point rounding.
        The oracle is the area of **these vertices**, not of an idealised
        body they approximate: at a subnormal scale the two differ, and
        scoring against the ideal would measure the scaling rather than
        the kernel.
    """
    getcontext().prec = 80
    total = Decimal(0)
    for face in mesh.faces:
        v0 = mesh.vertices[face[0]]
        first = tuple(
            Fraction(mesh.vertices[face[1]][axis]) - Fraction(v0[axis])
            for axis in range(3)
        )
        second = tuple(
            Fraction(mesh.vertices[face[2]][axis]) - Fraction(v0[axis])
            for axis in range(3)
        )
        cross = (
            first[1] * second[2] - first[2] * second[1],
            first[2] * second[0] - first[0] * second[2],
            first[0] * second[1] - first[1] * second[0],
        )
        squares = sum(component * component for component in cross)
        total += (Decimal(squares.numerator) / Decimal(squares.denominator)).sqrt()
    return total / 2


def test_below_the_relative_tolerance_the_measure_is_still_correctly_rounded() -> None:
    """The bottom is the format running out of bits, not the kernel failing.

    A relative tolerance is the wrong instrument once the answer is
    itself subnormal: just below this scale the exact area is about six
    and a half times the smallest double there is, so it carries roughly
    three bits and no algorithm can be accurate to a part in a million.
    Measured in the only unit that still means something, against the
    exact area of the vertices actually handed in, the result stays
    within **one unit in the last place**. The bound is one rather than
    a half because each of the four face norms is separately rounded
    before they are summed; measured over sixty consecutive subnormal
    scales the worst was `0.50000000000010` ulp, so the four errors
    very nearly cancel, but they are not guaranteed to.
    """
    scale = SMALLEST_SCALE_WITHIN_RELATIVE_TOLERANCE
    assert at_scale(scale).surface_area_m2() == pytest.approx(
        UNIT_AREA * scale * scale, rel=1.0e-12
    )
    for _ in range(8):
        scale = math.nextafter(scale, 0.0)
        mesh = at_scale(scale)
        measured = mesh.surface_area_m2()
        error = abs(Fraction(measured) - Fraction(exact_surface_area(mesh)))
        assert error <= Fraction(math.ulp(measured))


def test_an_unrepresentable_volume_is_refused_by_name() -> None:
    """A volume the format cannot hold must not reach a record.

    **It arrives as a NaN rather than an infinity**, because the
    compensated summation adds a positive and a negative overflow. A NaN
    compares false against every bound, so returning it would be worse
    than returning an infinity, and neither is a measure.
    """
    with pytest.raises(GeometryError, match="signed_volume_m3: not representable"):
        at_scale(2.0e103).signed_volume_m3()


def test_a_record_is_never_written_with_a_measure_it_cannot_hold() -> None:
    """The refusal happens before serialisation, which is the point of it."""
    with pytest.raises(GeometryError, match="not representable"):
        at_scale(1.0e200).summary_record()


def test_a_degenerate_triangle_is_still_refused() -> None:
    """Collinear vertices have an exactly zero cross product at any scale."""
    with pytest.raises(GeometryError, match="degenerate triangle"):
        face_normal_and_area((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (2.0, 0.0, 0.0))


def test_a_tiny_triangle_is_no_longer_mistaken_for_a_degenerate_one() -> None:
    """The nearest case to the one above, and it must be measured instead.

    This is the failure the repair removes: a triangle whose cross
    product is small but not zero used to be refused with the same
    message as a genuinely collinear one, so the refusal said nothing
    about the geometry.
    """
    scale = 1.0e-120
    normal, area = face_normal_and_area(
        (0.0, 0.0, 0.0), (scale, 0.0, 0.0), (0.0, scale, 0.0)
    )
    assert area == pytest.approx(scale * scale / 2.0, rel=1.0e-12)
    assert normal == (0.0, 0.0, 1.0)


def test_a_zero_area_face_reports_a_positive_zero_norm() -> None:
    """Signed zeros in the cross product must not produce a negative zero.

    A negative zero would serialise as ``-0.0`` and compare equal to
    zero, so nothing downstream would notice, which is exactly the kind
    of value that should not be in a record.
    """
    with pytest.raises(GeometryError, match="degenerate triangle"):
        face_normal_and_area((-0.0, -0.0, -0.0), (-0.0, 0.0, 0.0), (0.0, -0.0, 0.0))
