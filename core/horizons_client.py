"""NASA JPL Horizons Ephemeris API Client with Dual-Frame (Geo/Helio) & SQLite Caching.

Queries NASA JPL Horizons REST API for high-precision geocentric and heliocentric
ecliptic coordinates, caching all responses locally to prevent rate limits.
"""
from __future__ import annotations

import json
import os
import sqlite3
import ssl
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

HORIZONS_API_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"

# Center definitions
CENTER_GEOCENTRIC = "500@399"  # Earth geocenter
CENTER_HELIOCENTRIC = "500@10"  # Sun center
CENTER_TOPOCENTRIC_MUMBAI = "coord@399"  # Earth surface site
DEFAULT_TOPOCENTRIC_COORD = "72.8777,18.9750,0"  # Mumbai (NSE Exchange Hub): Lon East, Lat North, Alt km

# Body registry
BODIES: dict[str, dict[str, str]] = {
    "SUN": {"id": "10", "name": "Sun", "geo": True, "helio": False},
    "MOON": {"id": "301", "name": "Moon", "geo": True, "helio": False},
    "MERCURY": {"id": "199", "name": "Mercury", "geo": True, "helio": True},
    "VENUS": {"id": "299", "name": "Venus", "geo": True, "helio": True},
    "EARTH": {"id": "399", "name": "Earth", "geo": False, "helio": True},
    "MARS": {"id": "499", "name": "Mars", "geo": True, "helio": True},
    "JUPITER": {"id": "599", "name": "Jupiter", "geo": True, "helio": True},
    "SATURN": {"id": "699", "name": "Saturn", "geo": True, "helio": True},
    "URANUS": {"id": "799", "name": "Uranus", "geo": True, "helio": True},
    "NEPTUNE": {"id": "899", "name": "Neptune", "geo": True, "helio": True},
    "PLUTO": {"id": "999", "name": "Pluto", "geo": True, "helio": True},
}


@dataclass(frozen=True)
class EphemerisSample:
    utc_time: datetime
    ecliptic_longitude: float  # Decimal degrees 0 <= lon < 360
    ecliptic_latitude: float   # Decimal degrees
    ra_deg: Optional[float] = None
    dec_deg: Optional[float] = None


class HorizonsClient:
    """Robust client for NASA JPL Horizons with persistent SQLite caching."""

    def __init__(self, cache_dir: Optional[str] = None):
        if cache_dir is None:
            if getattr(sys, "frozen", False):
                local_appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
                cache_dir = os.path.join(local_appdata, "GannCelestialTrackerPro", ".cache")
                os.makedirs(cache_dir, exist_ok=True)
                if hasattr(sys, "_MEIPASS"):
                    meipass_db = os.path.join(sys._MEIPASS, ".cache", "horizons_cache.sqlite3")
                    local_db = os.path.join(cache_dir, "horizons_cache.sqlite3")
                    if os.path.exists(meipass_db) and not os.path.exists(local_db):
                        import shutil
                        try:
                            shutil.copy2(meipass_db, local_db)
                        except Exception:
                            pass
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                cache_dir = os.path.join(base_dir, ".cache")
        os.makedirs(cache_dir, exist_ok=True)
        self.db_path = os.path.join(cache_dir, "horizons_cache.sqlite3")
        self._init_db()

        # SSL context
        try:
            import certifi
            self.ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            self.ssl_ctx = ssl._create_unverified_context()

    def _init_db(self):
        """Initialize the SQLite cache table."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ephemeris_cache (
                    cache_key TEXT PRIMARY KEY,
                    raw_csv TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def _build_cache_key(
        self, body_id: str, center: str, start_ut: str, stop_ut: str, step: str, site_coord: Optional[str] = None
    ) -> str:
        coord_suffix = f"|{site_coord}" if site_coord else ""
        return f"{body_id}|{center}|{start_ut}|{stop_ut}|{step}{coord_suffix}"

    def _get_from_cache(self, cache_key: str) -> Optional[str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT raw_csv FROM ephemeris_cache WHERE cache_key = ?", (cache_key,))
            row = cursor.fetchone()
            return row[0] if row else None

    def _save_to_cache(self, cache_key: str, raw_csv: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO ephemeris_cache (cache_key, raw_csv) VALUES (?, ?)",
                (cache_key, raw_csv)
            )
            conn.commit()

    def fetch_ephemeris(
        self,
        body_code: str,
        center: str = CENTER_GEOCENTRIC,
        start_utc: datetime = None,
        stop_utc: datetime = None,
        step_size: str = "1h",
        site_coord: Optional[str] = None,
        topocentric: bool = False,
        max_retries: int = 3
    ) -> list[EphemerisSample]:
        """Fetch ephemeris series for a given body and coordinate center (Geo, Helio, or Topocentric)."""
        body_id = BODIES.get(body_code.upper(), {}).get("id", body_code)

        effective_center = CENTER_TOPOCENTRIC_MUMBAI if (topocentric or center == CENTER_TOPOCENTRIC_MUMBAI) else center
        effective_site = site_coord or (DEFAULT_TOPOCENTRIC_COORD if effective_center == CENTER_TOPOCENTRIC_MUMBAI else None)

        start_str = start_utc.strftime("%Y-%m-%d %H:%M")
        stop_str = stop_utc.strftime("%Y-%m-%d %H:%M")
        cache_key = self._build_cache_key(body_id, effective_center, start_str, stop_str, step_size, effective_site)

        cached_csv = self._get_from_cache(cache_key)
        if cached_csv:
            return self._parse_csv_payload(cached_csv)

        params = {
            "format": "json",
            "COMMAND": f"'{body_id}'",
            "EPHEM_TYPE": "OBSERVER",
            "CENTER": f"'{effective_center}'",
            "START_TIME": f"'{start_str}'",
            "STOP_TIME": f"'{stop_str}'",
            "STEP_SIZE": f"'{step_size}'",
            "QUANTITIES": "'31'",  # 31 = ObsEcLon, ObsEcLat (ecliptic of date)
            "ANG_FORMAT": "DEG",
            "CSV_FORMAT": "YES",
            "OBJ_DATA": "NO",
        }
        if effective_site:
            params["SITE_COORD"] = f"'{effective_site}'"

        url = f"{HORIZONS_API_URL}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "GannEphemerisEngine/2.0 (Automated Quantitative Celestial Tracker)"}
        )

        last_error = None
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, context=self.ssl_ctx, timeout=20) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    result_text = data.get("result", "")

                    if "$$SOE" not in result_text or "$$EOE" not in result_text:
                        raise ValueError(f"JPL Horizons returned no ephemeris block: {result_text[:250]}")

                    soe = result_text.find("$$SOE") + 5
                    eoe = result_text.find("$$EOE")
                    raw_csv = result_text[soe:eoe].strip()

                    # Save to persistent cache
                    self._save_to_cache(cache_key, raw_csv)
                    return self._parse_csv_payload(raw_csv)
            except Exception as e:
                last_error = e
                # Linear backoff on JPL server 503 or network throttling
                time.sleep(1.5 * (attempt + 1))

        raise RuntimeError(f"Failed to fetch ephemeris for body {body_code} after {max_retries} attempts: {last_error}")

    def _parse_csv_payload(self, csv_text: str) -> list[EphemerisSample]:
        """Parse the Horizons CSV table between $$SOE and $$EOE."""
        samples: list[EphemerisSample] = []
        for line in csv_text.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 5:
                continue
            # parts[0]: '2026-Nov-05 00:00'
            date_str = parts[0]
            try:
                dt_utc = datetime.strptime(date_str, "%Y-%b-%d %H:%M").replace(tzinfo=timezone.utc)
                # ObsEcLon, ObsEcLat
                lon = float(parts[3]) % 360.0
                lat = float(parts[4])
                samples.append(EphemerisSample(
                    utc_time=dt_utc,
                    ecliptic_longitude=lon,
                    ecliptic_latitude=lat
                ))
            except Exception:
                continue

        return samples
