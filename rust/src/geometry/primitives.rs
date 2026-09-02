// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// SCPN Reactor Kernels — analytic surface tessellation kernel

//! Solid cylinder and annular tube tessellation on the device axis with the
//! vertex and face order of `scpn_reactor_kernels.geometry.primitives`.

use crate::geometry::trig::{unit_circle, SegmentsError};

/// Vertex and face streams of one closed body.
#[derive(Debug, Clone, PartialEq)]
pub struct Tessellation {
    /// Vertex coordinates in metres.
    pub vertices: Vec<[f64; 3]>,
    /// Outward-oriented triangles as vertex indices.
    pub faces: Vec<[u32; 3]>,
}

fn ring(radius: f64, z: f64, circle: &[[f64; 2]], out: &mut Vec<[f64; 3]>) {
    for &[cosine, sine] in circle {
        out.push([radius * cosine, radius * sine, z]);
    }
}

fn index(value: usize) -> u32 {
    u32::try_from(value).expect("vertex count fits in u32")
}

/// Closed solid cylinder: `2 n + 2` vertices, `4 n` faces.
///
/// The caller validates the radius and the axial extent; the kernel assumes
/// finite, strictly positive inputs with `z_high > z_low`.
///
/// # Errors
///
/// Returns [`SegmentsError`] when the segment count is inadmissible.
pub fn cylinder_solid(
    radius_m: f64,
    z_low_m: f64,
    z_high_m: f64,
    segments: usize,
) -> Result<Tessellation, SegmentsError> {
    let circle = unit_circle(segments)?;
    let count = circle.len();
    let mut vertices = Vec::with_capacity(2 * count + 2);
    ring(radius_m, z_low_m, &circle, &mut vertices);
    ring(radius_m, z_high_m, &circle, &mut vertices);
    vertices.push([0.0, 0.0, z_low_m]);
    vertices.push([0.0, 0.0, z_high_m]);
    let bottom_centre = index(2 * count);
    let top_centre = index(2 * count + 1);
    let mut faces = Vec::with_capacity(4 * count);
    for i in 0..count {
        let j = (i + 1) % count;
        faces.push([index(i), index(j), index(count + j)]);
        faces.push([index(i), index(count + j), index(count + i)]);
    }
    for i in 0..count {
        let j = (i + 1) % count;
        faces.push([bottom_centre, index(j), index(i)]);
    }
    for i in 0..count {
        let j = (i + 1) % count;
        faces.push([top_centre, index(count + i), index(count + j)]);
    }
    Ok(Tessellation { vertices, faces })
}

/// Closed annular tube: `4 n` vertices, `8 n` faces.
///
/// The caller validates the radii and the axial extent; the kernel assumes
/// finite, strictly positive inputs with `outer > inner` and
/// `z_high > z_low`.
///
/// # Errors
///
/// Returns [`SegmentsError`] when the segment count is inadmissible.
pub fn annular_tube(
    inner_radius_m: f64,
    outer_radius_m: f64,
    z_low_m: f64,
    z_high_m: f64,
    segments: usize,
) -> Result<Tessellation, SegmentsError> {
    let circle = unit_circle(segments)?;
    let count = circle.len();
    let mut vertices = Vec::with_capacity(4 * count);
    ring(outer_radius_m, z_low_m, &circle, &mut vertices);
    ring(outer_radius_m, z_high_m, &circle, &mut vertices);
    ring(inner_radius_m, z_low_m, &circle, &mut vertices);
    ring(inner_radius_m, z_high_m, &circle, &mut vertices);
    let outer_top = count;
    let inner_bottom = 2 * count;
    let inner_top = 3 * count;
    let mut faces = Vec::with_capacity(8 * count);
    for i in 0..count {
        let j = (i + 1) % count;
        faces.push([index(i), index(j), index(outer_top + j)]);
        faces.push([index(i), index(outer_top + j), index(outer_top + i)]);
    }
    for i in 0..count {
        let j = (i + 1) % count;
        faces.push([
            index(inner_bottom + i),
            index(inner_top + j),
            index(inner_bottom + j),
        ]);
        faces.push([
            index(inner_bottom + i),
            index(inner_top + i),
            index(inner_top + j),
        ]);
    }
    for i in 0..count {
        let j = (i + 1) % count;
        faces.push([index(i), index(inner_bottom + i), index(inner_bottom + j)]);
        faces.push([index(i), index(inner_bottom + j), index(j)]);
    }
    for i in 0..count {
        let j = (i + 1) % count;
        faces.push([
            index(outer_top + i),
            index(outer_top + j),
            index(inner_top + j),
        ]);
        faces.push([
            index(outer_top + i),
            index(inner_top + j),
            index(inner_top + i),
        ]);
    }
    Ok(Tessellation { vertices, faces })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::geometry::mesh::{signed_volume, surface_area};

    #[test]
    fn cylinder_counts_and_volume_converge() {
        let coarse = cylinder_solid(0.5, 0.0, 2.0, 8).unwrap();
        assert_eq!(coarse.vertices.len(), 18);
        assert_eq!(coarse.faces.len(), 32);
        let exact = std::f64::consts::PI * 0.25 * 2.0;
        let error = |n: usize| {
            let t = cylinder_solid(0.5, 0.0, 2.0, n).unwrap();
            (exact - signed_volume(&t.vertices, &t.faces)) / exact
        };
        let ratio = error(64) / error(128);
        assert!((ratio - 4.0).abs() < 0.05, "ratio {ratio}");
        assert!(surface_area(&coarse.vertices, &coarse.faces) > 0.0);
    }

    #[test]
    fn tube_volume_is_outer_minus_inner() {
        let tube = annular_tube(0.3, 0.5, 0.0, 1.0, 32).unwrap();
        assert_eq!(tube.vertices.len(), 128);
        assert_eq!(tube.faces.len(), 256);
        let outer = cylinder_solid(0.5, 0.0, 1.0, 32).unwrap();
        let inner = cylinder_solid(0.3, 0.0, 1.0, 32).unwrap();
        let expected = signed_volume(&outer.vertices, &outer.faces)
            - signed_volume(&inner.vertices, &inner.faces);
        let got = signed_volume(&tube.vertices, &tube.faces);
        assert!((got - expected).abs() <= 1.0e-14 * expected);
    }
}
