# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — faceting of B-rep solids into closed meshes

"""Faceting of B-rep solids into the tier-G1 closed-mesh contract.

The OpenCASCADE incremental mesher (``BRepMesh_IncrementalMesh`` through
CadQuery ``Shape.tessellate``) facets every face of a solid with a linear
deflection (the largest chord distance to the true surface) and an
angular deflection; faces do not share vertex records, so the vertices are
welded by exact coordinate equality into one stream and the triangles are
re-indexed. The result is a :class:`TriangleMesh`, whose validation proves
the surface closed and consistently oriented; the mesher's outward face
orientation makes the signed volume positive. The faceted volume is below
the true one by the inscribed-chord deficit: for a circular profile of
radius ``r`` and deflection ``d`` the relative deficit is bounded by
``2 d / r`` (the exact deficit ``1 - sin(theta) / theta`` of a chord angle
``theta`` with sagitta ``d = r (1 - cos(theta/2))`` is below ``4 d / (3 r)``
for small angles). The G1 kernels' inscribed regular polygons obey the
exact ratio :func:`inscribed_polygon_area_ratio`, evaluated from the
library's unit circle. Nothing here describes a device.
"""

from __future__ import annotations

from typing import Any, Final

from scpn_reactor_kernels.cad.assembly import BrepAssembly
from scpn_reactor_kernels.cad.solids import BrepBody
from scpn_reactor_kernels.errors import CadError
from scpn_reactor_kernels.geometry.mesh import Face, TriangleMesh, Vertex
from scpn_reactor_kernels.geometry.trig import unit_circle
from scpn_reactor_kernels.validation import require_positive

#: Declared bound of the relative volume deficit of a faceted circular body.
DEFLECTION_DEFICIT_FACTOR: Final = 2.0
TWO_PI: Final = 6.283185307179586


def require_deflection(name: str, value: float) -> float:
    """Return a deflection when finite and strictly positive.

    Parameters
    ----------
    name
        Field name reported in the rejection message.
    value
        Deflection under validation.

    Returns
    -------
    float
        The validated deflection.

    Raises
    ------
    CadError
        If the deflection is non-finite or not strictly positive.
    """
    try:
        return require_positive(name, value)
    except ValueError as exc:
        raise CadError(str(exc)) from exc


def inscribed_polygon_area_ratio(segments: int) -> float:
    """Return the area ratio of the inscribed regular polygon to its circle.

    Parameters
    ----------
    segments
        Polygon sides; at least 8 and a multiple of 8 (the unit-circle
        kernel's rule).

    Returns
    -------
    float
        ``(n / (2 pi)) sin(2 pi / n)`` with the sine taken from the
        library's unit circle (bit-exact on both backends).
    """
    sine = unit_circle(segments)[1][1]
    return segments / TWO_PI * sine


def deflection_volume_bound(radius_m: float, linear_deflection_m: float) -> float:
    """Return the declared relative volume-deficit bound of a faceted circle.

    Parameters
    ----------
    radius_m
        Smallest circular radius of the body.
    linear_deflection_m
        Linear deflection used by the mesher.

    Returns
    -------
    float
        ``2 d / r``.
    """
    return DEFLECTION_DEFICIT_FACTOR * linear_deflection_m / radius_m


def weld(
    vertices: list[Any], triangles: list[tuple[int, int, int]]
) -> tuple[tuple[Vertex, ...], tuple[Face, ...]]:
    """Weld per-face vertex records by exact coordinate equality.

    Parameters
    ----------
    vertices
        Vertex objects with ``x``, ``y``, ``z`` attributes.
    triangles
        Index triples into ``vertices``.

    Returns
    -------
    (vertices, faces)
        The welded vertex stream (first occurrence order) and re-indexed
        faces.
    """
    lookup: dict[Vertex, int] = {}
    stream: list[Vertex] = []
    remap: list[int] = []
    for vertex in vertices:
        key: Vertex = (float(vertex.x), float(vertex.y), float(vertex.z))
        index = lookup.get(key)
        if index is None:
            index = len(stream)
            lookup[key] = index
            stream.append(key)
        remap.append(index)
    faces = tuple((remap[a], remap[b], remap[c]) for a, b, c in triangles)
    return tuple(stream), faces


def facet_body(
    body: BrepBody, linear_deflection_m: float, angular_deflection_rad: float
) -> TriangleMesh:
    """Facet one B-rep body into a closed triangle mesh.

    Parameters
    ----------
    body
        The solid.
    linear_deflection_m
        Largest chord distance to the true surface; strictly positive.
    angular_deflection_rad
        Largest angle between adjacent facet normals; strictly positive.

    Returns
    -------
    TriangleMesh
        The welded, closed, outward-oriented mesh named as the body.

    Raises
    ------
    CadError
        If a deflection is invalid; :class:`GeometryError` if the faceted
        surface violates the mesh contract.
    """
    linear = require_deflection("linear_deflection_m", linear_deflection_m)
    angular = require_deflection("angular_deflection_rad", angular_deflection_rad)
    vertices, triangles = body.shape.tessellate(linear, angular)
    stream, faces = weld(list(vertices), list(triangles))
    return TriangleMesh(
        name=body.name,
        role=body.role,
        material_identifier=body.material_identifier,
        vertices=stream,
        faces=faces,
    )


def facet_assembly(
    assembly: BrepAssembly, linear_deflection_m: float, angular_deflection_rad: float
) -> tuple[TriangleMesh, ...]:
    """Facet every body of an assembly in order.

    Parameters
    ----------
    assembly
        The bodies.
    linear_deflection_m, angular_deflection_rad
        Mesher deflections.

    Returns
    -------
    tuple of TriangleMesh
        One closed mesh per body, in the assembly order.
    """
    return tuple(
        facet_body(body, linear_deflection_m, angular_deflection_rad)
        for body in assembly.bodies
    )
