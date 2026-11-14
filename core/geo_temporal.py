"""Geographic and Temporal Reference Engine for Indian Financial Markets.

Handles Indian Standard Time (IST, UTC+05:30) conversions, geographic observer coordinates,
and continuous trading session timelines without interruptions.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date, time, timedelta, timezone
import math
from typing import Dict, Tuple, Optional

# Fixed Indian Standard Time (UTC+05:30, invariant year-round, no DST)
IST = timezone(timedelta(hours=5, minutes=30), name="IST")
UTC = timezone.utc


@dataclass(frozen=True)
class GeoLocation:
    name: str
    latitude: float   # Decimal degrees North
    longitude: float  # Decimal degrees East
    elevation_m: float = 0.0


# Standard Geographic Stations across India
INDIAN_STATIONS: dict[str, GeoLocation] = {
    "MUMBAI_NSE": GeoLocation(
        name="Mumbai (NSE Exchange Hub)",
        latitude=19.0760,
        longitude=72.8777,
        elevation_m=14.0
    ),
    "DELHI_NORTH": GeoLocation(
        name="New Delhi (Northern Capital)",
        latitude=28.6139,
        longitude=77.2090,
        elevation_m=216.0
    ),
    "UJJAIN_ZERO": GeoLocation(
        name="Ujjain (Ancient Indian Prime Meridian)",
        latitude=23.1765,
        longitude=75.7885,
        elevation_m=491.0
    ),
    "IST_MERIDIAN": GeoLocation(
        name="Mirzapur (82.5°E Standard Time Axis)",
        latitude=25.1337,
        longitude=82.5644,
        elevation_m=80.0
    ),
}

DEFAULT_STATION = INDIAN_STATIONS["MUMBAI_NSE"]


@dataclass(frozen=True)
class SessionWindow:
    name: str
    start_time: time
    end_time: time
    is_next_day_close: bool = False

    @property
    def total_duration_minutes(self) -> float:
        start_mins = self.start_time.hour * 60 + self.start_time.minute + self.start_time.second / 60.0
        end_mins = self.end_time.hour * 60 + self.end_time.minute + self.end_time.second / 60.0
        if self.is_next_day_close or end_mins < start_mins:
            end_mins += 1440.0
        return end_mins - start_mins


# Indian Continuous Market Sessions
SESSION_NSE = SessionWindow(
    name="NSE_EQUITY_AND_FNO",
    start_time=time(9, 15, 0),
    end_time=time(15, 30, 0)
)  # Exactly 375 continuous minutes

SESSION_MCX_SUMMER = SessionWindow(
    name="MCX_COMMODITY_SUMMER",
    start_time=time(9, 0, 0),
    end_time=time(23, 30, 0)
)  # 870 continuous minutes (US DST active)

SESSION_MCX_WINTER = SessionWindow(
    name="MCX_COMMODITY_WINTER",
    start_time=time(9, 0, 0),
    end_time=time(23, 55, 0)
)  # 895 continuous minutes

SESSION_FULL_DAY = SessionWindow(
    name="FULL_24H_CONTINUOUS",
    start_time=time(0, 0, 0),
    end_time=time(23, 59, 59)
)  # 1440 continuous minutes


def is_us_dst(target_date: date) -> bool:
    """Check if US Daylight Saving Time is active for a given date (affects MCX close)."""
    # 2nd Sunday in March to 1st Sunday in November
    year = target_date.year
    # Find 2nd Sunday in March
    mar1 = date(year, 3, 1)
    first_sun_mar = mar1 + timedelta(days=(6 - mar1.weekday()) % 7)
    second_sun_mar = first_sun_mar + timedelta(days=7)
    # Find 1st Sunday in November
    nov1 = date(year, 11, 1)
    first_sun_nov = nov1 + timedelta(days=(6 - nov1.weekday()) % 7)

    return second_sun_mar <= target_date < first_sun_nov


def get_mcx_session(target_date: date) -> SessionWindow:
    """Return active continuous MCX session (23:30 in summer DST vs 23:55 in winter)."""
    return SESSION_MCX_SUMMER if is_us_dst(target_date) else SESSION_MCX_WINTER


def to_utc(dt_ist: datetime) -> datetime:
    """Convert an IST datetime to UTC datetime."""
    if dt_ist.tzinfo is None:
        dt_ist = dt_ist.replace(tzinfo=IST)
    return dt_ist.astimezone(UTC)


def to_ist(dt_utc: datetime) -> datetime:
    """Convert a UTC datetime to IST datetime."""
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=UTC)
    return dt_utc.astimezone(IST)


def calculate_equation_of_time(target_date: date) -> float:
    """Calculate Spencer's Equation of Time (EoT) in minutes for a given calendar day."""
    day_of_year = target_date.timetuple().tm_yday
    # Fractional year gamma in radians
    gamma = 2.0 * math.pi * (day_of_year - 1) / 365.0

    eot = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2.0 * gamma)
        - 0.040849 * math.sin(2.0 * gamma)
    )
    return eot


def calculate_true_solar_noon(
    target_date: date,
    station: GeoLocation = DEFAULT_STATION
) -> datetime:
    """Calculate the exact instant of True Solar Noon (meridian transit) in IST."""
    eot_minutes = calculate_equation_of_time(target_date)
    # Longitude correction: 4 minutes per degree from IST meridian (82.5°E)
    lon_offset_minutes = 4.0 * (station.longitude - 82.5)
    # Solar noon offset from 12:00:00 IST
    noon_shift_minutes = - (lon_offset_minutes + eot_minutes)

    noon_seconds = int(round(noon_shift_minutes * 60.0))
    base_noon = datetime.combine(target_date, time(12, 0, 0), tzinfo=IST)
    true_solar_noon = base_noon + timedelta(seconds=noon_seconds)
    return true_solar_noon


def generate_continuous_session_timeline(
    target_date: date,
    session: SessionWindow = SESSION_NSE,
    step_minutes: int = 1
) -> list[datetime]:
    """Generate an unbroken, continuous sequence of IST timestamps across the session."""
    start_dt = datetime.combine(target_date, session.start_time, tzinfo=IST)
    end_dt = datetime.combine(target_date, session.end_time, tzinfo=IST)
    if session.is_next_day_close or end_dt <= start_dt:
        end_dt += timedelta(days=1)

    timeline: list[datetime] = []
    curr = start_dt
    delta = timedelta(minutes=step_minutes)
    while curr <= end_dt:
        timeline.append(curr)
        curr += delta

    if timeline[-1] != end_dt:
        timeline.append(end_dt)

    return timeline
