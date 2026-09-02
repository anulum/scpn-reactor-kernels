# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — kernel inventory generation

"""Generate the public kernel inventory from the kernel manifest.

The inventory is the repository's truthful public statement of implemented
kernels. It is derived, never hand-edited: the kernel list, the consumer
pins and the evidence maturity are copied from ``kernels-domain.json`` and
the manifest's SHA-256 is embedded so drift is detectable. ``--check``
fails when the committed inventory differs byte-for-byte from a fresh
generation; ``--write`` regenerates it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Final

from manifest_io import canonical_json_bytes, load_json_object, sha256_of_file

INVENTORY_SCHEMA: Final = "scpn.kernel-inventory.v1"
INVENTORY_SCHEMA_VERSION: Final = "1.0.0"


def generate_inventory(manifest_path: Path) -> dict[str, Any]:
    """Build the inventory object from one kernel manifest.

    Parameters
    ----------
    manifest_path
        Manifest file to project.

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
        "consumers": manifest.get("consumers"),
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
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        generated = canonical_json_bytes(generate_inventory(args.manifest))
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
