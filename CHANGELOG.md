<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
SCPN Reactor Kernels — CHANGELOG
-->

# Changelog

## [Unreleased]

### Added

- Aiming a body, and placing it on a sphere (`geometry_placement`,
  `cad_placement`, ADR 0017 and ADR 0018). Until now there was **no
  rotation anywhere in this library**: a body could be moved off the axis
  but not turned, so every body stood parallel to the axis wherever it
  was put. A machine whose bodies converge on a point could not be
  modelled at all — one filed source prints thirty bodies on four
  latitudes of a spherical chamber, at 20.1, 59.0, 121.0 and 159.9
  degrees with five, ten, ten and five members, each pointing at the
  centre.

  **The rotation is built from two angles, never from a direction
  vector**, and that choice was measured rather than argued. The textbook
  minimal rotation from `z` to a unit vector divides by `1 + d_z`, which
  loses every significant digit near the negative `z` axis even for a
  perfect unit vector: one microradian short of half a turn it departs
  from orthogonality by `3.6e-4`. The form used here has no such term and
  departs by at most `4.440892098500626e-16` over two hundred thousand
  angle pairs, the antipode included. A test computes both and asserts
  the difference, so the reason cannot be lost.

  Both entry points take circle points rather than angles, which keeps
  the exactness where it exists: a ring with no twist returns the plain
  circle bit for bit, and the reversals a sphere needs are sign changes
  alone.

  **The gate checks that a rotation is a rotation.** A scaling would
  change every placed body's volume and a reflection its handedness — and
  a reflection passes every orthonormality check, so only the determinant
  catches it. Both are asserted.

  The roll about the aimed axis is a convention, not a consequence, and
  the record says so: a direction fixes two of three degrees of freedom.

  Tier G2 is handed the same rotation, not a second one. The frame the
  B-rep back-end builds from it departs by at most
  `1.1102230246251565e-16` in any component, and its measures of the
  thirty placed solids depart from the analytic forms by at most
  `4.0e-16` relative. In tier G1 the corresponding drift over the same
  thirty placements is `5.1e-14` in volume and `1.0e-15` in area.

- Sine and cosine of an angle a source prints (`geometry_unit_circle`,
  ADR 0016). Every angle this library had needed was a rational multiple
  of a turn, which `circle_points` reaches by integer arithmetic without
  ever forming an angle. A filed source prints latitudes instead — one
  device family's node set sits at 20.1, 43.4, 59.0, 80.1, 99.9, 121.0,
  136.6 and 159.9 degrees — and none of those can be reached that way.

  The new path reduces the angle against a three-word split of `pi/2` in
  a fixed operation order and then evaluates **the same two polynomials**.
  The domain is declared and refused at its edge: the quadrant index is
  bounded at `2^21`, measured against the nearest indices at which either
  reduction product stops being exact (5340355 and 4017387).

  **The residue is not strictly bounded by `pi/4`, and the record says
  so** rather than asserting a bound that does not hold. The quotient
  picking the index is formed with a rounded `2/pi`, so the quarter turn
  is passed by one unit in the last place at `pi/4` and by `3.9e-10` at
  the top of the domain — where the result is still accurate to one unit
  in the last place, measured.

  `circle_points` stays the entry point for rings and tessellations, and
  a test measures why the two are not interchangeable: for a
  thirty-member ring only 4 of 30 points come out identical, and the
  exact zeros and ones on the axes belong to the count-based path alone.

  Native parity is bit-exact over a scan of the domain; agreement with
  the platform library is `2.220446049250313e-16` at worst.

- The rectangular prism (`geometry_primitives`, `cad_brep_solids`,
  ADR 0015): the first body in this library that is **not a solid of
  revolution**, and the first that is tessellated exactly rather than
  approximated. It carries no segment count, because there is no
  inscribed approximation to refine, and a test asserts that absence on
  the signature itself.

  Two module descriptions said every body here was a solid of revolution.
  Both are corrected rather than quietly widened, because consuming
  families word their non-claims around them.

  **The evidence bounds could not be reused by analogy.** Measured over
  nine prisms from 1 micrometre to 10 metres and aspect ratios to
  1000:1, at every deflection the back-end accepts: the mesher returns
  8 vertices and 12 triangles every time, no deflection changes any
  measure, and the worst relative volume deviation is 2.581e-16 — falling
  on either side of the analytic value. The chord bound `2 d / r` needs a
  radius a prism has no such thing as, and supplying the half-width gives
  eleven orders of slack; the polygon bound is 0.0997 against a measured
  difference of exactly zero. So a body without curvature declares a
  round-off tolerance of `1e-12` instead — four orders above the measured
  ceiling, three orders below the curved bodies' measure tolerance — and
  a caller states which regime a body is in by passing its smallest
  circular radius or `None`.

### Fixed

- **A malformed mesh row is refused where it is given, not where it is
  eventually unpacked.** `TriangleMesh` checked that coordinates were
  finite and that indices were in range, and left the shape and the types
  of every row to whatever consumed it next. So a vertex with four
  coordinates was constructed, validated and measured, and then failed as
  `struct.error: pack expected 3 items for packing (got 4)` in the
  canonical bytes, the digest, the GLB writer and the summary record; a
  vertex with two failed earlier as `IndexError: tuple index out of
  range`; a coordinate that was a string reached `math.isfinite` as
  `TypeError: must be real number, not str`; and a fractional face index
  reached the vertex list as `TypeError: tuple indices must be integers
  or slices, not float`. **None of them named the field, the row or the
  body, and none was the error type the module documents.**

  Rows are now required to have exactly three components before anything
  indexes or unpacks them; a coordinate must be a real number and finite;
  and an index must satisfy the integer protocol, so an integer from
  another library is accepted while a fractional one is refused rather
  than truncated. A boolean is refused on both streams — it is a real
  number to Python and is neither a coordinate nor an index to anyone
  else — and it is now refused **as a type rather than as a range**,
  which is the honest reason: `True` names vertex one perfectly well.

  **The frozen dataclass is now telling the truth.** Rows given as lists
  were stored as lists, so a mesh that declared itself frozen, slotted
  and hashable raised `TypeError: unhashable type: 'list'` the first time
  anything hashed it, and a caller could still change the geometry from
  outside. Rows are normalised into tuples on construction, so lists are
  accepted, hashing works, and the mesh no longer aliases the caller's
  data.

  **Nothing that was already valid moved.** Every digest of the library's
  twelve fixture bodies and of the fifty bodies of the six device
  families is identical to the committed code, and a mesh built from
  lists, from tuples or from integer coordinates produces the same
  canonical bytes.

  The native boundary was asked the same questions and **was not as
  strict**: it accepted a non-finite coordinate and returned a NaN
  measure, which compares false against every bound it is later checked
  against. It now refuses one by name, in the same words as the Python
  side. Two differences remain and are deliberate, declared and asserted
  so that neither can change quietly: the native entry points take flat
  streams rather than a body, so they carry no four-vertex minimum, and a
  boolean index reaches them through the back-end's own integer
  conversion.

- **A meshing call no longer ends a session it did not start.** The
  volume-mesh kernel called gmsh's `initialize` unconditionally and its
  `finalize` from `finally`, so a consumer that already had a gmsh session
  open lost it — models, options and all — the first time it asked for a
  mesh. **The failure path destroyed exactly as much as the success
  path**: refusing a STEP file with no volume left the caller's session
  just as finalised as meshing one did, which is the half of this the
  reported reproducer does not show.

  Two further consequences of the same assumption were measured while
  repairing it, and neither had been reported:

  - **A caller's options reached the kernel's output.** The kernel sets
    seven options and two mesh sizes and inherited everything else from
    whatever session it ran in, so its documented fixed option set was not
    fixed. A session with `Mesh.RecombineAll` on made it emit pyramids and
    fail its own element-type check. Nine caller options were each
    measured to change the result.
  - **A worker thread could not use it at all.** Opening a gmsh session
    installs an interrupt handler, which CPython allows only on the main
    thread, so the call raised `ValueError: signal only works in main
    thread of the main interpreter` from a module the caller never
    imported.

  ADR 0019 refuses an already initialised session before Gmsh mutation.
  Otherwise the kernel owns a fresh session, disables interrupt-handler
  installation and finalises from finally. Worker-thread calls through
  this module are serialised. Unrelated concurrent Gmsh access requires
  external coordination or process isolation.

  The reviewed borrow-and-restore candidate was rejected because derived
  state could not be fully restored. Real-backend tests confirm no change
  to caller models, options or derived bounding-box state on refusal.

- **An export no longer writes a body it has already destroyed.** Binary
  STL and GLB both store positions as float32, and neither writer looked
  at what that did. A tetrahedron whose four corners are a metre apart, on
  a grid a hundred thousand kilometres from the origin, came back out of
  both containers as **one point and four triangles of zero area** — as
  ordinary bytes, with a valid header, a correct triangle count and a
  correct length. Every test the module had passed on those bytes.

  **The collapse is the end of the damage, not the start of it.** Measured
  on this library's own fixture bodies, of which the annular tube's
  one-centimetre wall is the finest: past **sixty-four metres** of offset
  more than a thousandth of a facet's area is already gone; at ten
  kilometres the tube has lost a tenth of it and at a hundred kilometres a
  third — with every triangle still a triangle and nothing to see. Only
  past two hundred kilometres does anything collapse. A check for
  degenerate triangles alone would have passed all of it.

  Both writers now measure the geometry they are about to store and refuse
  one that has lost more than `EXPORT_AREA_TOLERANCE`, one part in a
  thousand, of any facet's area, or that has collapsed a facet, or that
  carries a coordinate outside the float32 range. **The tolerance was
  chosen from the bodies that exist**: across the fifty bodies of the six
  device families that use these writers the worst measured loss is
  `5.61e-6` and this library's own fixtures sit at `7.7e-7`, so the bound
  is about a hundred and eighty times above anything real. It cannot be
  tightened much further either, because a rebased body is no better than
  the same body at the origin and the tube is already at `7.2e-7` there.

  The two containers then differ in what they can offer instead, and the
  difference is a property of the formats:

  - **GLB has a node transform.** A body that does not survive absolute
    storage is stored about the midpoint of its own bounding box, with
    that midpoint in the node's `translation`. The body does not move —
    a glTF node's translation composes with its mesh — so nothing is
    moved silently, and the tetrahedron above comes back at a **hundred
    million times** its previous usable offset with its areas intact.
  - **Binary STL has no transform of any kind**, so rebasing one really
    would move the device. The writer refuses instead and names the
    translation that would work, which a caller passes explicitly through
    the new `translation_m` argument and is then responsible for
    recording, because the file cannot.

  A refusal only names a remedy once that remedy has been measured on the
  bodies that were refused; if the recommended midpoint fails, the writer
  reports that failure without claiming that every translation fails.

  **The rebase is an ordinary double, and the two cheaper rules were
  measured and rejected.** Rounding the translation to a float32 first
  costs `8.0e-2` at an offset of `1e12`; snapping it to a power of two is
  worse and collapses facets from `1e6` upwards. The bounding-box midpoint
  leaves a rebased body exactly as accurate as the same body at the
  origin, `7.17e-7` at every offset measured.

  A coordinate above the float32 range used to escape as `OverflowError`
  from the standard library, naming neither the body nor the vertex; it is
  now a `GeometryError` that names both. The range is checked before
  anything is converted, because the conversion itself is what raised.

  **Nothing that was already right moved.** Every export of this library's
  four fixture sets and of all fifty bodies of the six device families is
  byte-for-byte identical to the bytes the previous writer produced, and
  each of those six repositories' own export tests passes against the
  repaired writer unchanged.

- **A measure the format can hold is no longer thrown away by its own
  intermediates.** The surface area squared each cross-product component
  before taking a square root, so the sum of squares left the exponent
  range long before the answer did. At a coordinate scale of `1e100` the
  exact area is `2.37e200` — comfortably inside a double — and the whole
  area came back as infinity. The same defect at the other end was worse
  than a wrong number: far enough down, the squares fell to zero, the
  norm with them, and a perfectly ordinary triangle was **refused as
  degenerate** with the same message a genuinely collinear one gets.

  Measured on the library's tetrahedron, the range that gave a correct
  area ran from a scale of `9.543299509722758e-79` to
  `8.798296151866603e+76`. It now runs from `2.222758749485082e-162` to
  `8.716619296087305e+153`, and one unit in the last place beyond that
  the area genuinely does not fit and is refused by name. **About 160
  orders of magnitude of representable results were being discarded.**

  The norm is now rescaled by the largest component, but **only where the
  direct sum of squares would fail** — it is kept wherever it lands on a
  finite normal double, as checked on ordinary-scale fixtures. Measured over
  3660 face norms and five body areas of the library's own bodies,
  **nothing that was already right moved by a single bit.** Rescaling by
  a power of two instead would make the scaling exact and was measured
  alongside at `9.94e-17` against `1.19e-16` worst relative error over
  sixty vectors spanning the double range; it was not adopted, because
  the native kernel's standard library has no `ldexp` and reimplementing
  one is more surface for the two languages to disagree on than a sixth
  of a rounding unit is worth.

  Where the answer is itself subnormal a relative tolerance stops
  meaning anything — an area of `3e-323` carries about three bits — so
  the claim there is in units of the last place: within one ulp, and
  measured at `0.50000000000010` ulp over sixty consecutive subnormal
  scales.

  **A measure that genuinely does not fit is now refused rather than
  returned.** It reaches `summary_record` and from there a JSON document
  with no way to write it. Note the failure mode: after the volume
  repair above, an overflowing volume arrives as a **NaN** rather than an
  infinity, because the compensated summation adds a positive and a
  negative overflow — and a NaN satisfies every bound it is compared
  against. Both are refused, naming the body and the measure.

- **A mesh far from the origin no longer loses its volume.** The signed
  volume was summed over products of absolute coordinates. The
  divergence theorem is exactly translation-invariant in real arithmetic
  and catastrophically is not in floating point: each term grows with the
  square of the distance to the origin while the total does not, so a
  body away from the origin was measured as a difference of large
  numbers.

  Measured on this library's own bodies, the previous form was wrong by
  **3 % at an offset of 10 km**, by four orders of magnitude at
  1000 km, and returned **exactly zero** for a unit tetrahedron moved to
  `(-1e8, 1e8, -1e8)` — a body with no volume and no complaint. Against
  the exact rational value of the same meshes its worst relative error
  over the cases measured was `1.26e9`.

  The sum is now taken about the mesh's own first vertex and accumulated
  with a compensation, in an operation order that is part of the contract
  because the parity tests compare bit patterns. Worst relative error
  against the exact rational value, over four body families at five
  offsets: **`5.8e-16`**. The first vertex is the origin rather than a
  bounding-box midpoint because it needs no arithmetic of its own and the
  native kernel reads the same bits; the midpoint was measured alongside
  it at `4.22e-16`, which does not buy the extra surface for two
  languages to diverge on.

  How much a measure moves when the *geometry* is translated is a
  separate quantity that no accumulation can improve, since translating a
  mesh rounds every coordinate at the new magnitude. The measured fixtures are compared with
  `3 * ulp(offset) / L` at the body's smallest feature `L`, and measured
  at a tenth of that bound.

  **This changes a kernel's output for valid inputs and is therefore a
  breaking change of the mesh measure.** Every existing body's volume
  moves in its last bits — measured between `6.5e-16` and `2.9e-14`
  relative on a consuming family's five bodies — and the movement is
  towards the exact value, being the size of the error the previous form
  carried. Any consumer record that embeds a volume changes digest: both
  device-state digests of the consuming family measured here move.
  Consumers must regenerate their fixture digests when they move their
  pin.

- **A body's evidence can no longer certify itself.** Every bound in
  `cad_evidence` was a bare comparison against a value the caller
  supplied, and a bare comparison is not a check. Four records that
  describe nothing were accepted: a relative error of `nan`, which
  compares `False` against a bound and against its negation at once and
  so satisfied both; a relative error of `-1.0`, which passes any *must
  not exceed* test whatever the geometry did; a declared bound of `nan`,
  which admitted a deficit of `1e100`; and a B-rep volume a hundred times
  its analytic form standing beside a claimed error of exactly zero,
  because the claim was never confronted with the measures it claims to
  describe.

  The record now proves each field finite before comparing it, proves
  each measure a ratio is taken against strictly positive, proves each
  magnitude not negative, and **recomputes all four derived quantities
  from its own raw measures**; a supplied value must equal what its
  measures give, and the bounds are then compared against the recomputed
  values rather than the supplied ones. The equality is exact and no
  allowance is granted, which is a measurement rather than a preference:
  the recomputation uses the same expressions in the same arithmetic
  order as the library computes them in, and on the curved and planar
  bodies of this library it reproduces every supplied value bit for bit.
  A recomputed ratio that overflows to infinity — possible from finite
  measures with a positive denominator — is refused as well.

  `body_evidence` now also checks that the B-rep body, its faceting and
  the reference mesh **are the same body** before comparing any of their
  measures. Measures do not carry identity, and the assembly form zips
  four sequences in one fixed order, which is exactly where a body can be
  paired with its neighbour's mesh and produce a small difference that
  certifies nothing.

  No valid record's values change; the change is a refusal where there
  was none. Every consumer that already builds evidence through
  `body_evidence` and `assembly_evidence` is unaffected, and a consumer
  constructing `BodyEvidence` directly must now supply measures its
  errors agree with.

- The faceted-volume deviation is compared **in magnitude** rather than
  one-sidedly. A faceted volume arbitrarily *larger* than its analytic
  form previously passed without comment. No curved body's evidence
  changes — an inscribed faceting always undershoots — so this is a
  strict tightening; it surfaced only because a prism's deviation is
  signed.

- Spherical bodies `geometry_spheres`
  (`src/scpn_reactor_kernels/geometry/spheres.py`, ADR 0013): the sphere's
  axial profile, sampled uniformly in polar angle from the first half turn of
  `circle_points` on twice the ring count, so the poles land on exactly
  `centre ± radius` with a radius of exactly zero and every coordinate is
  bit-identical to the native kernel; the named composition that revolves it;
  and the spherical shell, which is not a tube between aligned profiles and
  could not be built as one. The angular sampling was chosen by measurement:
  its volume deficit falls as the square of the ring count, the ratio between
  successive doublings running 3.990, 3.998, 3.999, 4.000. No ideal-sphere
  closed forms are exposed — these bodies are inscribed polyhedra, and the
  library already gives the exact volume of the body actually built.
- B-rep spherical bodies `cad_spheres`
  (`src/scpn_reactor_kernels/cad/spheres.py`, ADR 0014): the tier-G2 twins.
  The shell's generating polyline touches the axis along two segments, where
  the cavity's poles sit inside the outer body, and there is no way to bound
  the region without them; the back-end was measured to revolve it exactly,
  the volume equalling the difference of the two frustum stacks with a
  relative error of zero at sixteen rings.

### Changed

- The revolve helper of `cad.profiles` is shared with `cad.spheres` and lost
  its leading underscore for that reason. It is still not part of the
  package's public surface.
- Both benchmarks gained the new bodies and were rerun; the recorded results
  and the tables in `docs/benchmarks.md` are refreshed rather than carried
  over. The tessellation pass is larger than the previous run by the shell,
  so the two are not comparable row by row, and the record says so.


- CAD axial profile kernel `cad_profiles`
  (`src/scpn_reactor_kernels/cad/profiles.py`, ADR 0011): the tier-G2 twin of
  `geometry_profiles`, revolving the closed polyline through the profile's
  samples about the axis. The profile contract is not restated but imported:
  the same validators, the same rules, the same messages, surfacing under the
  CAD error type, so a caller who moves a profile between tiers meets one
  contract rather than two that could drift. The analytic references are the
  tier-G1 frustum-stack closed forms plus the end discs or annuli, exact for a
  linear profile, and the back-end agrees with them to `1e-16` on the solid
  and `2e-15` on the tube against a `1e-9` tolerance. A test proves the two
  tiers describe one body: faceting the revolved solid agrees in volume with
  the tessellated mesh of the same profile within the exact polygon deficit.
  The CAD benchmark gains `revolve_axial_profile`; a revolution costs about
  three times an extrusion, which is the price of a shape an extrusion cannot
  express.

- Axial profile kernel `geometry_profiles`
  (`src/scpn_reactor_kernels/geometry/profiles.py`, ADR 0010): surfaces of
  revolution through a sampled `(z, radius)` profile — a closed solid, a
  closed tube between two aligned profiles, and the exact frustum-stack
  closed forms of the resulting body. Every tier-G1 primitive so far built a
  body of constant radius; a magnetic mirror confines a flux tube, whose
  radius is a function of the field along the axis, and the filed source for
  that family prints a plasma radius and a magnet bore that a body of
  constant radius cannot satisfy at the same time. The surface passes exactly
  through the samples it is given and is linear between them: the kernel
  interpolates nothing beyond that, so a record built on it can say what the
  surface is without appealing to an undeclared smoothing rule. The
  generalisation is exact — a two-sample profile of constant radius
  reproduces `cylinder_solid` vertex for vertex, and a pair of them
  `annular_tube` — so no pinned digest moves for a shape that did not change.
  The tessellated volume differs from the closed form by exactly the
  inscribed-polygon deficit of the segment count, asserted as an equality
  rather than a bound. The native crate mirrors both primitives and both
  closed forms with bit-pattern parity, and the geometry benchmark
  tessellates a varying body in the same pass. The kernel inventory gains the
  entry and its digest changes accordingly.

### Fixed

- Bounding box of a B-rep body (`cad/solids.py`): the kernel's optimal box
  consults an attached triangulation by default, so once a body had been
  faceted its recorded box became the box of the faceted approximation —
  looser by the mesher's deflection — and every assembly manifest digest
  taken after a faceting differed from one taken before, for the same
  geometry and with nothing in the record saying why. The box is now taken
  from the geometry alone, without the triangulation and without the shape
  tolerance, so it is the exact box and does not depend on whether an
  unrelated kernel has run over the body (regression test in
  `tests/test_cad_solids.py`). Found while building the second tier-G2
  device model, whose placement identities are read from these boxes.
  Consumers that pin a manifest or model digest containing bounding boxes
  re-pin it when they re-pin the library: this is a governed data change.

- STEP export normalisation (`cad/step.py`): the OpenCASCADE writer wraps
  long lines onto indented continuation lines at a column counted from the
  pre-renumbering usage-occurrence identifier lengths, so once the
  process-wide counter crossed a digit boundary the renumbered exports
  still differed in their wrap positions (found with a six-body assembly
  exported twice in one process). The normaliser now unfolds the writer's
  continuation lines before renumbering; repeated exports of a six-body
  assembly and an export after an in-process STEP import are byte-identical
  (regression test in `tests/test_cad_step.py`).

### Added

- CAD body evidence kernel `cad_evidence`
  (`src/scpn_reactor_kernels/cad/evidence.py`, ADR 0009): the fail-closed
  record of one B-rep body against its analytic closed forms, the
  chord-deficit bound of its faceting and the tier-G1 mesh of the same body,
  plus the assembly form that keeps the body order. It refuses at
  construction — a violated bound raises with the body and the bound named —
  and refuses a ragged input rather than zipping four sequences of different
  lengths into a short answer. The machinery was written once inside a device
  repository; none of it is device knowledge, and keeping it there would have
  copied the same two hundred lines into every family that gains a CAD model,
  with nothing forcing the copies to stay equal. A family now writes its
  schema identity, its body composition and its non-claims, and consumes the
  evidence. The pilot family's copy is recorded in ADR 0009 as a second
  implementation scheduled to migrate; the library is the reference. The CAD
  benchmark gains `assembly_body_evidence`.

- CAD placement kernel `cad_placement`
  (`src/scpn_reactor_kernels/cad/placement.py`, ADR 0008): the tier-G2
  counterpart of `geometry_placement`. `translate_brep` places a B-rep body
  by a rigid translation and may rename it; `ring_brep_bodies` places one
  body once per centre of a ring, on the tier-G1 `ring_offsets`, so both
  tiers of a family sit on the same circle by construction. The analytic
  closed forms are carried over exactly and the placed solid's own measures
  are checked against them within the group's `1e-9` tolerance; the record
  and a test state the boundary rather than assuming it — OpenCASCADE
  integrates over the moved surface, so its volume of a placed solid is not
  bit-identical to its volume of the source solid, and on a ring of twelve
  identical rods the measured volumes differ in the last unit in the last
  place. Cross-tier evidence: faceting a placed solid agrees in volume with
  the tier-G1 mesh of the same body translated by the same offset, within
  the exact inscribed-polygon deficit bound. The CAD benchmark gains
  `place_ring_of_bodies` and the whole CAD table was re-measured on the
  landing tree. The kernel inventory gains the entry and its digest changes
  accordingly.

- Placement kernel `geometry_placement`
  (`src/scpn_reactor_kernels/geometry/placement.py`, ADR 0007): exact
  translation of a vertex stream, the centres of `count` identical bodies
  equally spaced on a circle around the axis, and the centre-to-centre
  distance of neighbours on that ring. A device repository can now carry a
  part that is not axisymmetric — the rods of a squirrel-cage cathode, a ring
  of feed conductors — without re-implementing geometry or substituting an
  axisymmetric body for it. The vendored circle is generalised in the same
  record: `circle_points(count)` serves any count of at least three and
  `unit_circle(segments)` becomes the tessellation entry point over the same
  points, which a test proves is bit-identical for every tessellation count,
  so no reference digest a consumer pins changes. The native crate mirrors
  both and the parity file compares bit patterns for counts 3 to 257, for the
  ring offsets and separation, and for a translated body; the geometry
  benchmark places a ring of twelve rods in the same pass so the kernel is
  measured on both backends. The kernel inventory gains the entry and its
  digest changes accordingly.

- CAD kernels (`src/scpn_reactor_kernels/cad/`, kernels `cad_brep_solids`,
  `cad_step_export`, `cad_faceting`, `cad_volume_mesh`, ADR 0006) behind
  the optional extra `cad` (`cadquery==2.8.0`, `gmsh==4.15.2`): B-rep
  solids of the cylinder and the annular tube with analytic reference
  measures and a `1e-9` tolerance, an ordered `BrepAssembly` with a
  canonical manifest and digest, deterministic STEP export (fixed header
  time stamp and file name, renumbered assembly usage identifiers, JSON
  provenance in the description), faceting into the `TriangleMesh`
  contract with the `2 d / r` deficit bound and the exact inscribed-polygon
  ratio, and a gmsh MSH 4.1 volume mesh summarised per entity against the
  B-rep volumes; lazy back-end loading with a named refusal; the library
  CI installs the extra; a standard-conformant benchmark with a committed
  local artefact. New owned domain `shared_cad_and_meshing_adapters`.
  Evidence class stated: third-party kernels, no bit-exact parity,
  determinism per environment only.

- Bessel kernels (`src/scpn_reactor_kernels/numerics/bessel.py`, kernel
  `numerics_bessel`, ADR 0005): `J0` and `J1` by the DLMF 10.2.2 ascending
  series in Horner form with exact integer-quotient coefficients, thirty
  terms, on the declared domain `|x| <= 8` (refused beyond, never
  clamped); the first zeros `j_{0,1}` and `j_{1,1}` as the correctly
  rounded OEIS expansions; verified against an exact rational evaluation
  of the same series; native kernels in `rust/src/numerics/bessel.rs`
  with scalar and stream bindings proven bit-exact by parity tests; a
  standard-conformant benchmark with a committed local artefact.

### Changed

- Native surface documentation is now a compiler gate, not a habit: the crate
  denies `missing_docs`, `missing_debug_implementations` and `unsafe_code`, and
  denies rustdoc's broken and private intra-doc links and invalid Rust code
  blocks. `cargo doc --no-deps` joins the local `rust` target and the hosted
  `rust` job, so a public item that ships without documentation fails the build
  rather than accumulating as debt for the next reader.

- First consumer recorded (ADR 0004): SCPN-Z-PINCH-CORE pins the
  distribution at `0.1.0.dev0` and the kernel-inventory digest of the
  commit it depends on, consuming the four geometry kernels; the
  `consumers` table of `kernels-domain.json` and the generated inventory
  carry the entry. The README states that a consumer's digest names the
  inventory at the pinned commit, since recording the consumer changes
  the inventory.
- Second consumer recorded: SCPN-MIRROR-CORE pins the same commit and
  inventory digest for the numerics kernel `numerics_transcendental`; its
  native crate depends on `scpn-reactor-kernels-rs` as a git dependency
  at that commit, the first use of the Rust crate as a library.
- Third consumer recorded: SCPN-DENSE-PLASMA-FOCUS-CORE retired its
  byte-identical copy of the numerics kernel for the same pin.
- Fourth consumer recorded: SCPN-RFP-CORE pins the commit that introduced
  the Bessel kernel `numerics_bessel` and its inventory digest, the first
  consumer of that kernel; its native crate depends on the Rust crate at
  that commit.
- Fifth consumer recorded: SCPN-SPHEROMAK-CORE pins the same commit for
  the Bessel kernel and the unit-circle kernel (its axial phases), the
  first device consumer of `geometry_unit_circle` outside a mesh.

### Added

- Repository established as the shared kernel library of the SCPN Reactor
  Systems Research Group: kernel manifest `kernels-domain.json` (schema
  `scpn.reactor-kernels-domain.v1`) with a fail-closed validator, generated
  kernel inventory with drift check, workflow modularity guard, preflight
  orchestrator, uniform gate and workflow surfaces (ADR 0001).
- Geometry kernels (`src/scpn_reactor_kernels/geometry/`), the first
  implemented kernel group at `computational_prototype` (ADR 0002): a
  vendored deterministic unit circle, the closed-mesh contract
  (`TriangleMesh`), solid-cylinder and annular-tube tessellation, binary
  STL and glTF 2.0 binary exports of any body list, native kernels in
  `rust/` proven bit-exact by parity tests, and a standard-conformant
  benchmark with a committed local artefact.
- Numerics kernels (`src/scpn_reactor_kernels/numerics/`), the second
  implemented kernel group at `computational_prototype` (ADR 0003): a
  vendored deterministic natural logarithm, exponential and real power
  with refused (never clamped) domains, measured accuracy bounds against
  the platform `math` module, native kernels in `rust/` with scalar and
  stream bindings proven bit-exact by parity tests, and a
  standard-conformant benchmark with a committed local artefact.


### Breaking development generation 1.0.0.dev0

The Python floor and native distribution advance together; the Rust crate
uses `1.0.0-dev.0`. Existing consumer pins and version records remain unchanged.
The mesh volume contract changes valid results and digests; CAD evidence now
rejects nonfinite and inconsistent records. Consumers need a reviewed pin
migration with regenerated evidence.

Power-of-two fallback scaling recovers representable areas and volumes even
when cross products, determinant terms or twice the final area overflow.
Public triangle measurements refuse nonfinite outputs; normal-range paths
retain their arithmetic order. Subnormal area totals are accumulated at scale
before the final rounding. The draft's half-range ceiling is superseded by
final-quantity checks with rational and Decimal oracles.


### Breaking development generation 2.0.0.dev0

Geometry export and constructor refusals, together with the Gmsh ownership
contract, advance the Python and native packages to 2.0.0.dev0 (Rust
2.0.0-dev.0). Consumer pins stay unchanged pending explicit adoption.

The reviewed borrowing design for Gmsh is superseded: existing sessions are
refused without mutation. Owned sessions disable signal-handler installation,
so worker-thread callers can mesh without touching a caller's session. Tests
exercise real Gmsh cleanup and preserve derived caller state on refusals.

The upper mesh-area threshold now has an exact-neighbour regression backed by
an independent Decimal oracle. Overlarge integer coordinates are refused with
GeometryError. Export midpoint guidance states only the measured heuristic;
changing units is not presented as a cure for relative float32 precision loss.
