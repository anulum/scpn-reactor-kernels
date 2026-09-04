// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// SCPN Reactor Kernels — spherical body kernel

//! Spherical bodies with the vertex and face order of
//! `scpn_reactor_kernels.geometry.spheres`.
//!
//! The profile is sampled uniformly in polar angle, taken from the first
//! half turn of [`circle_points`] on twice the ring count. That is what puts
//! the poles on exactly `centre ± radius` with a radius of exactly zero and
//! the equator on exactly the centre, and what makes every coordinate here
//! bit-identical to the Python floor: both read the same polynomial
//! trigonometry at the same indices.
//!
//! The caller validates the radii, the centre and the ring count; this
//! kernel assumes a finite centre, strictly positive radii and at least two
//! rings, exactly as the Python floor's guards guarantee before the
//! tessellation is reached.

use crate::geometry::primitives::Tessellation;
use crate::geometry::profiles::closed_profiled_solid;
use crate::geometry::trig::{circle_points, CircleCountError, SegmentsError};

/// Axial profile of a sphere, `rings + 1` samples of increasing height.
///
/// # Errors
///
/// Returns [`CircleCountError`] when twice the ring count is an
/// inadmissible circle-point count, which is the ring count below two.
pub fn sphere_profile(
    radius_m: f64,
    centre_z_m: f64,
    rings: usize,
) -> Result<Vec<[f64; 2]>, CircleCountError> {
    let points = circle_points(2 * rings)?;
    let mut profile: Vec<[f64; 2]> = Vec::with_capacity(rings + 1);
    for &[cosine, sine] in points.iter().take(rings) {
        profile.push([centre_z_m - radius_m * cosine, radius_m * sine]);
    }
    profile.push([centre_z_m + radius_m, 0.0]);
    Ok(profile)
}

/// Closed shell between two concentric spheres: both surfaces, no caps.
///
/// The outer surface as built and the inner surface with every triangle
/// reversed, so that it faces the cavity. The two profiles are taken rather
/// than the radii because a shell is not a tube between aligned profiles and
/// the caller has already built them.
///
/// # Errors
///
/// Returns [`SegmentsError`] when the segment count is inadmissible.
pub fn spherical_shell(
    outer_profile: &[[f64; 2]],
    inner_profile: &[[f64; 2]],
    segments: usize,
) -> Result<Tessellation, SegmentsError> {
    let outer = closed_profiled_solid(outer_profile, segments)?;
    let inner = closed_profiled_solid(inner_profile, segments)?;
    let offset = u32::try_from(outer.vertices.len()).expect("vertex count fits in u32");
    let mut vertices = outer.vertices;
    vertices.extend(inner.vertices);
    let mut faces = outer.faces;
    faces.reserve(inner.faces.len());
    for [first, second, third] in inner.faces {
        faces.push([first + offset, third + offset, second + offset]);
    }
    Ok(Tessellation { vertices, faces })
}
