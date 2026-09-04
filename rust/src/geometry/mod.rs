// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// SCPN Reactor Kernels — native geometry kernels

//! Native tessellation and mesh-measure kernels of the tier-G1 device 3D
//! model, operation-for-operation identical to
//! `scpn_reactor_kernels.geometry` so that every vertex coordinate, every
//! face index and every measure agrees bit for bit with the Python floor.
//! The unit circle comes from the vendored polynomial trigonometry in
//! [`trig`]; no `libm` call appears anywhere. Design record: ADR 0002.

pub mod mesh;
pub mod placement;
pub mod primitives;
pub mod profiles;
pub mod spheres;
pub mod trig;
