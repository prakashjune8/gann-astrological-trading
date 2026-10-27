"""Skill 2 – UT → IST conversion and Indian exchange session alignment."""
from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from . import config

UTC = timezone.utc
# IST is a fixed UTC+05:30 offset with no daylight saving.
IST = timezone(timedelta(hours=5, minutes=30), name="IST")

NSE_OPEN, NSE_CLOSE = time(9, 15), time(15, 30)
MCX_OPEN = time(9, 0)
MCX_CLOSE_US_DST, MCX_CLOSE_US_STD = time(23, 30), time(23, 55)
NIFTY_WEEKLY_EXPIRY_WEEKDAY = 1  # Tuesday (effective 1 Sep 2025)


def ut_to_ist(ut: datetime) -> datetime:
    """Convert a naive-UT or aware datetime to an aware IST datetime."""
    if ut.tzinfo is None:
        ut = ut.replace(tzinfo=UTC)
    return ut.astimezone(IST)


def ist_to_ut(ist: datetime) -> datetime:
    if ist.tzinfo is None:
        ist = ist.replace(tzinfo=IST)
    return ist.astimezone(UTC)


def interpolate_time(t0: datetime, t1: datetime, f0: float, f1: float) -> datetime:
    """Linear zero-crossing between two samples of an angular function."""
    if f0 == f1:
        return t0
    frac = f0 / (f0 - f1)
    return t0 + (t1 - t0) * max(0.0, min(1.0, frac))


def fmt_ist(dt: datetime) -> str:
    return ut_to_ist(dt).strftime("%Y-%m-%d %H:%M IST")


# ---------------------------------------------------------------- holidays --
def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    d = date(year, month, 1)
    d += timedelta(days=(weekday - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def us_dst_active(d: date) -> bool:
    """US DST: 2nd Sunday of March → 1st Sunday of November."""
    start = _nth_weekday(d.year, 3, 6, 2)
    end = _nth_weekday(d.year, 11, 6, 1)
    return start <= d < end


class HolidayCalendar:
    """User-maintained exchange holiday list (holidays.json). No dates are invented."""

    def __init__(self) -> None:
        self.nse: set[date] = set()
        self.mcx: set[date] = set()
        self.path = config.user_data_dir() / "holidays.json"
        if not self.path.exists():
            bundled = config.resource_dir() / "holidays.json"
            if bundled.exists():
                self.path.write_text(bundled.read_text(encoding="utf-8"), encoding="utf-8")
        self.reload()

    def reload(self) -> None:
        self.nse.clear()
        self.mcx.clear()
        try:
            data = json.loads(Path(self.path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        for key, bucket in (("NSE", self.nse), ("MCX", self.mcx)):
            for s in data.get(key, []):
                try:
                    bucket.add(date.fromisoformat(s))
                except ValueError:
                    pass

    def is_holiday(self, exchange: str, d: date) -> bool:
        return d in (self.nse if exchange == "NSE" else self.mcx)


def session_bounds(exchange: str, d: date) -> tuple[datetime, datetime]:
    if exchange == "NSE":
        o, c = NSE_OPEN, NSE_CLOSE
    else:
        o, c = MCX_OPEN, (MCX_CLOSE_US_DST if us_dst_active(d) else MCX_CLOSE_US_STD)
    return datetime.combine(d, o, IST), datetime.combine(d, c, IST)


def is_trading_day(exchange: str, d: date, cal: HolidayCalendar | None) -> bool:
    return d.weekday() < 5 and not (cal and cal.is_holiday(exchange, d))


def align_to_session(exchange: str, event_ut: datetime,
                     cal: HolidayCalendar | None = None) -> tuple[str, datetime]:
    """Return (status, actionable IST time) for an event.

    status: 'LIVE' if inside the session, otherwise 'PRE-OPEN', 'POST-CLOSE' or
    'NON-TRADING DAY' with the actionable time moved to the next session open.
    """
    ist = ut_to_ist(event_ut)
    d = ist.date()
    if is_trading_day(exchange, d, cal):
        o, c = session_bounds(exchange, d)
        if o <= ist <= c:
            return "LIVE", ist
        if ist < o:
            return "PRE-OPEN", o
        status = "POST-CLOSE"
    else:
        status = "NON-TRADING DAY"
    nd = d + timedelta(days=1)
    for _ in range(30):
        if is_trading_day(exchange, nd, cal):
            return status, session_bounds(exchange, nd)[0]
        nd += timedelta(days=1)
    return status, ist


def is_nifty_expiry(d: date, cal: HolidayCalendar | None = None) -> bool:
    """Weekly Nifty expiry = Tuesday, or previous trading day if Tuesday is a holiday."""
    tues = d + timedelta(days=(NIFTY_WEEKLY_EXPIRY_WEEKDAY - d.weekday()) % 7)
    exp = tues
    while not is_trading_day("NSE", exp, cal):
        exp -= timedelta(days=1)
    return exp == d
