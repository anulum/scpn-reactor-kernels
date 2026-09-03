<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — ADR 0009
-->

# ADR 0009 — The fail-closed body evidence belongs to the library

Status: accepted (2026-09-03). Adds the kernel `cad_evidence` to the CAD
group of ADR 0006.

## Context

The first tier-G2 device model was written in a device repository, and with
it the machinery that checks each body: the B-rep measures against the
analytic closed forms within the group's tolerance, the faceted volume
against the chord-deficit bound of the mesher's linear deflection, and the
faceted volume against the tier-G1 mesh of the same body within the exact
inscribed-polygon deficit bound. That was the right place to discover the
checks. It is the wrong place to keep them.

None of those checks is device knowledge. Every one of them is a statement
about a solid, a mesh and a bound this library already owns. Left where they
were, the same two hundred lines would be copied into every family that gains
a CAD model — and then a change to a bound, a new field in the record, or a
correction to a deficit formula would be a change in every one of those
repositories at once, with nothing forcing them to stay equal.

## Decision

1. A new kernel `cad_evidence` (`src/scpn_reactor_kernels/cad/evidence.py`)
   owns the checked record of one body: `BodyEvidence` (frozen, refusing at
   construction), `body_evidence(...)` computing it from a body, its smallest
   circular radius, its faceting and its tier-G1 reference mesh, and
   `assembly_evidence(...)` doing the same for an assembly in its fixed order.
2. The evidence refuses rather than reports. A violated bound raises
   `CadError` naming the body and the bound, so a model cannot be assembled
   around a body that failed a check and a caller cannot forget to look.
   `assembly_evidence` also refuses a ragged input rather than zipping four
   sequences of different lengths into a short answer.
3. What stays in a device repository is exactly what is device knowledge: the
   schema identity of the family's record, the composition of its bodies with
   their names, roles, material tokens and extents, the family's build
   invariants, and its non-claims. The device re-raises the library's
   `CadError` under its own error type, as it already does for every other
   library refusal.
4. `native_parity` is `false`: the evidence is a composition of measures taken
   by the pinned third-party kernel, and it inherits that evidence class.

## Consequences

A family gains a tier-G2 model by writing its composition and its record, not
by copying a checking apparatus. A change to a bound is one change.

The pilot family (SCPN-Z-PINCH-CORE) carries its own copy of this machinery,
landed before this record. It is not wrong and it is not urgent, but it is now
a second implementation of a library capability, and it is scheduled to move
onto this kernel in the pin-consolidation wave; the seat that owns that
repository has been notified. Until then, the library is the reference and the
copy is the exception, recorded here so no reader mistakes the duplication for
a design.

Nothing here describes a device: the kernel knows a solid, a mesh and a bound.
