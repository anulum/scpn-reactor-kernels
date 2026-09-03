// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// SCPN Reactor Kernels — axial profile tessellation kernel

//! Surfaces of revolution through a sampled axial radius profile, with the
//! vertex and face order of `scpn_reactor_kernels.geometry.profiles`.
//!
//! A profile is a slice of `(z, radius)` samples. The caller validates it;
//! this kernel assumes at least two finite samples, strictly increasing in
//! `z`, with strictly positive radii, exactly as the Python floor's
//! `require_profile` guarantees before it reaches the tessellation. The
//! arithmetic is the same multiplication per coordinate in the same order,
//! so every coordinate agrees bit for bit with the floor.

use crate::geometry::primitives::Tessellation;
use crate::geometry::trig::{unit_circle, SegmentsError};

fn ring(radius: f64, z: f64, circle: &[[f64; 2]], out: &mut Vec<[f64; 3]>) {
    for &[cosine, sine] in circle {
        out.push([radius * cosine, radius * sine, z]);
    }
}

fn index(value: usize) -> u32 {
    u32::try_from(value).expect("vertex count fits in u32")
}

fn side_faces(lower: usize, upper: usize, count: usize, faces: &mut Vec<[u32; 3]>) {
    for i in 0..count {
        let j = (i + 1) % count;
        faces.push([index(lower + i), index(lower + j), index(upper + j)]);
        faces.push([index(lower + i), index(upper + j), index(upper + i)]);
    }
}

/// Closed solid of revolution through an axial profile.
///
/// Produces `samples * n + 2` vertices (one ring per sample in profile
/// order, then the bottom and top disc centres) and
/// `(2 (samples - 1) + 2) n` outward-oriented faces.
///
/// # Errors
///
/// Returns [`SegmentsError`] when the segment count is inadmissible.
pub fn profiled_solid(
    profile: &[[f64; 2]],
    segments: usize,
) -> Result<Tessellation, SegmentsError> {
    let circle = unit_circle(segments)?;
    let count = circle.len();
    let samples = profile.len();
    let mut vertices = Vec::with_capacity(samples * count + 2);
    for &[z, radius] in profile {
        ring(radius, z, &circle, &mut vertices);
    }
    vertices.push([0.0, 0.0, profile[0][0]]);
    vertices.push([0.0, 0.0, profile[samples - 1][0]]);
    let bottom_centre = index(samples * count);
    let top_centre = index(samples * count + 1);
    let last_ring = (samples - 1) * count;
    let mut faces = Vec::with_capacity((2 * (samples - 1) + 2) * count);
    for band in 0..samples - 1 {
        side_faces(band * count, (band + 1) * count, count, &mut faces);
    }
    for i in 0..count {
        let j = (i + 1) % count;
        faces.push([bottom_centre, index(j), index(i)]);
    }
    for i in 0..count {
        let j = (i + 1) % count;
        faces.push([top_centre, index(last_ring + i), index(last_ring + j)]);
    }
    Ok(Tessellation { vertices, faces })
}

/// Closed tube of revolution between two aligned axial profiles.
///
/// Produces `2 samples n` vertices (the outer rings in profile order, then
/// the inner rings) and `(4 (samples - 1) + 4) n` outward-oriented faces.
/// The caller guarantees that the two profiles carry the same number of
/// samples at the same heights with every outer radius above its inner one.
///
/// # Errors
///
/// Returns [`SegmentsError`] when the segment count is inadmissible.
pub fn profiled_tube(
    inner_profile: &[[f64; 2]],
    outer_profile: &[[f64; 2]],
    segments: usize,
) -> Result<Tessellation, SegmentsError> {
    let circle = unit_circle(segments)?;
    let count = circle.len();
    let samples = inner_profile.len();
    let mut vertices = Vec::with_capacity(2 * samples * count);
    for &[z, radius] in outer_profile {
        ring(radius, z, &circle, &mut vertices);
    }
    for &[z, radius] in inner_profile {
        ring(radius, z, &circle, &mut vertices);
    }
    let inner_base = samples * count;
    let outer_last = (samples - 1) * count;
    let inner_last = inner_base + outer_last;
    let mut faces = Vec::with_capacity((4 * (samples - 1) + 4) * count);
    for band in 0..samples - 1 {
        side_faces(band * count, (band + 1) * count, count, &mut faces);
    }
    for band in 0..samples - 1 {
        let lower = inner_base + band * count;
        let upper = inner_base + (band + 1) * count;
        for i in 0..count {
            let j = (i + 1) % count;
            faces.push([index(lower + i), index(upper + j), index(lower + j)]);
            faces.push([index(lower + i), index(upper + i), index(upper + j)]);
        }
    }
    for i in 0..count {
        let j = (i + 1) % count;
        faces.push([index(i), index(inner_base + i), index(inner_base + j)]);
        faces.push([index(i), index(inner_base + j), index(j)]);
    }
    for i in 0..count {
        let j = (i + 1) % count;
        faces.push([
            index(outer_last + i),
            index(outer_last + j),
            index(inner_last + j),
        ]);
        faces.push([
            index(outer_last + i),
            index(inner_last + j),
            index(inner_last + i),
        ]);
    }
    Ok(Tessellation { vertices, faces })
}

/// Exact volume of the solid of revolution of a linear profile.
///
/// The frustum-stack closed form
/// `sum (pi / 3) (r_i^2 + r_i r_{i+1} + r_{i+1}^2) (z_{i+1} - z_i)`, summed
/// in profile order so the accumulation matches the Python floor bit for
/// bit.
#[must_use]
pub fn profile_volume_m3(profile: &[[f64; 2]]) -> f64 {
    let mut total = 0.0;
    for window in profile.windows(2) {
        let [low_z, low_radius] = window[0];
        let [high_z, high_radius] = window[1];
        total += (core::f64::consts::PI / 3.0)
            * (low_radius * low_radius + low_radius * high_radius + high_radius * high_radius)
            * (high_z - low_z);
    }
    total
}

/// Exact lateral area of the surface of revolution of a linear profile.
///
/// The frustum-stack closed form `sum pi (r_i + r_{i+1}) l_i` with the slant
/// `l_i = sqrt((r_{i+1} - r_i)^2 + (z_{i+1} - z_i)^2)`, summed in profile
/// order. The end discs are not included.
#[must_use]
pub fn profile_lateral_area_m2(profile: &[[f64; 2]]) -> f64 {
    let mut total = 0.0;
    for window in profile.windows(2) {
        let [low_z, low_radius] = window[0];
        let [high_z, high_radius] = window[1];
        let delta_radius = high_radius - low_radius;
        let delta_z = high_z - low_z;
        let slant = (delta_radius * delta_radius + delta_z * delta_z).sqrt();
        total += core::f64::consts::PI * (low_radius + high_radius) * slant;
    }
    total
}
