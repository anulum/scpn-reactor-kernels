# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — tetrahedral volume mesh of a STEP assembly

"""Tetrahedral volume mesh of a STEP assembly by gmsh (MSH 4.1).

The STEP bytes of :mod:`scpn_reactor_kernels.cad.step` are imported into
gmsh's OpenCASCADE model, meshed in three dimensions with a declared
characteristic length and a fixed option set, and written as MSH 4.1
bytes. The kernel sums the tetrahedra volumes per volume entity
(``|det(v1 - v0, v2 - v0, v3 - v0)| / 6`` in fixed order) so the mesh can
be checked against the B-rep volumes within a declared tolerance, and
reports node and element counts. The same STEP bytes and length give the
same MSH bytes in one environment (gmsh's algorithms are deterministic
for a fixed option set on one build); identity across gmsh versions is
not claimed. This is the entry point of the neutronics and
thermal-structural lanes; nothing here is an engineering result.
"""

from __future__ import annotations

import hashlib
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from scpn_reactor_kernels.cad._backend import load_backend
from scpn_reactor_kernels.errors import CadError
from scpn_reactor_kernels.validation import require_positive

MSH_FORMAT: Final = "MSH 4.1 ASCII"
TETRAHEDRON_TYPE: Final = 4
#: Fixed gmsh options (name, value) applied before meshing.
GMSH_OPTIONS: Final = (
    ("General.Terminal", 0.0),
    ("General.Verbosity", 0.0),
    ("Mesh.Algorithm", 6.0),
    ("Mesh.Algorithm3D", 1.0),
    ("Mesh.Optimize", 1.0),
    ("Mesh.MshFileVersion", 4.1),
    ("Mesh.Binary", 0.0),
)


@dataclass(frozen=True, slots=True)
class VolumeEntity:
    """Mesh summary of one volume entity.

    Parameters
    ----------
    tag
        gmsh entity tag.
    element_count
        Tetrahedra in the entity.
    volume_m3
        Sum of the tetrahedra volumes.
    """

    tag: int
    element_count: int
    volume_m3: float

    def to_record(self) -> dict[str, Any]:
        """Project the entity summary to a JSON-serialisable record."""
        return {
            "tag": self.tag,
            "element_count": self.element_count,
            "volume_m3": self.volume_m3,
        }


@dataclass(frozen=True, slots=True)
class VolumeMesh:
    """A tetrahedral mesh with its summary.

    Parameters
    ----------
    msh_bytes
        The MSH 4.1 ASCII file.
    characteristic_length_m
        Declared characteristic length.
    node_count
        Nodes in the mesh.
    entities
        One summary per volume entity in tag order.
    """

    msh_bytes: bytes
    characteristic_length_m: float
    node_count: int
    entities: tuple[VolumeEntity, ...]

    @property
    def element_count(self) -> int:
        """Tetrahedra over all entities."""
        return sum(entity.element_count for entity in self.entities)

    @property
    def total_volume_m3(self) -> float:
        """Sum of all tetrahedra volumes."""
        total = 0.0
        for entity in self.entities:
            total += entity.volume_m3
        return total

    def msh_sha256(self) -> str:
        """Identify the exact mesh bytes."""
        return hashlib.sha256(self.msh_bytes).hexdigest()

    def summary_record(self) -> dict[str, Any]:
        """Project the mesh summary to a JSON-serialisable record."""
        return {
            "format": MSH_FORMAT,
            "characteristic_length_m": self.characteristic_length_m,
            "node_count": self.node_count,
            "element_count": self.element_count,
            "total_volume_m3": self.total_volume_m3,
            "entities": [entity.to_record() for entity in self.entities],
            "msh_sha256": self.msh_sha256(),
        }


def _det3(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
    c: tuple[float, float, float],
) -> float:
    return (
        a[0] * (b[1] * c[2] - b[2] * c[1])
        - a[1] * (b[0] * c[2] - b[2] * c[0])
        + a[2] * (b[0] * c[1] - b[1] * c[0])
    )


def tetrahedron_volume(
    v0: tuple[float, float, float],
    v1: tuple[float, float, float],
    v2: tuple[float, float, float],
    v3: tuple[float, float, float],
) -> float:
    """Return the unsigned volume of one tetrahedron.

    Parameters
    ----------
    v0, v1, v2, v3
        Corner coordinates.

    Returns
    -------
    float
        ``|det(v1 - v0, v2 - v0, v3 - v0)| / 6``.
    """
    e1 = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
    e2 = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])
    e3 = (v3[0] - v0[0], v3[1] - v0[1], v3[2] - v0[2])
    return abs(_det3(e1, e2, e3)) / 6.0


def gmsh_volume_mesh(step: bytes, characteristic_length_m: float) -> VolumeMesh:
    """Mesh a STEP assembly into tetrahedra.

    Parameters
    ----------
    step
        STEP bytes (normalised or not).
    characteristic_length_m
        Target element size; strictly positive.

    Returns
    -------
    VolumeMesh
        The MSH bytes and the summary.

    Raises
    ------
    CadError
        If the length is invalid or the STEP carries no volume;
        :class:`CadUnavailableError` if gmsh is absent.
    """
    try:
        length = require_positive("characteristic_length_m", characteristic_length_m)
    except ValueError as exc:
        raise CadError(str(exc)) from exc
    if not step:
        raise CadError("step: must be non-empty bytes")
    gmsh = load_backend("gmsh")
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "assembly.step"
        source.write_bytes(step)
        target = Path(directory) / "assembly.msh"
        gmsh.initialize()
        try:
            for option, value in GMSH_OPTIONS:
                gmsh.option.setNumber(option, value)
            gmsh.model.add("scpn_reactor_kernels")
            gmsh.model.occ.importShapes(str(source))
            gmsh.model.occ.synchronize()
            volumes = gmsh.model.getEntities(3)
            if not volumes:
                raise CadError("step: the assembly carries no volume entity")
            gmsh.option.setNumber("Mesh.MeshSizeMin", length)
            gmsh.option.setNumber("Mesh.MeshSizeMax", length)
            gmsh.model.mesh.generate(3)
            node_tags, coordinates, _ = gmsh.model.mesh.getNodes()
            points = {
                int(tag): (
                    float(coordinates[3 * index]),
                    float(coordinates[3 * index + 1]),
                    float(coordinates[3 * index + 2]),
                )
                for index, tag in enumerate(node_tags)
            }
            entities: list[VolumeEntity] = []
            for _, tag in volumes:
                types, _, nodes = gmsh.model.mesh.getElements(3, tag)
                count = 0
                total = 0.0
                for element_type, element_nodes in zip(types, nodes, strict=True):
                    if int(element_type) != TETRAHEDRON_TYPE:
                        raise CadError(
                            f"mesh: unexpected element type {int(element_type)} "
                            f"in volume {tag}"
                        )
                    corners = [int(node) for node in element_nodes]
                    for start in range(0, len(corners), 4):
                        v0, v1, v2, v3 = (
                            points[corners[start + offset]] for offset in range(4)
                        )
                        total += tetrahedron_volume(v0, v1, v2, v3)
                        count += 1
                entities.append(VolumeEntity(int(tag), count, total))
            gmsh.write(str(target))
        finally:
            gmsh.finalize()
        data = target.read_bytes()
    return VolumeMesh(
        msh_bytes=data,
        characteristic_length_m=length,
        node_count=len(points),
        entities=tuple(entities),
    )
