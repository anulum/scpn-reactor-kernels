<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — ADR 0005
-->

# ADR 0005 — Bessel kernels: `J0`, `J1` and their first zeros

Status: accepted (2026-09-02). Adds the kernel `numerics_bessel` to the
numerics group at `computational_prototype`.

## Context

The relaxed (force-free) states of two device families are Bessel-function
profiles: the reversed-field pinch's Bessel-function model (`B_phi = B0
J0(mu r)`, `B_theta = B0 J1(mu r)`, reversal at `mu a = j_{0,1}`) and the
spheromak's Taylor eigenvalue of a cylindrical flux conserver
(`lambda = sqrt((j_{1,1}/R)^2 + (pi/L)^2)`). The bit-exact rule forbids
platform special functions; the device repositories must not vendor copies
(the library exists to prevent that drift).

## Decision

1. `bessel_j0(x)` and `bessel_j1(x)` evaluate the ascending series of NIST
   DLMF 10.2.2 in Horner form on `t = x^2/4` with the coefficient ratios
   `-t/k^2` (order 0) and `-t/(k (k + 1))` (order 1) as exact quotients of
   small integers, truncated after `t^30`, with the same operation order
   on both sides.
2. The declared domain is `|x| <= 8`: beyond it the alternating series
   loses digits (its largest term grows like `e^|x|`). An argument outside
   the domain or non-finite is refused, never clamped. The consumers'
   arguments (`2 Theta` of the pinch model with `Theta <= 4`; `j_{1,1}`
   for the spheromak) lie inside the domain.
3. The accuracy evidence is an exact rational evaluation of the same
   series to sixty terms (`fractions.Fraction` on the exact binary
   argument), which isolates the rounding of the float evaluation; the
   measured bound is `2e-14` absolute on the domain. The identities
   `J0' = -J1`, the parity in `x` (exact by construction), the origin
   values and the sign change at the zeros are tested.
4. The first zeros are the correctly rounded doubles of OEIS A115368
   (`j_{0,1}`) and A115369 (`j_{1,1}`), proven from the decimal expansions
   in the tests; DLMF 10.21 lists them.
5. Native kernels (`rust/src/numerics/bessel.rs`) mirror both functions
   with scalar and stream bindings; parity by float64 bytes.
6. A standard-conformant benchmark (`benchmarks/bessel.py`) with a
   committed local artefact.

## Consequences

Maturity stays `computational_prototype`; the claims inventory stays
empty. Higher orders, larger arguments (asymptotic forms), the zeros of
`J1'` (needed for the spheromak magnetic axis; OEIS A259616) and the
Bessel functions of the second kind (needed for the two-region relaxation
model of the filed RFP source) are separate increments with their own
sources. Consumers pin the commit that carries this kernel.
