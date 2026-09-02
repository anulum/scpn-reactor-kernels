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

/// Enclosed volume by the divergence theorem, `sum(v0 . (v1 x v2)) / 6`.
///
/// Indices are assumed valid (the Python floor validates the mesh).
#[must_use]
pub fn signed_volume(vertices: &[[f64; 3]], faces: &[[u32; 3]]) -> f64 {
    let mut total = 0.0;
    for face in faces {
        let v0 = vertices[face[0] as usize];
        let c = cross(vertices[face[1] as usize], vertices[face[2] as usize]);
        total += v0[0] * c[0] + v0[1] * c[1] + v0[2] * c[2];
    }
    total / 6.0
}

/// Total surface area, `sum(|(v1 - v0) x (v2 - v0)|) / 2`.
///
/// Indices are assumed valid (the Python floor validates the mesh).
#[must_use]
pub fn surface_area(vertices: &[[f64; 3]], faces: &[[u32; 3]]) -> f64 {
    let mut total = 0.0;
    for face in faces {
        let v0 = vertices[face[0] as usize];
        let c = cross(
            subtract(vertices[face[1] as usize], v0),
            subtract(vertices[face[2] as usize], v0),
        );
        total += (c[0] * c[0] + c[1] * c[1] + c[2] * c[2]).sqrt();
    }
    total / 2.0
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
}
