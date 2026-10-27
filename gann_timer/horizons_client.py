"""Skill 1 – NASA JPL Horizons API client (dynamic, authenticated ephemeris)."""
from __future__ import annotations

import hashlib
import json
import time as _time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable

import requests

from . import config

_MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
MAX_ROWS_PER_REQUEST = 20_000   # well below Horizons' ~90k line output cap
MAX_WORKERS = 1                 # JPL returns HTTP 503 for concurrent requests – keep serial
MAX_ATTEMPTS = 6


class HorizonsError(RuntimeError):
    pass


@dataclass
class BodySeries:
    name: str
    times: list[datetime] = field(default_factory=list)  # naive UT
    lon: list[float] = field(default_factory=list)       # apparent ecliptic longitude of date, deg
    lat: list[float] = field(default_factory=list)       # ecliptic latitude, deg
    ra: list[float] = field(default_factory=list)        # apparent RA, deg
    dec: list[float] = field(default_factory=list)       # apparent declination, deg


@dataclass
class Ephemeris:
    start: datetime
    stop: datetime
    step_hours: int
    bodies: dict[str, BodySeries]

    @property
    def times(self) -> list[datetime]:
        return next(iter(self.bodies.values())).times


def choose_step_hours(start: datetime, stop: datetime) -> int:
    """Hourly for ≤ ~13 months, coarser for longer spans (interpolation keeps minute accuracy)."""
    days = (stop - start).total_seconds() / 86400
    if days <= 400:
        return 1
    if days <= 1100:
        return 2
    if days <= 3700:
        return 4
    return 12


def _parse_ut(s: str) -> datetime:
    s = s.strip()
    if s.startswith("b"):
        raise HorizonsError("BC dates are not supported by this application.")
    d, hm = s.split(" ")
    y, mon, day = d.split("-")
    h, m = hm.split(":")[:2]
    return datetime(int(y), _MONTHS[mon], int(day), int(h), int(m))


def parse_result(text: str, name: str) -> BodySeries:
    if "$$SOE" not in text:
        snippet = text.strip().splitlines()[-15:]
        raise HorizonsError(f"Horizons returned no ephemeris for {name}:\n" + "\n".join(snippet))
    block = text.split("$$SOE", 1)[1].split("$$EOE", 1)[0]
    series = BodySeries(name)
    for line in block.strip().splitlines():
        cols = [c.strip() for c in line.split(",")]
        if len(cols) < 7:
            continue
        try:
            series.times.append(_parse_ut(cols[0]))
            series.ra.append(float(cols[3]))
            series.dec.append(float(cols[4]))
            series.lon.append(float(cols[5]) % 360.0)
            series.lat.append(float(cols[6]))
        except (ValueError, KeyError) as exc:
            raise HorizonsError(f"Unparseable Horizons row for {name}: {line!r}") from exc
    return series


class HorizonsClient:
    def __init__(self, timeout: float = 60.0, use_cache: bool = True) -> None:
        self.timeout = timeout
        self.use_cache = use_cache
        self.session = requests.Session()
        self.session.headers["User-Agent"] = f"{config.APP_NAME}/1.0 (Gann research desktop app)"

    # ------------------------------------------------------------ low level --
    def _params(self, body_id: str, start: datetime, stop: datetime, step_h: int) -> dict:
        return {
            "format": "json",
            "COMMAND": f"'{body_id}'",
            "OBJ_DATA": "NO",
            "MAKE_EPHEM": "YES",
            "EPHEM_TYPE": "OBSERVER",
            "CENTER": "'500@399'",
            "START_TIME": f"'{start:%Y-%m-%d %H:%M}'",
            "STOP_TIME": f"'{stop:%Y-%m-%d %H:%M}'",
            "STEP_SIZE": f"'{step_h}h'",
            "QUANTITIES": "'2,31'",
            "ANG_FORMAT": "DEG",
            "CSV_FORMAT": "YES",
            "EXTRA_PREC": "YES",
            "CAL_FORMAT": "CAL",
            "TIME_DIGITS": "MINUTES",
        }

    def _fetch_chunk(self, name: str, start: datetime, stop: datetime, step_h: int) -> BodySeries:
        params = self._params(config.BODIES[name], start, stop, step_h)
        key = hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest()
        cache_file = config.cache_dir() / f"{name}_{key}.json"
        if self.use_cache and cache_file.exists():
            text = json.loads(cache_file.read_text(encoding="utf-8"))["result"]
            return parse_result(text, name)

        last_exc: Exception | None = None
        for attempt in range(MAX_ATTEMPTS):
            try:
                r = self.session.get(config.HORIZONS_URL, params=params, timeout=self.timeout)
                if r.status_code == 503:
                    raise HorizonsError("Horizons busy (HTTP 503)")
                r.raise_for_status()
                payload = r.json()
                if "error" in payload:
                    raise HorizonsError(f"Horizons error for {name}: {payload['error']}")
                series = parse_result(payload["result"], name)
                if self.use_cache:
                    cache_file.write_text(json.dumps({"result": payload["result"],
                                                      "signature": payload.get("signature")}),
                                          encoding="utf-8")
                return series
            except HorizonsError as exc:
                if "busy" not in str(exc):
                    raise
                last_exc = exc
            except (requests.RequestException, ValueError) as exc:
                last_exc = exc
            _time.sleep(3 * (attempt + 1))
        raise HorizonsError(f"Failed to download {name} from NASA JPL Horizons: {last_exc}")

    # ----------------------------------------------------------- high level --
    def fetch(self, bodies: list[str], start: datetime, stop: datetime,
              step_hours: int | None = None,
              progress: Callable[[str], None] | None = None) -> Ephemeris:
        """Download geocentric apparent coordinates for *bodies* between UT start and stop."""
        if stop <= start:
            raise HorizonsError("Stop date must be after start date.")
        step_h = step_hours or choose_step_hours(start, stop)
        chunk_span = timedelta(hours=step_h * MAX_ROWS_PER_REQUEST)
        chunks: list[tuple[datetime, datetime]] = []
        cur = start
        while cur < stop:
            nxt = min(stop, cur + chunk_span)
            chunks.append((cur, nxt))
            cur = nxt + timedelta(hours=step_h)

        jobs = [(b, c0, c1) for b in bodies for (c0, c1) in chunks]
        done = 0

        def run(job):
            nonlocal done
            res = self._fetch_chunk(job[0], job[1], job[2], step_h)
            done += 1
            if progress:
                progress(f"NASA JPL Horizons: {done}/{len(jobs)} series downloaded ({job[0]})")
            return job, res

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            results = list(pool.map(run, jobs))

        merged: dict[str, BodySeries] = {b: BodySeries(b) for b in bodies}
        for (name, _c0, _c1), part in sorted(results, key=lambda x: (x[0][0], x[0][1])):
            tgt = merged[name]
            tgt.times += part.times
            tgt.lon += part.lon
            tgt.lat += part.lat
            tgt.ra += part.ra
            tgt.dec += part.dec

        lengths = {len(s.times) for s in merged.values()}
        if len(lengths) != 1 or 0 in lengths:
            raise HorizonsError("Inconsistent sample counts returned by Horizons.")
        return Ephemeris(start, stop, step_h, merged)
