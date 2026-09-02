# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — manifest input/output primitives

"""Strict JSON input/output primitives shared by the validation tooling.

Every loader rejects duplicate JSON member names and non-object top levels,
so a manifest edit can never silently shadow an earlier field. Canonical
serialisation is deterministic (sorted keys, two-space indent, trailing
newline) so generated artefacts are byte-stable and drift-checkable.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build one JSON object while rejecting repeated member names.

    Parameters
    ----------
    pairs
        Decoded ``(name, value)`` members in document order.

    Returns
    -------
    dict[str, Any]
        The object with every member name unique.

    Raises
    ------
    ValueError
        If a member name occurs more than once.
    """
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json_object(path: Path) -> dict[str, Any]:
    """Load a UTF-8 JSON object with duplicate-key rejection.

    Parameters
    ----------
    path
        File to read.

    Returns
    -------
    dict[str, Any]
        The decoded top-level object.

    Raises
    ------
    OSError
        If the file cannot be read.
    ValueError
        If the document is not valid JSON, contains a duplicate member
        name, or its top level is not an object.
    """
    try:
        with path.open(encoding="utf-8") as stream:
            value = json.load(stream, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path}: top-level JSON value must be an object")
    return value


def canonical_json_bytes(value: dict[str, Any]) -> bytes:
    """Serialise one object deterministically for drift-checked artefacts.

    Parameters
    ----------
    value
        Object to serialise.

    Returns
    -------
    bytes
        UTF-8 JSON with sorted keys, two-space indentation, no NaN values,
        and a trailing newline.
    """
    text = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        indent=2,
        sort_keys=True,
    )
    return (text + "\n").encode("utf-8")


def sha256_of_file(path: Path) -> str:
    """Return the lowercase hexadecimal SHA-256 digest of one file.

    Parameters
    ----------
    path
        File to digest.

    Returns
    -------
    str
        Sixty-four lowercase hexadecimal characters.

    Raises
    ------
    OSError
        If the file cannot be read.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()
