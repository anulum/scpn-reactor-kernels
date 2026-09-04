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

use crate::geometry::trig::{
    circle_points, opposite_point, require_circle_point, supplementary_point, CircleCountError,
    CirclePointError,
};
use std::fmt;

/// Rejection of an inadmissible ring on a sphere.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum PlacementError {
    /// The member count was below three.
    Count(CircleCountError),
    /// A supplied pair was not a point of the unit circle.
    Point(CirclePointError),
}

impl fmt::Display for PlacementError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Count(error) => write!(f, "{error}"),
            Self::Point(error) => write!(f, "{error}"),
        }
    }
}

impl std::error::Error for PlacementError {}

impl From<CircleCountError> for PlacementError {
    fn from(error: CircleCountError) -> Self {
        Self::Count(error)
    }
}

impl From<CirclePointError> for PlacementError {
    fn from(error: CirclePointError) -> Self {
        Self::Point(error)
    }
}

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

/// A rotation as its three rows.
pub type Rotation = [[f64; 3]; 3];

/// The unit direction of a polar and an azimuthal circle point.
///
/// # Errors
///
/// Returns [`CirclePointError`] when either pair is not on the unit circle.
pub fn axis_direction(polar: [f64; 2], azimuth: [f64; 2]) -> Result<[f64; 3], CirclePointError> {
    let [polar_cosine, polar_sine] = require_circle_point(polar)?;
    let [azimuth_cosine, azimuth_sine] = require_circle_point(azimuth)?;
    Ok([
        polar_sine * azimuth_cosine,
        polar_sine * azimuth_sine,
        polar_cosine,
    ])
}

/// The rotation taking the positive `z` axis onto [`axis_direction`].
///
/// Built from the two angles rather than from a direction vector, which is
/// what keeps it well conditioned at the negative `z` axis.
///
/// # Errors
///
/// Returns [`CirclePointError`] when either pair is not on the unit circle.
pub fn aim_rotation(polar: [f64; 2], azimuth: [f64; 2]) -> Result<Rotation, CirclePointError> {
    let [polar_cosine, polar_sine] = require_circle_point(polar)?;
    let [azimuth_cosine, azimuth_sine] = require_circle_point(azimuth)?;
    Ok([
        [
            azimuth_cosine * polar_cosine,
            0.0 - azimuth_sine,
            azimuth_cosine * polar_sine,
        ],
        [
            azimuth_sine * polar_cosine,
            azimuth_cosine,
            azimuth_sine * polar_sine,
        ],
        [0.0 - polar_sine, 0.0, polar_cosine],
    ])
}

/// The rotation aiming `z` from a point of a sphere at the sphere's centre.
///
/// # Errors
///
/// Returns [`CirclePointError`] when either pair is not on the unit circle.
pub fn inward_aim(polar: [f64; 2], azimuth: [f64; 2]) -> Result<Rotation, CirclePointError> {
    aim_rotation(supplementary_point(polar)?, opposite_point(azimuth)?)
}

/// Rotates a vertex stream about the origin.
#[must_use]
pub fn rotate(vertices: &[[f64; 3]], rotation: Rotation) -> Vec<[f64; 3]> {
    let [first, second, third] = rotation;
    vertices
        .iter()
        .map(|&[x, y, z]| {
            [
                first[0] * x + first[1] * y + first[2] * z,
                second[0] * x + second[1] * y + second[2] * z,
                third[0] * x + third[1] * y + third[2] * z,
            ]
        })
        .collect()
}

/// Azimuths of `count` members of a ring, twisted by an offset.
///
/// # Errors
///
/// Returns [`PlacementError`] when the count is below three or the offset is
/// not a point of the unit circle.
pub fn ring_azimuths(count: usize, offset: [f64; 2]) -> Result<Vec<[f64; 2]>, PlacementError> {
    let points = circle_points(count)?;
    let [offset_cosine, offset_sine] = require_circle_point(offset)?;
    Ok(points
        .into_iter()
        .map(|[cosine, sine]| {
            [
                cosine * offset_cosine - sine * offset_sine,
                sine * offset_cosine + cosine * offset_sine,
            ]
        })
        .collect())
}

/// Centres of `count` bodies on one latitude of a sphere.
///
/// # Errors
///
/// Returns [`PlacementError`] when the count is below three or either pair is
/// not a point of the unit circle.
pub fn sphere_ring_offsets(
    count: usize,
    radius_m: f64,
    polar: [f64; 2],
    offset: [f64; 2],
) -> Result<Vec<[f64; 3]>, PlacementError> {
    let [polar_cosine, polar_sine] = require_circle_point(polar)?;
    let height = radius_m * polar_cosine;
    let plane_radius = radius_m * polar_sine;
    Ok(ring_azimuths(count, offset)?
        .into_iter()
        .map(|[cosine, sine]| [plane_radius * cosine, plane_radius * sine, height])
        .collect())
}

/// Distance between two body centres.
#[must_use]
pub fn centre_separation_m(first: [f64; 3], second: [f64; 3]) -> f64 {
    let delta_x = second[0] - first[0];
    let delta_y = second[1] - first[1];
    let delta_z = second[2] - first[2];
    (delta_x * delta_x + delta_y * delta_y + delta_z * delta_z).sqrt()
}

#[cfg(test)]
mod aiming_tests {
    use super::*;

    #[test]
    fn aiming_along_z_is_the_identity() {
        let rotation = aim_rotation([1.0, 0.0], [1.0, 0.0]).unwrap();
        assert_eq!(
            rotation,
            [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        );
    }

    #[test]
    fn the_third_column_is_the_axis() {
        let polar = [0.6, 0.8];
        let azimuth = [0.28, 0.96];
        let rotation = aim_rotation(polar, azimuth).unwrap();
        let axis = axis_direction(polar, azimuth).unwrap();
        assert_eq!([rotation[0][2], rotation[1][2], rotation[2][2]], axis);
    }

    #[test]
    fn a_zero_twist_leaves_the_ring_alone() {
        let plain = crate::geometry::trig::circle_points(10).unwrap();
        let twisted = ring_azimuths(10, [1.0, 0.0]).unwrap();
        assert_eq!(plain, twisted);
    }

    #[test]
    fn a_pair_off_the_circle_is_refused() {
        assert!(aim_rotation([1.0, 1.0], [1.0, 0.0]).is_err());
        assert!(axis_direction([1.0, 0.0], [f64::NAN, 0.0]).is_err());
        assert!(inward_aim([2.0, 0.0], [1.0, 0.0]).is_err());
        assert!(ring_azimuths(10, [1.0, 1.0]).is_err());
        assert!(ring_azimuths(2, [1.0, 0.0]).is_err());
        assert!(sphere_ring_offsets(5, 1.5, [2.0, 0.0], [1.0, 0.0]).is_err());
        assert!(
            !PlacementError::from(CirclePointError { point: [2.0, 0.0] })
                .to_string()
                .is_empty()
        );
        assert!(!PlacementError::from(CircleCountError { count: 2 })
            .to_string()
            .is_empty());
    }

    #[test]
    fn separation_is_the_euclidean_distance() {
        assert_eq!(centre_separation_m([0.0, 0.0, 0.0], [3.0, 4.0, 0.0]), 5.0);
    }
}
