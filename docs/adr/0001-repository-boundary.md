<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — ADR 0001: repository boundary
-->

# ADR 0001 — Repository boundary and ownership

**Status:** accepted (2026-09-02)

**Deciders:** project owner (programme decision D1-a); SCPN Reactor Systems
Research Group

## Context

The twenty device-family repositories of the group had, by design, no
numerics beyond closed-form limits. The programme that turns them into
reactor design and simulation tools needs the same published closed forms
and the same numerical substrate in every family: fusion reactivities,
radiation and collision coefficients, confinement criteria, integrators,
filament fields and inductances, tessellation and exports. Three homes were
possible: a copy in every device repository, the tokamak solver repository
`SCPN-FUSION-CORE`, or a new library. The solver repository is mid-work by
its own maintainers, tokamak-centred, and would make eighteen non-tokamak
families depend on a solver they do not consume; twenty copies would be
twenty sources of truth.

## Decision

1. `SCPN-REACTOR-KERNELS` is the group's shared kernel library. It owns
   three domains: `shared_physics_kernels` (published closed forms with
   declared validity ranges), `shared_geometry_kernels` (deterministic
   tessellation, mesh contract, exports) and `shared_numerical_integrators`.
2. It owns no device truth, no solver mathematics or validation evidence
   (`SCPN-FUSION-CORE`), no typed semantics (`SCPN-PHASE-ORCHESTRATOR`),
   no admitted action (`SCPN-CONTROL`), no presentation (`SCPN-STUDIO`)
   and no machine protection (independent, final veto). It reaches no
   actuator and no facility.
3. Every kernel satisfies the kernel contract of `docs/ARCHITECTURE.md`
   (published form, Python floor, bit-exact native kernel, parity by bit
   pattern, complete tests with analytic anchors, benchmark row, manifest
   entry with sources) before it enters `kernels-domain.json`.
4. Consumers pin the distribution version and the inventory SHA-256 in
   their own manifests; the library records its consumers. A kernel whose
   output changes for any input is a breaking change with a major version
   bump and consumer notice.
5. Where a kernel overlaps a private helper of `SCPN-FUSION-CORE`, the
   library cross-checks its values against that helper as evidence and
   leaves the helper in place until a seam migration is ruled by the
   portfolio's review authority.
6. The library is not a device core, is not listed in the configuration
   map (it owns no configuration), carries no SPO registry pin, no CONTROL
   adapter specification and no Studio descriptor; the shared Tier-0
   scaffold profile applies in full.

## Alternatives considered

- **Copies in every device repository**: rejected — twenty sources of
  truth, no single evidence record, drift by construction.
- **Kernels inside `SCPN-FUSION-CORE`**: rejected for now — that tree is
  mid-work by its maintainers, its style (solver modules with plotting) is
  not library-grade, and twenty repositories would depend on an unmerged
  branch; the overlap is handled by cross-checks and a future seam ruling.
- **A NumPy-dependent library**: rejected — the kernels are scalar
  contracts with bit-exact native counterparts; vectorised scans belong to
  the native path and keep the floor dependency-free.

## Consequences

- Device repositories gain one pinned dependency instead of local copies;
  the first consumer is `SCPN-Z-PINCH-CORE` (its geometry copies are
  byte-identical origins of the geometry kernels here).
- Public CI of a consumer can install the library only once it is mirrored
  or published, an owner act; until then the library accumulates its own
  evidence.
- The group's membership record and the portfolio architecture note gain
  a twenty-third child; the configuration map is unchanged.
