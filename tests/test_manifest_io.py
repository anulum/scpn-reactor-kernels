# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — manifest IO primitive tests

"""Contract tests for the strict JSON input/output primitives."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from manifest_io import canonical_json_bytes, load_json_object, sha256_of_file


def test_load_json_object_returns_decoded_object(tmp_path: Path) -> None:
    """A well-formed JSON object round-trips through the loader."""
    path = tmp_path / "manifest.json"
    path.write_text('{"alpha": 1, "beta": [true, null]}', encoding="utf-8")
    assert load_json_object(path) == {"alpha": 1, "beta": [True, None]}


def test_load_json_object_rejects_duplicate_keys(tmp_path: Path) -> None:
    """A repeated member name is a hard failure, never a silent shadow."""
    path = tmp_path / "manifest.json"
    path.write_text('{"alpha": 1, "alpha": 2}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key: alpha"):
        load_json_object(path)


def test_load_json_object_rejects_non_object_top_level(tmp_path: Path) -> None:
    """A top-level array is rejected even though it is valid JSON."""
    path = tmp_path / "manifest.json"
    path.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ValueError, match="top-level JSON value must be an object"):
        load_json_object(path)


def test_load_json_object_rejects_invalid_json(tmp_path: Path) -> None:
    """A syntax error surfaces as ``ValueError`` naming the file."""
    path = tmp_path / "manifest.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON"):
        load_json_object(path)


def test_load_json_object_missing_file_raises_oserror(tmp_path: Path) -> None:
    """A missing file is an ``OSError``, not an empty result."""
    with pytest.raises(FileNotFoundError, match=r"absent\.json"):
        load_json_object(tmp_path / "absent.json")


def test_canonical_json_bytes_is_deterministic_and_sorted() -> None:
    """Key order in the input does not change the canonical bytes."""
    first = canonical_json_bytes({"beta": 2, "alpha": 1})
    second = canonical_json_bytes({"alpha": 1, "beta": 2})
    assert first == second
    assert first.endswith(b"\n")
    assert first.index(b"alpha") < first.index(b"beta")


def test_canonical_json_bytes_rejects_nan() -> None:
    """Non-finite numbers cannot enter a drift-checked artefact."""
    with pytest.raises(ValueError, match="Out of range float values"):
        canonical_json_bytes({"value": float("nan")})


def test_sha256_of_file_matches_hashlib(tmp_path: Path) -> None:
    """The file digest equals a direct hashlib computation."""
    path = tmp_path / "payload.bin"
    path.write_bytes(b"tokamak")
    assert sha256_of_file(path) == hashlib.sha256(b"tokamak").hexdigest()
