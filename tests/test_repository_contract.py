# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — repository-level truth tests

"""Repository-level contract tests: the scaffold stays truthful."""

from __future__ import annotations

from pathlib import Path

import pytest

from manifest_io import load_json_object, sha256_of_file

REPO = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = (
    ".editorconfig",
    ".gitattributes",
    ".github/CODEOWNERS",
    ".github/FUNDING.yml",
    ".github/dependabot.yml",
    ".github/pull_request_template.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/workflow-inventory.json",
    ".github/workflows/ci.yml",
    ".github/workflows/reusable-static-policy.yml",
    ".github/workflows/reusable-tests.yml",
    ".gitignore",
    ".pre-commit-config.yaml",
    ".zenodo.json",
    "ARCHITECTURE.md",
    "CHANGELOG.md",
    "CITATION.cff",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "CONTRIBUTORS.md",
    "GOVERNANCE.md",
    "LICENSE",
    "Makefile",
    "NOTICE.md",
    "README.md",
    "REUSE.toml",
    "ROADMAP.md",
    "SECURITY.md",
    "SUPPORT.md",
    "VALIDATION.md",
    "benchmarks/geometry_tessellation.py",
    "benchmarks/results/geometry_tessellation.local.json",
    "benchmarks/transcendental.py",
    "benchmarks/results/transcendental.local.json",
    "benchmarks/bessel.py",
    "benchmarks/results/bessel.local.json",
    "benchmarks/cad.py",
    "benchmarks/results/cad.local.json",
    "conftest.py",
    "docs/ARCHITECTURE.md",
    "docs/THREAT_MODEL.md",
    "docs/adr/0001-repository-boundary.md",
    "docs/adr/0002-geometry-kernels.md",
    "docs/adr/0003-numerics-transcendental-kernels.md",
    "docs/adr/0004-first-consumer-pin.md",
    "docs/adr/0005-numerics-bessel-kernels.md",
    "docs/adr/0006-cad-kernels.md",
    "docs/adr/0015-bodies-without-curvature.md",
    "docs/adr/0016-arbitrary-angle-trigonometry.md",
    "docs/adr/0017-aimed-and-spherical-placement.md",
    "docs/adr/0018-cad-aimed-placement.md",
    "docs/benchmarks.md",
    "kernel-inventory.json",
    "kernels-domain.json",
    "pyproject.toml",
    "requirements-dev.txt",
    "rust/Cargo.toml",
    "rust/Cargo.lock",
    "rust/pyproject.toml",
    "rust/src/lib.rs",
    "rust/src/geometry/mod.rs",
    "rust/src/geometry/trig.rs",
    "rust/src/geometry/primitives.rs",
    "rust/src/geometry/mesh.rs",
    "rust/src/numerics/mod.rs",
    "rust/src/numerics/transcendental.rs",
    "rust/src/numerics/bessel.rs",
    "src/scpn_reactor_kernels/__init__.py",
    "src/scpn_reactor_kernels/errors.py",
    "src/scpn_reactor_kernels/validation.py",
    "src/scpn_reactor_kernels/geometry/__init__.py",
    "src/scpn_reactor_kernels/geometry/trig.py",
    "src/scpn_reactor_kernels/geometry/mesh.py",
    "src/scpn_reactor_kernels/geometry/primitives.py",
    "src/scpn_reactor_kernels/geometry/export.py",
    "src/scpn_reactor_kernels/numerics/__init__.py",
    "src/scpn_reactor_kernels/numerics/transcendental.py",
    "src/scpn_reactor_kernels/numerics/bessel.py",
    "src/scpn_reactor_kernels/cad/__init__.py",
    "src/scpn_reactor_kernels/cad/_backend.py",
    "src/scpn_reactor_kernels/cad/solids.py",
    "src/scpn_reactor_kernels/cad/assembly.py",
    "src/scpn_reactor_kernels/cad/step.py",
    "src/scpn_reactor_kernels/cad/facet.py",
    "src/scpn_reactor_kernels/cad/volume_mesh.py",
    "tools/preflight.py",
    "tools/validate_kernels_domain.py",
    "tools/generate_kernel_inventory.py",
)

REQUIRED_IGNORE_LINES = (
    "/BACKUP/",
    "/ARCHIVE/",
    "/.coordination/",
    "/04_ARCANE_SAPIENCE/",
)

FORBIDDEN_BADGE_MARKERS = (
    "[![",
    "api.reuse.software/badge/",
    "api.scorecard.dev/projects/",
    "bestpractices.dev/projects/",
    "pypi.org/project/",
)


@pytest.mark.parametrize("relative", REQUIRED_PATHS)
def test_required_path_exists_and_is_not_empty(relative: str) -> None:
    """Every Tier-0 and library surface exists with content."""
    path = REPO / relative
    assert path.is_file(), relative
    assert path.stat().st_size > 0, relative


def test_gitignore_carries_defensive_lines() -> None:
    """The ignore rules keep agent-state and backup trees out."""
    lines = {
        line.strip()
        for line in (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
    }
    for required in REQUIRED_IGNORE_LINES:
        assert required in lines, required


def test_readme_carries_no_unearned_badge() -> None:
    """No badge appears before its live evidence exists."""
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    for marker in FORBIDDEN_BADGE_MARKERS:
        assert marker not in readme, marker


def test_changelog_starts_unreleased() -> None:
    """The changelog carries an Unreleased section and no invented release."""
    changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "[Unreleased]" in changelog


def test_manifest_declares_the_library_truth() -> None:
    """The manifest names the library, its kernels and its empty claims."""
    manifest = load_json_object(REPO / "kernels-domain.json")
    assert manifest["project"] == "SCPN-REACTOR-KERNELS"
    assert manifest["library"]["distribution"] == "scpn-reactor-kernels"
    assert manifest["library"]["package"] == "scpn_reactor_kernels"
    assert manifest["evidence_maturity"] == "computational_prototype"
    assert [kernel["identifier"] for kernel in manifest["kernels"]] == [
        "geometry_unit_circle",
        "geometry_mesh_contract",
        "geometry_primitives",
        "geometry_exports",
        "geometry_profiles",
        "geometry_spheres",
        "geometry_placement",
        "numerics_transcendental",
        "numerics_bessel",
        "cad_brep_solids",
        "cad_step_export",
        "cad_faceting",
        "cad_volume_mesh",
        "cad_profiles",
        "cad_spheres",
        "cad_evidence",
        "cad_placement",
    ]
    assert manifest["owned_domains"] == [
        "shared_physics_geometry_and_numerics_kernels",
        "shared_physics_kernels",
        "shared_geometry_kernels",
        "shared_numerical_integrators",
        "shared_cad_and_meshing_adapters",
    ]
    assert manifest["claims"] == []
    assert manifest["consumers"] == [
        {
            "project": "SCPN-BEAM-TARGET-CORE",
            "version": "0.1.0.dev0",
            "source_commit": "9ea9eaee41a4378a8c23e647bbfde01bfb21bc49",
            "inventory_sha256": (
                "943d8f7a3e96069309ceab13f92d0c3fe86838216d23a067c531b50f45db8462"
            ),
        },
        {
            "project": "SCPN-DENSE-PLASMA-FOCUS-CORE",
            "version": "0.1.0.dev0",
            "source_commit": "98e6de5139f8856f5d50b4ac86f531b7dc38c1dc",
            "inventory_sha256": (
                "8b409c63435088f2e36d66322ec7a379243474bf8b99856100e8fc4c8add679a"
            ),
        },
        {
            "project": "SCPN-FRC-CORE",
            "version": "0.1.0.dev0",
            "source_commit": "7f419ea413af0e8fc051587ec0b3c83edf209c9f",
            "inventory_sha256": (
                "c1db6afb2dc0f196500514bcc53305c2bc69878e6e5d61730c76e3afcdc418f6"
            ),
        },
        {
            "project": "SCPN-FUSION-FISSION-HYBRID-CORE",
            "version": "0.1.0.dev0",
            "source_commit": "9ea9eaee41a4378a8c23e647bbfde01bfb21bc49",
            "inventory_sha256": (
                "943d8f7a3e96069309ceab13f92d0c3fe86838216d23a067c531b50f45db8462"
            ),
        },
        {
            "project": "SCPN-ICF-BEAM-CORE",
            "version": "0.1.0.dev0",
            "source_commit": "4d48b811ebf0c5a633963c047410c790ed0daa57",
            "inventory_sha256": (
                "de551e5ee272c42c646a89b77be5ad7a0475ceda951b0ac2d8a975fd00c42b79"
            ),
        },
        {
            "project": "SCPN-ICF-IMPACT-CORE",
            "version": "0.1.0.dev0",
            "source_commit": "4095aa8304974fd44d02c718d36eafc69b254944",
            "inventory_sha256": (
                "704bcca75675615fa87ff1c1debdf594f3dcdb9df17b19de48ef28046f95a303"
            ),
        },
        {
            "project": "SCPN-ICF-LASER-CORE",
            "version": "0.1.0.dev0",
            "source_commit": "4d48b811ebf0c5a633963c047410c790ed0daa57",
            "inventory_sha256": (
                "de551e5ee272c42c646a89b77be5ad7a0475ceda951b0ac2d8a975fd00c42b79"
            ),
        },
        {
            "project": "SCPN-LEVITATED-DIPOLE-CORE",
            "version": "0.1.0.dev0",
            "source_commit": "4095aa8304974fd44d02c718d36eafc69b254944",
            "inventory_sha256": (
                "704bcca75675615fa87ff1c1debdf594f3dcdb9df17b19de48ef28046f95a303"
            ),
        },
        {
            "project": "SCPN-MIF-LINER-CORE",
            "version": "0.1.0.dev0",
            "source_commit": "5bb26fd6bfd43acec34c3df9ef4c074532d671e4",
            "inventory_sha256": (
                "4e3f85ff448b6ff86ff85cda007319c0edb31553d0e2874e0578da9fd4ede888"
            ),
        },
        {
            "project": "SCPN-MIF-MAGLIF-CORE",
            "version": "0.1.0.dev0",
            "source_commit": "d9db5a425ae744bf60659edc7a1c3dda16bb1802",
            "inventory_sha256": (
                "9c43405ec5a184b813171f29ac0fc1a44eb0860777de9b08e65cd4a7554abb57"
            ),
        },
        {
            "project": "SCPN-MIF-PLASMA-JET-CORE",
            "version": "0.1.0.dev0",
            "source_commit": "86f14c0f0fd2dfb05e4cf9c78bad6308dcd5197e",
            "inventory_sha256": (
                "2bcbfd2adb3873ed38508bebefc3b5175fae9548fb372c9efa7cb845157ff7ac"
            ),
        },
        {
            "project": "SCPN-MIRROR-CORE",
            "version": "0.1.0.dev0",
            "source_commit": "98e6de5139f8856f5d50b4ac86f531b7dc38c1dc",
            "inventory_sha256": (
                "8b409c63435088f2e36d66322ec7a379243474bf8b99856100e8fc4c8add679a"
            ),
        },
        {
            "project": "SCPN-RFP-CORE",
            "version": "0.1.0.dev0",
            "source_commit": "98e6de5139f8856f5d50b4ac86f531b7dc38c1dc",
            "inventory_sha256": (
                "8b409c63435088f2e36d66322ec7a379243474bf8b99856100e8fc4c8add679a"
            ),
        },
        {
            "project": "SCPN-SPHEROMAK-CORE",
            "version": "0.1.0.dev0",
            "source_commit": "98e6de5139f8856f5d50b4ac86f531b7dc38c1dc",
            "inventory_sha256": (
                "8b409c63435088f2e36d66322ec7a379243474bf8b99856100e8fc4c8add679a"
            ),
        },
        {
            "project": "SCPN-THETA-PINCH-CORE",
            "version": "0.1.0.dev0",
            "source_commit": "98e6de5139f8856f5d50b4ac86f531b7dc38c1dc",
            "inventory_sha256": (
                "8b409c63435088f2e36d66322ec7a379243474bf8b99856100e8fc4c8add679a"
            ),
        },
        {
            "project": "SCPN-TOKAMAK-CORE",
            "version": "0.1.0.dev0",
            "source_commit": "9ea9eaee41a4378a8c23e647bbfde01bfb21bc49",
            "inventory_sha256": (
                "943d8f7a3e96069309ceab13f92d0c3fe86838216d23a067c531b50f45db8462"
            ),
        },
        {
            "project": "SCPN-Z-PINCH-CORE",
            "version": "0.1.0.dev0",
            "source_commit": "98e6de5139f8856f5d50b4ac86f531b7dc38c1dc",
            "inventory_sha256": (
                "8b409c63435088f2e36d66322ec7a379243474bf8b99856100e8fc4c8add679a"
            ),
        },
    ]


def test_inventory_embeds_current_manifest_digest() -> None:
    """The generated inventory points at the exact committed manifest bytes."""
    digest = sha256_of_file(REPO / "kernels-domain.json")
    inventory = load_json_object(REPO / "kernel-inventory.json")
    assert inventory["source"]["manifest_sha256"] == digest
    assert inventory["implemented_kernel_count"] == 17


def test_no_agent_state_trees_exist() -> None:
    """Forbidden agent-state paths are absent from the repository."""
    for forbidden in (
        ".coordination",
        "04_ARCANE_SAPIENCE",
        "BACKUP",
        "ARCHIVE",
    ):
        assert not (REPO / forbidden).exists(), forbidden


def test_package_agrees_with_manifest_truth() -> None:
    """The package identity matches the manifest's library block."""
    import scpn_reactor_kernels

    manifest = load_json_object(REPO / "kernels-domain.json")
    assert scpn_reactor_kernels.__name__ == manifest["library"]["package"]
    assert (REPO / "src" / "scpn_reactor_kernels" / "py.typed").is_file()
