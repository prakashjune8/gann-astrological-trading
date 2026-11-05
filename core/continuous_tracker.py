"""Continuous Celestial Tracker across Indian Trading Sessions.

Provides seamless, uninterrupted mathematical tracking of individual celestial bodies
across continuous market sessions (NSE, MCX, 24H) in both Geocentric and Heliocentric frames.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np

from core.geo_temporal import (
    IST, UTC, SessionWindow, SESSION_NSE, get_mcx_session, SESSION_FULL_DAY,
    to_utc, to_ist, generate_continuous_session_timeline, calculate_true_solar_noon,
    DEFAULT_STATION
)
from core.horizons_client import (
    HorizonsClient, CENTER_GEOCENTRIC, CENTER_HELIOCENTRIC, BODIES, EphemerisSample
)

# Traditional Zodiac Sign Definitions (30° per sign)
ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]


@dataclass(frozen=True)
class ZodiacCoordinate:
    sign: str
    degrees: int
    minutes: int
    seconds: float
    total_degrees: float

    def format_dms(self) -> str:
        return f"{self.sign} {self.degrees:02d}° {self.minutes:02d}' {self.seconds:04.1f}\""

    @classmethod
    def from_degrees(cls, total_deg: float) -> ZodiacCoordinate:
        deg = total_deg % 360.0
        sign_idx = int(deg // 30.0)
        sign_name = ZODIAC_SIGNS[sign_idx]
        rem = deg - (sign_idx * 30.0)
        d = int(rem)
        rem_m = (rem - d) * 60.0
        m = int(rem_m)
        s = (rem_m - m) * 60.0
        return cls(
            sign=sign_name,
            degrees=d,
            minutes=m,
            seconds=s,
            total_degrees=deg
        )


@dataclass(frozen=True)
class ContinuousCelestialState:
    timestamp_ist: datetime
    session_elapsed_pct: float     # 0.0% to 100.0%
    session_circle_deg: float      # 0.0° to 360.0° (Gann session time circle)
    # Geocentric coordinates
    geo_longitude: float
    geo_zodiac: ZodiacCoordinate
    geo_velocity_deg_per_hour: float
    geo_motion_state: str          # "DIRECT", "STATIONARY", "RETROGRADE"
    # Heliocentric coordinates (if available)
    helio_longitude: Optional[float] = None
    helio_zodiac: Optional[ZodiacCoordinate] = None
    helio_velocity_deg_per_hour: Optional[float] = None


class ContinuousCelestialTracker:
    """Tracks any celestial object continuously across Indian market sessions."""

    def __init__(self, client: Optional[HorizonsClient] = None):
        self.client = client or HorizonsClient()

    def track_body(
        self,
        body_name: str,
        target_date: date,
        session: SessionWindow = SESSION_NSE,
        step_minutes: int = 1
    ) -> list[ContinuousCelestialState]:
        """Generate continuous, minute-by-minute trajectory across the entire session."""
        body_upper = body_name.upper()
        if body_upper not in BODIES:
            raise ValueError(f"Unknown celestial body: {body_name}. Valid bodies: {list(BODIES.keys())}")

        body_meta = BODIES[body_upper]
        has_geo = body_meta["geo"]
        has_helio = body_meta["helio"]

        # Continuous session timeline in IST
        timeline_ist = generate_continuous_session_timeline(
            target_date=target_date,
            session=session,
            step_minutes=step_minutes
        )

        total_session_seconds = (timeline_ist[-1] - timeline_ist[0]).total_seconds()

        # Conversion to UTC window with a 2-hour buffer on each side for robust interpolation
        start_utc_padded = to_utc(timeline_ist[0]) - timedelta(hours=2)
        stop_utc_padded = to_utc(timeline_ist[-1]) + timedelta(hours=2)

        # 1. Fetch Geocentric anchor data
        geo_interpolator = None
        if has_geo:
            geo_samples = self.client.fetch_ephemeris(
                body_code=body_upper,
                center=CENTER_GEOCENTRIC,
                start_utc=start_utc_padded,
                stop_utc=stop_utc_padded,
                step_size="1h"
            )
            geo_interpolator = self._create_spline_interpolator(geo_samples)

        # 2. Fetch Heliocentric anchor data
        helio_interpolator = None
        if has_helio:
            helio_samples = self.client.fetch_ephemeris(
                body_code=body_upper,
                center=CENTER_HELIOCENTRIC,
                start_utc=start_utc_padded,
                stop_utc=stop_utc_padded,
                step_size="1h"
            )
            helio_interpolator = self._create_spline_interpolator(helio_samples)

        # 3. Continuous evaluation along the unbroken session timeline
        results: list[ContinuousCelestialState] = []
        for dt_ist in timeline_ist:
            dt_utc = to_utc(dt_ist)
            t_epoch = dt_utc.timestamp()

            # Session progress metrics
            elapsed_sec = (dt_ist - timeline_ist[0]).total_seconds()
            progress_ratio = max(0.0, min(1.0, elapsed_sec / total_session_seconds))
            session_circle_deg = progress_ratio * 360.0

            # Evaluate Geocentric
            geo_lon = 0.0
            geo_vel = 0.0
            geo_state = "DIRECT"
            if geo_interpolator:
                geo_lon, geo_vel = geo_interpolator(t_epoch)
                if abs(geo_vel) <= 0.005:
                    geo_state = "STATIONARY"
                elif geo_vel < 0.0:
                    geo_state = "RETROGRADE"
                else:
                    geo_state = "DIRECT"

            # Evaluate Heliocentric
            helio_lon = None
            helio_vel = None
            helio_zod = None
            if helio_interpolator:
                h_lon, h_vel = helio_interpolator(t_epoch)
                helio_lon = h_lon
                helio_vel = h_vel
                helio_zod = ZodiacCoordinate.from_degrees(h_lon)

            results.append(ContinuousCelestialState(
                timestamp_ist=dt_ist,
                session_elapsed_pct=progress_ratio * 100.0,
                session_circle_deg=session_circle_deg,
                geo_longitude=geo_lon,
                geo_zodiac=ZodiacCoordinate.from_degrees(geo_lon),
                geo_velocity_deg_per_hour=geo_vel,
                geo_motion_state=geo_state,
                helio_longitude=helio_lon,
                helio_zodiac=helio_zod,
                helio_velocity_deg_per_hour=helio_vel
            ))

        return results

    def _create_spline_interpolator(self, samples: list[EphemerisSample]):
        """Build continuous unwrapped polynomial interpolator with normalized hours."""
        if len(samples) < 3:
            raise ValueError("Insufficient ephemeris samples to build continuous interpolator.")

        times = np.array([s.utc_time.timestamp() for s in samples])
        raw_lons = np.array([s.ecliptic_longitude for s in samples])

        # Angular phase unwrap to avoid 359° -> 0° boundary discontinuities
        unwrapped_lons = np.unwrap(np.radians(raw_lons))

        # Normalize time to hours from t0 for perfect matrix conditioning
        t0 = times[0]
        hours = (times - t0) / 3600.0

        poly_deg = min(3, len(samples) - 1)
        poly_coeffs = np.polyfit(hours, unwrapped_lons, deg=poly_deg)
        deriv_coeffs = np.polyder(poly_coeffs)

        def evaluate(t_sec: float) -> Tuple[float, float]:
            h = (t_sec - t0) / 3600.0
            rad_val = np.polyval(poly_coeffs, h)
            rad_deriv = np.polyval(deriv_coeffs, h)  # rad per hour
            deg_val = np.degrees(rad_val) % 360.0
            deg_per_hour = np.degrees(rad_deriv)
            return float(deg_val), float(deg_per_hour)

        return evaluate
