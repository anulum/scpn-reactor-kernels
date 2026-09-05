<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — ADR 0019
-->

# ADR 0019 — Own a fresh Gmsh session or refuse

Status: accepted, 2026-09-05.

## Context

Gmsh holds process-global models, options and derived state. The original
kernel finalised caller sessions. A reviewed borrowing candidate preserved
models and many numeric options but changed General.BoundingBoxSize, which
cannot be restored by setNumber. Option snapshotting also mutates Print.Format
and does not establish protection from unrelated concurrent Gmsh users.

## Decision

Under a module lock, check isInitialized before any Gmsh mutation. If true,
raise CadError and leave the caller untouched. If false, initialise with
interruptible=False, create and mesh the owned model, and finalise from finally.
The disabled signal-handler installation allows worker threads to run owned
sessions serially without needing a caller session.

This follows the explicit refusal alternative in the ownership contract.
Snapshot-and-restore is rejected because preservation was incomplete. A separate
worker process remains the route for clients needing simultaneous independent
sessions or backend crash isolation. No worker service is implicitly spawned.

## Consequences and evidence

Existing callers with a session must close it themselves or isolate the call.
No library call closes a caller session on their behalf. Tests use real Gmsh:
valid and invalid STEP requests with an existing session preserve model entities,
options and derived bounding-box state; owned success and failure finalise;
two worker-thread calls produce the same MSH bytes as a main-thread call.
A real higher-order mesh exercises the element-type guard without a fake backend.

The lock coordinates only calls through this module. External Gmsh calls must
not race this library. This does not claim crash isolation or thread safety for
arbitrary concurrent users of the Gmsh global API. Package 2.0.0.dev0 marks the
changed refusal/ownership contract; publication and consumer adoption are separate.
