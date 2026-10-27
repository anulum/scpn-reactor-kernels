# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — dependency lock integrity tests

"""Hash-locked install sets stay complete and agree with their inputs."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
LOCKS = sorted(REPO.glob("requirements-*.txt"))
INPUTS = sorted(REPO.glob("requirements-*.in"))
WORKFLOWS = sorted((REPO / ".github" / "workflows").glob("*.yml"))
KERNEL_PIN = re.compile(
    r"scpn-reactor-kernels(?:\[[a-z,]+\])? @ "
    r"git\+https://github\.com/anulum/scpn-reactor-kernels\.git@([0-9a-f]{40})"
)
KERNEL_ARCHIVE = re.compile(r"scpn-reactor-kernels/archive/([0-9a-f]{40})\.tar\.gz")
PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==(\S+)$")
ACCEPTED_INSTALL = re.compile(
    r"pip install (?:--require-hashes -r \S+(?: -r \S+)*"
    r"|--no-deps -e \.|--no-deps dist/\*\.whl)$"
)


def _normalise(name: str) -> str:
    """Return the PEP 503 normalised form of a distribution name.

    Parameters
    ----------
    name
        Distribution name as written in a requirement.

    Returns
    -------
    str
        Lower-case name with runs of ``-``, ``_`` and ``.`` collapsed to ``-``.
    """
    return re.sub(r"[-_.]+", "-", name).lower()


def _entries(lock: Path) -> list[str]:
    """Split a lock file into its requirement entries.

    Parameters
    ----------
    lock
        Hash-locked requirement file.

    Returns
    -------
    list of str
        One string per requirement, continuation lines included.
    """
    entries: list[str] = []
    for line in lock.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith(" "):
            entries[-1] += "\n" + line
        else:
            entries.append(line)
    return entries


def test_locks_exist() -> None:
    """The development and audit sets are locked."""
    names = {lock.name for lock in LOCKS}
    assert {"requirements-dev.txt", "requirements-audit.txt"} <= names


@pytest.mark.parametrize("lock", LOCKS, ids=lambda path: path.name)
def test_every_locked_requirement_carries_a_digest(lock: Path) -> None:
    """Every entry is an exact pin or archive with at least one sha256 digest."""
    entries = _entries(lock)
    assert entries, lock.name
    for entry in entries:
        head = entry.split(" \\", 1)[0]
        assert "==" in head or " @ https://" in head, head
        assert "--hash=sha256:" in entry, head


@pytest.mark.parametrize("lock", LOCKS, ids=lambda path: path.name)
def test_every_lock_is_regenerated_by_make(lock: Path) -> None:
    """``make lock`` writes every committed lock file."""
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    assert f"> {lock.name}" in makefile, lock.name


@pytest.mark.parametrize("source", INPUTS, ids=lambda path: path.name)
def test_top_level_pins_are_locked_unchanged(source: Path) -> None:
    """Each exact pin of a lock input is locked at the same version."""
    lock = source.with_suffix(".txt")
    locked = {
        _normalise(match.group(1)): match.group(2)
        for entry in _entries(lock)
        if (match := PIN.match(entry.split(" \\", 1)[0]))
    }
    for line in source.read_text(encoding="utf-8").splitlines():
        if match := PIN.match(line.strip()):
            assert locked.get(_normalise(match.group(1))) == match.group(2), line


def test_kernel_archive_matches_the_declared_commit() -> None:
    """The kernel archive lock names the commit pinned in pyproject.toml."""
    pyproject = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    declared = set(KERNEL_PIN.findall(pyproject))
    kernel_files = [REPO / "requirements-kernels.in", REPO / "requirements-kernels.txt"]
    if not declared:
        assert not any(path.exists() for path in kernel_files)
        return
    assert len(declared) == 1, declared
    for path in kernel_files:
        assert set(KERNEL_ARCHIVE.findall(path.read_text(encoding="utf-8"))) == declared


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda path: path.name)
def test_workflows_install_only_from_locks(workflow: Path) -> None:
    """Every CI install is hash-locked, the package itself, or a built wheel."""
    for line in workflow.read_text(encoding="utf-8").splitlines():
        command = line.strip().removeprefix("run: ")
        if "pip install" in command:
            assert ACCEPTED_INSTALL.search(command), command


def test_dependabot_skips_the_derived_cad_lock() -> None:
    """Dependabot never bumps a transitive pin of the derived CAD lock alone."""
    config = (REPO / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    if (REPO / "requirements-cad.txt").exists():
        assert '- "requirements-cad.txt"' in config
