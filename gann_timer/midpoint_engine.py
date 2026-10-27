"""Gann Midpoint & 360-degree Time Harmonics Engine for Indian Markets."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from .timeconv import us_dst_active

# Standard Exchange Operational Hours (IST)
NSE_OPEN = time(9, 15)
NSE_CLOSE = time(15, 30)

MCX_OPEN = time(9, 0)
MCX_CLOSE_DST = time(23, 30)
MCX_CLOSE_STD = time(23, 55)

# Mumbai Exchange Geographic Coordinates
MUMBAI_LONGITUDE = 72.825  # 72°49'30" E
IST_MERIDIAN = 82.5        # UTC+05:30


@dataclass(frozen=True)
class DegreeTimePoint:
    degree: float
    time_left: datetime
    time_right: datetime
    label: str
    is_major: bool


@dataclass(frozen=True)
class MidpointAnalysisResult:
    mode_name: str
    session_date: date
    midpoint_time: datetime
    session_open: datetime | None
    session_close: datetime | None
    total_minutes: float
    minutes_per_degree: float
    seconds_per_degree: float
    description: str
    harmonic_points: list[DegreeTimePoint]


STANDARD_DEGREES = [
    (0.0, "0° Center Axis - THE MIDPOINT OF THE DAY (Equilibrium)", True),
    (15.0, "1/24 Circle - Minor Sub-Harmonic", False),
    (30.0, "1/12 Circle - Semi-Sextile (30° Sign division)", True),
    (45.0, "1/8 Circle - Octile / Semi-Square", True),
    (60.0, "1/6 Circle - Sextile (Trine sub-harmonic)", True),
    (72.0, "1/5 Circle - Quintile (Golden Ratio harmonic)", False),
    (90.0, "1/4 Circle - Square / Quadrant (Major Pivot)", True),
    (108.0, "3/10 Circle - Tridecile", False),
    (120.0, "1/3 Circle - Trine (Major Harmonic)", True),
    (135.0, "3/8 Circle - Sesqui-Square", True),
    (144.0, "2/5 Circle - Biquintile (Gann 144 Master Number)", True),
    (150.0, "5/12 Circle - Quincunx", False),
    (180.0, "1/2 Circle - Opposition / Session Extremes", True),
]


def equation_of_time(day_of_year: int) -> float:
    """Equation of Time in minutes given the day of the year (1-366)."""
    b = 2.0 * math.pi * (day_of_year - 81) / 365.0
    return 9.87 * math.sin(2.0 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)


def calculate_mumbai_solar_noon(d: date) -> datetime:
    """Local Apparent Noon (True Solar Noon) in Mumbai (72.825° E) in IST."""
    doy = d.timetuple().tm_yday
    eot = equation_of_time(doy)
    # Longitude offset from 82.5° E (4 min per deg) - Equation of Time
    meridian_offset_minutes = (IST_MERIDIAN - MUMBAI_LONGITUDE) * 4.0
    total_offset = meridian_offset_minutes - eot
    noon_base = datetime.combine(d, time(12, 0))
    return noon_base + timedelta(minutes=total_offset)


def compute_degree_points(midpoint: datetime, scale_min_per_deg: float,
                          custom_degrees: list[float] | None = None) -> list[DegreeTimePoint]:
    """Calculate Left (-deg) and Right (+deg) timestamps from midpoint."""
    degrees_map: dict[float, tuple[str, bool]] = {deg: (lbl, maj) for deg, lbl, maj in STANDARD_DEGREES}
    
    if custom_degrees:
        for cdeg in custom_degrees:
            if cdeg > 0 and cdeg not in degrees_map:
                degrees_map[cdeg] = (f"Custom Angle ({cdeg:g}°)", True)

    sorted_degs = sorted(degrees_map.keys())
    results: list[DegreeTimePoint] = []
    
    for deg in sorted_degs:
        lbl, maj = degrees_map[deg]
        offset = timedelta(minutes=deg * scale_min_per_deg)
        t_left = midpoint - offset
        t_right = midpoint + offset
        results.append(DegreeTimePoint(
            degree=deg,
            time_left=t_left,
            time_right=t_right,
            label=lbl,
            is_major=maj
        ))
    return results


def analyze_midpoints(d: date, mode: str, custom_degrees: list[float] | None = None) -> MidpointAnalysisResult:
    """Analyze midpoint and harmonic time degrees for the selected Indian market option.

    mode: 'NSE_BSE', 'MCX', or 'SOLAR'
    """
    if mode == "NSE_BSE":
        dt_open = datetime.combine(d, NSE_OPEN)
        dt_close = datetime.combine(d, NSE_CLOSE)
        total_mins = (dt_close - dt_open).total_seconds() / 60.0  # 375.0 mins
        midpoint = dt_open + timedelta(minutes=total_mins / 2.0)    # 12:22:30 IST
        scale_min = total_mins / 360.0                             # 1.0416667 min/deg
        desc = "NSE & BSE Cash/Equity Session: 09:15 to 15:30 IST (375 min = 360°)"

    elif mode == "MCX":
        dt_open = datetime.combine(d, MCX_OPEN)
        close_t = MCX_CLOSE_DST if us_dst_active(d) else MCX_CLOSE_STD
        dt_close = datetime.combine(d, close_t)
        total_mins = (dt_close - dt_open).total_seconds() / 60.0  # 870 or 895 mins
        midpoint = dt_open + timedelta(minutes=total_mins / 2.0)
        scale_min = total_mins / 360.0
        dst_str = "US DST Active (Closes 23:30)" if us_dst_active(d) else "US Standard (Closes 23:55)"
        desc = f"MCX Commodity Session: 09:00 to {close_t.strftime('%H:%M')} IST ({total_mins:.0f} min = 360°, {dst_str})"

    elif mode == "SOLAR":
        midpoint = calculate_mumbai_solar_noon(d)
        total_mins = 1440.0                                       # 24 hours Earth rotation = 360°
        scale_min = 4.0                                           # Exactly 4 min per deg
        dt_open = None
        dt_close = None
        desc = "Natural Solar Cycle: Mumbai Local Apparent Solar Noon (1440 min = 360°, 4.0 min/deg)"

    else:
        raise ValueError(f"Unknown mode: {mode}")

    pts = compute_degree_points(midpoint, scale_min, custom_degrees)
    
    return MidpointAnalysisResult(
        mode_name=mode,
        session_date=d,
        midpoint_time=midpoint,
        session_open=dt_open,
        session_close=dt_close,
        total_minutes=total_mins,
        minutes_per_degree=scale_min,
        seconds_per_degree=scale_min * 60.0,
        description=desc,
        harmonic_points=pts
    )
