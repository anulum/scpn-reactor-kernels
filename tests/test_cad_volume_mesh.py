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
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any

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
from scpn_reactor_kernels.cad.volume_mesh import (
    MODEL_NAME,
)
from scpn_reactor_kernels.errors import CadError

gmsh = pytest.importorskip("gmsh")

LENGTH_M = 0.02
CALLER_MODEL = "caller_model"
CALLER_OPTIONS = (
    ("Mesh.Algorithm", 5.0),
    ("Mesh.Algorithm3D", 7.0),
    ("Mesh.Optimize", 0.0),
    ("Mesh.RecombineAll", 1.0),
    ("Mesh.ElementOrder", 2.0),
    ("Mesh.MshFileVersion", 2.2),
    ("Mesh.MeshSizeFactor", 3.0),
    ("General.Verbosity", 4.0),
)
STEP_WITHOUT_A_VOLUME = (
    b"ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('x'),'2;1');\n"
    b"FILE_NAME('x','2000-01-01T00:00:00',(''),(''),'','','');\n"
    b"FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));\n"
    b"ENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n"
)


@pytest.fixture(autouse=True)
def _no_session_leaks_between_tests() -> Iterator[None]:
    """Leave gmsh uninitialised whatever a test does to it.

    These tests are the only ones in the suite that open real gmsh
    sessions, and a session left open would silently change which branch
    of the ownership contract every later test takes.
    """
    yield
    while gmsh.isInitialized():
        gmsh.finalize()


@pytest.fixture(scope="module")
def step() -> bytes:
    """Return the reference assembly, built once for the whole module."""
    return step_bytes(assembly(), {"test": True})


def open_caller_session(model: str = CALLER_MODEL) -> None:
    """Open a session the way a consumer that owns gmsh would."""
    gmsh.initialize()
    for option, value in CALLER_OPTIONS:
        gmsh.option.setNumber(option, value)
    gmsh.model.add(model)


def caller_state() -> dict[str, Any]:
    """Everything a caller can observe of its own session."""
    return {
        "initialized": int(gmsh.isInitialized()),
        "models": sorted(gmsh.model.list()),
        "current_model": gmsh.model.getCurrent(),
        "options": {name: gmsh.option.getNumber(name) for name, _ in CALLER_OPTIONS},
    }


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


@pytest.mark.parametrize("use_valid_step", [True, False])
def test_existing_session_is_refused_without_mutation(
    step: bytes, *, use_valid_step: bool
) -> None:
    """Both inputs preserve caller models, options and derived state."""
    open_caller_session(model=MODEL_NAME)
    gmsh.model.occ.addBox(0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
    gmsh.model.occ.synchronize()
    before = caller_state()
    entities = gmsh.model.getEntities()
    bounding = gmsh.option.getNumber("General.BoundingBoxSize")
    with pytest.raises(CadError, match="existing caller session"):
        gmsh_volume_mesh(step if use_valid_step else STEP_WITHOUT_A_VOLUME, LENGTH_M)
    assert caller_state() == before
    assert gmsh.model.getEntities() == entities
    assert gmsh.option.getNumber("General.BoundingBoxSize") == bounding


def test_owned_session_cleanup_after_real_backend_refusal(
    monkeypatch: pytest.MonkeyPatch, step: bytes
) -> None:
    """A real higher-order mesh exercises element refusal and finalisation."""
    from scpn_reactor_kernels.cad import volume_mesh

    monkeypatch.setattr(
        volume_mesh,
        "GMSH_OPTIONS",
        (*volume_mesh.GMSH_OPTIONS, ("Mesh.ElementOrder", 2.0)),
    )
    with pytest.raises(CadError, match="unexpected element type"):
        gmsh_volume_mesh(step, LENGTH_M)
    assert not gmsh.isInitialized()


def test_worker_threads_own_serial_fresh_sessions(step: bytes) -> None:
    """No signal handler or caller session is needed by either worker."""
    reference = gmsh_volume_mesh(step, LENGTH_M).msh_sha256()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda _: gmsh_volume_mesh(step, LENGTH_M).msh_sha256(), range(2))
        )
    assert results == [reference, reference]
    assert not gmsh.isInitialized()
