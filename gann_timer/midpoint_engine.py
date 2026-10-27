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
    price_level: float | None = None
    price_left: float | None = None
    price_right: float | None = None


@dataclass(frozen=True)
class MidpointAnalysisResult:
    method_key: str
    method_name: str
    session_date: date
    midpoint_time: datetime
    session_open: datetime | None
    session_close: datetime | None
    total_minutes: float
    minutes_per_degree: float
    seconds_per_degree: float
    description: str
    harmonic_points: list[DegreeTimePoint]
    price_equilibrium: float | None = None
    price_high: float | None = None
    price_low: float | None = None
    price_range: float | None = None


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


MIDPOINT_METHODS = {
    "NSE_SESSION": {
        "name": "Method 1: NSE/BSE Equity Session Midpoint (12:22:30 IST)",
        "desc": "Calculates 50% temporal center of the NSE/BSE 09:15 to 15:30 session (375 min = 360°, 1° = 1.0417 min).",
        "requires_price": False,
        "default_market": "NSE",
    },
    "MCX_SESSION": {
        "name": "Method 2: MCX Commodity Session Midpoint (16:15 / 16:27 IST)",
        "desc": "Calculates 50% temporal center of the MCX 09:00 to 23:30/23:55 session (870/895 min = 360°, 1° = 2.4167 min).",
        "requires_price": False,
        "default_market": "MCX",
    },
    "SOLAR_NOON": {
        "name": "Method 3: Astronomical True Solar Noon (Mumbai Meridian 72.825° E)",
        "desc": "Calculates the exact celestial moment the Sun transits the Mumbai meridian, adjusted for Equation of Time (1440 min = 360°, 1° = 4.0 min).",
        "requires_price": False,
        "default_market": "ALL",
    },
    "OPENING_RANGE": {
        "name": "Method 4: Opening Range Midpoint (First 45-60 min Balance)",
        "desc": "Calculates 50% temporal balance of the opening first-hour window (09:15 to 10:15 IST, Midpoint = 09:45 IST, 60 min = 360°, 1° = 10 sec).",
        "requires_price": False,
        "default_market": "NSE",
    },
    "CUSTOM_TIME": {
        "name": "Method 5: Custom Pivot Time (User Anchor)",
        "desc": "Anchors the 0° midpoint at any custom pivot timestamp (e.g., morning extreme high/low time) and projects harmonic waves.",
        "requires_price": False,
        "default_market": "CUSTOM",
    },
    "PRICE_50": {
        "name": "Method 6: Gann 50% Price Equilibrium & Harmonic Octaves",
        "desc": "Calculates the exact 50% midpoint between High and Low, projecting harmonic support/resistance price levels & time squaring.",
        "requires_price": True,
        "default_market": "ALL",
    },
}


def equation_of_time(day_of_year: int) -> float:
    b = 2.0 * math.pi * (day_of_year - 81) / 365.0
    return 9.87 * math.sin(2.0 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)


def calculate_mumbai_solar_noon(d: date) -> datetime:
    doy = d.timetuple().tm_yday
    eot = equation_of_time(doy)
    meridian_offset_minutes = (IST_MERIDIAN - MUMBAI_LONGITUDE) * 4.0
    total_offset = meridian_offset_minutes - eot
    noon_base = datetime.combine(d, time(12, 0))
    return noon_base + timedelta(minutes=total_offset)


def compute_degree_points(
    midpoint: datetime,
    scale_min_per_deg: float,
    custom_degrees: list[float] | None = None,
    price_mid: float | None = None,
    price_range: float | None = None,
) -> list[DegreeTimePoint]:
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
        
        # Calculate price levels if in Price Equilibrium mode
        p_left = None
        p_right = None
        if price_mid is not None and price_range is not None:
            # In Gann octaves, 180° = 50% of the range from midpoint
            # delta = (deg / 180.0) * (price_range / 2.0)
            delta = (deg / 180.0) * (price_range / 2.0) if price_range > 0 else (deg * 0.5)
            p_left = price_mid - delta
            p_right = price_mid + delta

        results.append(DegreeTimePoint(
            degree=deg,
            time_left=t_left,
            time_right=t_right,
            label=lbl,
            is_major=maj,
            price_left=p_left,
            price_right=p_right,
        ))
    return results


def analyze_midpoints_v2(
    d: date,
    method_key: str,
    custom_time_val: time | None = None,
    time_scale_mode: str = "SESSION_SCALE",
    price_high: float | None = None,
    price_low: float | None = None,
    custom_degrees: list[float] | None = None,
) -> MidpointAnalysisResult:
    method_info = MIDPOINT_METHODS.get(method_key, MIDPOINT_METHODS["NSE_SESSION"])
    method_name = method_info["name"]
    price_eq = None
    p_range = None

    if method_key == "NSE_SESSION":
        dt_open = datetime.combine(d, NSE_OPEN)
        dt_close = datetime.combine(d, NSE_CLOSE)
        total_mins = (dt_close - dt_open).total_seconds() / 60.0
        midpoint = dt_open + timedelta(minutes=total_mins / 2.0)
        scale_min = total_mins / 360.0
        desc = "NSE/BSE 50% Session Time Midpoint: 12:22:30 IST (375 min = 360°, 1° = 1.0417 min)"

    elif method_key == "MCX_SESSION":
        dt_open = datetime.combine(d, MCX_OPEN)
        close_t = MCX_CLOSE_DST if us_dst_active(d) else MCX_CLOSE_STD
        dt_close = datetime.combine(d, close_t)
        total_mins = (dt_close - dt_open).total_seconds() / 60.0
        midpoint = dt_open + timedelta(minutes=total_mins / 2.0)
        scale_min = total_mins / 360.0
        dst_str = "US DST Active (Closes 23:30)" if us_dst_active(d) else "US Standard (Closes 23:55)"
        desc = f"MCX 50% Session Time Midpoint: {midpoint.strftime('%H:%M:%S')} IST ({total_mins:.0f} min = 360°, {dst_str})"

    elif method_key == "SOLAR_NOON":
        midpoint = calculate_mumbai_solar_noon(d)
        total_mins = 1440.0
        scale_min = 4.0
        dt_open = None
        dt_close = None
        desc = f"Astronomical True Solar Noon (Mumbai 72.825° E): {midpoint.strftime('%H:%M:%S')} IST (1440 min = 360°, 1° = 4.0 min)"

    elif method_key == "OPENING_RANGE":
        dt_open = datetime.combine(d, NSE_OPEN)
        dt_first_hr = dt_open + timedelta(minutes=60)
        total_mins = 60.0
        midpoint = dt_open + timedelta(minutes=30.0)
        scale_min = 60.0 / 360.0
        dt_close = dt_first_hr
        desc = f"Gann Opening First-Hour Midpoint (09:15 to 10:15 IST): {midpoint.strftime('%H:%M:%S')} IST (60 min = 360°, 1° = 10 sec)"

    elif method_key == "CUSTOM_TIME":
        t_anchor = custom_time_val or time(12, 0)
        midpoint = datetime.combine(d, t_anchor)
        dt_open = datetime.combine(d, NSE_OPEN)
        dt_close = datetime.combine(d, NSE_CLOSE)
        
        if time_scale_mode == "SOLAR_4MIN":
            scale_min = 4.0
            total_mins = 1440.0
            scale_desc = "Solar scale 4.0 min/deg"
        elif time_scale_mode == "OPENING_10SEC":
            scale_min = 60.0 / 360.0
            total_mins = 60.0
            scale_desc = "Opening scale 10.0 sec/deg"
        else:
            total_mins = 375.0
            scale_min = 375.0 / 360.0
            scale_desc = "NSE session scale 1.0417 min/deg"

        desc = f"Custom Anchor Midpoint: {midpoint.strftime('%H:%M:%S')} IST ({scale_desc})"

    elif method_key == "PRICE_50":
        hi = price_high if price_high is not None and price_high > 0 else 24400.0
        lo = price_low if price_low is not None and price_low > 0 else 24200.0
        if lo > hi:
            hi, lo = lo, hi
        price_eq = (hi + lo) / 2.0
        p_range = hi - lo
        dt_open = datetime.combine(d, NSE_OPEN)
        dt_close = datetime.combine(d, NSE_CLOSE)
        total_mins = 375.0
        midpoint = dt_open + timedelta(minutes=total_mins / 2.0)  # Session midpoint 12:22:30 IST
        scale_min = total_mins / 360.0
        desc = (
            f"Gann 50% Price Equilibrium: High {hi:.2f} | Low {lo:.2f} | "
            f"Equilibrium Midpoint = {price_eq:.2f} pts (Range: {p_range:.2f} pts)"
        )

    else:
        raise ValueError(f"Unknown method key: {method_key}")

    pts = compute_degree_points(
        midpoint=midpoint,
        scale_min_per_deg=scale_min,
        custom_degrees=custom_degrees,
        price_mid=price_eq,
        price_range=p_range,
    )

    return MidpointAnalysisResult(
        method_key=method_key,
        method_name=method_name,
        session_date=d,
        midpoint_time=midpoint,
        session_open=dt_open,
        session_close=dt_close,
        total_minutes=total_mins,
        minutes_per_degree=scale_min,
        seconds_per_degree=scale_min * 60.0,
        description=desc,
        harmonic_points=pts,
        price_equilibrium=price_eq,
        price_high=price_high,
        price_low=price_low,
        price_range=p_range,
    )
