# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — placement of B-rep bodies off the axis

"""Placement of B-rep solids away from the device axis (tier G2).

The B-rep constructors in :mod:`scpn_reactor_kernels.cad.solids` build
every solid centred on ``z``, exactly as their tessellating twins do.
Assemblies that carry bodies off the axis — the rods of a squirrel-cage
cathode, a ring of feed conductors, a set of ports — need the same
placement in tier G2 as :mod:`scpn_reactor_kernels.geometry.placement`
gives tier G1, and for the same reason: a device repository must never
re-implement geometry.

The operation is a rigid translation, so the analytic closed forms of the
body are invariant and are carried over unchanged; the placed solid's own
measures are then checked against them by the same
:meth:`~scpn_reactor_kernels.cad.solids.BrepBody.volume_relative_error`
and
:meth:`~scpn_reactor_kernels.cad.solids.BrepBody.surface_area_relative_error`
as any other body. OpenCASCADE stays a pinned third-party kernel and is
not the bit-exact floor of the group, and this shows here: the kernel
integrates over the moved surface, so its measure of the placed solid is
NOT bit-identical to its measure of the source solid — for a ring of
identical rods the volumes differ in the last unit in the last place.
What this kernel declares is therefore the honest pair: the analytic
measures are carried over exactly, the placed solid's measured volume and
area stay within the declared tolerance of them, and the bounding box
shifts by exactly the offset. The centres of a ring of identical bodies
come from the tier-G1
:func:`~scpn_reactor_kernels.geometry.placement.ring_offsets`, which is
the deterministic circle of the geometry group — one set of centres
serves both tiers. Nothing here describes a device.
"""

from __future__ import annotations

from typing import Any

from scpn_reactor_kernels.cad._backend import load_backend
from scpn_reactor_kernels.cad.solids import BrepBody
from scpn_reactor_kernels.errors import CadError
from scpn_reactor_kernels.geometry.mesh import Vertex
from scpn_reactor_kernels.geometry.placement import Rotation, require_rotation
from scpn_reactor_kernels.validation import require_finite


def _translated_shape(shape: Any, offsets: tuple[float, float, float]) -> Any:
    cadquery = load_backend("cadquery")
    return shape.translate(cadquery.Vector(*offsets))


def translate_brep(
    body: BrepBody,
    offset_x_m: float,
    offset_y_m: float,
    offset_z_m: float,
    name: str | None = None,
) -> BrepBody:
    """Translate a B-rep body by a fixed offset.

    Parameters
    ----------
    body
        The body to place; its role, material token and analytic measures
        are carried over unchanged, because a rigid translation leaves the
        closed forms invariant. The B-rep kernel's own measure of the
        placed solid is not claimed bit-identical to its measure of the
        source solid, only within the declared tolerance of the analytic
        form.
    offset_x_m, offset_y_m, offset_z_m
        Translation in metres; every component finite.
    name
        Name of the placed body. A ring of identical bodies needs one name
        per member, so the caller may rename here; ``None`` keeps the
        source body's name.

    Returns
    -------
    BrepBody
        The placed body, carrying the analytic volume and surface area of
        the source.

    Raises
    ------
    CadError
        If any offset component is non-finite, or if a supplied name is
        empty; :class:`~scpn_reactor_kernels.errors.CadUnavailableError`
        if the back-end is absent.
    """
    require_finite("offset_x_m", offset_x_m, CadError)
    require_finite("offset_y_m", offset_y_m, CadError)
    require_finite("offset_z_m", offset_z_m, CadError)
    if name is not None and not name:
        raise CadError("name: must be non-empty")
    return BrepBody(
        name=body.name if name is None else name,
        role=body.role,
        material_identifier=body.material_identifier,
        shape=_translated_shape(body.shape, (offset_x_m, offset_y_m, offset_z_m)),
        analytic_volume_m3=body.analytic_volume_m3,
        analytic_surface_area_m2=body.analytic_surface_area_m2,
    )


def ring_brep_bodies(
    body: BrepBody,
    names: tuple[str, ...],
    offsets: tuple[tuple[float, float], ...],
) -> tuple[BrepBody, ...]:
    """Place one body once per centre of a ring.

    Parameters
    ----------
    body
        The body every member of the ring is a placement of.
    names
        One name per member, in the order of the centres.
    offsets
        The ``(x, y)`` centres, normally those of
        :func:`~scpn_reactor_kernels.geometry.placement.ring_offsets`.

    Returns
    -------
    tuple of BrepBody
        The placed bodies in the order of ``names``.

    Raises
    ------
    CadError
        If the ring is empty, if the name count differs from the centre
        count, or if a name is empty or repeated.
    """
    if not offsets:
        raise CadError("offsets: must not be empty")
    if len(names) != len(offsets):
        raise CadError(
            "names: must carry one name per centre, got "
            f"{len(names)!r} names for {len(offsets)!r} centres"
        )
    if len(set(names)) != len(names):
        raise CadError("names: must be unique")
    return tuple(
        translate_brep(body, offset_x, offset_y, 0.0, name)
        for name, (offset_x, offset_y) in zip(names, offsets, strict=True)
    )


def _placement_location(rotation: Rotation, centre: Vertex) -> Any:
    cadquery = load_backend("cadquery")
    first_column = (rotation[0][0], rotation[1][0], rotation[2][0])
    third_column = (rotation[0][2], rotation[1][2], rotation[2][2])
    return cadquery.Location(
        cadquery.Plane(origin=centre, xDir=first_column, normal=third_column)
    )


def place_brep(
    body: BrepBody,
    rotation: Rotation,
    centre: Vertex,
    name: str | None = None,
) -> BrepBody:
    """Place a B-rep body at a centre, aimed by a rotation.

    Parameters
    ----------
    body
        The body to place, built about ``z`` like its tessellating twin.
        Its role, material token and analytic measures are carried over
        unchanged, because a rigid motion leaves the closed forms
        invariant.
    rotation
        The rotation, normally from
        :func:`~scpn_reactor_kernels.geometry.placement.aim_rotation` or
        :func:`~scpn_reactor_kernels.geometry.placement.inward_aim`. The
        **same** rotation the tier-G1 kernel uses, so the two tiers place
        one body in one frame.
    centre
        Where the body's origin lands, in metres.
    name
        Name of the placed body; ``None`` keeps the source body's name.

    Returns
    -------
    BrepBody
        The placed body, carrying the analytic volume and surface area of
        the source.

    Raises
    ------
    CadError
        If the rotation is not a rotation, if any coordinate is
        non-finite, or if a supplied name is empty;
        :class:`~scpn_reactor_kernels.errors.CadUnavailableError` if the
        back-end is absent.

    Notes
    -----
    The placement is expressed as the frame whose first and third columns
    are those of the rotation, which is how the B-rep back-end takes a
    rigid motion. It re-orthogonalises that frame; measured over thirty
    bodies placed on the latitudes of a sphere, the frame it builds
    departs from the tier-G1 rotation by at most ``1.11e-16`` in any
    component.

    OpenCASCADE stays a pinned third-party kernel and is not the
    bit-exact floor of the group. Measured over the same thirty
    placements, its volume of the placed solid departs from the analytic
    volume of the source by at most ``3.7e-16`` relative and its area by
    ``3.8e-16``.
    """
    require_rotation("rotation", rotation, CadError)
    for index, value in enumerate(centre):
        require_finite(f"centre[{index}]", value, CadError)
    if name is not None and not name:
        raise CadError("name: must be non-empty")
    return BrepBody(
        name=body.name if name is None else name,
        role=body.role,
        material_identifier=body.material_identifier,
        shape=body.shape.moved(_placement_location(rotation, centre)),
        analytic_volume_m3=body.analytic_volume_m3,
        analytic_surface_area_m2=body.analytic_surface_area_m2,
    )


def sphere_ring_brep_bodies(
    body: BrepBody,
    names: tuple[str, ...],
    centres: tuple[Vertex, ...],
    rotations: tuple[Rotation, ...],
) -> tuple[BrepBody, ...]:
    """Place one body once per centre of a latitude, each aimed by its own rotation.

    Parameters
    ----------
    body
        The body every member of the latitude is a placement of.
    names
        One name per member, in the order of the centres.
    centres
        The centres, normally those of
        :func:`~scpn_reactor_kernels.geometry.placement.sphere_ring_offsets`.
    rotations
        One rotation per member, normally from
        :func:`~scpn_reactor_kernels.geometry.placement.inward_aim`.

    Returns
    -------
    tuple of BrepBody
        The placed bodies in the order of ``names``.

    Raises
    ------
    CadError
        If the latitude is empty, if the three sequences differ in
        length, or if a name is empty or repeated.
    """
    if not centres:
        raise CadError("centres: must not be empty")
    if len(names) != len(centres) or len(rotations) != len(centres):
        raise CadError(
            "names, centres and rotations must have one entry per member, got "
            f"{len(names)!r} names, {len(centres)!r} centres and "
            f"{len(rotations)!r} rotations"
        )
    if len(set(names)) != len(names):
        raise CadError("names: must be unique")
    return tuple(
        place_brep(body, rotation, centre, name)
        for name, centre, rotation in zip(names, centres, rotations, strict=True)
    )
