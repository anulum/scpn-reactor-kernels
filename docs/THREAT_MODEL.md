<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — Threat model
-->

# Threat model

Scoped to the current state: the executable surface is the kernel library
(`src/`), its optional native extension (`rust/`), the benchmarks and the
validation tooling (`tools/`); the valuable content is the correctness of
every kernel and the truthfulness of the kernel manifest. The model is
revisited whenever a new kernel group or a new consumer contract is added.

## Assets

| Asset | Why it matters |
|---|---|
| Kernel implementations (`src/`, `rust/`) | twenty device repositories will compute from them; a silent numerical error propagates to every consumer |
| `kernels-domain.json` | the inventory consumers pin by digest; must never overstate maturity or sources |
| `kernel-inventory.json` | public truthfulness of the implemented kernel set |
| Parity fixtures and benchmark artefacts | evidence that the native path equals the floor |
| Pinned third-party CAD kernels (CadQuery/OpenCASCADE, gmsh; optional extra `cad`) | every STEP file and volume mesh a consumer records comes from them; a silent version drift would change exported bytes and digests |
| Workflow definitions | future execution with hosted credentials |
| Licensing/provenance metadata | legal integrity of the repository |

## Trust boundaries and actors

- **Repository editor** (owner, reviewed contributor): trusted after review;
  every change passes the gate sequence.
- **Consumer** (device repository, benchmark, reviewer): trusts a kernel
  only as far as its manifest entry, sources and evidence record; must not
  be able to read more validity out of a kernel than its declared range.
- **Hosted CI** (future, after a remote exists): untrusted-by-default
  execution environment; workflows carry empty top-level permissions,
  per-job least privilege, pinned action commit objects, and bounded
  timeouts.
- **Supply chain**: the pinned Python toolchain in `requirements-dev.txt`,
  the pinned Rust dependency (`pyo3`) in `rust/Cargo.lock`, and the pinned
  GitHub Actions are the only third-party code paths.

## Misuse paths and mitigations

| Misuse path | Mitigation |
|---|---|
| Feeding a kernel an input outside its validity range and using the result | every kernel refuses non-finite and out-of-range inputs with a named error; ranges are declared in the docstring and the manifest |
| Silent unit errors | SI units in every field name; no implicit unit conversion in any public function |
| A native kernel diverging from the floor | parity tests by float64 bit pattern in the hosted `rust` job and locally; identical operation order is a review requirement |
| Editing the inventory to imply an implemented kernel | the inventory is generated; `--check` drift gates in pre-commit, preflight and CI fail on any manual edit |
| Adding a kernel without sources or evidence | the validator refuses a kernel item without a non-empty source list, a resolvable module path and a resolvable evidence pointer |
| Consumer pinning a stale digest | consumers record the inventory SHA-256; a mismatch is detectable on both sides |
| Workflow tampering towards write authority | no write-authority workflow exists; permissions are empty at top level; action references must be 40-hex commit objects (shared Tier-0 audit enforces) |
| Dependency substitution | exact version pins; updates land only through the full gate sequence |
| A CAD back-end version drifting under a consumer's recorded digests | the extra pins exact versions; `backend_versions()` travels in every export's provenance; determinism is claimed per environment only and a version bump is a governed data change (ADR 0006) |
| Treating a faceted or volume mesh as exact | the faceting reports the declared deficit bound and the volume mesh its per-entity volumes against the B-rep; tolerances are declared, never hidden |
| Secret introduction | no secrets exist or are needed; security-audit workflow and review gates scan the diff |

## Fail-closed behaviour

Every kernel raises a named error on invalid input instead of clamping or
returning NaN. Every validator in `tools/` exits non-zero on the first
unrecoverable finding, treats a missing file, unparseable JSON, duplicate
JSON keys, or an unknown schema as failure (never as "skip"), and prints
the exact failing check. The preflight orchestrator aggregates gate results
and fails if any gate fails or cannot run — a missing tool is a failed
gate, not a pass.

## Residual risks

- Bit-exact parity is proven for the platforms the tests run on; a
  platform whose compiler contracts floating-point operations (fused
  multiply-add) without being asked would break parity and would be caught
  by the parity tests, not prevented.
- Licence-text files and generated JSON carry no in-file provenance header
  (format constraints); REUSE.toml annotations close this gap.
- No cryptographic signing of the manifest exists yet; digest pinning
  covers integrity of derivation, not authorship. Signing is a future
  portfolio decision.
