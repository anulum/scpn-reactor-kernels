<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — pull request template
-->

## What and why

<!-- One paragraph: what changes and the reason. -->

## Boundary check

- [ ] The change stays inside the shared-kernel boundary (no device truth,
      no solver mathematics, no control admission, no actuation, no
      presentation-layer work).
- [ ] Every new or changed kernel cites its published form and validity
      range, ships its native counterpart with bit-exact parity tests, its
      analytic anchors, its benchmark row and its manifest entry.
- [ ] Evidence maturity stays truthful: no kernel or claim is added without
      the evidence its target state requires.

## Gates

- [ ] `make lint` passes
- [ ] `make typecheck` passes
- [ ] `make test` passes (100 % statement and branch coverage on `src/` and `tools/`)
- [ ] `make validate` passes (manifest, inventory)
- [ ] `make rust` passes and the parity tests run against the rebuilt native module
- [ ] `reuse lint` and `actionlint` pass
- [ ] Documentation updated in the same change where behaviour changed

## Notes for the reviewer

<!-- Anything non-obvious: decisions, alternatives rejected, follow-ups. -->
