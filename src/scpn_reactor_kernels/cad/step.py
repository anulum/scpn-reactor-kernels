# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — deterministic STEP export

"""STEP (ISO 10303-21) export of a B-rep assembly with a normalised header.

The OpenCASCADE writer (``STEPControl_Writer`` through CadQuery's
``Assembly.export``) emits a Part 21 file whose ``HEADER`` carries a
``FILE_NAME`` with the wall-clock time stamp and whose
``NEXT_ASSEMBLY_USAGE_OCCURRENCE`` entities carry identifiers drawn from a
process-wide running counter, so two exports of the same assembly differ
in bytes. This kernel rewrites both deterministically: the time stamp
becomes the fixed literal :data:`STEP_FIXED_TIMESTAMP`, the file name the
fixed :data:`STEP_FILE_NAME`, the usage-occurrence identifiers are
renumbered from ``1`` in order of appearance, and the ``FILE_DESCRIPTION``
carries the generator name and the caller's provenance extras as a JSON
string (apostrophes doubled per Part 21). The writer also wraps long
lines onto indented continuation lines at a fixed column counted from the
PRE-renumbering identifier lengths, so the normaliser first unfolds every
continuation line (a newline followed by indentation is deleted: Part 21
whitespace is insignificant outside string literals, and the writer never
wraps inside a string); only then are the identifiers renumbered, making
the bytes independent of the counter's digit length. The same assembly
then yields the same bytes in the same environment, identified by
SHA-256; identity across OpenCASCADE versions is not claimed (the
versions travel in the extras a consumer records).
"""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
from pathlib import Path
from typing import Any, Final

from scpn_reactor_kernels.cad.assembly import BrepAssembly
from scpn_reactor_kernels.errors import CadError

STEP_FIXED_TIMESTAMP: Final = "2000-01-01T00:00:00"
STEP_FILE_NAME: Final = "scpn_reactor_kernels_assembly.step"
STEP_GENERATOR: Final = "scpn-reactor-kernels cad_step_export"

_FILE_NAME: Final = re.compile(r"FILE_NAME\('[^']*','[^']*'")
_FILE_DESCRIPTION: Final = re.compile(r"FILE_DESCRIPTION\(\('[^']*'\)")
_USAGE_OCCURRENCE: Final = re.compile(r"NEXT_ASSEMBLY_USAGE_OCCURRENCE\('\d+',")
#: The writer's line wrap: a newline followed by the continuation indent.
_CONTINUATION: Final = re.compile(r"\n +")


def _part21_string(text: str) -> str:
    """Escape a string for a Part 21 quoted literal (apostrophes doubled)."""
    return text.replace("'", "''")


def normalise_step_text(text: str, extras: dict[str, Any]) -> str:
    """Rewrite the non-deterministic parts of a Part 21 text.

    Parameters
    ----------
    text
        The writer's output.
    extras
        JSON-serialisable provenance placed into ``FILE_DESCRIPTION``.

    Returns
    -------
    str
        The normalised text: continuation lines unfolded, fixed file name
        and time stamp, provenance in the description, usage-occurrence
        identifiers renumbered from one.

    Raises
    ------
    CadError
        If the text lacks the expected header entities.
    """
    text = _CONTINUATION.sub("", text)
    if _FILE_NAME.search(text) is None or _FILE_DESCRIPTION.search(text) is None:
        raise CadError("step: the writer output lacks the Part 21 header entities")
    description = _part21_string(
        STEP_GENERATOR
        + " "
        + json.dumps(extras, sort_keys=True, separators=(",", ":"), allow_nan=False)
    )
    text = _FILE_NAME.sub(
        f"FILE_NAME('{STEP_FILE_NAME}','{STEP_FIXED_TIMESTAMP}'", text, count=1
    )
    text = _FILE_DESCRIPTION.sub(f"FILE_DESCRIPTION(('{description}')", text, count=1)
    counter = 0

    def renumber(_: re.Match[str]) -> str:
        nonlocal counter
        counter += 1
        return f"NEXT_ASSEMBLY_USAGE_OCCURRENCE('{counter}',"

    return _USAGE_OCCURRENCE.sub(renumber, text)


def step_bytes(assembly: BrepAssembly, extras: dict[str, Any]) -> bytes:
    """Export an assembly as normalised STEP bytes.

    Parameters
    ----------
    assembly
        The bodies to export, in order, named as their nodes.
    extras
        JSON-serialisable provenance (a consumer puts its schema, digests,
        units and back-end versions here).

    Returns
    -------
    bytes
        The Part 21 text as UTF-8, deterministic in one environment.

    Raises
    ------
    CadError
        If ``extras`` is not a JSON-serialisable object or the writer output
        is malformed; :class:`CadUnavailableError` if the back-end is
        absent.
    """
    if not isinstance(extras, dict):
        raise CadError("extras: must be a JSON object")
    try:
        json.dumps(extras, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise CadError(f"extras: must be JSON-serialisable: {exc}") from exc
    cad_assembly = assembly.to_cadquery()
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / STEP_FILE_NAME
        cad_assembly.export(str(target))
        text = target.read_text(encoding="utf-8")
    return normalise_step_text(text, extras).encode("utf-8")


def step_sha256(data: bytes) -> str:
    """Identify exact STEP bytes.

    Parameters
    ----------
    data
        STEP bytes.

    Returns
    -------
    str
        SHA-256 as lowercase hex.
    """
    return hashlib.sha256(data).hexdigest()


def write_step(path: Path, assembly: BrepAssembly, extras: dict[str, Any]) -> int:
    """Write the normalised STEP file.

    Parameters
    ----------
    path
        Target file.
    assembly
        The bodies to export.
    extras
        Provenance extras.

    Returns
    -------
    int
        Bytes written.
    """
    data = step_bytes(assembly, extras)
    path.write_bytes(data)
    return len(data)
