# local_solar_time_lib

Computes local mean and apparent solar time from a longitude and a standard
meridian, so you can turn a clock reading into the time a sundial would show.

```python
from datetime import datetime
from local_solar_time_lib import (
    SolarTime,
    equation_of_time_minutes,
    local_apparent_solar_time,
    local_mean_solar_time,
    time_offset_minutes,
)

standard = datetime(2024, 2, 11, 12, 0, 0)

# Mean solar time: longitude correction only, four minutes per degree.
time_offset_minutes(15.0, 0.0)          # 60.0
local_mean_solar_time(standard, 15.0, 0.0)

# Apparent solar time: longitude correction plus the equation of time.
# The day of year is taken from the datetime unless you pass it.
equation_of_time_minutes(42)             # about -14.2
local_apparent_solar_time(standard, 15.0, 0.0)
local_apparent_solar_time(standard, 15.0, 0.0, day_of_year=42)

# Or bind a location and an optional clock once.
site = SolarTime(longitude=15.0, standard_meridian=0.0)
site.apparent_solar_time(standard)
site.equation_of_time(standard)
```

## Why this exists

Solar time is a two-step correction and it is easy to apply only one of them.
The longitude correction (four minutes per degree from the standard meridian)
is exact and linear; the equation of time is neither, and most people reach for
it only when they notice their sundial is wrong by a quarter of an hour.
This library keeps the two separate so a caller can use mean solar time when
that is what they mean and apparent solar time when they need the sundial
reading.

The trade-off is accuracy against dependencies. The equation of time uses the
common `9.87 sin(2B) - 7.53 cos(B) - 1.5 sin(B)` approximation, which is good
to roughly half a minute. A full VSOP-style ephemeris would be more accurate
and would also be far more code, and the input longitude is usually known to a
fraction of a degree anyway. The library has no third-party dependencies at
all.

## The awkward edge

The equation of time is periodic and its approximation crosses zero three
times a year, so a small absolute error looks large in relative terms near
those crossings. If you are comparing against a published table, expect
disagreement of up to about half a minute and compare with a tolerance rather
than equality.

A second edge: `local_apparent_solar_time` derives the day of year from the
datetime it is given. Around midnight, the longitude correction can push the
result into the previous or next day, but the equation of time is still taken
from the original date. That is the intended behaviour — the correction is
applied to a standard-clock instant, so the date that matters is the one on
the standard clock. Pass `day_of_year` explicitly if you want a different
date's equation of time.

## API

- `time_offset_minutes(longitude, standard_meridian) -> float` — longitude
  correction in minutes, positive east of the meridian.
- `equation_of_time_minutes(day_of_year) -> float` — equation of time in
  minutes. `day_of_year` is 1-based and must be between 1 and 366.
- `local_mean_solar_time(standard_time, longitude, standard_meridian) -> datetime`.
- `local_apparent_solar_time(standard_time, longitude, standard_meridian, day_of_year=None) -> datetime`.
- `EquationOfTime` — frozen dataclass with `day_of_year`, `minutes`,
  `timedelta`, and `EquationOfTime.for_day(day_of_year)`.
- `SolarTime(longitude, standard_meridian, clock=datetime.now)` — binds a
  location and an optional clock; methods `mean_solar_time`, `apparent_solar_time`,
  and `equation_of_time`.

All returned datetimes keep the `tzinfo` of the input and are not normalised
across midnight, so subtracting two of them gives the true offset.
