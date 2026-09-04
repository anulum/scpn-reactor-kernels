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

## Addendum (2026-09-02, same day)

SCPN-MIRROR-CORE is the second consumer: it pins the same commit for the
kernel `numerics_transcendental` and its native crate `scpn-mirror-rs`
declares `scpn-reactor-kernels-rs` as a git dependency at that commit
(default features, no Python binding), the first use of this crate as a
Rust library. The same rule on digests applies; the consumer table
carries both entries. SCPN-DENSE-PLASMA-FOCUS-CORE followed the same day,
retiring the byte-identical copy it had carried since its first level-0
landing; the table carries three entries.
SCPN-RFP-CORE is the fourth consumer and the first of the Bessel kernel
`numerics_bessel` (ADR 0005): it pins the commit that introduced the
kernel and the inventory digest at that commit, with its native crate
`scpn-rfp-rs` depending on this crate at the same commit; the table
carries four entries.
SCPN-SPHEROMAK-CORE is the fifth consumer, pinning the same commit for
`numerics_bessel` and `geometry_unit_circle` (the phases of its axial
stations come from the unit circle, so no platform trigonometric function
enters the device); the table carries five entries.

## Addendum (2026-09-04) — the sixth consumer, and what the digest column is

SCPN-THETA-PINCH-CORE has consumed the geometry kernels since its tier-G1
landing on 2026-09-03 and was never recorded here. It is entered now as
the sixth consumer, with the inventory digest at the commit it first
pinned, which is the same state the first three consumers pinned.

Entering it late made the meaning of the digest column worth stating
outright, because two readings were open and only one matches what the
table has done. No entry has ever been rewritten: every consumer has
re-pinned at least once since it was recorded, and every row still
carries the digest of the inventory at that consumer's **first** pin.
The column is therefore a registration history, not a live statement of
what each consumer pins today; the live pin is read from the consumer's
own manifest, which is the identity item 2 above already names as exact.
A consumer that re-pins does not amend its row here, and a reader must
not treat a row as current.

Recorded on the day the six consuming repositories were consolidated onto
one library commit. That consolidation moved every consumer's own
manifest and touched no row of this table.

## Consequences

The library now has a consumer whose numerics depend on it; a change of
any geometry kernel's output for any input is a breaking change with a
major version bump and a notice to that consumer (ADR 0001 item 4). No
kernel, claim or maturity changes in this record.
