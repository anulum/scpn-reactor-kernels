# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — CAD back-end loader tests

"""The optional back-ends load lazily and their absence is a named refusal."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from types import ModuleType

import pytest

from scpn_reactor_kernels.cad._backend import (
    INSTALL_HINT,
    backend_versions,
    load_backend,
)
from scpn_reactor_kernels.errors import CadError, CadUnavailableError, KernelInputError


def blocking(names: set[str]) -> Callable[..., ModuleType]:
    """Return an import function that refuses the given module names."""
    original = importlib.import_module

    def fake(name: str, package: str | None = None) -> ModuleType:
        if name in names:
            raise ImportError(name)
        return original(name, package)

    return fake


def test_missing_backend_is_a_named_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing back-end raises CadUnavailableError with the install hint."""
    monkeypatch.setattr(importlib, "import_module", blocking({"cadquery"}))
    with pytest.raises(CadUnavailableError, match="cadquery") as info:
        load_backend("cadquery")
    assert INSTALL_HINT in str(info.value)
    assert isinstance(info.value, CadError)
    assert isinstance(info.value, KernelInputError)
    assert info.value.__cause__ is not None


def test_versions_report_unavailable_backends(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each version entry falls back to 'unavailable' when its module is absent."""
    monkeypatch.setattr(
        importlib, "import_module", blocking({"cadquery", "OCP", "gmsh"})
    )
    assert backend_versions() == {
        "cadquery": "unavailable",
        "ocp": "unavailable",
        "gmsh": "unavailable",
    }


def test_versions_report_a_partial_installation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CadQuery present without OCP or gmsh yields the two unavailable entries."""
    pytest.importorskip("cadquery")
    monkeypatch.setattr(importlib, "import_module", blocking({"OCP", "gmsh"}))
    versions = backend_versions()
    assert versions["cadquery"] != "unavailable"
    assert versions["ocp"] == "unavailable"
    assert versions["gmsh"] == "unavailable"


def test_versions_are_strings_when_installed() -> None:
    """With the extra installed every version is a non-empty string."""
    pytest.importorskip("cadquery")
    pytest.importorskip("gmsh")
    versions = backend_versions()
    assert set(versions) == {"cadquery", "ocp", "gmsh"}
    assert all(value and value != "unavailable" for value in versions.values())
    assert load_backend("gmsh").__name__ == "gmsh"
