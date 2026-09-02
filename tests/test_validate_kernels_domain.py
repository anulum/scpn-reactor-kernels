# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — kernel manifest validator tests

"""Contract tests for the kernel manifest validator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from manifest_io import load_json_object
from validate_kernels_domain import main, validate_manifest

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "kernels-domain.json"


def write_manifest(tmp_path: Path, manifest: dict[str, Any]) -> Path:
    """Serialise one manifest object into a temporary file."""
    path = tmp_path / "kernels-domain.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def write_manifest_with_pointers(tmp_path: Path, manifest: dict[str, Any]) -> Path:
    """Serialise a manifest and create every pointer target except "absent" ones."""
    for kernel in manifest.get("kernels", []):
        if not isinstance(kernel, dict):
            continue
        for key in ("module", "evidence_pointer", "benchmark"):
            pointer = kernel.get(key)
            if isinstance(pointer, str) and pointer and "absent" not in pointer:
                target = tmp_path / pointer.split("#", 1)[0]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("x\n", encoding="utf-8")
    return write_manifest(tmp_path, manifest)


def mutated(**overrides: Any) -> dict[str, Any]:
    """Return the repository manifest with top-level fields replaced."""
    manifest = load_json_object(MANIFEST)
    manifest.update(overrides)
    return manifest


def kernel(**overrides: Any) -> dict[str, Any]:
    """Return the first committed kernel item with fields replaced."""
    item = dict(load_json_object(MANIFEST)["kernels"][0])
    item.update(overrides)
    return item


def test_repository_manifest_is_valid() -> None:
    """The committed manifest passes validation."""
    assert validate_manifest(MANIFEST) == []


def test_missing_manifest_is_one_finding(tmp_path: Path) -> None:
    """An unreadable manifest fails closed with a single load finding."""
    findings = validate_manifest(tmp_path / "absent.json")
    assert len(findings) == 1
    assert findings[0].startswith("manifest:")


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"schema": "other"}, "schema:"),
        ({"schema_version": "9.9.9"}, "schema_version:"),
        ({"project": ""}, "project:"),
        ({"license": "MIT"}, "license:"),
        ({"evidence_maturity": "finished"}, "evidence_maturity:"),
        ({"claims": ["fast"]}, "claims:"),
        ({"non_claims": []}, "non_claims:"),
        ({"owned_domains": []}, "owned_domains:"),
        ({"excluded_domains": []}, "excluded_domains:"),
        ({"excluded_domains": ["text"]}, "excluded_domains[0]:"),
        (
            {"excluded_domains": [{"domain": "", "owner": "X"}]},
            "excluded_domains[0].domain:",
        ),
        (
            {"research_group": {"display_name": "X", "coordination_identity": "OTHER"}},
            "coordination_identity: must be",
        ),
        ({"research_group": {"coordination_identity": "X"}}, "display_name: missing"),
        ({"library": "text"}, "library: missing"),
        ({"library": {"distribution": "scpn-x", "surprise": 1}}, "unknown fields"),
        ({"library": {"distribution": "Bad Name"}}, "library.distribution: invalid"),
        ({"machine_protection": None}, "machine_protection: missing"),
        (
            {"machine_protection": {"final_veto": "software", "statement": ""}},
            "final_veto: must be independent",
        ),
        (
            {"machine_protection": {"final_veto": "independent"}},
            "machine_protection.statement:",
        ),
        ({"consumers": "none"}, "consumers: must be a list"),
        ({"consumers": ["text"]}, "consumers[0]: must be an object"),
        (
            {"consumers": [{"project": "", "version": "1", "extra": 1}]},
            "unknown fields",
        ),
        (
            {
                "consumers": [
                    {"project": "X", "version": "1.0.0", "inventory_sha256": "zz"}
                ]
            },
            "inventory_sha256: must be 64",
        ),
        (
            {"evidence_maturity": "architecture_only"},
            "kernels: must be [] at architecture_only",
        ),
    ],
)
def test_defect_produces_finding(
    tmp_path: Path, overrides: dict[str, Any], fragment: str
) -> None:
    """Each contract violation yields a finding naming the failing field."""
    path = write_manifest_with_pointers(tmp_path, mutated(**overrides))
    findings = validate_manifest(path)
    assert any(fragment in finding for finding in findings), findings


def test_valid_consumer_pin_is_accepted(tmp_path: Path) -> None:
    """A well-formed consumer pin yields no finding."""
    manifest = mutated(
        consumers=[
            {
                "project": "SCPN-Z-PINCH-CORE",
                "version": "0.1.0.dev0",
                "inventory_sha256": "0" * 64,
            }
        ]
    )
    assert validate_manifest(write_manifest_with_pointers(tmp_path, manifest)) == []


def test_architecture_only_with_empty_kernels_is_valid(tmp_path: Path) -> None:
    """An architecture-only manifest with no kernels passes."""
    manifest = mutated(evidence_maturity="architecture_only", kernels=[])
    assert validate_manifest(write_manifest(tmp_path, manifest)) == []


@pytest.mark.parametrize(
    ("kernels", "maturity", "fragment"),
    [
        ([], "computational_prototype", "must be a non-empty list"),
        (["text"], "computational_prototype", "kernels[0]: must be an object"),
        ([kernel(surprise=1)], "computational_prototype", "unknown fields"),
        ([{"identifier": "a"}], "computational_prototype", "missing fields"),
        (
            [kernel(identifier="Bad-Name")],
            "computational_prototype",
            "invalid identifier",
        ),
        (
            [kernel(evidence_maturity="architecture_only")],
            "computational_prototype",
            "evidence_maturity: must be one of",
        ),
        (
            [kernel(module="src/absent.py")],
            "computational_prototype",
            "module: no committed",
        ),
        (
            [kernel(evidence_pointer="")],
            "computational_prototype",
            "evidence_pointer: no committed",
        ),
        (
            [kernel(benchmark="docs/absent.md#x")],
            "computational_prototype",
            "benchmark: no committed",
        ),
        ([kernel(native_parity="yes")], "computational_prototype", "native_parity:"),
        ([kernel(sources=[])], "computational_prototype", "sources:"),
        ([kernel(sources=["ok", ""])], "computational_prototype", "sources:"),
        ([kernel(), kernel()], "computational_prototype", "identifiers must be unique"),
        ([kernel()], "benchmark_validated", "ceiling rule"),
    ],
)
def test_kernel_inventory_violations(
    tmp_path: Path, kernels: list[Any], maturity: str, fragment: str
) -> None:
    """Each kernel-inventory violation yields its precise finding."""
    manifest = mutated(kernels=kernels, evidence_maturity=maturity)
    findings = validate_manifest(write_manifest_with_pointers(tmp_path, manifest))
    assert any(fragment in finding for finding in findings), findings


def test_main_pass_and_fail_exit_codes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The command-line interface reports PASS with 0 and FAIL with 1."""
    assert main([str(MANIFEST)]) == 0
    assert "kernels-domain: PASS" in capsys.readouterr().out
    broken = write_manifest(tmp_path, mutated(license="MIT"))
    assert main([str(broken)]) == 1
    output = capsys.readouterr().out
    assert "kernels-domain: FAIL" in output
    assert "- license:" in output
