"""Skill 3 – Gann market harmonics: aspects, ingresses, stations, price-time squaring."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from itertools import combinations

from . import config
from .horizons_client import Ephemeris
from .instruments import Segment, filter_allowed, is_excluded, symbols_for
from .timeconv import HolidayCalendar, align_to_session, is_nifty_expiry, ut_to_ist


# ------------------------------------------------------------------ helpers --
def wrap180(x: float) -> float:
    return (x + 180.0) % 360.0 - 180.0


def fmt_zodiac(lon: float) -> str:
    lon %= 360.0
    sign = int(lon // 30)
    deg_in = lon - sign * 30
    d = int(deg_in)
    m = int(round((deg_in - d) * 60))
    if m == 60:
        d, m = d + 1, 0
    return f"{d:02d}°{config.SIGN_ABBR[sign]}{m:02d}′"


def sq9_levels(ref_price: float, degree: float) -> tuple[float, float]:
    """Square-of-Nine fixed wheel rungs bracketing *ref_price* along ray *degree*.

    In Gann's authentic Square-of-Nine spiral:
    - Odd squares (1, 9, 25, 49, 81...) anchor the 0° base axis: (2k + 1)^2.
    - Each 360° revolution advances the square root by exactly +2.0.
    - Ray angle theta corresponds to: sqrt(P) = 2k + 1 + (theta % 360) / 180.
    """
    if ref_price <= 0:
        return (math.nan, math.nan)
    off = (degree % 360.0) / 180.0
    r = math.sqrt(ref_price)
    k = math.floor((r - 1.0 - off) / 2.0)
    below = (2.0 * k + 1.0 + off) ** 2
    above = (2.0 * (k + 1.0) + 1.0 + off) ** 2
    if below > ref_price:  # numeric boundary guard
        k -= 1
        below = (2.0 * k + 1.0 + off) ** 2
        above = (2.0 * (k + 1.0) + 1.0 + off) ** 2
    elif above <= ref_price:
        k += 1
        below = (2.0 * k + 1.0 + off) ** 2
        above = (2.0 * (k + 1.0) + 1.0 + off) ** 2
    return below, above


def sq9_relative_harmonic(ref_price: float, degree: float) -> tuple[float, float]:
    """Square-of-Nine relative harmonic price levels projected directly from *ref_price*.

    Support: (sqrt(P) - theta/180)^2
    Resistance: (sqrt(P) + theta/180)^2
    """
    if ref_price <= 0:
        return (math.nan, math.nan)
    r = math.sqrt(ref_price)
    delta = degree / 180.0
    sup = (max(0.0, r - delta)) ** 2
    res = (r + delta) ** 2
    return sup, res


def price_to_degree(price: float) -> float:
    """Gann's natural 360° circle mapping: price modulo 360."""
    return price % 360.0


def sq9_price_to_degree(price: float) -> float:
    """Gann's Square of Nine spiral angle: theta = ((sqrt(P) - 1) % 2) * 180°."""
    if price <= 0:
        return 0.0
    r = math.sqrt(price)
    return ((r - 1.0) % 2.0) * 180.0


def round_to_step(x: float, step: float | None) -> float:
    return round(x / step) * step if step else x


# ------------------------------------------------------------------- models --
@dataclass
class CelestialEvent:
    time_ut: datetime
    kind: str                     # Aspect, Ingress, Station, Lunar Phase, Time Square, Price-Time Square
    bodies: tuple[str, ...]
    title: str
    score: float
    key_degree: float             # degree used for Square-of-Nine price conversion
    universal: bool = False       # applies to every segment regardless of rulership
    window_days: int = 1
    implication: str = ""
    positions: dict[str, float] = field(default_factory=dict)

    @property
    def strength(self) -> str:
        return "High" if self.score >= 7 else "Medium" if self.score >= 4.5 else "Low"


@dataclass
class TriggerRow:
    event: CelestialEvent
    segment: Segment
    ist_time: datetime
    session_status: str
    actionable_ist: datetime
    symbols: list[str]
    sq9_support: float
    sq9_resistance: float
    notes: str


@dataclass
class AnalysisSettings:
    bodies: list[str]
    include_octiles: bool = False
    include_moon_aspects: bool = False
    include_lunar_phases: bool = True
    include_ingresses: bool = True
    include_stations: bool = True
    pivot_ut: datetime | None = None
    pivot_price: float | None = None
    pivot_sun_lon: float | None = None
    reference_price: float | None = None
    min_score: float = 0.0


# ------------------------------------------------------------------- engine --
class GannEngine:
    def __init__(self, eph: Ephemeris, settings: AnalysisSettings) -> None:
        self.eph = eph
        self.s = settings
        self.t = eph.times
        self.step = timedelta(hours=eph.step_hours)

    # -- generic machinery ---------------------------------------------------
    def _lon_at(self, body: str, i: int, frac: float) -> float:
        lon = self.eph.bodies[body].lon
        a = lon[i]
        b = lon[min(i + 1, len(lon) - 1)]
        return (a + wrap180(b - a) * frac) % 360.0

    def _positions(self, i: int, frac: float) -> dict[str, float]:
        return {b: self._lon_at(b, i, frac) for b in self.eph.bodies}

    def _crossings(self, f: list[float]):
        """Yield (index, frac) where wrapped function f crosses zero (ignoring ±180 wraps)."""
        for i in range(len(f) - 1):
            f0, f1 = f[i], f[i + 1]
            if ((f0 < 0 <= f1) or (f0 > 0 >= f1)) and abs(f1 - f0) < 90:
                frac = f0 / (f0 - f1) if f0 != f1 else 0.0
                yield i, frac

    def _time(self, i: int, frac: float) -> datetime:
        """Linear interpolation between hourly samples (minute-level accuracy)."""
        return self.t[i] + (self.t[i + 1] - self.t[i]) * frac

    @staticmethod
    def _window(bodies) -> int:
        slow = {"Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"}
        if any(b in slow for b in bodies):
            return 3
        if "Mars" in bodies:
            return 2
        return 1

    # -- event generators ----------------------------------------------------
    def aspects(self) -> list[CelestialEvent]:
        table = dict(config.MAJOR_ASPECTS)
        if self.s.include_octiles:
            table.update(config.OCTILE_ASPECTS)
        bodies = [b for b in self.s.bodies if b != "Moon" or self.s.include_moon_aspects]
        out: list[CelestialEvent] = []
        for a, b in combinations(bodies, 2):
            if {a, b} == {"Sun", "Moon"}:
                continue  # handled as lunar phases
            la, lb = self.eph.bodies[a].lon, self.eph.bodies[b].lon
            diff = [x - y for x, y in zip(la, lb)]
            for name, (angles, w) in table.items():
                for ang in angles:
                    f = [wrap180(d - ang) for d in diff]
                    for i, frac in self._crossings(f):
                        pos = self._positions(i, frac)
                        score = min(10.0, w * (config.PLANET_WEIGHT[a] + config.PLANET_WEIGHT[b]) / 6 * 10)
                        if name in ("Conjunction", "Opposition", "Square"):
                            impl = "Trend-reversal / volatility watch (hard aspect)"
                        elif name == "Trine":
                            impl = "Trend acceleration or minor turn (soft aspect)"
                        else:
                            impl = "Minor Gann 1/8 harmonic – short-term turn"
                        out.append(CelestialEvent(
                            self._time(i, frac), "Aspect", (a, b),
                            f"{a} {config.ASPECT_SYMBOL[name]} {name} {b} ({int(ang)}°)",
                            score, pos[a], window_days=self._window((a, b)),
                            implication=impl, positions=pos))
        return out

    def lunar_phases(self) -> list[CelestialEvent]:
        if not {"Sun", "Moon"} <= self.eph.bodies.keys():
            return []
        sun, moon = self.eph.bodies["Sun"].lon, self.eph.bodies["Moon"].lon
        diff = [m - s for m, s in zip(moon, sun)]
        out = []
        for ang, label in config.LUNAR_PHASES.items():
            f = [wrap180(d - ang) for d in diff]
            for i, frac in self._crossings(f):
                pos = self._positions(i, frac)
                major = ang in (0.0, 180.0)
                out.append(CelestialEvent(
                    self._time(i, frac), "Lunar Phase", ("Sun", "Moon"),
                    f"{label} at {fmt_zodiac(pos['Moon'])}",
                    6.5 if major else 4.6, pos["Moon"], universal=True, window_days=1,
                    implication="Short-term (weekly/expiry) turn window", positions=pos))
        return out

    def ingresses(self) -> list[CelestialEvent]:
        out = []
        for b in self.s.bodies:
            if b == "Moon":
                continue  # Moon changes sign every ~2.5 days – noise for Gann timing
            lon = self.eph.bodies[b].lon
            for i in range(len(lon) - 1):
                s0, s1 = int(lon[i] // 30), int(lon[i + 1] // 30)
                if s0 == s1:
                    continue
                motion = wrap180(lon[i + 1] - lon[i])
                boundary = (s1 * 30.0) if motion > 0 else (s0 * 30.0)
                f0, f1 = wrap180(lon[i] - boundary), wrap180(lon[i + 1] - boundary)
                frac = f0 / (f0 - f1) if f0 != f1 else 0.0
                entered = s1
                cardinal = entered in config.CARDINAL_SIGNS
                rx = " (Rx)" if motion < 0 else ""
                pos = self._positions(i, frac)
                score = min(10.0, (0.9 if cardinal else 0.5) * config.PLANET_WEIGHT[b] / 3 * 10)
                out.append(CelestialEvent(
                    self._time(i, frac), "Ingress", (b,),
                    f"{b} enters {config.SIGNS[entered]}{rx}" + (" – cardinal point" if cardinal else ""),
                    score, boundary % 360.0, universal=(b == "Sun" and cardinal),
                    window_days=self._window((b,)),
                    implication="Seasonal Gann time point" if cardinal else "Change of planetary tone",
                    positions=pos))
        return out

    def stations(self) -> list[CelestialEvent]:
        out = []
        for b in self.s.bodies:
            if b not in config.STATIONING_BODIES:
                continue
            lon = self.eph.bodies[b].lon
            spd = [wrap180(lon[i + 1] - lon[i]) for i in range(len(lon) - 1)]
            for i in range(len(spd) - 1):
                v0, v1 = spd[i], spd[i + 1]
                if (v0 > 0 >= v1) or (v0 < 0 <= v1):
                    frac = 0.5 + v0 / (v0 - v1)  # speed samples sit at mid-intervals
                    j = i + int(frac)
                    frac -= int(frac)
                    j = min(j, len(lon) - 2)
                    kind = "Stationary Retrograde" if v0 > 0 else "Stationary Direct"
                    pos = self._positions(j, frac)
                    out.append(CelestialEvent(
                        self._time(j, frac), "Station", (b,),
                        f"{b} {kind} at {fmt_zodiac(pos[b])}",
                        min(10.0, 0.9 * config.PLANET_WEIGHT[b] / 3 * 10), pos[b],
                        window_days=self._window((b,)),
                        implication="Trend-reversal watch (planetary station)", positions=pos))
        return out

    def pivot_time_squares(self) -> list[CelestialEvent]:
        """Sun arcs of 90/120/180/240/270/360° from a pivot = time squared."""
        if self.s.pivot_sun_lon is None or "Sun" not in self.eph.bodies:
            return []
        sun = self.eph.bodies["Sun"].lon
        out = []
        for arc in config.PIVOT_SUN_ARCS:
            target = (self.s.pivot_sun_lon + arc) % 360.0
            f = [wrap180(x - target) for x in sun]
            for i, frac in self._crossings(f):
                t = self._time(i, frac)
                if self.s.pivot_ut and t <= self.s.pivot_ut + timedelta(days=5):
                    continue
                pos = self._positions(i, frac)
                label = "Solar return of pivot (360°)" if arc == 360 else f"Sun +{int(arc)}° from pivot"
                out.append(CelestialEvent(
                    t, "Time Square", ("Sun",), f"{label} – time squared",
                    9.0 if arc in (90, 180, 270, 360) else 7.0, target, universal=True, window_days=2,
                    implication="Gann time-from-pivot cycle completion", positions=pos))
        return out

    def price_time_squares(self) -> list[CelestialEvent]:
        """A planet transiting the pivot/reference price expressed in degrees."""
        price = self.s.pivot_price or self.s.reference_price
        if not price:
            return []
        deg = price_to_degree(price)
        out = []
        for b in self.s.bodies:
            if b == "Moon":
                continue
            angles = (0.0, 90.0, 180.0, 270.0) if b == "Sun" else (0.0,)
            lon = self.eph.bodies[b].lon
            for ang in angles:
                target = (deg + ang) % 360.0
                f = [wrap180(x - target) for x in lon]
                for i, frac in self._crossings(f):
                    pos = self._positions(i, frac)
                    out.append(CelestialEvent(
                        self._time(i, frac), "Price-Time Square", (b,),
                        f"{b} at {fmt_zodiac(target)} = price {price:g} (mod 360 = {deg:.1f}°)"
                        + (f" +{int(ang)}°" if ang else ""),
                        min(10.0, 0.8 * config.PLANET_WEIGHT[b] / 3 * 10), target, universal=True,
                        window_days=self._window((b,)),
                        implication="Price squared by time – reversal watch", positions=pos))
        return out

    def run(self) -> list[CelestialEvent]:
        events = self.aspects()
        if self.s.include_lunar_phases and "Moon" in self.s.bodies:
            events += self.lunar_phases()
        if self.s.include_ingresses:
            events += self.ingresses()
        if self.s.include_stations:
            events += self.stations()
        events += self.pivot_time_squares()
        events += self.price_time_squares()
        events = [e for e in events
                  if self.eph.start <= e.time_ut <= self.eph.stop and e.score >= self.s.min_score]
        events.sort(key=lambda e: e.time_ut)
        return events


# ------------------------------------------------------------------ routing --
def route_triggers(events: list[CelestialEvent], segments: list[Segment],
                   reference_price: float | None, cal: HolidayCalendar | None,
                   rulership_filter: bool = True, live_only: bool = False) -> list[TriggerRow]:
    """Map celestial events to market segments in IST, aligned to exchange sessions."""
    rows: list[TriggerRow] = []
    for ev in events:
        for seg in segments:
            bodies = () if (ev.universal or not rulership_filter) else ev.bodies
            syms = symbols_for([seg], bodies)
            if not syms:
                continue
            status, actionable = align_to_session(seg.exchange_session, ev.time_ut, cal)
            if live_only and status != "LIVE":
                continue
            sup = res = math.nan
            if reference_price:
                sup, res = sq9_levels(reference_price, ev.key_degree)
                if seg.strike_step:
                    sup, res = round_to_step(sup, seg.strike_step), round_to_step(res, seg.strike_step)
            notes = []
            if seg.key == "OPTIONS" and is_nifty_expiry(actionable.date(), cal):
                notes.append("Nifty weekly expiry day")
            ist = ut_to_ist(ev.time_ut)
            w = ev.window_days
            notes.append(f"Window {(ist - timedelta(days=w)):%d-%b} → {(ist + timedelta(days=w)):%d-%b}")
            rows.append(TriggerRow(ev, seg, ist, status, actionable, syms, sup, res, "; ".join(notes)))
    # Layer 3: final output guard – no gold/silver may ever be emitted.
    for r in rows:
        r.symbols = filter_allowed(r.symbols)
        assert not any(is_excluded(s) for s in r.symbols)
    return [r for r in rows if r.symbols]
