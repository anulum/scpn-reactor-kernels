// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// SCPN Reactor Kernels — deterministic unit-circle trigonometry kernel

//! Vendored degree-15 sine and degree-16 cosine Taylor polynomials in
//! Horner form on `[0, pi/4]`, with exact octant and quadrant symmetry,
//! mirroring `scpn_reactor_kernels.geometry.trig` operation for operation.

use std::fmt;

/// `pi / 2` (the halving of the correctly rounded `pi` is exact).
pub const HALF_PI: f64 = std::f64::consts::PI / 2.0;
/// Smallest admissible segment count.
pub const MIN_SEGMENTS: usize = 8;
/// Every segment count must be a multiple of this (eight equal arcs).
pub const SEGMENT_MULTIPLE: usize = 8;

/// Smallest number of equally spaced points that encloses the axis.
pub const MIN_CIRCLE_POINTS: usize = 3;

const S3: f64 = 1.0 / 6.0;
const S5: f64 = 1.0 / 120.0;
const S7: f64 = 1.0 / 5040.0;
const S9: f64 = 1.0 / 362_880.0;
const S11: f64 = 1.0 / 39_916_800.0;
const S13: f64 = 1.0 / 6_227_020_800.0;
const S15: f64 = 1.0 / 1_307_674_368_000.0;
const C2: f64 = 1.0 / 2.0;
const C4: f64 = 1.0 / 24.0;
const C6: f64 = 1.0 / 720.0;
const C8: f64 = 1.0 / 40_320.0;
const C10: f64 = 1.0 / 3_628_800.0;
const C12: f64 = 1.0 / 479_001_600.0;
const C14: f64 = 1.0 / 87_178_291_200.0;
const C16: f64 = 1.0 / 20_922_789_888_000.0;

/// Rejection of an inadmissible segment count.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SegmentsError {
    /// The rejected count.
    pub segments: usize,
}

impl fmt::Display for SegmentsError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "segments: must be at least {MIN_SEGMENTS} and a multiple of {SEGMENT_MULTIPLE}, got {}",
            self.segments
        )
    }
}

impl std::error::Error for SegmentsError {}

/// Rejection of an inadmissible circle-point count.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CircleCountError {
    /// The rejected count.
    pub count: usize,
}

impl fmt::Display for CircleCountError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "count: must be at least {MIN_CIRCLE_POINTS}, got {}",
            self.count
        )
    }
}

impl std::error::Error for CircleCountError {}

/// Degree-15 Taylor sine on the reduced interval (Horner form in `x^2`).
#[must_use]
pub fn sine_polynomial(angle_rad: f64) -> f64 {
    let square = angle_rad * angle_rad;
    let mut polynomial = 0.0 - S15;
    polynomial = polynomial * square + S13;
    polynomial = polynomial * square - S11;
    polynomial = polynomial * square + S9;
    polynomial = polynomial * square - S7;
    polynomial = polynomial * square + S5;
    polynomial = polynomial * square - S3;
    polynomial = polynomial * square + 1.0;
    angle_rad * polynomial
}

/// Degree-16 Taylor cosine on the reduced interval (Horner form in `x^2`).
#[must_use]
pub fn cosine_polynomial(angle_rad: f64) -> f64 {
    let square = angle_rad * angle_rad;
    let mut polynomial = C16;
    polynomial = polynomial * square - C14;
    polynomial = polynomial * square + C12;
    polynomial = polynomial * square - C10;
    polynomial = polynomial * square + C8;
    polynomial = polynomial * square - C6;
    polynomial = polynomial * square + C4;
    polynomial = polynomial * square - C2;
    polynomial * square + 1.0
}

/// Validate a segment count.
///
/// # Errors
///
/// Returns [`SegmentsError`] when the count is below [`MIN_SEGMENTS`] or not
/// a multiple of [`SEGMENT_MULTIPLE`].
pub fn require_segments(segments: usize) -> Result<usize, SegmentsError> {
    if segments < MIN_SEGMENTS || segments % SEGMENT_MULTIPLE != 0 {
        return Err(SegmentsError { segments });
    }
    Ok(segments)
}

/// Validates a count of equally spaced circle points.
///
/// # Errors
///
/// Returns [`CircleCountError`] when the count is below
/// [`MIN_CIRCLE_POINTS`].
pub fn require_circle_points(count: usize) -> Result<usize, CircleCountError> {
    if count < MIN_CIRCLE_POINTS {
        return Err(CircleCountError { count });
    }
    Ok(count)
}

/// Equally spaced circle points for any count, bit-exact with the Python floor.
///
/// The quadrant and the residue inside it come from integer arithmetic on
/// `(k, count)`, so a point on an axis is exactly `0` and `±1`; the residual
/// angle is reduced into `[0, pi/4]` before the polynomials run.
///
/// # Errors
///
/// Returns [`CircleCountError`] when the count is below
/// [`MIN_CIRCLE_POINTS`].
pub fn circle_points(count: usize) -> Result<Vec<[f64; 2]>, CircleCountError> {
    require_circle_points(count)?;
    let mut points: Vec<[f64; 2]> = Vec::with_capacity(count);
    for index in 0..count {
        let quadrant = (4 * index) / count;
        let residue = 4 * index - quadrant * count;
        let (cosine, sine) = if 2 * residue <= count {
            let angle = (HALF_PI * residue as f64) / count as f64;
            (cosine_polynomial(angle), sine_polynomial(angle))
        } else {
            let angle = (HALF_PI * (count - residue) as f64) / count as f64;
            (sine_polynomial(angle), cosine_polynomial(angle))
        };
        points.push(match quadrant {
            0 => [cosine, sine],
            1 => [0.0 - sine, cosine],
            2 => [0.0 - cosine, 0.0 - sine],
            _ => [sine, 0.0 - cosine],
        });
    }
    Ok(points)
}

/// Equally spaced unit-circle points for a tessellation segment count.
///
/// # Errors
///
/// Returns [`SegmentsError`] when the count is below [`MIN_SEGMENTS`] or not
/// a multiple of [`SEGMENT_MULTIPLE`].
pub fn unit_circle(segments: usize) -> Result<Vec<[f64; 2]>, SegmentsError> {
    require_segments(segments)?;
    Ok(circle_points(segments).expect("a valid segment count exceeds three"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn quadrant_points_are_exact() {
        let points = unit_circle(8).unwrap();
        assert_eq!(points[0], [1.0, 0.0]);
        assert_eq!(points[2], [0.0, 1.0]);
        assert_eq!(points[4], [-1.0, 0.0]);
        assert_eq!(points[6], [0.0, -1.0]);
        assert_eq!(points.len(), 8);
    }

    #[test]
    fn polynomials_match_libm_closely() {
        for k in 0..=64 {
            let x = std::f64::consts::FRAC_PI_4 * k as f64 / 64.0;
            assert!((sine_polynomial(x) - x.sin()).abs() <= 1.0e-15);
            assert!((cosine_polynomial(x) - x.cos()).abs() <= 1.0e-15);
        }
    }

    #[test]
    fn invalid_counts_are_rejected() {
        assert!(unit_circle(4).is_err());
        assert!(unit_circle(12).is_err());
        assert_eq!(require_segments(16), Ok(16));
        assert_eq!(
            SegmentsError { segments: 12 }.to_string(),
            "segments: must be at least 8 and a multiple of 8, got 12"
        );
    }
}
