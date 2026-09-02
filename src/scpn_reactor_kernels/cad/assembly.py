# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — B-rep assembly and its manifest

"""An ordered assembly of B-rep bodies with a canonical manifest.

The assembly keeps the bodies in the order given (a device fixes its body
order), refuses an empty list and duplicate names, projects one summary
per body (:meth:`BrepBody.summary_record`) into a manifest whose canonical
bytes (sorted keys, minimal separators, trailing newline, no NaN) are
digested by SHA-256, and builds the CadQuery ``Assembly`` the STEP writer
consumes. The manifest is the record a consumer stores; the STEP file is
an export of it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Final

from scpn_reactor_kernels.cad._backend import load_backend
from scpn_reactor_kernels.cad.solids import BrepBody
from scpn_reactor_kernels.errors import CadError

MANIFEST_SCHEMA: Final = "scpn.reactor-kernels-brep-assembly-manifest.v1"
MANIFEST_SCHEMA_VERSION: Final = "1.0.0"


@dataclass(frozen=True)
class BrepAssembly:
    """An ordered, uniquely named set of B-rep bodies.

    Parameters
    ----------
    bodies
        At least one body; names unique.

    Raises
    ------
    CadError
        If the list is empty or a name repeats.
    """

    bodies: tuple[BrepBody, ...]

    def __post_init__(self) -> None:
        """Validate the body inventory.

        Raises
        ------
        CadError
            If the list is empty or a name repeats.
        """
        if not self.bodies:
            raise CadError("bodies: at least one body is required")
        names = [body.name for body in self.bodies]
        if len(names) != len(set(names)):
            raise CadError(f"bodies: body names must be unique, got {names!r}")

    def manifest(self) -> dict[str, Any]:
        """Project the assembly to a JSON-serialisable manifest.

        Returns
        -------
        dict[str, Any]
            Schema identity, body count and one summary per body in order.
        """
        return {
            "schema": MANIFEST_SCHEMA,
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "body_count": len(self.bodies),
            "bodies": [body.summary_record() for body in self.bodies],
        }

    def manifest_bytes(self) -> bytes:
        """Serialise the manifest canonically.

        Returns
        -------
        bytes
            UTF-8 JSON with sorted keys, minimal separators and a trailing
            newline; NaN and infinity are never emitted.
        """
        text = json.dumps(
            self.manifest(), sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        return (text + "\n").encode("utf-8")

    def manifest_sha256(self) -> str:
        """Identify the exact manifest.

        Returns
        -------
        str
            SHA-256 of :meth:`manifest_bytes` as lowercase hex.
        """
        return hashlib.sha256(self.manifest_bytes()).hexdigest()

    def to_cadquery(self, name: str = "assembly") -> Any:
        """Build the CadQuery assembly the exporters consume.

        Parameters
        ----------
        name
            Root node name.

        Returns
        -------
        Any
            A ``cadquery.Assembly`` with one child per body, named as the
            body, in order.
        """
        cadquery = load_backend("cadquery")
        assembly = cadquery.Assembly(name=name)
        for body in self.bodies:
            assembly.add(body.shape, name=body.name)
        return assembly
