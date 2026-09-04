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
import sys
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
SUMMATION_RULE: Final = (
    "compensated: running total plus a correction that keeps the part of "
    "each term the running total was too large to hold, added once at the "
    "end; the branch takes the larger magnitude first"
)
SMALLEST_NORMAL: Final = sys.float_info.min
"""Smallest positive normal double; below it a sum of squares is rescaled.

The direct sum of squares is used whenever it lands at or above this,
for the measured ordinary-scale fixtures, so no measure that was already right
changes by a bit.
"""
TRANSLATION_DRIFT_FACTOR: Final = 3.0
"""Factor of ``ulp(offset) / L`` bounding the drift of a translated mesh.

``L`` is the body's smallest feature. The bound is a property of the
coordinate grid, not of the summation: translating a mesh rounds every
coordinate at the new magnitude, so the body itself changes shape. Over
this library's bodies at offsets from 100 m to 1e8 m the measured drift
never exceeded a tenth of it.
"""


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


def _norm(vector: Vertex) -> float:
    """Euclidean norm, rescaled only where the direct form would fail.

    Parameters
    ----------
    vector
        The three components.

    Returns
    -------
    float
        ``sqrt(x*x + y*y + z*z)``, never a negative zero.

    Notes
    -----
    **The direct form is kept exactly where it works**, so no mesh whose
    norm was already right changes by a bit. It is used whenever the sum
    of squares is a finite normal double, as checked on ordinary-scale
    fixtures. It fails in two ways outside that, and both were losing
    results the format can hold:

    - the sum of squares overflows to infinity while the norm itself is
      representable, which for the library's tetrahedron began at a
      coordinate scale of ``8.798296151866776e+76`` even though the exact
      area there is ``1.83e154``;
    - the sum of squares falls subnormal or to zero while the norm is
      representable, which cost accuracy below a scale of
      ``9.543299509722758e-79`` and, further down, made a perfectly
      ordinary triangle be refused as degenerate.

    In both cases the components are divided by the largest of them, the
    norm of that unit-scale vector is taken, and the scale is multiplied
    back. Scaling by a power of two instead would make the division exact
    and was measured alongside: `9.94e-17` against `1.19e-16` worst
    relative error over sixty vectors spanning the double range. It was
    not adopted, because the native kernel's standard library has no
    ``ldexp`` and reimplementing one is more surface for the two
    languages to disagree on than a sixth of a rounding unit is worth.

    The remaining error is a property of the inputs rather than of the
    rule: at a coordinate scale of ``1e-320`` the worst relative error is
    ``1.98e-4`` for **both** rules, because a subnormal coordinate there
    carries about four significant digits to begin with.
    """
    total = vector[0] * vector[0] + vector[1] * vector[1] + vector[2] * vector[2]
    if math.isfinite(total) and total >= SMALLEST_NORMAL:
        return math.sqrt(total)
    largest = max(abs(vector[0]), abs(vector[1]), abs(vector[2]))
    if largest == 0.0:
        return 0.0
    a = vector[0] / largest
    b = vector[1] / largest
    c = vector[2] / largest
    return largest * math.sqrt(a * a + b * b + c * c)


def _rescale(value: float, exponent: int) -> float:
    """Multiply by a power of two in bounded steps shared with Rust."""
    while exponent > 512:
        value *= 2.0**512
        exponent -= 512
    while exponent < -512:
        value *= 2.0**-512
        exponent += 512
    return value * 2.0**exponent


def _scaled_vertices(vertices: tuple[Vertex, ...]) -> tuple[tuple[Vertex, ...], int]:
    """Return power-of-two scaled coordinates and their shared exponent."""
    largest = max(abs(x) for vertex in vertices for x in vertex)
    exponent = math.frexp(largest)[1]
    return tuple(
        (
            _rescale(v[0], -exponent),
            _rescale(v[1], -exponent),
            _rescale(v[2], -exponent),
        )
        for v in vertices
    ), exponent


def _face_measure(v0: Vertex, v1: Vertex, v2: Vertex) -> tuple[Vertex, float]:
    """Measure a face, rescaling coordinates if cross products lose range."""
    cross = _cross(_subtract(v1, v0), _subtract(v2, v0))
    norm = _norm(cross)
    if math.isfinite(norm) and norm >= SMALLEST_NORMAL:
        return (cross[0] / norm, cross[1] / norm, cross[2] / norm), norm / 2.0
    vertices, exponent = _scaled_vertices((v0, v1, v2))
    cross = _cross(
        _subtract(vertices[1], vertices[0]), _subtract(vertices[2], vertices[0])
    )
    norm = _norm(cross)
    if norm == 0.0:
        raise GeometryError("face: degenerate triangle with zero area")
    area = _rescale(norm / 2.0, 2 * exponent)
    return (cross[0] / norm, cross[1] / norm, cross[2] / norm), area


def _require_representable(name: str, value: float) -> float:
    """Refuse a measure the format cannot hold.

    Parameters
    ----------
    name
        The measure's name, so the refusal says which.
    value
        The computed measure.

    Returns
    -------
    float
        The value, unchanged.

    Raises
    ------
    GeometryError
        If the value is not finite.

    Notes
    -----
    An infinity is not a measure. It reaches
    :meth:`TriangleMesh.summary_record` and from there a JSON document,
    which has no way to write it, and it reaches a consuming family's
    evidence bounds. Refusing here names the body and the measure instead
    of leaving a record that cannot be serialised.
    """
    if not math.isfinite(value):
        raise GeometryError(
            f"{name}: not representable at this coordinate scale, got {value!r}"
        )
    return value


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
        If coordinates are nonfinite, the triangle is degenerate, or its
        final area is outside the representable range.

    Notes
    -----
    The ordinary path preserves the direct arithmetic order. If cross
    products lose range, coordinates are scaled by a common power of two
    before subtraction and multiplication; the area is rescaled after
    halving. Zero scaled cross products are refused as degenerate.
    """
    if not all(math.isfinite(x) for v in (v0, v1, v2) for x in v):
        raise GeometryError("face: coordinates must be finite")
    normal, area = _face_measure(v0, v1, v2)
    _require_representable("face.area", area)
    if area == 0.0:
        raise GeometryError("face.area: below the representable range")
    return normal, area


def _volume_sum(vertices: tuple[Vertex, ...], faces: tuple[Face, ...]) -> float:
    """Accumulate local-origin determinants in the native operation order."""
    origin = vertices[0]
    total = 0.0
    compensation = 0.0
    for face in faces:
        a = _subtract(vertices[face[0]], origin)
        b = _subtract(vertices[face[1]], origin)
        c = _subtract(vertices[face[2]], origin)
        cross = _cross(b, c)
        term = a[0] * cross[0] + a[1] * cross[1] + a[2] * cross[2]
        running = total + term
        if abs(total) >= abs(term):
            compensation += (total - running) + term
        else:
            compensation += (term - running) + total
        total = running
    return (total + compensation) / 6.0


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
        """Enclosed volume by the divergence theorem, about a local origin.

        Returns
        -------
        float
            ``sum(a . (b x c)) / 6`` over the faces in order, with ``a``,
            ``b`` and ``c`` the face's vertices taken relative to the
            mesh's first vertex, accumulated with the compensation of
            :data:`SUMMATION_RULE`. Positive for outward orientation,
            negative for a uniformly inward one.

        Notes
        -----
        **The sum is taken about the mesh's own first vertex, and the
        reason is that the products of absolute coordinates cancel.** The
        divergence theorem is exactly translation-invariant in real
        arithmetic and catastrophically is not in floating point: each
        term grows with the square of the distance to the origin while
        the total does not, so a body far from the origin is a difference
        of large numbers. Measured on this library's own bodies, the
        previous form was wrong by 3 % at an offset of 10 km, by four
        orders of magnitude at 1000 km, and returned exactly zero for a
        unit tetrahedron moved to ``(-1e8, 1e8, -1e8)`` — a body with no
        volume and no complaint.

        The first vertex is the origin rather than a centroid or a box
        midpoint because it needs no arithmetic of its own: it is a value
        already in the mesh, so the native kernel reads the same bits
        without reproducing a reduction. A box midpoint was measured
        alongside it and is better by about a quarter in the worst case
        — `4.22e-16` against `5.76e-16` relative — which does not buy the
        extra surface for the two languages to diverge on.

        Two accuracies are involved here and they are not the same
        number. Against the exact rational value of the mesh it is
        handed, this form is within `5.8e-16` relative over every body
        and offset measured. How much the answer *moves* when the
        geometry itself is translated is a property of the coordinate
        grid rather than of any accumulation: translating a mesh rounds
        every coordinate at the new magnitude, and the resulting drift is
        compared in the recorded tests with ``3 * ulp(offset) / L`` at the
        body's smallest
        feature ``L``. This is a fixture-specific comparison, not a general error bound
        for arbitrary meshes.

        Raises
        ------
        GeometryError
            If the volume is not representable as a double.
        """
        volume = _volume_sum(self.vertices, self.faces)
        if not math.isfinite(volume) or abs(volume) < SMALLEST_NORMAL:
            vertices, exponent = _scaled_vertices(self.vertices)
            volume = _rescale(_volume_sum(vertices, self.faces), 3 * exponent)
        return _require_representable(f"{self.name}.signed_volume_m3", volume)

    def surface_area_m2(self) -> float:
        """Total surface area.

        Returns
        -------
        float
            Sum of ``|(v1 - v0) x (v2 - v0)|`` over the faces in order,
            divided by two.

        Raises
        ------
        GeometryError
            If the area is not representable as a double. That is a fact
            about the coordinates, not about the summation: an infinity
            reaches :meth:`summary_record` and from there a JSON document
            that has no way to write it.

        Notes
        -----
        Each face's norm is taken by :func:`_norm`, which keeps the
        direct form wherever it works. Before this, the whole area
        collapsed to infinity once a single cross product's square
        overflowed, which for the library's tetrahedron happened at a
        coordinate scale of ``8.8e76`` while the true area was
        ``1.8e154`` — comfortably inside the format.
        """
        total = 0.0
        for face in self.faces:
            v0 = self.vertices[face[0]]
            cross = _cross(
                _subtract(self.vertices[face[1]], v0),
                _subtract(self.vertices[face[2]], v0),
            )
            total += _norm(cross)
        area = total / 2.0
        if area < SMALLEST_NORMAL:
            vertices, exponent = _scaled_vertices(self.vertices)
            scaled_area = 0.0
            for face in self.faces:
                _, face_area = _face_measure(*(vertices[i] for i in face))
                scaled_area += face_area
            area = _rescale(scaled_area, 2 * exponent)
        elif not math.isfinite(area):
            # Halve each face before accumulation: twice the final area need
            # not fit even when the final geometric quantity does.
            area = 0.0
            for face in self.faces:
                _, face_area = _face_measure(*(self.vertices[i] for i in face))
                area += face_area
        return _require_representable(f"{self.name}.surface_area_m2", area)

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
