"""Static configuration: celestial bodies, aspects, weights and app paths."""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "GannCelestialTimer"
APP_TITLE = "Gann Celestial Timer – Indian Markets"

HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"

# Horizons body IDs (geocentric targets).  Order = display order.
BODIES: dict[str, str] = {
    "Sun": "10",
    "Moon": "301",
    "Mercury": "199",
    "Venus": "299",
    "Mars": "499",
    "Jupiter": "599",
    "Saturn": "699",
    "Uranus": "799",
    "Neptune": "899",
    "Pluto": "999",
}

GLYPHS = {
    "Sun": "☉", "Moon": "☽", "Mercury": "☿", "Venus": "♀", "Mars": "♂",
    "Jupiter": "♃", "Saturn": "♄", "Uranus": "♅", "Neptune": "♆", "Pluto": "♇",
}

# Gann weighting – slow/heavy bodies dominate long-term trend changes.
PLANET_WEIGHT = {
    "Sun": 3.0, "Moon": 1.0, "Mercury": 1.0, "Venus": 1.5, "Mars": 2.0,
    "Jupiter": 3.0, "Saturn": 3.0, "Uranus": 2.5, "Neptune": 2.5, "Pluto": 2.5,
}

# Bodies that can station (Sun and Moon never turn retrograde geocentrically).
STATIONING_BODIES = ("Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto")

# Major Gann aspects: name -> (angles in 0..360 measured as lonA - lonB, weight)
MAJOR_ASPECTS: dict[str, tuple[tuple[float, ...], float]] = {
    "Conjunction": ((0.0,), 1.00),
    "Opposition": ((180.0,), 0.95),
    "Square": ((90.0, 270.0), 0.85),
    "Trine": ((120.0, 240.0), 0.60),
}
# Optional Gann 1/8 circle harmonics.
OCTILE_ASPECTS: dict[str, tuple[tuple[float, ...], float]] = {
    "Semi-square (45°)": ((45.0, 315.0), 0.40),
    "Sesqui-square (135°)": ((135.0, 225.0), 0.40),
}

ASPECT_SYMBOL = {
    "Conjunction": "☌", "Opposition": "☍", "Square": "□", "Trine": "△",
    "Semi-square (45°)": "∠", "Sesqui-square (135°)": "⚼",
}

LUNAR_PHASES = {0.0: "New Moon", 90.0: "First Quarter", 180.0: "Full Moon", 270.0: "Last Quarter"}

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_ABBR = ["Ar", "Ta", "Ge", "Cn", "Le", "Vi", "Li", "Sc", "Sg", "Cp", "Aq", "Pi"]
CARDINAL_SIGNS = {0, 3, 6, 9}  # Aries, Cancer, Libra, Capricorn

# Gann seasonal divisions of the solar circle used for time-from-pivot squaring.
PIVOT_SUN_ARCS = (90.0, 120.0, 180.0, 240.0, 270.0, 360.0)


def resource_dir() -> Path:
    """Folder containing bundled read-only resources (works under PyInstaller)."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))


def user_data_dir() -> Path:
    """Writable per-user folder for cache and editable settings."""
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME") or str(Path.home())
    path = Path(base) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_dir() -> Path:
    path = user_data_dir() / "horizons_cache"
    path.mkdir(parents=True, exist_ok=True)
    return path
