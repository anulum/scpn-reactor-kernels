<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — GOVERNANCE
-->

# Governance

## Ownership and decision authority

The project is owned by Miroslav Šotek (ANULUM, Marbach SG, Switzerland;
ORCID 0009-0009-3560-0851). Final authority over scope, releases, licensing,
publication, and every outward action rests with the owner.

The repository is stewarded by the SCPN Reactor Systems Research Group, which
coordinates the reactor-family portfolio and its cross-project boundaries.

## Boundary control

The project boundary — shared physics kernels, shared geometry kernels and
shared numerical integrators that more than one device family needs, and
the exclusions listed in the README — derives from the SCPN reactor family
repository standard and the group's programme decisions. A kernel moves
here from a device repository only as a byte-identical origin followed by
the device's pin; a kernel that overlaps a solver helper of
`SCPN-FUSION-CORE` is cross-checked as evidence and never replaces that
helper without a seam migration ruled by the portfolio's review authority.
This repository never redefines its own boundary unilaterally.

## Change process

1. Changes land locally on `main` after the full gate sequence in
   `VALIDATION.md` passes.
2. Evidence maturity advances only per the reactor family standard: each
   kernel declares exactly one state, and no state is advanced by
   repository age, code volume, or simulation output alone.
3. Contract surfaces (kernel manifest schema, distribution version,
   inventory digest) change only through versioned revisions that preserve
   or explicitly break compatibility, never silently; consumers are
   notified of every breaking kernel change.
4. Remote creation, push, package publication, release, deployment, and
   external registrations each require separate owner authority.

## Roles

| Role | Holder | Authority |
|---|---|---|
| Owner | Miroslav Šotek | all final decisions, all outward actions |
| Steward | SCPN Reactor Systems Research Group | portfolio boundaries, cross-project contracts |
| Maintainers | per `.github/CODEOWNERS` | review of changes within the boundary |
