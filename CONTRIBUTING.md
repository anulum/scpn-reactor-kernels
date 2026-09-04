<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — CONTRIBUTING
-->

# Contributing

The repository is public and its gates run in CI on every push.
Contributions are coordinated directly with the owner
(protoscience@anulum.li).

## Ground rules

1. **Truthful maturity.** Every kernel enters the manifest at
   `computational_prototype` and advances only with documented accepted
   cases and thresholds. No placeholder API, toy solver, fabricated data,
   empty test, readiness language, or claim entry without evidence.
2. **Boundary discipline.** Work stays inside the shared-kernel boundary:
   published closed forms, standard numerical methods, geometry substrate.
   Device truth belongs to the device repositories; solver mathematics to
   `SCPN-FUSION-CORE`; typed semantics to `SCPN-PHASE-ORCHESTRATOR`;
   control admission to `SCPN-CONTROL`; presentation to `SCPN-STUDIO`.
   Nothing here actuates hardware.
3. **Complete units.** A kernel ships with its Python floor, its native
   kernel, parity tests by bit pattern, statement- and branch-complete
   tests with analytic anchors, a benchmark row, its sources, its manifest
   entry and its documentation in the same commit.
4. **Model fidelity.** Each kernel matches its cited publication exactly
   within a declared applicability domain; a form that cannot be traced to
   a published source is not implemented.
5. **Licensing and provenance.** Every file carries the seven-line
   provenance header in its native comment syntax (HTML comment in rendered
   Markdown; `REUSE.toml` annotations where a format has no comments).
   `reuse lint` must pass.
6. **Language and tone.** British English; descriptive names; no
   self-applied quality labels; no internal planning codes in any tracked
   file.

## Workflow

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
make lint typecheck test validate rust   # or: make preflight
```

All gates in `VALIDATION.md` must pass before a commit is proposed. Commits
are atomic, descriptive, and staged by explicit pathspec. History is never
rewritten.

## Numerically sensitive changes

Any change that alters a kernel's output for any input is a breaking change
of that kernel: it requires a new major version, an updated evidence record,
regenerated parity fixtures and notice to every consumer listed in the
manifest.
