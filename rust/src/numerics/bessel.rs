// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// SCPN Reactor Kernels — Bessel functions J0 and J1

//! Bessel functions `J0` and `J1` of the first kind on `|x| <= 8` by the
//! DLMF 10.2.2 ascending series in Horner form, operation-for-operation
//! identical to `scpn_reactor_kernels.numerics.bessel`; first zeros from
//! OEIS A115368 and A115369.

use crate::numerics::transcendental::NumericsError;

/// First positive zero of `J0` (OEIS A115368), correctly rounded.
pub const BESSEL_J0_FIRST_ZERO: f64 = 2.404_825_557_695_773;
/// First positive zero of `J1` (OEIS A115369), correctly rounded.
pub const BESSEL_J1_FIRST_ZERO: f64 = 3.831_705_970_207_512_5;
/// Largest admissible `|x|`.
pub const BESSEL_DOMAIN: f64 = 8.0;
/// Series terms after the leading one.
pub const BESSEL_TERMS: u32 = 30;

fn require_bessel_argument(name: &str, value: f64) -> Result<f64, NumericsError> {
    if !value.is_finite() {
        return Err(NumericsError {
            message: format!("{name}: must be finite, got {value:?}"),
        });
    }
    if !(-BESSEL_DOMAIN..=BESSEL_DOMAIN).contains(&value) {
        return Err(NumericsError {
            message: format!(
                "{name}: the Bessel series is evaluated on |x| <= {BESSEL_DOMAIN:?}, got {value:?}"
            ),
        });
    }
    Ok(value)
}

/// `sum_k (-t)^k / (k!)^2` by Horner recursion.
#[must_use]
pub fn bessel_j0_series(t: f64) -> f64 {
    let mut acc = 1.0;
    for k in (1..=BESSEL_TERMS).rev() {
        acc = 1.0 - t * acc / f64::from(k * k);
    }
    acc
}

/// `sum_k (-t)^k / (k! (k + 1)!)` by Horner recursion.
#[must_use]
pub fn bessel_j1_series(t: f64) -> f64 {
    let mut acc = 1.0;
    for k in (1..=BESSEL_TERMS).rev() {
        acc = 1.0 - t * acc / f64::from(k * (k + 1));
    }
    acc
}

/// `J0(x)` on the declared domain.
///
/// # Errors
/// Returns [`NumericsError`] when `x` is non-finite or `|x| > 8`.
pub fn bessel_j0(x: f64) -> Result<f64, NumericsError> {
    require_bessel_argument("x", x)?;
    Ok(bessel_j0_series(x * x / 4.0))
}

/// `J1(x)` on the declared domain.
///
/// # Errors
/// Returns [`NumericsError`] when `x` is non-finite or `|x| > 8`.
pub fn bessel_j1(x: f64) -> Result<f64, NumericsError> {
    require_bessel_argument("x", x)?;
    Ok((x / 2.0) * bessel_j1_series(x * x / 4.0))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn zeros_and_origin() {
        assert_eq!(bessel_j0(0.0).unwrap(), 1.0);
        assert_eq!(bessel_j1(0.0).unwrap(), 0.0);
        assert!(bessel_j0(BESSEL_J0_FIRST_ZERO).unwrap().abs() <= 1.0e-14);
        assert!(bessel_j1(BESSEL_J1_FIRST_ZERO).unwrap().abs() <= 1.0e-14);
        assert!(bessel_j0(8.5).is_err());
        assert!(bessel_j1(f64::NAN).is_err());
    }
}
