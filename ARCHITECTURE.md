<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — Architecture summary
-->

# Architecture summary

`SCPN-REACTOR-KERNELS` is the shared physics and geometry kernel library
of the SCPN Reactor Systems Research Group. It holds one implemented kernel
group at `computational_prototype` — the geometry kernels (ADR 0002:
deterministic unit circle, closed-mesh contract, cylinder and tube
tessellation, STL and glTF exports, native counterparts in `rust/`) — in
`src/scpn_reactor_kernels/`, alongside the kernel manifest, the validation
tooling that enforces it, and the benchmark that measures it.

The authoritative architecture record is
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). The ownership decision and
its consequences are fixed in
[`docs/adr/0001-repository-boundary.md`](docs/adr/0001-repository-boundary.md).

Boundary in one paragraph: this repository owns published closed forms and
standard numerical methods that more than one device family needs, each
with a Python floor, a bit-exact native kernel, parity evidence and a
benchmark, and the inventory consumers pin. It owns no device truth
(device repositories), no solver mathematics or validation evidence
(`SCPN-FUSION-CORE`), no typed semantics (`SCPN-PHASE-ORCHESTRATOR`), no
admitted action (`SCPN-CONTROL`), no presentation (`SCPN-STUDIO`), and no
machine protection (independent, final veto).
