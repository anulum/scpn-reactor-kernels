<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — ADR 0003
-->

# ADR 0003 — Numerics kernels: deterministic logarithm, exponential and power

Status: accepted (2026-09-02). Adds the second implemented kernel group,
`numerics`, at `computational_prototype`.

## Context

The physics closed forms the device families evaluate carry natural
logarithms (coaxial inductances `ln(b/a)`, Coulomb logarithms),
exponentials (reactivity parametrisations, self-absorption factors) and
real powers (empirical scaling laws, non-integer temperature exponents).
The library's contract is that every kernel's native counterpart
reproduces the Python floor bit for bit. Platform `libm` implementations
of `log`, `exp` and `pow` are not guaranteed to be correctly rounded and
differ between languages and libraries, so a kernel that called them on
either side could not meet that contract. The geometry group already
vendors its trigonometry for the same reason (ADR 0002); the physics
kernels need the same treatment for the three remaining transcendental
operations before any of them can land.

## Decision

1. `numerics/transcendental.py` implements, with only `+ - * /`, exact
   binary decomposition and exact power-of-two scaling:
   `ln(x) = k ln 2 + 2 atanh((m - 1)/(m + 1))` for `x = m 2^k` with `m`
   in `[sqrt(1/2), sqrt(2))` (odd series truncated after `s^25`, Horner
   form in `s^2`, reciprocal odd integers as exact quotients);
   `exp(y) = 2^k exp(r)` with `k = floor(y / ln 2 + 1/2)` and the
   Cody–Waite reduction `r = (y - k ln2_hi) - k ln2_lo` (Taylor series
   truncated after `r^17`, reciprocal factorials as exact quotients);
   `pow(x, y) = exp(y ln x)`.
2. Domains are refused, never clamped: the logarithm needs a positive
   normal double; the exponential an argument in `[-708, 709]` so that the
   result is a normal double; the power a positive normal base, a finite
   exponent and a product `y ln x` inside the exponential's domain.
3. `rust/src/numerics/transcendental.rs` mirrors every operation in the
   same order; the constants are the standard-library doubles (proven to
   carry the same bits as the Python literals) and the Cody–Waite parts
   are given by their bit patterns. Bindings expose the three scalar
   kernels and three stream forms (one call per array).
4. Accuracy is an evidence record, not a claim of correct rounding: the
   tests bound the logarithm and the exponential to `1e-15` relative
   against the platform `math` module over their whole domains, and the
   power to `1e-13` relative for `|y ln x| <= 100` (its error grows with
   the magnitude of `y ln x`, which the docstring states).
5. Consumers that need these operations before the library is pinned
   (D7, owner mirror) vendor an identical copy with the migration note of
   the geometry precedent; the library copy is canonical.

## Consequences

One kernel enters the manifest (`numerics_transcendental`) at
`computational_prototype` with `VALIDATION.md#numerics-kernels` as its
evidence record; the claims inventory stays empty. The physics kernel
groups planned in the roadmap (collisions, reactivities, radiation,
confinement) consume this group instead of `libm`.
