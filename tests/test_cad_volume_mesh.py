# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — volume mesh tests

"""The gmsh volume mesh is deterministic, summarised and checked against the B-rep."""

from __future__ import annotations

import math

import pytest

from cad_fixtures import assembly
from scpn_reactor_kernels.cad import (
    MSH_FORMAT,
    VolumeEntity,
    VolumeMesh,
    gmsh_volume_mesh,
    step_bytes,
    tetrahedron_volume,
)
from scpn_reactor_kernels.errors import CadError

pytest.importorskip("gmsh")

LENGTH_M = 0.02


def test_volume_mesh_is_deterministic_and_consistent() -> None:
    """Two runs give the same bytes; tetrahedra volumes track the B-rep volumes."""
    built = assembly()
    step = step_bytes(built, {"test": True})
    first = gmsh_volume_mesh(step, LENGTH_M)
    second = gmsh_volume_mesh(step, LENGTH_M)
    assert isinstance(first, VolumeMesh)
    assert first.msh_bytes == second.msh_bytes
    assert first.msh_sha256() == second.msh_sha256()
    assert first.msh_bytes.startswith(b"$MeshFormat\n4.1 0 8\n")
    assert first.node_count > 0
    assert first.element_count == sum(e.element_count for e in first.entities)
    assert len(first.entities) == 2
    brep_total = sum(body.volume_m3 for body in built.bodies)
    assert math.isclose(first.total_volume_m3, brep_total, rel_tol=2.0e-2)
    per_body = sorted(body.volume_m3 for body in built.bodies)
    per_entity = sorted(entity.volume_m3 for entity in first.entities)
    for got, reference in zip(per_entity, per_body, strict=True):
        assert math.isclose(got, reference, rel_tol=3.0e-2)
    record = first.summary_record()
    assert record["format"] == MSH_FORMAT
    assert record["characteristic_length_m"] == LENGTH_M
    assert record["msh_sha256"] == first.msh_sha256()
    assert [entity["tag"] for entity in record["entities"]] == [1, 2]
    assert isinstance(first.entities[0], VolumeEntity)


def test_tetrahedron_volume_closed_form() -> None:
    """The unit right tetrahedron has volume 1/6; orientation does not matter."""
    corners = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    assert tetrahedron_volume(*corners) == 1.0 / 6.0
    assert (
        tetrahedron_volume(corners[0], corners[2], corners[1], corners[3]) == 1.0 / 6.0
    )


@pytest.mark.parametrize(
    ("step", "length", "fragment"),
    [
        (b"", LENGTH_M, "non-empty"),
        (b"ISO-10303-21;", 0.0, "characteristic_length_m"),
        (b"ISO-10303-21;", math.nan, "characteristic_length_m"),
    ],
)
def test_invalid_inputs_are_refused(step: bytes, length: float, fragment: str) -> None:
    """Empty STEP bytes and non-positive lengths are refused before gmsh runs."""
    with pytest.raises(CadError, match=fragment):
        gmsh_volume_mesh(step, length)


def test_step_without_a_volume_is_refused() -> None:
    """A Part 21 file with no solid yields no volume entity and is refused."""
    empty = (
        b"ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('x'),'2;1');\n"
        b"FILE_NAME('x','2000-01-01T00:00:00',(''),(''),'','','');\n"
        b"FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));\n"
        b"ENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n"
    )
    with pytest.raises(CadError, match="no volume entity"):
        gmsh_volume_mesh(empty, LENGTH_M)


def test_non_tetrahedral_elements_are_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """A mesher returning a non-tetrahedral 3D element type is refused, never summed."""
    from types import SimpleNamespace

    from scpn_reactor_kernels.cad import volume_mesh

    calls: list[str] = []
    fake = SimpleNamespace(
        initialize=lambda: calls.append("init"),
        finalize=lambda: calls.append("finalize"),
        write=lambda *_: calls.append("write"),
        option=SimpleNamespace(setNumber=lambda *_: None),
        model=SimpleNamespace(
            add=lambda *_: None,
            occ=SimpleNamespace(importShapes=lambda *_: None, synchronize=lambda: None),
            getEntities=lambda *_: [(3, 1)],
            mesh=SimpleNamespace(
                generate=lambda *_: None,
                getNodes=lambda: ([1, 2, 3, 4], [0.0] * 12, []),
                getElements=lambda *_: ([5], [[1]], [[1, 2, 3, 4, 1, 2, 3, 4]]),
            ),
        ),
    )
    monkeypatch.setattr(volume_mesh, "load_backend", lambda *_: fake)
    with pytest.raises(CadError, match="unexpected element type 5"):
        gmsh_volume_mesh(b"ISO-10303-21;", LENGTH_M)
    assert calls == ["init", "finalize"]
