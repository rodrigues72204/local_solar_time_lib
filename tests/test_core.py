"""Tests for local_solar_time_lib.core.

Every test is deterministic: no wall-clock reads, no sleeps, and float
comparisons use an explicit tolerance.
"""

import math
import unittest
from datetime import datetime, timedelta, timezone

from local_solar_time_lib import (
    EquationOfTime,
    SolarTime,
    equation_of_time_minutes,
    local_apparent_solar_time,
    local_mean_solar_time,
    time_offset_minutes,
)


class TimeOffsetTests(unittest.TestCase):
    def test_on_standard_meridian_is_zero(self):
        self.assertEqual(time_offset_minutes(0.0, 0.0), 0.0)
        self.assertEqual(time_offset_minutes(15.0, 15.0), 0.0)

    def test_east_is_positive(self):
        # One degree east of the meridian is four minutes ahead.
        self.assertAlmostEqual(time_offset_minutes(1.0, 0.0), 4.0)
        self.assertAlmostEqual(time_offset_minutes(15.0, 0.0), 60.0)

    def test_west_is_negative(self):
        self.assertAlmostEqual(time_offset_minutes(-1.0, 0.0), -4.0)
        self.assertAlmostEqual(time_offset_minutes(-75.0, -75.0), 0.0)

    def test_fractional_longitude(self):
        self.assertAlmostEqual(time_offset_minutes(0.5, 0.0), 2.0)


class EquationOfTimeTests(unittest.TestCase):
    def test_known_mid_february_minimum(self):
        # The equation of time reaches roughly -14 minutes around 11 February.
        value = equation_of_time_minutes(42)
        self.assertLess(value, -13.0)
        self.assertGreater(value, -15.0)

    def test_known_early_november_maximum(self):
        # Around 3 November the equation of time peaks near +16 minutes.
        value = equation_of_time_minutes(307)
        self.assertGreater(value, 15.0)
        self.assertLess(value, 17.0)

    def test_zero_crossings_in_april_and_june(self):
        # The approximation crosses zero three times; April and June are the
        # two easiest to pin down without depending on a precise calendar.
        self.assertLess(abs(equation_of_time_minutes(105)), 1.0)
        self.assertLess(abs(equation_of_time_minutes(165)), 1.0)

    def test_day_one_is_accepted(self):
        value = equation_of_time_minutes(1)
        self.assertTrue(math.isfinite(value))

    def test_day_366_is_accepted(self):
        value = equation_of_time_minutes(366)
        self.assertTrue(math.isfinite(value))

    def test_out_of_range_days_raise(self):
        with self.assertRaises(ValueError):
            equation_of_time_minutes(0)
        with self.assertRaises(ValueError):
            equation_of_time_minutes(367)


class LocalMeanSolarTimeTests(unittest.TestCase):
    def test_east_of_meridian_runs_ahead(self):
        standard = datetime(2024, 3, 20, 12, 0, 0)
        got = local_mean_solar_time(standard, 15.0, 0.0)
        self.assertEqual(got, standard + timedelta(minutes=60.0))

    def test_west_of_meridian_runs_behind(self):
        standard = datetime(2024, 3, 20, 12, 0, 0)
        got = local_mean_solar_time(standard, -15.0, 0.0)
        self.assertEqual(got, standard - timedelta(minutes=60.0))

    def test_result_carries_across_midnight(self):
        standard = datetime(2024, 3, 20, 0, 30, 0)
        got = local_mean_solar_time(standard, -120.0, 0.0)
        self.assertEqual(got, datetime(2024, 3, 19, 16, 30, 0))

    def test_preserves_tzinfo(self):
        tz = timezone(timedelta(hours=-5))
        standard = datetime(2024, 3, 20, 12, 0, 0, tzinfo=tz)
        got = local_mean_solar_time(standard, -75.0, -75.0)
        self.assertEqual(got.tzinfo, tz)
        self.assertEqual(got, standard)


class LocalApparentSolarTimeTests(unittest.TestCase):
    def test_uses_equation_of_time_when_day_given(self):
        standard = datetime(2024, 2, 11, 12, 0, 0)
        eot = equation_of_time_minutes(42)
        got = local_apparent_solar_time(standard, 0.0, 0.0, day_of_year=42)
        expected = standard + timedelta(minutes=eot)
        self.assertEqual(got, expected)

    def test_derives_day_from_standard_time(self):
        standard = datetime(2024, 2, 11, 12, 0, 0)
        got = local_apparent_solar_time(standard, 0.0, 0.0)
        self.assertEqual(
            got,
            local_apparent_solar_time(standard, 0.0, 0.0, day_of_year=42),
        )

    def test_longitude_and_eot_combine(self):
        standard = datetime(2024, 6, 21, 12, 0, 0)
        eot = equation_of_time_minutes(173)
        got = local_apparent_solar_time(standard, 30.0, 0.0, day_of_year=173)
        expected = standard + timedelta(minutes=120.0 + eot)
        self.assertEqual(got, expected)

    def test_leap_day_is_day_60(self):
        standard = datetime(2024, 2, 29, 12, 0, 0)
        got = local_apparent_solar_time(standard, 0.0, 0.0)
        expected = standard + timedelta(minutes=equation_of_time_minutes(60))
        self.assertEqual(got, expected)

    def test_explicit_day_overrides_calendar(self):
        standard = datetime(2024, 2, 11, 12, 0, 0)
        got = local_apparent_solar_time(standard, 0.0, 0.0, day_of_year=307)
        expected = standard + timedelta(minutes=equation_of_time_minutes(307))
        self.assertEqual(got, expected)


class EquationOfTimeDataclassTests(unittest.TestCase):
    def test_for_day_matches_function(self):
        value = EquationOfTime.for_day(100)
        self.assertEqual(value.day_of_year, 100)
        self.assertAlmostEqual(value.minutes, equation_of_time_minutes(100))

    def test_timedelta_property(self):
        value = EquationOfTime(day_of_year=42, minutes=-14.0)
        self.assertEqual(value.timedelta, timedelta(minutes=-14.0))

    def test_frozen(self):
        value = EquationOfTime.for_day(42)
        with self.assertRaises(Exception):
            value.minutes = 0.0  # type: ignore[misc]


class SolarTimeTests(unittest.TestCase):
    def _fixed_clock(self):
        fixed = datetime(2024, 2, 11, 12, 0, 0)
        return lambda: fixed

    def test_mean_solar_time_with_explicit_time(self):
        st = SolarTime(longitude=15.0, standard_meridian=0.0)
        standard = datetime(2024, 3, 20, 12, 0, 0)
        self.assertEqual(
            st.mean_solar_time(standard),
            standard + timedelta(minutes=60.0),
        )

    def test_apparent_solar_time_with_bound_clock(self):
        clock = self._fixed_clock()
        st = SolarTime(longitude=0.0, standard_meridian=0.0, clock=clock)
        got = st.apparent_solar_time()
        expected = clock() + timedelta(minutes=equation_of_time_minutes(42))
        self.assertEqual(got, expected)

    def test_equation_of_time_uses_bound_clock(self):
        st = SolarTime(longitude=0.0, standard_meridian=0.0, clock=self._fixed_clock())
        self.assertAlmostEqual(st.equation_of_time(), equation_of_time_minutes(42))

    def test_explicit_time_beats_clock(self):
        st = SolarTime(longitude=0.0, standard_meridian=0.0, clock=self._fixed_clock())
        other = datetime(2024, 6, 21, 0, 0, 0)
        self.assertAlmostEqual(
            st.equation_of_time(other),
            equation_of_time_minutes(173),
        )


if __name__ == "__main__":
    unittest.main()
