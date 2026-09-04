# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# SCPN Reactor Kernels — arbitrary-angle trigonometry tests

"""The reduction, its declared domain, and why two entry points exist.

The count-based :func:`circle_points` and the angle-based
:func:`circle_point` are not interchangeable, and the tests that say so
are the point of this module: the first returns exact zeros and ones on
the axes because it never forms an angle, and the second cannot, because
the angle a caller hands it is not exactly a quarter turn.
"""

from __future__ import annotations

import math
from fractions import Fraction

import pytest

from scpn_reactor_kernels.errors import GeometryError
from scpn_reactor_kernels.geometry.trig import (
    DEGREES_PER_HALF_TURN,
    MAX_ANGLE_RAD,
    MAX_QUADRANT_INDEX,
    PIO2_A,
    PIO2_B,
    PIO2_C,
    circle_point,
    circle_points,
    cosine,
    quadrant_reduction,
    radians_from_degrees,
    require_reducible_angle,
    sine,
)

#: Measured worst absolute difference from the platform library over the
#: whole declared domain: one unit in the last place of one.
LIBM_TOLERANCE = 2.220446049250313e-16

#: The eight latitudes a filed source prints for a node set on a sphere,
#: in degrees. They are here because they are not rational multiples of a
#: turn, which is the case this kernel exists for.
PRINTED_LATITUDES_DEG = (20.1, 43.4, 59.0, 80.1, 99.9, 121.0, 136.6, 159.9)

#: Measured coefficient of the residue overshoot: scanned at the
#: half-quadrant points across the whole domain, the residue exceeds
#: ``pi/4`` by at most this much per radian of angle.
RESIDUE_EXCESS_PER_RADIAN = 1.2e-16

#: ``pi`` to fifty digits, as an exact rational, so the three-word split
#: can be checked against the real constant rather than against its
#: double.
TRUE_PI = Fraction(31415926535897932384626433832795028841971693993751, 10**49)


def _exact_product(index: int, word: float) -> bool:
    """Return whether ``index * word`` carries no rounding error."""
    return Fraction(index) * Fraction(word) == Fraction(index * word)


def test_half_a_turn_in_degrees_is_pi_exactly() -> None:
    """``(180 * pi) / 180`` returns the same double as ``pi``."""
    assert radians_from_degrees(DEGREES_PER_HALF_TURN) == math.pi
    assert radians_from_degrees(0.0) == 0.0
    assert radians_from_degrees(-DEGREES_PER_HALF_TURN) == 0.0 - math.pi


def test_the_degree_conversion_is_one_product_and_one_quotient() -> None:
    """The operation order is fixed, so the native kernel repeats it."""
    for degrees in (20.1, 43.4, 59.0, 159.9, 1.0e5, -359.99):
        assert radians_from_degrees(degrees) == (degrees * math.pi) / 180.0


@pytest.mark.parametrize("degrees", [math.nan, math.inf, -math.inf])
def test_the_degree_conversion_refuses_a_non_finite_angle(degrees: float) -> None:
    """A non-finite angle is refused, never propagated."""
    with pytest.raises(GeometryError):
        radians_from_degrees(degrees)


def test_the_three_words_sum_to_the_double_pi_over_two() -> None:
    """The split reconstructs ``pi/2`` and its remainder is negligible.

    The first two words carry trailing zero mantissa bits so their
    products with a quadrant index stay exact; the third carries what is
    left, and what is left beyond all three is far below the precision of
    any result.
    """
    assert math.pi / 2.0 == PIO2_A + PIO2_B + PIO2_C
    remainder = TRUE_PI / 2 - (Fraction(PIO2_A) + Fraction(PIO2_B) + Fraction(PIO2_C))
    assert abs(remainder) < Fraction(1, 10**30)
    assert abs(TRUE_PI / 2 - Fraction(PIO2_A)) > Fraction(1, 10**11)


def test_the_products_of_the_reduction_are_exact_across_the_domain() -> None:
    """The domain is chosen for this property, so it is asserted, not assumed."""
    indices = [0, 1, 2, 3, 255, 4096, 1048575, MAX_QUADRANT_INDEX]
    for index in indices:
        assert _exact_product(index, PIO2_A)
        assert _exact_product(index, PIO2_B)


def test_the_nearest_indices_that_break_exactness_lie_outside_the_domain() -> None:
    """Measured, not assumed: the first failures are far above the bound.

    ``PIO2_A`` first multiplies inexactly at 5340355 and ``PIO2_B`` at
    4017387, both above :data:`MAX_QUADRANT_INDEX`. A domain that reached
    either would silently lose the exactness the reduction rests on.
    """
    assert not _exact_product(5340355, PIO2_A)
    assert _exact_product(5340354, PIO2_A)
    assert not _exact_product(4017387, PIO2_B)
    assert _exact_product(4017386, PIO2_B)
    assert MAX_QUADRANT_INDEX < 4017387


def test_the_domain_accepts_its_edge_and_refuses_the_next_double() -> None:
    """The nearest failing case, not a comfortable one."""
    assert require_reducible_angle(MAX_ANGLE_RAD) == MAX_ANGLE_RAD
    assert require_reducible_angle(0.0 - MAX_ANGLE_RAD) == 0.0 - MAX_ANGLE_RAD
    with pytest.raises(GeometryError):
        require_reducible_angle(math.nextafter(MAX_ANGLE_RAD, math.inf))
    with pytest.raises(GeometryError):
        require_reducible_angle(math.nextafter(0.0 - MAX_ANGLE_RAD, -math.inf))


@pytest.mark.parametrize("angle", [math.nan, math.inf, -math.inf])
def test_the_domain_refuses_a_non_finite_angle(angle: float) -> None:
    """A non-finite angle is refused before the reduction runs."""
    with pytest.raises(GeometryError):
        quadrant_reduction(angle)
    with pytest.raises(GeometryError):
        sine(angle)
    with pytest.raises(GeometryError):
        cosine(angle)


def test_the_index_at_the_edge_of_the_domain_is_the_declared_maximum() -> None:
    """The bound on the angle is the bound on the index it produces."""
    index, residue = quadrant_reduction(MAX_ANGLE_RAD)
    assert index == MAX_QUADRANT_INDEX
    assert abs(residue) <= math.pi / 4.0 + MAX_ANGLE_RAD * RESIDUE_EXCESS_PER_RADIAN


@pytest.mark.parametrize("scale", [0.0, 0.25, 1.0, 7.5, -3.25, 1000.5, -99999.75])
def test_the_residue_stays_inside_the_measured_bound(scale: float) -> None:
    """The bound is ``pi/4`` plus a term that grows with the angle.

    A strict ``pi/4`` is the bound the reduction would have if the
    quotient that picks the index were exact. It is not, so at a
    half-quadrant the index can be the neighbour of the nearest one; the
    quarter turn is passed, and by how much is measured rather than
    hoped for.
    """
    angle = scale * math.pi
    index, residue = quadrant_reduction(angle)
    allowance = math.pi / 4.0 + abs(angle) * RESIDUE_EXCESS_PER_RADIAN
    assert abs(residue) <= allowance
    assert index == math.floor(angle * (2.0 / math.pi) + 0.5)


def test_the_quarter_turn_itself_overshoots_by_one_unit_in_the_last_place() -> None:
    """The smallest case of the overshoot, asserted rather than smoothed away.

    A tie rounds upward, so ``pi/4`` reduces against the *second*
    quadrant and its residue is the negative quarter turn — whose
    magnitude is one unit in the last place above ``math.pi / 4``.
    """
    index, residue = quadrant_reduction(math.pi / 4.0)
    assert index == 1
    assert residue < 0.0
    assert abs(residue) > math.pi / 4.0
    assert abs(residue) == math.nextafter(math.pi / 4.0, math.inf)


def test_the_worst_residue_of_the_domain_is_still_accurate() -> None:
    """At the largest overshoot the result is still within one ulp.

    Scanned at the half-quadrant points of the whole domain, the largest
    residue is about ``pi/4 + 3.9e-10``. The polynomials are evaluated
    there anyway, and that is the measurement which says the overshoot
    costs nothing.
    """
    angle = 3290522.209527707
    _, residue = quadrant_reduction(angle)
    assert abs(residue) > math.pi / 4.0
    assert abs(residue) - math.pi / 4.0 == pytest.approx(3.86e-10, rel=1.0e-2)
    cosine_value, sine_value = circle_point(angle)
    assert abs(cosine_value - math.cos(angle)) <= LIBM_TOLERANCE
    assert abs(sine_value - math.sin(angle)) <= LIBM_TOLERANCE


@pytest.mark.parametrize("quarter", range(-4, 5))
def test_every_quadrant_is_placed_correctly(quarter: int) -> None:
    """All four branches of the placement are exercised and correct."""
    angle = quarter * (math.pi / 2.0)
    cosine_value, sine_value = circle_point(angle)
    assert cosine_value == pytest.approx(math.cos(angle), abs=LIBM_TOLERANCE)
    assert sine_value == pytest.approx(math.sin(angle), abs=LIBM_TOLERANCE)


def test_the_accessors_return_the_members_of_the_point() -> None:
    """``sine`` and ``cosine`` are the two members and nothing else."""
    for degrees in PRINTED_LATITUDES_DEG:
        angle = radians_from_degrees(degrees)
        cosine_value, sine_value = circle_point(angle)
        assert cosine(angle) == cosine_value
        assert sine(angle) == sine_value


@pytest.mark.parametrize("degrees", PRINTED_LATITUDES_DEG)
def test_a_printed_latitude_tracks_the_platform_library(degrees: float) -> None:
    """The angles this kernel exists for agree to one unit in the last place."""
    angle = radians_from_degrees(degrees)
    cosine_value, sine_value = circle_point(angle)
    assert abs(cosine_value - math.cos(angle)) <= LIBM_TOLERANCE
    assert abs(sine_value - math.sin(angle)) <= LIBM_TOLERANCE


def test_the_scan_across_the_domain_stays_within_one_unit_in_the_last_place() -> None:
    """A scan, not a sample: the bound is measured over the whole range."""
    steps = 4001
    worst = 0.0
    for step in range(steps):
        angle = 0.0 - MAX_ANGLE_RAD + 2.0 * MAX_ANGLE_RAD * step / (steps - 1)
        cosine_value, sine_value = circle_point(angle)
        worst = max(
            worst,
            abs(cosine_value - math.cos(angle)),
            abs(sine_value - math.sin(angle)),
        )
    assert worst <= LIBM_TOLERANCE


def test_the_identity_holds_across_the_domain() -> None:
    """``cos^2 + sin^2`` stays at one, which no reduction error survives."""
    for step in range(-500, 501):
        angle = step * 137.0
        cosine_value, sine_value = circle_point(angle)
        assert abs(cosine_value * cosine_value + sine_value * sine_value - 1.0) <= (
            4.0 * LIBM_TOLERANCE
        )


def test_the_count_based_circle_is_exact_on_the_axes_and_this_one_is_not() -> None:
    """The reason both entry points exist, stated as an assertion.

    ``circle_points`` never forms an angle, so a point on an axis is
    exactly zero and one. ``circle_point`` is handed a double that is not
    exactly a quarter turn, so its cosine there is the cosine of the
    double it was given — which is right, and is not zero.
    """
    assert circle_points(4) == ((1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0))
    quarter_cosine, quarter_sine = circle_point(math.pi / 2.0)
    assert quarter_cosine != 0.0
    assert abs(quarter_cosine) <= LIBM_TOLERANCE
    assert quarter_sine == 1.0


@pytest.mark.parametrize("count", [3, 5, 8, 10, 12, 30])
def test_the_two_entry_points_agree_numerically_but_not_bit_for_bit(
    count: int,
) -> None:
    """Measured: they agree to a few units in the last place, and no further.

    A consumer that needs the members of one ring uses ``circle_points``
    and gets bodies whose azimuths are exactly symmetric. Reaching the
    same ring through ``circle_point`` would give a set that differs in
    the last places and is no longer exactly symmetric, which is why the
    ring kernels call the first and never the second.
    """
    identical = 0
    for index, (exact_cosine, exact_sine) in enumerate(circle_points(count)):
        angle = 2.0 * math.pi * index / count
        approximate_cosine, approximate_sine = circle_point(angle)
        assert abs(exact_cosine - approximate_cosine) <= 4.0 * LIBM_TOLERANCE
        assert abs(exact_sine - approximate_sine) <= 4.0 * LIBM_TOLERANCE
        if (exact_cosine, exact_sine) == (approximate_cosine, approximate_sine):
            identical += 1
    assert identical < count
