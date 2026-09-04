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
//! circle of [`geometry::trig`]; the logarithm, exponential and power of
//! [`numerics::transcendental`]; the Bessel functions of
//! [`numerics::bessel`]). Nothing here solves an equation and no
//! value describes a real machine; design records are the ADRs of the
//! repository (ADR 0002 for the geometry kernels, ADR 0003 for the
//! numerics kernels).

pub mod geometry;
pub mod numerics;

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

    /// Equally spaced circle points for any count as a flat stream.
    #[pyfunction]
    fn circle_points(count: usize) -> PyResult<Vec<f64>> {
        let points = crate::geometry::trig::circle_points(count)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok(points.iter().flat_map(|p| p.iter().copied()).collect())
    }

    /// Ring centres of `count` bodies on a circle as a flat stream.
    #[pyfunction]
    fn ring_offsets(count: usize, radius_m: f64) -> PyResult<Vec<f64>> {
        let offsets = crate::geometry::placement::ring_offsets(count, radius_m)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok(offsets.iter().flat_map(|p| p.iter().copied()).collect())
    }

    /// Centre-to-centre distance of neighbouring bodies on a ring.
    #[pyfunction]
    fn ring_separation(count: usize, radius_m: f64) -> PyResult<f64> {
        crate::geometry::placement::ring_separation_m(count, radius_m)
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    /// Translation of a flat vertex stream by a fixed offset.
    #[pyfunction]
    fn translate(
        vertices: Vec<f64>,
        offset_x_m: f64,
        offset_y_m: f64,
        offset_z_m: f64,
    ) -> PyResult<Vec<f64>> {
        if vertices.len() % 3 != 0 {
            return Err(PyValueError::new_err(
                "vertices: length must be a multiple of three",
            ));
        }
        let triples: Vec<[f64; 3]> = vertices
            .chunks_exact(3)
            .map(|c| [c[0], c[1], c[2]])
            .collect();
        let moved =
            crate::geometry::placement::translate(&triples, [offset_x_m, offset_y_m, offset_z_m]);
        Ok(moved.iter().flat_map(|p| p.iter().copied()).collect())
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

    /// Unflatten a flat `(z, radius, ...)` stream into profile samples.
    fn unflatten_profile(stream: &[f64]) -> PyResult<Vec<[f64; 2]>> {
        if stream.len() % 2 != 0 {
            return Err(PyValueError::new_err(
                "profile: must carry an even number of values (z, radius pairs)",
            ));
        }
        Ok(stream.chunks_exact(2).map(|c| [c[0], c[1]]).collect())
    }

    /// Profiled solid tessellation as flat vertex and face streams.
    #[pyfunction]
    fn tessellate_profiled_solid(
        profile: Vec<f64>,
        segments: usize,
    ) -> PyResult<(Vec<f64>, Vec<u32>)> {
        let samples = unflatten_profile(&profile)?;
        let t = crate::geometry::profiles::profiled_solid(&samples, segments)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok((flatten_vertices(&t.vertices), flatten_faces(&t.faces)))
    }

    /// Closed profiled solid tessellation as flat vertex and face streams.
    #[pyfunction]
    fn tessellate_closed_profiled_solid(
        profile: Vec<f64>,
        segments: usize,
    ) -> PyResult<(Vec<f64>, Vec<u32>)> {
        let samples = unflatten_profile(&profile)?;
        let t = crate::geometry::profiles::closed_profiled_solid(&samples, segments)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok((flatten_vertices(&t.vertices), flatten_faces(&t.faces)))
    }

    /// Sphere axial profile as a flat `(z, radius)` stream.
    #[pyfunction]
    fn sphere_profile(radius_m: f64, centre_z_m: f64, rings: usize) -> PyResult<Vec<f64>> {
        let profile = crate::geometry::spheres::sphere_profile(radius_m, centre_z_m, rings)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok(profile.iter().flat_map(|s| s.iter().copied()).collect())
    }

    /// Spherical shell tessellation as flat vertex and face streams.
    #[pyfunction]
    fn tessellate_spherical_shell(
        outer_profile: Vec<f64>,
        inner_profile: Vec<f64>,
        segments: usize,
    ) -> PyResult<(Vec<f64>, Vec<u32>)> {
        let outer = unflatten_profile(&outer_profile)?;
        let inner = unflatten_profile(&inner_profile)?;
        let t = crate::geometry::spheres::spherical_shell(&outer, &inner, segments)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok((flatten_vertices(&t.vertices), flatten_faces(&t.faces)))
    }

    /// Profiled tube tessellation as flat vertex and face streams.
    #[pyfunction]
    fn tessellate_profiled_tube(
        inner_profile: Vec<f64>,
        outer_profile: Vec<f64>,
        segments: usize,
    ) -> PyResult<(Vec<f64>, Vec<u32>)> {
        let inner = unflatten_profile(&inner_profile)?;
        let outer = unflatten_profile(&outer_profile)?;
        let t = crate::geometry::profiles::profiled_tube(&inner, &outer, segments)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok((flatten_vertices(&t.vertices), flatten_faces(&t.faces)))
    }

    /// Exact volume of the solid of revolution of a linear profile.
    #[pyfunction]
    fn profile_volume(profile: Vec<f64>) -> PyResult<f64> {
        let samples = unflatten_profile(&profile)?;
        Ok(crate::geometry::profiles::profile_volume_m3(&samples))
    }

    /// Exact lateral area of the surface of revolution of a linear profile.
    #[pyfunction]
    fn profile_lateral_area(profile: Vec<f64>) -> PyResult<f64> {
        let samples = unflatten_profile(&profile)?;
        Ok(crate::geometry::profiles::profile_lateral_area_m2(&samples))
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

    /// Natural logarithm of one positive normal double.
    #[pyfunction]
    fn natural_log(x: f64) -> PyResult<f64> {
        crate::numerics::transcendental::natural_log(x)
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    /// Exponential of one argument whose result is a normal double.
    #[pyfunction]
    fn exponential(y: f64) -> PyResult<f64> {
        crate::numerics::transcendental::exponential(y)
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    /// Real power `base ** exponent` of one positive normal base.
    #[pyfunction]
    fn power(base: f64, exponent: f64) -> PyResult<f64> {
        crate::numerics::transcendental::power(base, exponent)
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    /// Natural logarithm of every value of a stream (the first refusal aborts).
    #[pyfunction]
    fn natural_log_stream(values: Vec<f64>) -> PyResult<Vec<f64>> {
        values
            .iter()
            .map(|&x| {
                crate::numerics::transcendental::natural_log(x)
                    .map_err(|e| PyValueError::new_err(e.to_string()))
            })
            .collect()
    }

    /// Exponential of every value of a stream (the first refusal aborts).
    #[pyfunction]
    fn exponential_stream(values: Vec<f64>) -> PyResult<Vec<f64>> {
        values
            .iter()
            .map(|&y| {
                crate::numerics::transcendental::exponential(y)
                    .map_err(|e| PyValueError::new_err(e.to_string()))
            })
            .collect()
    }

    /// Element-wise power of two equally long streams (the first refusal aborts).
    #[pyfunction]
    fn power_stream(bases: Vec<f64>, exponents: Vec<f64>) -> PyResult<Vec<f64>> {
        if bases.len() != exponents.len() {
            return Err(PyValueError::new_err(
                "bases and exponents must have the same length",
            ));
        }
        bases
            .iter()
            .zip(exponents.iter())
            .map(|(&b, &e)| {
                crate::numerics::transcendental::power(b, e)
                    .map_err(|err| PyValueError::new_err(err.to_string()))
            })
            .collect()
    }

    /// `J0` of one argument on `|x| <= 8`.
    #[pyfunction]
    fn bessel_j0(x: f64) -> PyResult<f64> {
        crate::numerics::bessel::bessel_j0(x).map_err(|e| PyValueError::new_err(e.to_string()))
    }

    /// `J1` of one argument on `|x| <= 8`.
    #[pyfunction]
    fn bessel_j1(x: f64) -> PyResult<f64> {
        crate::numerics::bessel::bessel_j1(x).map_err(|e| PyValueError::new_err(e.to_string()))
    }

    /// `J0` of every value of a stream (the first refusal aborts).
    #[pyfunction]
    fn bessel_j0_stream(values: Vec<f64>) -> PyResult<Vec<f64>> {
        values
            .iter()
            .map(|&x| {
                crate::numerics::bessel::bessel_j0(x)
                    .map_err(|e| PyValueError::new_err(e.to_string()))
            })
            .collect()
    }

    /// `J1` of every value of a stream (the first refusal aborts).
    #[pyfunction]
    fn bessel_j1_stream(values: Vec<f64>) -> PyResult<Vec<f64>> {
        values
            .iter()
            .map(|&x| {
                crate::numerics::bessel::bessel_j1(x)
                    .map_err(|e| PyValueError::new_err(e.to_string()))
            })
            .collect()
    }

    /// Python module `scpn_reactor_kernels_native`.
    #[pymodule]
    fn scpn_reactor_kernels_native(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(unit_circle, m)?)?;
        m.add_function(wrap_pyfunction!(circle_points, m)?)?;
        m.add_function(wrap_pyfunction!(ring_offsets, m)?)?;
        m.add_function(wrap_pyfunction!(ring_separation, m)?)?;
        m.add_function(wrap_pyfunction!(translate, m)?)?;
        m.add_function(wrap_pyfunction!(tessellate_cylinder, m)?)?;
        m.add_function(wrap_pyfunction!(tessellate_annular_tube, m)?)?;
        m.add_function(wrap_pyfunction!(tessellate_profiled_solid, m)?)?;
        m.add_function(wrap_pyfunction!(tessellate_closed_profiled_solid, m)?)?;
        m.add_function(wrap_pyfunction!(tessellate_profiled_tube, m)?)?;
        m.add_function(wrap_pyfunction!(sphere_profile, m)?)?;
        m.add_function(wrap_pyfunction!(tessellate_spherical_shell, m)?)?;
        m.add_function(wrap_pyfunction!(profile_volume, m)?)?;
        m.add_function(wrap_pyfunction!(profile_lateral_area, m)?)?;
        m.add_function(wrap_pyfunction!(mesh_volume, m)?)?;
        m.add_function(wrap_pyfunction!(mesh_area, m)?)?;
        m.add_function(wrap_pyfunction!(natural_log, m)?)?;
        m.add_function(wrap_pyfunction!(exponential, m)?)?;
        m.add_function(wrap_pyfunction!(power, m)?)?;
        m.add_function(wrap_pyfunction!(natural_log_stream, m)?)?;
        m.add_function(wrap_pyfunction!(exponential_stream, m)?)?;
        m.add_function(wrap_pyfunction!(power_stream, m)?)?;
        m.add_function(wrap_pyfunction!(bessel_j0, m)?)?;
        m.add_function(wrap_pyfunction!(bessel_j1, m)?)?;
        m.add_function(wrap_pyfunction!(bessel_j0_stream, m)?)?;
        m.add_function(wrap_pyfunction!(bessel_j1_stream, m)?)?;
        Ok(())
    }
}
