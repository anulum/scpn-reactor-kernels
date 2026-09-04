# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — kernel inventory generation

"""Generate the public kernel inventory from the kernel manifest.

The inventory is the repository's truthful public statement of implemented
kernels. Kernel metadata is projected from ``kernels-domain.json``. Consumer
rows are projected from explicit device-manifest paths when supplied; this is
the authoritative cross-repository mode. Omitting those paths preserves the
standalone repository check against the manifest's generated consumer mirror.
``--check`` fails when the committed inventory differs byte-for-byte from a
fresh generation; ``--write`` regenerates it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Final

from manifest_io import canonical_json_bytes, load_json_object, sha256_of_file

INVENTORY_SCHEMA: Final = "scpn.kernel-inventory.v1"
INVENTORY_SCHEMA_VERSION: Final = "1.0.0"
CONSUMER_FIELDS: Final = frozenset(
    {"project", "version", "source_commit", "inventory_sha256"}
)


def _consumer_from_manifest(manifest_path: Path) -> dict[str, Any]:
    """Project one exact reverse-inventory row from a device manifest."""
    manifest = load_json_object(manifest_path)
    project = manifest.get("project")
    pin = manifest.get("kernel_library")
    if not isinstance(project, str) or not project:
        raise ValueError(f"{manifest_path}: project must be a non-empty string")
    if not isinstance(pin, dict):
        raise ValueError(f"{manifest_path}: kernel_library must be an object")
    required = {"version", "source_commit", "inventory_sha256"}
    missing = sorted(required - set(pin))
    if missing:
        raise ValueError(f"{manifest_path}: kernel_library missing {missing!r}")
    return {
        "project": project,
        "version": pin["version"],
        "source_commit": pin["source_commit"],
        "inventory_sha256": pin["inventory_sha256"],
    }


def _consumer_rows(
    manifest: dict[str, Any], consumer_manifest_paths: list[Path]
) -> list[dict[str, Any]]:
    """Return sorted unique consumer rows from explicit or local inputs."""
    if consumer_manifest_paths:
        rows = [_consumer_from_manifest(path) for path in consumer_manifest_paths]
    else:
        value = manifest.get("consumers")
        if not isinstance(value, list):
            raise ValueError("manifest consumers field must be a list")
        rows = []
        for index, row in enumerate(value):
            if not isinstance(row, dict) or set(row) != CONSUMER_FIELDS:
                raise ValueError(
                    f"manifest consumers[{index}] must contain exactly "
                    f"{sorted(CONSUMER_FIELDS)!r}"
                )
            rows.append(dict(row))
    projects = [row.get("project") for row in rows]
    if any(not isinstance(project, str) or not project for project in projects):
        raise ValueError("consumer projects must be non-empty strings")
    if len(projects) != len(set(projects)):
        raise ValueError("consumer projects must be unique")
    return sorted(rows, key=lambda row: str(row["project"]))


def generate_inventory(
    manifest_path: Path, consumer_manifest_paths: list[Path] | None = None
) -> dict[str, Any]:
    """Build the inventory object from one kernel manifest.

    Parameters
    ----------
    manifest_path
        Manifest file to project.
    consumer_manifest_paths
        Explicit authoritative device manifests. ``None`` uses the generated
        consumer mirror already stored in the kernel manifest.

    Returns
    -------
    dict[str, Any]
        The inventory object, ready for canonical serialisation.

    Raises
    ------
    OSError
        If the manifest cannot be read.
    ValueError
        If the manifest is not a valid JSON object or its kernel field is
        not a list.
    """
    manifest = load_json_object(manifest_path)
    kernels = manifest.get("kernels")
    if not isinstance(kernels, list):
        raise ValueError("manifest kernels field must be a list")
    return {
        "schema": INVENTORY_SCHEMA,
        "schema_version": INVENTORY_SCHEMA_VERSION,
        "project": manifest.get("project"),
        "library": manifest.get("library"),
        "evidence_maturity": manifest.get("evidence_maturity"),
        "implemented_kernel_count": len(kernels),
        "kernels": kernels,
        "consumers": _consumer_rows(manifest, consumer_manifest_paths or []),
        "claims": manifest.get("claims"),
        "source": {
            "manifest_path": manifest_path.name,
            "manifest_sha256": sha256_of_file(manifest_path),
        },
    }


def main(argv: list[str] | None = None) -> int:
    """Run the kernel inventory command-line interface.

    Parameters
    ----------
    argv
        Argument vector; ``None`` reads ``sys.argv``.

    Returns
    -------
    int
        ``0`` on success (in-sync check or completed write), ``1`` on
        drift or generation failure.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("kernels-domain.json"))
    parser.add_argument("--inventory", type=Path, default=Path("kernel-inventory.json"))
    parser.add_argument(
        "--consumer-manifest",
        action="append",
        type=Path,
        default=[],
        help="explicit authoritative device manifest (repeatable)",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        generated = canonical_json_bytes(
            generate_inventory(args.manifest, args.consumer_manifest)
        )
    except (OSError, ValueError) as exc:
        print(f"kernel-inventory: FAIL {exc}")
        return 1
    if args.write:
        args.inventory.parent.mkdir(parents=True, exist_ok=True)
        args.inventory.write_bytes(generated)
        print(f"kernel-inventory: wrote {args.inventory}")
        return 0
    try:
        committed = args.inventory.read_bytes()
    except OSError as exc:
        print(f"kernel-inventory: FAIL cannot read committed inventory: {exc}")
        return 1
    if committed != generated:
        print("kernel-inventory: FAIL drift between manifest and inventory")
        return 1
    print("kernel-inventory: PASS in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
