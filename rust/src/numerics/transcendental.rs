// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// SCPN Reactor Kernels — deterministic natural logarithm, exponential and power

//! Vendored `ln`, `exp` and real power mirroring
//! `scpn_reactor_kernels.numerics.transcendental` operation for operation:
//! `ln(x) = k ln 2 + 2 atanh((m - 1)/(m + 1))` with `x = m 2^k` from an
//! exact binary decomposition and a degree-25 odd series; `exp(y) = 2^k
//! exp(r)` with the Cody–Waite reduction and a degree-17 Taylor series;
//! `pow(x, y) = exp(y ln x)`. Only `+ - * /`, exact bit manipulation and
//! exact power-of-two scaling are used.

use std::fmt;

/// Smallest positive normal double; the logarithm's lower admissible bound.
pub const MIN_NORMAL: f64 = f64::MIN_POSITIVE;
/// Correctly rounded `ln 2` (the standard constant carries the same bits as
/// the Python literal; the parity tests prove it).
pub const LN2: f64 = std::f64::consts::LN_2;
/// High part of the Cody–Waite split of `ln 2` (trailing zero bits).
pub const LN2_HI: f64 = f64::from_bits(0x3fe6_2e42_fee0_0000);
/// Low part of the Cody–Waite split of `ln 2` (`LN2_HI + LN2_LO == LN2`).
pub const LN2_LO: f64 = f64::from_bits(0x3dea_39ef_3579_3c76);
/// Correctly rounded `1 / ln 2`.
pub const INV_LN2: f64 = std::f64::consts::LOG2_E;
/// Correctly rounded `sqrt(1/2)`.
pub const SQRT_HALF: f64 = std::f64::consts::FRAC_1_SQRT_2;
/// Largest admissible exponential argument.
pub const EXP_MAX: f64 = 709.0;
/// Smallest admissible exponential argument.
pub const EXP_MIN: f64 = -708.0;

const A3: f64 = 1.0 / 3.0;
const A5: f64 = 1.0 / 5.0;
const A7: f64 = 1.0 / 7.0;
const A9: f64 = 1.0 / 9.0;
const A11: f64 = 1.0 / 11.0;
const A13: f64 = 1.0 / 13.0;
const A15: f64 = 1.0 / 15.0;
const A17: f64 = 1.0 / 17.0;
const A19: f64 = 1.0 / 19.0;
const A21: f64 = 1.0 / 21.0;
const A23: f64 = 1.0 / 23.0;
const A25: f64 = 1.0 / 25.0;

const F2: f64 = 1.0 / 2.0;
const F3: f64 = 1.0 / 6.0;
const F4: f64 = 1.0 / 24.0;
const F5: f64 = 1.0 / 120.0;
const F6: f64 = 1.0 / 720.0;
const F7: f64 = 1.0 / 5040.0;
const F8: f64 = 1.0 / 40_320.0;
const F9: f64 = 1.0 / 362_880.0;
const F10: f64 = 1.0 / 3_628_800.0;
const F11: f64 = 1.0 / 39_916_800.0;
const F12: f64 = 1.0 / 479_001_600.0;
const F13: f64 = 1.0 / 6_227_020_800.0;
const F14: f64 = 1.0 / 87_178_291_200.0;
const F15: f64 = 1.0 / 1_307_674_368_000.0;
const F16: f64 = 1.0 / 20_922_789_888_000.0;
const F17: f64 = 1.0 / 355_687_428_096_000.0;

/// Rejection of an argument outside a kernel's admissible range.
#[derive(Debug, Clone, PartialEq)]
pub struct NumericsError {
    /// Human-readable description naming the field and the violated bound.
    pub message: String,
}

impl fmt::Display for NumericsError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.message)
    }
}

impl std::error::Error for NumericsError {}

fn require_positive_normal(name: &str, value: f64) -> Result<f64, NumericsError> {
    if !value.is_finite() {
        return Err(NumericsError {
            message: format!("{name}: must be finite, got {value:?}"),
        });
    }
    if value < MIN_NORMAL {
        return Err(NumericsError {
            message: format!(
                "{name}: must be a positive normal number (at least {MIN_NORMAL:?}), got {value:?}"
            ),
        });
    }
    Ok(value)
}

/// Exact split of a positive normal `x` into `(m, k)` with `x = m 2^k` and
/// `m` in `[sqrt(1/2), sqrt(2))`, identical to `math.frexp` followed by the
/// window shift of the Python floor.
#[must_use]
pub fn binary_decompose(x: f64) -> (f64, i32) {
    let bits = x.to_bits();
    let biased = ((bits >> 52) & 0x7ff) as i32;
    let mantissa_bits = (bits & 0x000f_ffff_ffff_ffff) | (0x3fe_u64 << 52);
    let mut mantissa = f64::from_bits(mantissa_bits);
    let mut exponent = biased - 1022;
    if mantissa < SQRT_HALF {
        mantissa *= 2.0;
        exponent -= 1;
    }
    (mantissa, exponent)
}

/// Exact `2^k` for `k` in `[-1022, 1023]`.
#[must_use]
pub fn power_of_two(k: i32) -> f64 {
    f64::from_bits(((k + 1023) as u64) << 52)
}

/// `2 atanh(s)` by its odd series truncated after `s^25` (Horner in `s^2`).
#[must_use]
pub fn atanh_series(s: f64) -> f64 {
    let square = s * s;
    let mut polynomial = A25;
    polynomial = polynomial * square + A23;
    polynomial = polynomial * square + A21;
    polynomial = polynomial * square + A19;
    polynomial = polynomial * square + A17;
    polynomial = polynomial * square + A15;
    polynomial = polynomial * square + A13;
    polynomial = polynomial * square + A11;
    polynomial = polynomial * square + A9;
    polynomial = polynomial * square + A7;
    polynomial = polynomial * square + A5;
    polynomial = polynomial * square + A3;
    polynomial = polynomial * square + 1.0;
    (2.0 * s) * polynomial
}

/// `exp(r)` by its Taylor series truncated after `r^17` (Horner form).
#[must_use]
pub fn exponential_series(r: f64) -> f64 {
    let mut polynomial = F17;
    polynomial = polynomial * r + F16;
    polynomial = polynomial * r + F15;
    polynomial = polynomial * r + F14;
    polynomial = polynomial * r + F13;
    polynomial = polynomial * r + F12;
    polynomial = polynomial * r + F11;
    polynomial = polynomial * r + F10;
    polynomial = polynomial * r + F9;
    polynomial = polynomial * r + F8;
    polynomial = polynomial * r + F7;
    polynomial = polynomial * r + F6;
    polynomial = polynomial * r + F5;
    polynomial = polynomial * r + F4;
    polynomial = polynomial * r + F3;
    polynomial = polynomial * r + F2;
    polynomial = polynomial * r + 1.0;
    polynomial * r + 1.0
}

/// Natural logarithm of a positive normal double.
///
/// # Errors
///
/// Returns [`NumericsError`] when `x` is non-finite, zero, negative or subnormal.
pub fn natural_log(x: f64) -> Result<f64, NumericsError> {
    require_positive_normal("x", x)?;
    let (mantissa, exponent) = binary_decompose(x);
    let s = (mantissa - 1.0) / (mantissa + 1.0);
    Ok(f64::from(exponent) * LN2 + atanh_series(s))
}

/// `exp(y)` for arguments whose result is a normal double.
///
/// # Errors
///
/// Returns [`NumericsError`] when `y` is non-finite or outside `[EXP_MIN, EXP_MAX]`.
pub fn exponential(y: f64) -> Result<f64, NumericsError> {
    if !y.is_finite() {
        return Err(NumericsError {
            message: format!("y: must be finite, got {y:?}"),
        });
    }
    if !(EXP_MIN..=EXP_MAX).contains(&y) {
        return Err(NumericsError {
            message: format!(
                "y: must lie within [{EXP_MIN:?}, {EXP_MAX:?}] so that the result is a normal number, got {y:?}"
            ),
        });
    }
    let k = (y * INV_LN2 + 0.5).floor();
    let r = (y - k * LN2_HI) - k * LN2_LO;
    Ok(exponential_series(r) * power_of_two(k as i32))
}

/// `base ^ exponent` as `exp(exponent ln base)`.
///
/// # Errors
///
/// Returns [`NumericsError`] when `base` is not a positive normal number,
/// `exponent` is non-finite, or the result would not be a normal number.
pub fn power(base: f64, exponent: f64) -> Result<f64, NumericsError> {
    require_positive_normal("base", base)?;
    if !exponent.is_finite() {
        return Err(NumericsError {
            message: format!("exponent: must be finite, got {exponent:?}"),
        });
    }
    let product = exponent * natural_log(base)?;
    if !(EXP_MIN..=EXP_MAX).contains(&product) {
        return Err(NumericsError {
            message: format!(
                "power: exponent * ln(base) = {product:?} leaves [{EXP_MIN:?}, {EXP_MAX:?}]; the result would not be a normal number"
            ),
        });
    }
    exponential(product)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn constants_carry_the_documented_bits() {
        assert_eq!(LN2.to_bits(), 0x3fe6_2e42_fefa_39ef);
        assert_eq!(LN2_HI + LN2_LO, LN2);
        assert_eq!(INV_LN2, 1.0 / LN2);
        assert_eq!(SQRT_HALF.to_bits(), 0x3fe6_a09e_667f_3bcd);
        assert_eq!(MIN_NORMAL, 2.2250738585072014e-308);
    }

    #[test]
    fn decomposition_is_exact_and_windowed() {
        for &x in &[1.0, 1.5, 3.0, 0.3, 1e-300, 1e300, MIN_NORMAL] {
            let (m, k) = binary_decompose(x);
            assert!((SQRT_HALF..2.0 * SQRT_HALF).contains(&m), "{x}");
            assert_eq!(m * power_of_two(k), x);
        }
        let (m, k) = binary_decompose(f64::MAX);
        assert_eq!(k, 1024);
        assert_eq!((m * power_of_two(k - 1)) * 2.0, f64::MAX);
        assert!((natural_log(f64::MAX).unwrap() - 709.782_712_893_384).abs() < 1e-12);
    }

    #[test]
    fn exact_points() {
        assert_eq!(natural_log(1.0).unwrap(), 0.0);
        assert_eq!(natural_log(2.0).unwrap(), LN2);
        assert_eq!(natural_log(0.5).unwrap(), -LN2);
        assert_eq!(exponential(0.0).unwrap(), 1.0);
        assert_eq!(power(3.0, 0.0).unwrap(), 1.0);
    }

    #[test]
    fn agrees_with_libm_to_a_few_ulp() {
        for i in -600..=600 {
            let x = f64::from(i) * 1.0 + 0.5;
            if x > 0.0 {
                let got = natural_log(x).unwrap();
                let want = x.ln();
                assert!((got - want).abs() <= 4.0 * f64::EPSILON * want.abs().max(1.0));
            }
            let y = f64::from(i);
            let got = exponential(y).unwrap();
            let want = y.exp();
            assert!((got - want).abs() <= 4.0 * f64::EPSILON * want);
        }
        let got = power(10.0, 2.5).unwrap();
        assert!((got - 316.227_766_016_837_94).abs() < 1e-12);
    }

    #[test]
    fn refusals() {
        assert!(natural_log(0.0).is_err());
        assert!(natural_log(-1.0).is_err());
        assert!(natural_log(f64::NAN).is_err());
        assert!(natural_log(5e-324).is_err());
        assert!(exponential(f64::INFINITY).is_err());
        assert!(exponential(709.5).is_err());
        assert!(exponential(-708.5).is_err());
        assert!(power(0.0, 1.0).is_err());
        assert!(power(2.0, f64::NAN).is_err());
        assert!(power(10.0, 400.0).is_err());
        assert!(power(1e-300, 3.0).is_err());
        assert_eq!(
            natural_log(0.0).unwrap_err().to_string(),
            format!("x: must be a positive normal number (at least {MIN_NORMAL:?}), got 0.0")
        );
    }
}
