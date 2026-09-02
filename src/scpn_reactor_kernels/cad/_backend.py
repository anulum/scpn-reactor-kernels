# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — optional CAD back-end loader

"""Lazy loaders of the optional CAD back-ends (CadQuery/OCP, gmsh).

Nothing in the library imports the back-ends at import time: a consumer
without the ``cad`` extra can use every other kernel. A CAD kernel asks
for its back-end here and receives :class:`CadUnavailableError` with the
install hint when the extra is absent.
"""

from __future__ import annotations

import importlib
from types import ModuleType
from typing import Final

from scpn_reactor_kernels.errors import CadUnavailableError

INSTALL_HINT: Final = (
    "install the optional extra: pip install 'scpn-reactor-kernels[cad]'"
)


def load_backend(module_name: str) -> ModuleType:
    """Import one optional back-end module.

    Parameters
    ----------
    module_name
        ``"cadquery"`` or ``"gmsh"``.

    Returns
    -------
    ModuleType
        The imported module.

    Raises
    ------
    CadUnavailableError
        If the module cannot be imported.
    """
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        raise CadUnavailableError(
            f"{module_name}: the optional CAD back-end is not installed; {INSTALL_HINT}"
        ) from exc


def backend_versions() -> dict[str, str]:
    """Return the versions of the installed CAD back-ends.

    Returns
    -------
    dict[str, str]
        ``cadquery``, ``ocp`` and ``gmsh`` versions, or ``"unavailable"``.
    """
    versions: dict[str, str] = {}
    try:
        cadquery = load_backend("cadquery")
        versions["cadquery"] = str(cadquery.__version__)
        ocp = load_backend("OCP")
        versions["ocp"] = str(ocp.__version__)
    except CadUnavailableError:
        versions.setdefault("cadquery", "unavailable")
        versions.setdefault("ocp", "unavailable")
    try:
        gmsh = load_backend("gmsh")
        versions["gmsh"] = str(gmsh.__version__)
    except CadUnavailableError:
        versions["gmsh"] = "unavailable"
    return versions
