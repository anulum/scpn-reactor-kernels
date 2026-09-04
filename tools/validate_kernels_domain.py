# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — kernel manifest validator

"""Fail closed when the kernel manifest violates its contract.

The validator enforces the ``scpn.reactor-kernels-domain.v1`` schema: the
library identity, the research-group identity, the licence, the
maturity-independent boundary invariants (empty claims inventory,
non-empty non-claims, the machine-protection final-veto declaration, the
owned and excluded domain tables), the per-state kernel rules (empty at
``architecture_only``; at every implemented state each kernel item has
the ratified shape with a module path, an evidence pointer and a
benchmark pointer that resolve to committed files, a non-empty source
list and a boolean native-parity flag, and the repository-level maturity
equals the highest kernel state), and the consumer pins (project,
distribution version and inventory digest).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Final

from manifest_io import load_json_object

SCHEMA: Final = "scpn.reactor-kernels-domain.v1"
SCHEMA_VERSION: Final = "1.0.0"
GROUP_IDENTITY: Final = "SCPN-REACTOR-SYSTEMS"
LICENSE_IDENTIFIER: Final = "AGPL-3.0-or-later"
EVIDENCE_STATES: Final = (
    "architecture_only",
    "computational_prototype",
    "benchmark_validated",
    "external_code_parity",
    "experiment_correlated",
    "control_research_ready",
)
HEX_DIGEST: Final = re.compile(r"^[0-9a-f]{64}$")
IDENTIFIER: Final = re.compile(r"^[a-z][a-z0-9_]*$")
DISTRIBUTION: Final = re.compile(r"^[a-z][a-z0-9-]*$")
COMMIT_OBJECT: Final = re.compile(r"^[0-9a-f]{40}$")
PEP440_VERSION: Final = re.compile(
    r"^(?:0|[1-9]\d*)(?:\.(?:0|[1-9]\d*)){2}"
    r"(?:(?:a|b|rc)(?:0|[1-9]\d*))?"
    r"(?:\.post(?:0|[1-9]\d*))?"
    r"(?:\.dev(?:0|[1-9]\d*))?"
    r"(?:\+[a-z0-9]+(?:[._-][a-z0-9]+)*)?$"
)
PROJECT: Final = "SCPN-REACTOR-KERNELS"
KERNEL_LIBRARY_DISTRIBUTION: Final = "scpn-reactor-kernels"
KERNEL_UMBRELLA_DOMAIN: Final = "shared_physics_geometry_and_numerics_kernels"
LIBRARY_FIELDS: Final = {
    "distribution": DISTRIBUTION,
    "package": IDENTIFIER,
    "native_distribution": DISTRIBUTION,
    "native_module": IDENTIFIER,
}
KERNEL_KEYS: Final = {
    "identifier",
    "module",
    "evidence_maturity",
    "evidence_pointer",
    "benchmark",
    "native_parity",
    "sources",
}


def _require_string(
    manifest: dict[str, Any], field: str, findings: list[str]
) -> str | None:
    """Return one required non-empty string field or record a finding.

    Parameters
    ----------
    manifest
        Decoded manifest object.
    field
        Dotted path of the field inside the manifest.
    findings
        Mutable finding sink.

    Returns
    -------
    str or None
        The value when present and valid, otherwise ``None``.
    """
    node: Any = manifest
    for part in field.split("."):
        if not isinstance(node, dict) or part not in node:
            findings.append(f"{field}: missing required field")
            return None
        node = node[part]
    if not isinstance(node, str) or not node:
        findings.append(f"{field}: must be a non-empty string")
        return None
    return node


def _validate_library(manifest: dict[str, Any], findings: list[str]) -> None:
    """Validate the library identity block.

    Parameters
    ----------
    manifest
        Decoded manifest object.
    findings
        Mutable finding sink.
    """
    library = manifest.get("library")
    if not isinstance(library, dict):
        findings.append("library: missing required object")
        return
    unknown = sorted(set(library) - set(LIBRARY_FIELDS))
    if unknown:
        findings.append(f"library: unknown fields {unknown!r}")
    for field, pattern in LIBRARY_FIELDS.items():
        value = _require_string(manifest, f"library.{field}", findings)
        if value is not None and pattern.fullmatch(value) is None:
            findings.append(f"library.{field}: invalid identifier {value!r}")
    if library.get("distribution") != KERNEL_LIBRARY_DISTRIBUTION:
        findings.append(
            f"library.distribution: must be {KERNEL_LIBRARY_DISTRIBUTION!r}"
        )


def _validate_boundary_invariants(
    manifest: dict[str, Any], findings: list[str]
) -> None:
    """Enforce the boundary rules that hold at every maturity state.

    Parameters
    ----------
    manifest
        Decoded manifest object.
    findings
        Mutable finding sink.
    """
    if manifest.get("claims") != []:
        findings.append("claims: must be [] until a claims contract exists")
    non_claims = manifest.get("non_claims")
    if not isinstance(non_claims, list) or not non_claims:
        findings.append("non_claims: must be a non-empty list")
    owned = manifest.get("owned_domains")
    if not isinstance(owned, list) or not owned:
        findings.append("owned_domains: must be a non-empty list")
    elif KERNEL_UMBRELLA_DOMAIN not in owned:
        findings.append("owned_domains: must include the shared-kernel umbrella domain")
    protection = manifest.get("machine_protection")
    if not isinstance(protection, dict):
        findings.append("machine_protection: missing required object")
    else:
        if protection.get("final_veto") != "independent":
            findings.append("machine_protection.final_veto: must be independent")
        statement = protection.get("statement")
        if not isinstance(statement, str) or not statement:
            findings.append("machine_protection.statement: must be a non-empty string")


def _validate_excluded_domains(manifest: dict[str, Any], findings: list[str]) -> None:
    """Validate the excluded-domain ownership table.

    Parameters
    ----------
    manifest
        Decoded manifest object.
    findings
        Mutable finding sink.
    """
    value = manifest.get("excluded_domains")
    if not isinstance(value, list) or not value:
        findings.append("excluded_domains: must be a non-empty list")
        return
    for index, entry in enumerate(value):
        if not isinstance(entry, dict):
            findings.append(f"excluded_domains[{index}]: must be an object")
            continue
        for key in ("domain", "owner"):
            field = entry.get(key)
            if not isinstance(field, str) or not field:
                findings.append(
                    f"excluded_domains[{index}].{key}: must be a non-empty string"
                )


def _resolves(manifest_dir: Path, pointer: Any) -> bool:
    """Return whether a ``path#anchor`` pointer names a committed file."""
    if not isinstance(pointer, str) or not pointer:
        return False
    return (manifest_dir / pointer.split("#", maxsplit=1)[0]).is_file()


def _validate_kernels(
    manifest: dict[str, Any],
    maturity: str,
    manifest_dir: Path,
    findings: list[str],
) -> None:
    """Validate the populated kernel inventory of an implemented state.

    Parameters
    ----------
    manifest
        Decoded manifest object.
    maturity
        Repository-level evidence-maturity state.
    manifest_dir
        Directory the pointers resolve against.
    findings
        Mutable finding sink.
    """
    kernels = manifest.get("kernels")
    if not isinstance(kernels, list) or not kernels:
        findings.append(f"kernels: must be a non-empty list at {maturity}")
        return
    implemented_states = EVIDENCE_STATES[1:]
    identifiers: list[str] = []
    highest = -1
    for index, item in enumerate(kernels):
        if not isinstance(item, dict):
            findings.append(f"kernels[{index}]: must be an object")
            continue
        unknown = sorted(set(item) - KERNEL_KEYS)
        if unknown:
            findings.append(f"kernels[{index}]: unknown fields {unknown!r}")
        missing = sorted(KERNEL_KEYS - set(item))
        if missing:
            findings.append(f"kernels[{index}]: missing fields {missing!r}")
        identifier = item.get("identifier")
        if not isinstance(identifier, str) or IDENTIFIER.fullmatch(identifier) is None:
            findings.append(
                f"kernels[{index}].identifier: invalid identifier {identifier!r}"
            )
        else:
            identifiers.append(identifier)
        state = item.get("evidence_maturity")
        if state not in implemented_states:
            findings.append(
                f"kernels[{index}].evidence_maturity: must be one of "
                f"{implemented_states!r}, got {state!r}"
            )
        else:
            highest = max(highest, EVIDENCE_STATES.index(state))
        for pointer_field in ("module", "evidence_pointer", "benchmark"):
            if not _resolves(manifest_dir, item.get(pointer_field)):
                findings.append(
                    f"kernels[{index}].{pointer_field}: no committed file behind "
                    f"{item.get(pointer_field)!r}"
                )
        if not isinstance(item.get("native_parity"), bool):
            findings.append(f"kernels[{index}].native_parity: must be a boolean")
        sources = item.get("sources")
        if (
            not isinstance(sources, list)
            or not sources
            or any(not isinstance(source, str) or not source for source in sources)
        ):
            findings.append(
                f"kernels[{index}].sources: must be a non-empty list of "
                "non-empty strings"
            )
    if len(identifiers) != len(set(identifiers)):
        findings.append("kernels: identifiers must be unique")
    if highest >= 0 and EVIDENCE_STATES.index(maturity) != highest:
        findings.append(
            "evidence_maturity: must equal the highest kernel state "
            f"{EVIDENCE_STATES[highest]!r} (ceiling rule)"
        )


def _validate_consumers(manifest: dict[str, Any], findings: list[str]) -> None:
    """Validate the consumer pin table.

    Parameters
    ----------
    manifest
        Decoded manifest object.
    findings
        Mutable finding sink.
    """
    consumers = manifest.get("consumers")
    if not isinstance(consumers, list):
        findings.append("consumers: must be a list")
        return
    for index, entry in enumerate(consumers):
        if not isinstance(entry, dict):
            findings.append(f"consumers[{index}]: must be an object")
            continue
        fields = {"project", "version", "source_commit", "inventory_sha256"}
        missing = sorted(fields - set(entry))
        if missing:
            findings.append(f"consumers[{index}]: missing fields {missing!r}")
        unknown = sorted(set(entry) - fields)
        if unknown:
            findings.append(f"consumers[{index}]: unknown fields {unknown!r}")
        project = entry.get("project")
        if not isinstance(project, str) or not project:
            findings.append(f"consumers[{index}].project: must be a non-empty string")
        version = entry.get("version")
        if not isinstance(version, str) or PEP440_VERSION.fullmatch(version) is None:
            findings.append(
                f"consumers[{index}].version: invalid governed PEP 440 version"
            )
        commit = entry.get("source_commit")
        if not isinstance(commit, str) or COMMIT_OBJECT.fullmatch(commit) is None:
            findings.append(
                f"consumers[{index}].source_commit: must be a 40-hex commit object"
            )
        digest = entry.get("inventory_sha256")
        if not isinstance(digest, str) or HEX_DIGEST.fullmatch(digest) is None:
            findings.append(
                f"consumers[{index}].inventory_sha256: must be 64 lowercase "
                "hexadecimal characters"
            )
    projects = [
        entry.get("project")
        for entry in consumers
        if isinstance(entry, dict) and isinstance(entry.get("project"), str)
    ]
    if len(projects) != len(set(projects)) or projects != sorted(projects):
        findings.append("consumers: projects must be unique and sorted")


def validate_manifest(manifest_path: Path) -> list[str]:
    """Validate one kernel manifest and return the findings.

    Parameters
    ----------
    manifest_path
        Manifest file to validate.

    Returns
    -------
    list[str]
        Human-readable findings; empty when the manifest is valid.
    """
    findings: list[str] = []
    try:
        manifest = load_json_object(manifest_path)
    except (OSError, ValueError) as exc:
        return [f"manifest: {exc}"]
    if manifest.get("schema") != SCHEMA:
        findings.append(f"schema: must be {SCHEMA!r}")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        findings.append(f"schema_version: must be {SCHEMA_VERSION!r}")
    project = _require_string(manifest, "project", findings)
    if project is not None and project != PROJECT:
        findings.append(f"project: must be {PROJECT!r}")
    _require_string(manifest, "research_group.display_name", findings)
    group = _require_string(manifest, "research_group.coordination_identity", findings)
    if group is not None and group != GROUP_IDENTITY:
        findings.append(
            f"research_group.coordination_identity: must be {GROUP_IDENTITY!r}"
        )
    if manifest.get("license") != LICENSE_IDENTIFIER:
        findings.append(f"license: must be {LICENSE_IDENTIFIER!r}")
    _validate_library(manifest, findings)
    _validate_boundary_invariants(manifest, findings)
    _validate_excluded_domains(manifest, findings)
    maturity = manifest.get("evidence_maturity")
    if maturity not in EVIDENCE_STATES:
        findings.append(f"evidence_maturity: unknown state {maturity!r}")
    elif maturity == "architecture_only":
        if manifest.get("kernels") != []:
            findings.append("kernels: must be [] at architecture_only")
    else:
        _validate_kernels(manifest, maturity, manifest_path.parent, findings)
    _validate_consumers(manifest, findings)
    return findings


def main(argv: list[str] | None = None) -> int:
    """Run the kernel manifest validator command-line interface.

    Parameters
    ----------
    argv
        Argument vector; ``None`` reads ``sys.argv``.

    Returns
    -------
    int
        ``0`` when the manifest is valid, ``1`` otherwise.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args(argv)
    findings = validate_manifest(args.manifest)
    if findings:
        print(f"kernels-domain: FAIL findings={len(findings)}")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("kernels-domain: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
