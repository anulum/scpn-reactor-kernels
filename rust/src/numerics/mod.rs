// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// SCPN Reactor Kernels — native numerics kernels

//! Numerical substrate kernels mirrored operation for operation from
//! `scpn_reactor_kernels.numerics`: the vendored deterministic natural
//! logarithm, exponential and real power in [`transcendental`]. No `libm`
//! call appears anywhere. Design record: ADR 0003.

pub mod bessel;
pub mod transcendental;
