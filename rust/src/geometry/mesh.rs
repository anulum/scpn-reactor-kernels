// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// SCPN Reactor Kernels — mesh measure kernel

//! Signed volume and surface area of a closed triangle mesh with the fixed
//! summation order of `scpn_reactor_kernels.geometry.mesh.TriangleMesh`.

fn cross(a: [f64; 3], b: [f64; 3]) -> [f64; 3] {
    [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]
}

fn subtract(a: [f64; 3], b: [f64; 3]) -> [f64; 3] {
    [a[0] - b[0], a[1] - b[1], a[2] - b[2]]
}

/// Euclidean norm, rescaled only where the direct form would fail.
///
/// The direct sum of squares is kept wherever it lands on a finite normal
/// double, as checked on ordinary-scale fixtures, so no measure that was already
/// right changes by a bit and the Python floor agrees bit for bit.
///
/// Outside that the sum of squares loses a result the format can hold: it
/// overflows to infinity while the norm is representable, or falls subnormal
/// while the norm is representable. Both are recovered by dividing through by
/// the largest component and multiplying the scale back. The operation order
/// is the Python floor's, because the parity tests compare bit patterns.
fn norm(vector: [f64; 3]) -> f64 {
    let total = vector[0] * vector[0] + vector[1] * vector[1] + vector[2] * vector[2];
    if total.is_finite() && total >= f64::MIN_POSITIVE {
        return total.sqrt();
    }
    let largest = vector[0].abs().max(vector[1].abs()).max(vector[2].abs());
    if largest == 0.0 {
        return 0.0;
    }
    let a = vector[0] / largest;
    let b = vector[1] / largest;
    let c = vector[2] / largest;
    largest * (a * a + b * b + c * c).sqrt()
}

fn rescale(mut value: f64, mut exponent: i32) -> f64 {
    while exponent > 512 {
        value *= 2.0_f64.powi(512);
        exponent -= 512;
    }
    while exponent < -512 {
        value *= 2.0_f64.powi(-512);
        exponent += 512;
    }
    value * 2.0_f64.powi(exponent)
}

fn scaled_vertices(vertices: &[[f64; 3]]) -> (Vec<[f64; 3]>, i32) {
    let largest = vertices
        .iter()
        .flatten()
        .fold(0.0_f64, |a, x| a.max(x.abs()));
    let exponent = if largest == 0.0 {
        0
    } else if largest < f64::MIN_POSITIVE {
        i32::from(((largest * 2.0_f64.powi(512)).to_bits() >> 52) as u16) - 1022 - 512
    } else {
        i32::from((largest.to_bits() >> 52) as u16) - 1022
    };
    (
        vertices
            .iter()
            .map(|v| {
                [
                    rescale(v[0], -exponent),
                    rescale(v[1], -exponent),
                    rescale(v[2], -exponent),
                ]
            })
            .collect(),
        exponent,
    )
}

fn face_area(v0: [f64; 3], v1: [f64; 3], v2: [f64; 3]) -> f64 {
    let length = norm(cross(subtract(v1, v0), subtract(v2, v0)));
    if length.is_finite() && length >= f64::MIN_POSITIVE {
        return length / 2.0;
    }
    let (v, exponent) = scaled_vertices(&[v0, v1, v2]);
    let length = norm(cross(subtract(v[1], v[0]), subtract(v[2], v[0])));
    rescale(length / 2.0, 2 * exponent)
}

/// Enclosed volume by the divergence theorem, about the mesh's first vertex.
///
/// `sum(a . (b x c)) / 6` over the faces in order, with `a`, `b` and `c` the
/// face's vertices taken relative to `vertices[0]`, accumulated with the same
/// compensation as the Python floor.
///
/// The products of absolute coordinates cancel: each term grows with the
/// square of the distance to the origin while the total does not, so a body
/// far from the origin is a difference of large numbers. Taking the sum about
/// a vertex of the mesh removes that, and the first vertex is used because it
/// needs no arithmetic of its own — both languages read the same bits.
///
/// The operation order is part of the contract: the parity tests compare bit
/// patterns against the Python floor, so the branch, the running total and
/// the correction must all be evaluated exactly as they are here.
///
/// Indices are assumed valid (the Python floor validates the mesh). An empty
/// vertex slice returns zero rather than panicking, which is what the previous
/// form did and which no validated mesh can reach.
#[must_use]
pub fn signed_volume(vertices: &[[f64; 3]], faces: &[[u32; 3]]) -> f64 {
    let value = volume_sum(vertices, faces);
    if !value.is_finite() || value.abs() < f64::MIN_POSITIVE {
        if vertices.is_empty() {
            return value;
        }
        let (scaled, exponent) = scaled_vertices(vertices);
        return rescale(volume_sum(&scaled, faces), 3 * exponent);
    }
    value
}

fn volume_sum(vertices: &[[f64; 3]], faces: &[[u32; 3]]) -> f64 {
    let Some(&origin) = vertices.first() else {
        return 0.0;
    };
    let mut total = 0.0;
    let mut compensation = 0.0;
    for face in faces {
        let a = subtract(vertices[face[0] as usize], origin);
        let b = subtract(vertices[face[1] as usize], origin);
        let c = subtract(vertices[face[2] as usize], origin);
        let n = cross(b, c);
        let term = a[0] * n[0] + a[1] * n[1] + a[2] * n[2];
        let running = total + term;
        if total.abs() >= term.abs() {
            compensation += (total - running) + term;
        } else {
            compensation += (term - running) + total;
        }
        total = running;
    }
    (total + compensation) / 6.0
}

/// Total surface area, `sum(|(v1 - v0) x (v2 - v0)|) / 2`.
///
/// Each face's norm is taken by [`norm`], so a triangle whose cross product
/// overflows or falls subnormal is measured rather than lost.
///
/// Indices are assumed valid, and a measure the format cannot hold is
/// returned as it comes out rather than refused: **the Python floor is the
/// validation layer here**, as it is for mesh validity, and it raises a
/// `GeometryError` naming the body and the measure. A caller reaching this
/// function directly gets the IEEE result.
#[must_use]
pub fn surface_area(vertices: &[[f64; 3]], faces: &[[u32; 3]]) -> f64 {
    let mut total = 0.0;
    for face in faces {
        let v0 = vertices[face[0] as usize];
        let c = cross(
            subtract(vertices[face[1] as usize], v0),
            subtract(vertices[face[2] as usize], v0),
        );
        total += norm(c);
    }
    let area = total / 2.0;
    if area < f64::MIN_POSITIVE && !vertices.is_empty() {
        let (v, exponent) = scaled_vertices(vertices);
        let mut total = 0.0;
        for face in faces {
            total += face_area(
                v[face[0] as usize],
                v[face[1] as usize],
                v[face[2] as usize],
            );
        }
        return rescale(total, 2 * exponent);
    }
    if !area.is_finite() {
        let mut area = 0.0;
        for face in faces {
            area += face_area(
                vertices[face[0] as usize],
                vertices[face[1] as usize],
                vertices[face[2] as usize],
            );
        }
        return area;
    }
    area
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unit_tetrahedron_measures() {
        let vertices = [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ];
        let faces = [[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]];
        let volume = signed_volume(&vertices, &faces);
        assert!((volume - 1.0 / 6.0).abs() <= 1.0e-16);
        let area = surface_area(&vertices, &faces);
        let expected = 1.5 + 3.0_f64.sqrt() / 2.0;
        assert!((area - expected).abs() <= 1.0e-15);
    }

    fn tetrahedron(offset: [f64; 3]) -> ([[f64; 3]; 4], [[u32; 3]; 4]) {
        let base = [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ];
        let mut moved = [[0.0; 3]; 4];
        for (target, vertex) in moved.iter_mut().zip(base.iter()) {
            for axis in 0..3 {
                target[axis] = vertex[axis] + offset[axis];
            }
        }
        (moved, [[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])
    }

    #[test]
    fn translation_does_not_change_the_volume() {
        // The offsets the Python floor is measured at, including the two
        // that the previous form got wrong: 1e8 returned 33333333.33 and
        // the mixed-sign one returned exactly zero.
        for offset in [
            [0.0, 0.0, 0.0],
            [1.0e2, 1.0e2, 1.0e2],
            [1.0e4, 1.0e4, 1.0e4],
            [1.0e6, 1.0e6, 1.0e6],
            [1.0e8, 1.0e8, 1.0e8],
            [-1.0e8, 1.0e8, -1.0e8],
        ] {
            let (vertices, faces) = tetrahedron(offset);
            let volume = signed_volume(&vertices, &faces);
            assert!(
                (volume - 1.0 / 6.0).abs() <= 1.0e-16,
                "offset {offset:?} gave {volume}"
            );
        }
    }

    #[test]
    fn a_uniformly_inward_mesh_keeps_a_negative_volume() {
        let (vertices, _) = tetrahedron([1.0e8, 1.0e8, 1.0e8]);
        let inward = [[0, 1, 2], [0, 3, 1], [0, 2, 3], [1, 3, 2]];
        let volume = signed_volume(&vertices, &inward);
        assert!((volume + 1.0 / 6.0).abs() <= 1.0e-16, "got {volume}");
    }

    #[test]
    fn an_empty_mesh_measures_zero_rather_than_panicking() {
        let vertices: [[f64; 3]; 0] = [];
        let faces: [[u32; 3]; 0] = [];
        assert!(signed_volume(&vertices, &faces) == 0.0);
    }

    fn scaled(scale: f64) -> ([[f64; 3]; 4], [[u32; 3]; 4]) {
        let base = [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ];
        let mut out = [[0.0; 3]; 4];
        for (target, vertex) in out.iter_mut().zip(base.iter()) {
            for axis in 0..3 {
                target[axis] = vertex[axis] * scale;
            }
        }
        (out, [[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])
    }

    #[test]
    fn the_area_survives_a_scale_whose_squares_overflow() {
        // The exact area is 1.5 + sqrt(3)/2 times the square of the scale.
        // At 1e100 that is 2.37e200, well inside the format, but the sum of
        // squares of the cross product is 1e400 and used to overflow.
        let unit_area = 1.5 + 3.0_f64.sqrt() / 2.0;
        for exponent in [77, 100, 150, 153] {
            let scale = 10.0_f64.powi(exponent);
            let (vertices, faces) = scaled(scale);
            let area = surface_area(&vertices, &faces);
            let expected = unit_area * scale * scale;
            assert!(area.is_finite(), "exponent {exponent} gave {area}");
            assert!(
                (area - expected).abs() / expected <= 1.0e-12,
                "exponent {exponent} gave {area}, expected {expected}"
            );
        }
    }

    #[test]
    fn the_area_survives_a_scale_whose_squares_fall_subnormal() {
        let unit_area = 1.5 + 3.0_f64.sqrt() / 2.0;
        for exponent in [-100, -154, -155] {
            let scale = 10.0_f64.powi(exponent);
            let (vertices, faces) = scaled(scale);
            let area = surface_area(&vertices, &faces);
            let expected = unit_area * scale * scale;
            assert!(
                (area - expected).abs() / expected <= 1.0e-12,
                "exponent {exponent} gave {area}, expected {expected}"
            );
        }
    }

    #[test]
    fn the_ordinary_scale_still_takes_the_direct_form() {
        // Bit-for-bit, so the repair cannot have moved a measure that was
        // already right; the Python floor asserts the same thing.
        for exponent in [-50, -10, 0, 10, 50] {
            let scale = 10.0_f64.powi(exponent);
            let (vertices, faces) = scaled(scale);
            let mut direct = 0.0;
            for face in &faces {
                let v0 = vertices[face[0] as usize];
                let c = cross(
                    subtract(vertices[face[1] as usize], v0),
                    subtract(vertices[face[2] as usize], v0),
                );
                direct += (c[0] * c[0] + c[1] * c[1] + c[2] * c[2]).sqrt();
            }
            assert!(surface_area(&vertices, &faces).to_bits() == (direct / 2.0).to_bits());
        }
    }

    #[test]
    fn a_zero_vector_has_a_norm_of_positive_zero() {
        let value = norm([0.0, -0.0, 0.0]);
        assert!(value == 0.0);
        assert!(value.is_sign_positive());
    }
}
