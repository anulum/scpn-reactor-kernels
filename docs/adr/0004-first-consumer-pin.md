<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — ADR 0004
-->

# ADR 0004 — First consumer pin and what a pinned digest names

Status: accepted (2026-09-02). Records the event ADR 0001 reserved for a
new decision record: a consumer's first pin.

## Context

SCPN-Z-PINCH-CORE, whose geometry substrate was the origin of the
geometry kernels (ADR 0002), has retired its copies and consumes the
library: it declares the distribution as its one runtime dependency,
pinned to a commit object of this repository (no release exists yet), and
records in its manifest the distribution, the version, the source commit,
the SHA-256 of the generated `kernel-inventory.json` at that commit and
the identifiers of the four geometry kernels it consumes. Its device model
is proven bit-exact body by body against this library's native module.

## Decision

1. The `consumers` table of `kernels-domain.json` carries the entry
   `{project: SCPN-Z-PINCH-CORE, version: 0.1.0.dev0, inventory_sha256}`
   with the digest the consumer pinned; the generated inventory carries it
   too.
2. A consumer's `inventory_sha256` names the inventory at the commit the
   consumer pins. Recording the consumer changes the inventory, so the
   inventory that lists a consumer can never be the one that consumer
   pinned; the commit object in the consumer's manifest is the exact
   identity until a release exists. This is stated in the README so that
   no reader takes the two digests for a mismatch.
3. Until the distribution is published, consumers install from the
   repository at the pinned commit (their CI does the same); the first
   published release will let consumers replace the commit pin by a
   version pin, recorded then as a new decision.

## Consequences

The library now has a consumer whose numerics depend on it; a change of
any geometry kernel's output for any input is a breaking change with a
major version bump and a notice to that consumer (ADR 0001 item 4). No
kernel, claim or maturity changes in this record.
