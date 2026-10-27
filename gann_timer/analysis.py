"""Orchestration: IST range -> Horizons download -> Gann engine -> segment triggers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Callable

from . import config
from .gann_engine import AnalysisSettings, CelestialEvent, GannEngine, TriggerRow, route_triggers
from .horizons_client import Ephemeris, HorizonsClient
from .instruments import segments_for_choice
from .timeconv import IST, HolidayCalendar, ist_to_ut


@dataclass
class AnalysisRequest:
    start_ist: date
    end_ist: date
    instrument_choice: str
    settings: AnalysisSettings
    rulership_filter: bool = True
    live_only: bool = False


@dataclass
class AnalysisResult:
    ephemeris: Ephemeris
    events: list[CelestialEvent]
    triggers: list[TriggerRow]


def ist_range_to_ut(start_ist: date, end_ist: date) -> tuple[datetime, datetime]:
    """Full IST days -> naive UT bounds, floored/ceiled to 00:00 UT so daily
    00:00 UT samples line up with the Astrodienst baseline tables (05:30 IST)."""
    s = ist_to_ut(datetime.combine(start_ist, time(0, 0), IST)).replace(tzinfo=None)
    e = ist_to_ut(datetime.combine(end_ist, time(23, 59), IST)).replace(tzinfo=None)
    s = datetime(s.year, s.month, s.day)
    e = datetime(e.year, e.month, e.day) + timedelta(days=1)
    return s, e


class AnalysisService:
    def __init__(self) -> None:
        self.client = HorizonsClient()
        self.calendar = HolidayCalendar()

    def _pivot_sun_lon(self, pivot_ut: datetime, progress) -> float:
        start = pivot_ut.replace(minute=0, second=0, microsecond=0)
        eph = self.client.fetch(["Sun"], start, start + timedelta(hours=2), step_hours=1, progress=progress)
        sun = eph.bodies["Sun"]
        frac = (pivot_ut - sun.times[0]).total_seconds() / 3600.0
        a, b = sun.lon[0], sun.lon[1]
        return (a + ((b - a + 180) % 360 - 180) * frac) % 360.0

    def run(self, req: AnalysisRequest, progress: Callable[[str], None] | None = None) -> AnalysisResult:
        self.calendar.reload()
        s = req.settings
        bodies = [b for b in config.BODIES if b in s.bodies]
        fetch_bodies = list(dict.fromkeys(bodies + ["Sun"]))  # Sun always needed for time squares
        start_ut, stop_ut = ist_range_to_ut(req.start_ist, req.end_ist)
        if progress:
            progress(f"Requesting NASA JPL Horizons ephemeris {start_ut:%Y-%m-%d} → {stop_ut:%Y-%m-%d} UT …")
        eph = self.client.fetch(fetch_bodies, start_ut, stop_ut, progress=progress)

        if s.pivot_ut is not None:
            s.pivot_sun_lon = self._pivot_sun_lon(s.pivot_ut, progress)

        if progress:
            progress("Computing Gann aspects, ingresses, stations and price-time squares …")
        events = GannEngine(eph, s).run()
        triggers = route_triggers(events, segments_for_choice(req.instrument_choice),
                                  s.reference_price, self.calendar,
                                  rulership_filter=req.rulership_filter, live_only=req.live_only)
        # keep only events whose IST date is inside the requested IST range
        triggers = [t for t in triggers if req.start_ist <= t.ist_time.date() <= req.end_ist]
        return AnalysisResult(eph, events, triggers)
