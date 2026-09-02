// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// SCPN Reactor Kernels — native kernels

//! Native kernels of SCPN Reactor Kernels.
//!
//! Every function mirrors one evaluation of the pure-Python floor in
//! `scpn_reactor_kernels` with the identical operation order, so the
//! IEEE-754 double results agree bit for bit. The kernels use only `+`,
//! `-`, `*`, `/` and `sqrt` (all correctly rounded) plus vendored
//! deterministic implementations of anything else (the polynomial unit
//! circle of [`geometry::trig`]). Nothing here solves an equation and no
//! value describes a real machine; design records are the ADRs of the
//! repository (ADR 0002 for the geometry kernels).

pub mod geometry;

#[cfg(feature = "python")]
mod python {
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    type Streams = (Vec<[f64; 3]>, Vec<[u32; 3]>);

    fn flatten_vertices(vertices: &[[f64; 3]]) -> Vec<f64> {
        vertices.iter().flat_map(|v| v.iter().copied()).collect()
    }

    fn flatten_faces(faces: &[[u32; 3]]) -> Vec<u32> {
        faces.iter().flat_map(|f| f.iter().copied()).collect()
    }

    fn unflatten(vertices: &[f64], faces: &[u32]) -> PyResult<Streams> {
        if vertices.len() % 3 != 0 || faces.len() % 3 != 0 {
            return Err(PyValueError::new_err(
                "vertices and faces must be flat streams of triples",
            ));
        }
        let vertex_triples: Vec<[f64; 3]> = vertices
            .chunks_exact(3)
            .map(|c| [c[0], c[1], c[2]])
            .collect();
        let count = vertex_triples.len();
        let mut face_triples: Vec<[u32; 3]> = Vec::with_capacity(faces.len() / 3);
        for chunk in faces.chunks_exact(3) {
            for &corner in chunk {
                if corner as usize >= count {
                    return Err(PyValueError::new_err(format!(
                        "face index {corner} out of range [0, {count})"
                    )));
                }
            }
            face_triples.push([chunk[0], chunk[1], chunk[2]]);
        }
        Ok((vertex_triples, face_triples))
    }

    /// Unit-circle points as a flat `[cos0, sin0, cos1, sin1, ...]` stream.
    #[pyfunction]
    fn unit_circle(segments: usize) -> PyResult<Vec<f64>> {
        let points = crate::geometry::trig::unit_circle(segments)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok(points.iter().flat_map(|p| p.iter().copied()).collect())
    }

    /// Solid cylinder tessellation as flat vertex and face streams.
    #[pyfunction]
    fn tessellate_cylinder(
        radius_m: f64,
        z_low_m: f64,
        z_high_m: f64,
        segments: usize,
    ) -> PyResult<(Vec<f64>, Vec<u32>)> {
        let t = crate::geometry::primitives::cylinder_solid(radius_m, z_low_m, z_high_m, segments)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok((flatten_vertices(&t.vertices), flatten_faces(&t.faces)))
    }

    /// Annular tube tessellation as flat vertex and face streams.
    #[pyfunction]
    fn tessellate_annular_tube(
        inner_radius_m: f64,
        outer_radius_m: f64,
        z_low_m: f64,
        z_high_m: f64,
        segments: usize,
    ) -> PyResult<(Vec<f64>, Vec<u32>)> {
        let t = crate::geometry::primitives::annular_tube(
            inner_radius_m,
            outer_radius_m,
            z_low_m,
            z_high_m,
            segments,
        )
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok((flatten_vertices(&t.vertices), flatten_faces(&t.faces)))
    }

    /// Signed volume of a mesh given as flat streams, see `crate::geometry::mesh::signed_volume`.
    #[pyfunction]
    fn mesh_volume(vertices: Vec<f64>, faces: Vec<u32>) -> PyResult<f64> {
        let (v, f) = unflatten(&vertices, &faces)?;
        Ok(crate::geometry::mesh::signed_volume(&v, &f))
    }

    /// Surface area of a mesh given as flat streams, see `crate::geometry::mesh::surface_area`.
    #[pyfunction]
    fn mesh_area(vertices: Vec<f64>, faces: Vec<u32>) -> PyResult<f64> {
        let (v, f) = unflatten(&vertices, &faces)?;
        Ok(crate::geometry::mesh::surface_area(&v, &f))
    }

    /// Python module `scpn_reactor_kernels_native`.
    #[pymodule]
    fn scpn_reactor_kernels_native(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(unit_circle, m)?)?;
        m.add_function(wrap_pyfunction!(tessellate_cylinder, m)?)?;
        m.add_function(wrap_pyfunction!(tessellate_annular_tube, m)?)?;
        m.add_function(wrap_pyfunction!(mesh_volume, m)?)?;
        m.add_function(wrap_pyfunction!(mesh_area, m)?)?;
        Ok(())
    }
}
