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

// The three words below are the shortest literals that round-trip to the
// doubles the Python floor writes as 1.57079632673412561417e00,
// 6.07710050630396597660e-11 and 2.02226624879595063154e-21; the parity
// test compares the bit patterns rather than trusting the spelling.
/// First word of the three-word split of `pi / 2` (22 trailing zero bits).
pub const PIO2_A: f64 = 1.570_796_326_734_125_6_f64;
/// Second word of the split (21 trailing zero bits).
pub const PIO2_B: f64 = 6.077_100_506_303_966e-11;
/// Third word of the split; what remains of `pi / 2` is below `1.1e-37`.
pub const PIO2_C: f64 = 2.022_266_248_795_950_6e-21;
/// `2 / pi`, the reciprocal used to find the quadrant index.
pub const TWO_OVER_PI: f64 = 2.0 / std::f64::consts::PI;
/// Degrees in half a turn.
pub const DEGREES_PER_HALF_TURN: f64 = 180.0;
/// Largest quadrant index whose products with the split stay exact.
pub const MAX_QUADRANT_INDEX: i64 = 2_097_152;
/// Largest angle magnitude the reduction accepts, in radians.
pub const MAX_ANGLE_RAD: f64 = 2_097_152.0 * HALF_PI;

/// Rejection of an angle outside the declared reduction domain.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct AngleError {
    /// The rejected angle, in radians.
    pub angle_rad: f64,
}

impl fmt::Display for AngleError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "angle_rad: must be finite with magnitude at most {MAX_ANGLE_RAD}, got {}",
            self.angle_rad
        )
    }
}

impl std::error::Error for AngleError {}

/// Converts degrees to radians as one multiplication then one division.
#[must_use]
pub fn radians_from_degrees(degrees: f64) -> f64 {
    (degrees * std::f64::consts::PI) / DEGREES_PER_HALF_TURN
}

/// Validates an angle against the declared reduction domain.
///
/// # Errors
///
/// Returns [`AngleError`] when the angle is not finite or its magnitude
/// exceeds [`MAX_ANGLE_RAD`].
pub fn require_reducible_angle(angle_rad: f64) -> Result<f64, AngleError> {
    if !angle_rad.is_finite() || angle_rad.abs() > MAX_ANGLE_RAD {
        return Err(AngleError { angle_rad });
    }
    Ok(angle_rad)
}

/// Reduces an angle to a quadrant index and a residue in `[-pi/4, pi/4]`.
///
/// # Errors
///
/// Returns [`AngleError`] when the angle leaves the declared domain.
pub fn quadrant_reduction(angle_rad: f64) -> Result<(i64, f64), AngleError> {
    require_reducible_angle(angle_rad)?;
    let count = (angle_rad * TWO_OVER_PI + 0.5).floor();
    let residue = ((angle_rad - count * PIO2_A) - count * PIO2_B) - count * PIO2_C;
    #[allow(clippy::cast_possible_truncation)]
    Ok((count as i64, residue))
}

/// `(cos, sin)` of an arbitrary angle, bit-exact with the Python floor.
///
/// # Errors
///
/// Returns [`AngleError`] when the angle leaves the declared domain.
pub fn circle_point(angle_rad: f64) -> Result<[f64; 2], AngleError> {
    let (index, residue) = quadrant_reduction(angle_rad)?;
    let sine_value = sine_polynomial(residue);
    let cosine_value = cosine_polynomial(residue);
    Ok(match index.rem_euclid(4) {
        0 => [cosine_value, sine_value],
        1 => [0.0 - sine_value, cosine_value],
        2 => [0.0 - cosine_value, 0.0 - sine_value],
        _ => [sine_value, 0.0 - cosine_value],
    })
}

/// Sine of an arbitrary angle.
///
/// # Errors
///
/// Returns [`AngleError`] when the angle leaves the declared domain.
pub fn sine(angle_rad: f64) -> Result<f64, AngleError> {
    Ok(circle_point(angle_rad)?[1])
}

/// Cosine of an arbitrary angle.
///
/// # Errors
///
/// Returns [`AngleError`] when the angle leaves the declared domain.
pub fn cosine(angle_rad: f64) -> Result<f64, AngleError> {
    Ok(circle_point(angle_rad)?[0])
}

#[cfg(test)]
mod arbitrary_angle_tests {
    use super::*;

    #[test]
    fn quadrant_axes_are_recovered() {
        let quarter = HALF_PI;
        assert!(cosine(0.0).unwrap() == 1.0);
        assert!(sine(0.0).unwrap() == 0.0);
        assert!(cosine(quarter).unwrap().abs() < 1.0e-16);
        assert!((sine(quarter).unwrap() - 1.0).abs() < 1.0e-16);
    }

    #[test]
    fn arbitrary_angles_match_libm() {
        for k in -2000..=2000 {
            let x = k as f64 * 0.031_25;
            assert!((cosine(x).unwrap() - x.cos()).abs() <= 2.3e-16);
            assert!((sine(x).unwrap() - x.sin()).abs() <= 2.3e-16);
        }
    }

    #[test]
    fn the_domain_is_refused_at_its_edge() {
        assert!(circle_point(MAX_ANGLE_RAD).is_ok());
        assert!(circle_point(f64::NAN).is_err());
        assert!(sine(f64::INFINITY).is_err());
        assert!(cosine(-2.0 * MAX_ANGLE_RAD).is_err());
    }

    #[test]
    fn degrees_convert_in_a_fixed_order() {
        assert!(radians_from_degrees(180.0) == std::f64::consts::PI);
        assert!(radians_from_degrees(0.0) == 0.0);
    }
}

/// Largest departure from the unit circle a supplied pair may carry.
pub const UNIT_POINT_TOLERANCE: f64 = 1.0e-12;

/// Rejection of a pair that is not a point of the unit circle.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct CirclePointError {
    /// The rejected pair.
    pub point: [f64; 2],
}

impl fmt::Display for CirclePointError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "point: must lie on the unit circle within {UNIT_POINT_TOLERANCE}, got [{}, {}]",
            self.point[0], self.point[1]
        )
    }
}

impl std::error::Error for CirclePointError {}

/// Validates a `(cos, sin)` pair as a point of the unit circle.
///
/// # Errors
///
/// Returns [`CirclePointError`] when a component is not finite or the pair
/// departs from the unit circle by more than [`UNIT_POINT_TOLERANCE`].
pub fn require_circle_point(point: [f64; 2]) -> Result<[f64; 2], CirclePointError> {
    let [cosine_value, sine_value] = point;
    if !cosine_value.is_finite() || !sine_value.is_finite() {
        return Err(CirclePointError { point });
    }
    let departure = (cosine_value * cosine_value + sine_value * sine_value - 1.0).abs();
    if departure > UNIT_POINT_TOLERANCE {
        return Err(CirclePointError { point });
    }
    Ok(point)
}

/// The point half a turn away, by two sign changes.
///
/// # Errors
///
/// Returns [`CirclePointError`] when the pair is not on the unit circle.
pub fn opposite_point(point: [f64; 2]) -> Result<[f64; 2], CirclePointError> {
    let [cosine_value, sine_value] = require_circle_point(point)?;
    Ok([0.0 - cosine_value, 0.0 - sine_value])
}

/// The point of the supplementary angle, by one sign change.
///
/// # Errors
///
/// Returns [`CirclePointError`] when the pair is not on the unit circle.
pub fn supplementary_point(point: [f64; 2]) -> Result<[f64; 2], CirclePointError> {
    let [cosine_value, sine_value] = require_circle_point(point)?;
    Ok([0.0 - cosine_value, sine_value])
}
