"""Core computations for local apparent solar time.

All functions are pure and depend only on their arguments, so results are
reproducible and testable without a clock.  Angles are in degrees, times are
in minutes unless a function name says otherwise.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable

__all__ = [
    "EquationOfTime",
    "SolarTime",
    "equation_of_time_minutes",
    "local_apparent_solar_time",
    "local_mean_solar_time",
    "time_offset_minutes",
]

# The standard meridian is a whole number of 15-degree time zones from
# Greenwich.  Using 15.0 rather than 15 keeps the arithmetic in floats and
# avoids an accidental integer division on Python 2 style callers.
_DEGREES_PER_HOUR = 15.0
_MINUTES_PER_DEGREE = 4.0


def _normalise_degrees(angle: float) -> float:
    """Return *angle* reduced to the half-open interval [0, 360).

    The solar geometry formulas are periodic, so feeding them an angle that
    has already been reduced avoids surprises when callers pass longitudes
    outside the usual [-180, 180] range.
    """
    return angle % 360.0


def equation_of_time_minutes(day_of_year: int) -> float:
    """Return the equation of time in minutes for a day of the year.

    *day_of_year* is 1-based (1 January is 1).  The equation of time is the
    difference between apparent solar time and mean solar time; it is the
    correction that turns a mean solar clock into a sundial reading.

    The implementation uses the commonly published approximation

        B = 360 / 365 * (N - 81)
        EoT = 9.87 sin(2B) - 7.53 cos(B) - 1.5 sin(B)

    which is accurate to roughly half a minute for civil use.  A higher order
    expansion would be overkill for a library whose input is a longitude the
    caller usually knows to a fraction of a degree.
    """
    if not 1 <= day_of_year <= 366:
        raise ValueError("day_of_year must be between 1 and 366")
    b = math.radians(360.0 / 365.0 * (day_of_year - 81))
    return 9.87 * math.sin(2.0 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)


def time_offset_minutes(longitude: float, standard_meridian: float) -> float:
    """Return the longitude correction in minutes.

    A location east of its standard meridian sees solar noon earlier than the
    standard clock, so the correction is positive for east longitudes.  The
    factor of four comes from the Earth turning one degree every four minutes.
    """
    return (longitude - standard_meridian) * _MINUTES_PER_DEGREE


def local_mean_solar_time(
    standard_time: datetime,
    longitude: float,
    standard_meridian: float,
) -> datetime:
    """Return local mean solar time for a standard-clock instant.

    Mean solar time ignores the equation of time; it is the clock a sundial
    would keep if the Earth's orbit were a circle.  The returned datetime has
    the same tzinfo as *standard_time* and is not normalised across midnight,
    so callers can compare raw offsets.
    """
    offset = time_offset_minutes(longitude, standard_meridian)
    return standard_time + timedelta(minutes=offset)


def local_apparent_solar_time(
    standard_time: datetime,
    longitude: float,
    standard_meridian: float,
    day_of_year: int | None = None,
) -> datetime:
    """Return local apparent solar time for a standard-clock instant.

    Apparent solar time is what a sundial reads: mean solar time plus the
    equation of time.  When *day_of_year* is omitted it is taken from
    *standard_time*, which is the usual case.  Pass it explicitly when the
    caller wants the equation of time for a different date, for example when
    comparing a fixed date against a range of standard times.
    """
    if day_of_year is None:
        day_of_year = standard_time.timetuple().tm_yday
    offset = time_offset_minutes(longitude, standard_meridian)
    eot = equation_of_time_minutes(day_of_year)
    return standard_time + timedelta(minutes=offset + eot)


@dataclass(frozen=True)
class EquationOfTime:
    """Equation of time for a single day, in minutes and as a timedelta."""

    day_of_year: int
    minutes: float

    @property
    def timedelta(self) -> timedelta:
        return timedelta(minutes=self.minutes)

    @classmethod
    def for_day(cls, day_of_year: int) -> "EquationOfTime":
        return cls(day_of_year, equation_of_time_minutes(day_of_year))


@dataclass(frozen=True)
class SolarTime:
    """A solar-time conversion bound to one location and one clock.

    The clock is a callable returning a naive or aware datetime; it defaults to
    :func:`datetime.now` but tests pass a fixed function so the suite never
    depends on the wall clock.  The standard meridian is stored so that the
    longitude correction can be recomputed without repeating the caller's
    arguments.
    """

    longitude: float
    standard_meridian: float
    clock: Callable[[], datetime] = datetime.now

    def mean_solar_time(self, standard_time: datetime | None = None) -> datetime:
        """Local mean solar time for *standard_time* or the bound clock."""
        if standard_time is None:
            standard_time = self.clock()
        return local_mean_solar_time(
            standard_time, self.longitude, self.standard_meridian
        )

    def apparent_solar_time(
        self,
        standard_time: datetime | None = None,
        day_of_year: int | None = None,
    ) -> datetime:
        """Local apparent solar time for *standard_time* or the bound clock."""
        if standard_time is None:
            standard_time = self.clock()
        return local_apparent_solar_time(
            standard_time,
            self.longitude,
            self.standard_meridian,
            day_of_year,
        )

    def equation_of_time(self, standard_time: datetime | None = None) -> float:
        """Equation of time in minutes for *standard_time* or the bound clock."""
        if standard_time is None:
            standard_time = self.clock()
        return equation_of_time_minutes(standard_time.timetuple().tm_yday)
