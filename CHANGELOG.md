<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — CHANGELOG
-->

# Changelog

## [Unreleased]

### Added

- Bessel kernels (`src/scpn_reactor_kernels/numerics/bessel.py`, kernel
  `numerics_bessel`, ADR 0005): `J0` and `J1` by the DLMF 10.2.2 ascending
  series in Horner form with exact integer-quotient coefficients, thirty
  terms, on the declared domain `|x| <= 8` (refused beyond, never
  clamped); the first zeros `j_{0,1}` and `j_{1,1}` as the correctly
  rounded OEIS expansions; verified against an exact rational evaluation
  of the same series; native kernels in `rust/src/numerics/bessel.rs`
  with scalar and stream bindings proven bit-exact by parity tests; a
  standard-conformant benchmark with a committed local artefact.

### Changed

- First consumer recorded (ADR 0004): SCPN-Z-PINCH-CORE pins the
  distribution at `0.1.0.dev0` and the kernel-inventory digest of the
  commit it depends on, consuming the four geometry kernels; the
  `consumers` table of `kernels-domain.json` and the generated inventory
  carry the entry. The README states that a consumer's digest names the
  inventory at the pinned commit, since recording the consumer changes
  the inventory.
- Second consumer recorded: SCPN-MIRROR-CORE pins the same commit and
  inventory digest for the numerics kernel `numerics_transcendental`; its
  native crate depends on `scpn-reactor-kernels-rs` as a git dependency
  at that commit, the first use of the Rust crate as a library.
- Third consumer recorded: SCPN-DENSE-PLASMA-FOCUS-CORE retired its
  byte-identical copy of the numerics kernel for the same pin.
- Fourth consumer recorded: SCPN-RFP-CORE pins the commit that introduced
  the Bessel kernel `numerics_bessel` and its inventory digest, the first
  consumer of that kernel; its native crate depends on the Rust crate at
  that commit.

### Added

- Repository established as the shared kernel library of the SCPN Reactor
  Systems Research Group: kernel manifest `kernels-domain.json` (schema
  `scpn.reactor-kernels-domain.v1`) with a fail-closed validator, generated
  kernel inventory with drift check, workflow modularity guard, preflight
  orchestrator, uniform gate and workflow surfaces (ADR 0001).
- Geometry kernels (`src/scpn_reactor_kernels/geometry/`), the first
  implemented kernel group at `computational_prototype` (ADR 0002): a
  vendored deterministic unit circle, the closed-mesh contract
  (`TriangleMesh`), solid-cylinder and annular-tube tessellation, binary
  STL and glTF 2.0 binary exports of any body list, native kernels in
  `rust/` proven bit-exact by parity tests, and a standard-conformant
  benchmark with a committed local artefact.
- Numerics kernels (`src/scpn_reactor_kernels/numerics/`), the second
  implemented kernel group at `computational_prototype` (ADR 0003): a
  vendored deterministic natural logarithm, exponential and real power
  with refused (never clamped) domains, measured accuracy bounds against
  the platform `math` module, native kernels in `rust/` with scalar and
  stream bindings proven bit-exact by parity tests, and a
  standard-conformant benchmark with a committed local artefact.
