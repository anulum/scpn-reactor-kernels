// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// SCPN Reactor Kernels — native placement of tessellated bodies off the axis

//! Native placement kernels, operation-for-operation identical to
//! `scpn_reactor_kernels.geometry.placement`: a translation of a vertex
//! stream and the offsets of `count` identical bodies equally spaced on a
//! circle around the axis. Design record: ADR 0008.

use crate::geometry::trig::{circle_points, CircleCountError};

/// Translates a vertex stream by a fixed offset, one addition per coordinate.
#[must_use]
pub fn translate(vertices: &[[f64; 3]], offset: [f64; 3]) -> Vec<[f64; 3]> {
    vertices
        .iter()
        .map(|&[x, y, z]| [x + offset[0], y + offset[1], z + offset[2]])
        .collect()
}

/// Centres of `count` bodies equally spaced on a circle of `radius_m`.
///
/// # Errors
///
/// Returns [`CircleCountError`] when the count is below three.
pub fn ring_offsets(count: usize, radius_m: f64) -> Result<Vec<[f64; 2]>, CircleCountError> {
    let points = circle_points(count)?;
    Ok(points
        .into_iter()
        .map(|[cosine, sine]| [radius_m * cosine, radius_m * sine])
        .collect())
}

/// Centre-to-centre distance of neighbouring bodies on the ring.
///
/// # Errors
///
/// Returns [`CircleCountError`] when the count is below three.
pub fn ring_separation_m(count: usize, radius_m: f64) -> Result<f64, CircleCountError> {
    let offsets = ring_offsets(count, radius_m)?;
    let delta_x = offsets[1][0] - offsets[0][0];
    let delta_y = offsets[1][1] - offsets[0][1];
    Ok((delta_x * delta_x + delta_y * delta_y).sqrt())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn translation_adds_each_component() {
        let moved = translate(&[[1.0, 2.0, 3.0]], [0.1, 0.2, 0.3]);
        assert_eq!(moved, vec![[1.0 + 0.1, 2.0 + 0.2, 3.0 + 0.3]]);
    }

    #[test]
    fn ring_offsets_start_on_the_x_axis() {
        let offsets = ring_offsets(6, 0.05).expect("six is admissible");
        assert_eq!(offsets.len(), 6);
        assert_eq!(offsets[0], [0.05, 0.0]);
        assert_eq!(offsets[3], [-0.05, 0.0]);
    }

    #[test]
    fn ring_separation_matches_the_chord() {
        let separation = ring_separation_m(6, 0.05).expect("six is admissible");
        assert!((separation - 0.05).abs() <= 1.0e-15);
        assert!(ring_offsets(2, 0.05).is_err());
        assert!(ring_separation_m(2, 0.05).is_err());
    }
}
