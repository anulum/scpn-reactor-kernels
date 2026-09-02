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
