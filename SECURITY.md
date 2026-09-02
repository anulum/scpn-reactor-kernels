<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — SECURITY
-->

# Security policy

## Supported states

| State | Supported |
|---|---|
| Local `main` at current tip | yes — the only supported state |
| Any released version | none exists |

The executable surface is the pure-Python kernel library under `src/`, the
optional native extension built from `rust/`, the benchmarks, and the
validation tooling under `tools/`. There is no network service, no daemon,
no solver, no controller, and no hardware path.

## Reporting a vulnerability

Report privately to **protoscience@anulum.li**. Do not open public reports.
Include the affected file, a reproduction, and the impact you see. You will
receive an acknowledgement, and coordinated disclosure will be agreed before
any public statement. Good-faith research within this scope is welcome.

## Response scope

In scope: the kernel library and its native extension (including any input
that produces a silently wrong or non-finite result instead of a refusal),
the validation tooling, workflow definitions, licensing and provenance
metadata, and any way the repository could misrepresent a kernel's
evidence maturity or sources.

Out of scope: reactor physics claims (none exist), hardware and actuation
paths (none exist and none are permitted here), the machine-protection
domain (independent by design), and third-party infrastructure.

## Non-claims

This policy is not a safety certification and does not make any consumer
machine-ready. Fail-closed behaviour of the kernels and validators is
described in [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md).
