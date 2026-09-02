# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — STEP export tests

"""Determinism, header normalisation, round trip and refusals of the STEP export."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from cad_fixtures import assembly, cylinder
from scpn_reactor_kernels.cad import (
    MEASURE_TOLERANCE,
    STEP_FILE_NAME,
    STEP_FIXED_TIMESTAMP,
    STEP_GENERATOR,
    BrepAssembly,
    normalise_step_text,
    step_bytes,
    step_sha256,
    write_step,
)
from scpn_reactor_kernels.cad._backend import load_backend
from scpn_reactor_kernels.errors import CadError

EXTRAS = {"schema": "test", "digest": "0" * 8, "note": "it's synthetic"}


def test_exports_are_byte_identical_and_normalised() -> None:
    """Two exports agree bit for bit; the header carries the fixed fields."""
    first = step_bytes(assembly(), EXTRAS)
    second = step_bytes(assembly(), EXTRAS)
    assert first == second
    text = first.decode("utf-8")
    assert text.startswith("ISO-10303-21;")
    assert f"FILE_NAME('{STEP_FILE_NAME}','{STEP_FIXED_TIMESTAMP}'" in text
    assert STEP_GENERATOR in text
    assert "it''s synthetic" in text
    occurrences = [
        line for line in text.splitlines() if "NEXT_ASSEMBLY_USAGE_OCCURRENCE" in line
    ]
    assert [line.split("'")[1] for line in occurrences] == ["1", "2"]
    assert "'inner'" in occurrences[0]
    assert "'outer'" in occurrences[1]
    assert step_sha256(first) == step_sha256(second)
    assert len(step_sha256(first)) == 64


def test_extras_change_the_bytes_and_the_digest() -> None:
    """The provenance extras are part of the file."""
    one = step_bytes(assembly(), {"a": 1})
    two = step_bytes(assembly(), {"a": 2})
    assert one != two
    assert step_sha256(one) != step_sha256(two)


def test_round_trip_reproduces_the_volumes(tmp_path: Path) -> None:
    """Re-importing the written file gives the bodies' volumes within tolerance."""
    target = tmp_path / "assembly.step"
    written = write_step(target, assembly(), EXTRAS)
    assert written == target.stat().st_size
    assert target.read_bytes() == step_bytes(assembly(), EXTRAS)
    cadquery = load_backend("cadquery")
    imported = cadquery.importers.importStep(str(target))
    solids = imported.solids().vals()
    assert len(solids) == 2
    expected = sorted(body.analytic_volume_m3 for body in assembly().bodies)
    got = sorted(float(solid.Volume()) for solid in solids)
    for value, reference in zip(got, expected, strict=True):
        assert math.isclose(value, reference, rel_tol=MEASURE_TOLERANCE)


@pytest.mark.parametrize(
    ("extras", "fragment"),
    [
        ("text", "JSON object"),
        ({"nan": math.nan}, "JSON-serialisable"),
        ({"obj": object()}, "JSON-serialisable"),
    ],
)
def test_invalid_extras_are_refused(extras: object, fragment: str) -> None:
    """Extras must be a JSON-serialisable object."""
    with pytest.raises(CadError, match=fragment):
        step_bytes(assembly(), extras)  # type: ignore[arg-type]


def test_malformed_writer_output_is_refused() -> None:
    """A text without the Part 21 header entities is refused."""
    with pytest.raises(CadError, match="header"):
        normalise_step_text("ISO-10303-21;\nHEADER;\nENDSEC;\n", {})
    single = BrepAssembly((cylinder(),))
    text = step_bytes(single, {}).decode("utf-8")
    assert normalise_step_text(text, {}) == text
