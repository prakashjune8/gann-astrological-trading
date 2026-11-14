"""State Persistence & User Preferences Engine (Rememberance Protocol).

Persists and restores user settings across application sessions:
- Active script selection
- Theme preference (Dark / Light)
- Coordinate frame (Geocentric / Heliocentric)
- Alert toggles (Chime, Voice, Banner, Ledger)
- Granularity step & custom time inputs
- Harmonic layer toggles (Cardinal, Fixed, Planetary, Equilibrium)
- View mode (Control Deck, 360° Wheel, Dual Split)
- Custom user-added scripts list
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional


@dataclass
class UserPreferences:
    theme: str = "DARK"
    coordinate_frame: str = "GEOCENTRIC"     # "GEOCENTRIC" or "HELIOCENTRIC"
    active_view: str = "DUAL_SPLIT"          # "CONTROL_DECK", "CELESTIAL_WHEEL", "DUAL_SPLIT"
    operating_mode: str = "SIMULATION"       # Forced Simulation Mode (Live Orders Blocked)
    active_script: str = "NIFTY_50"
    time_step: str = "1 Min"                 # "1 Min", "5 Mins", "15 Mins", "1 Hour", "Custom"
    custom_time: str = "13:56"
    station_key: str = "MUMBAI_NSE"

    # Harmonic Layers
    show_cardinal_cross: bool = True
    show_fixed_cross: bool = True
    show_planetary_lines: bool = True
    show_equilibrium_line: bool = True

    # Alert Toggles
    alert_banner: bool = True
    alert_sound: bool = True
    alert_voice: bool = True
    alert_mode: str = "BOTH"                 # "CHIME", "VOICE", "BOTH", "MUTE"

    # Geodetic / Topocentric Parallax Correction
    topocentric_lunar: bool = True           # True = Topocentric Mumbai parallax, False = Standard Geocentric

    # User-added custom scripts
    custom_scripts: list[dict[str, str]] = None

    # Backtest & River Flow Viewport Persistence
    backtest_timeframe: str = "1-Min"
    backtest_custom_minutes: int = 3
    backtest_saved_timestamp: str = ""
    backtest_saved_date: str = ""
    backtest_saved_cursor: int = 750

    def __post_init__(self):
        if self.custom_scripts is None:
            self.custom_scripts = []


class StateManager:
    """Manages persistent JSON state on disk."""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            if getattr(sys, "frozen", False):
                local_appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
                app_dir = os.path.join(local_appdata, "GannCelestialTrackerPro")
                os.makedirs(app_dir, exist_ok=True)
                config_path = os.path.join(app_dir, "user_preferences.json")
                if hasattr(sys, "_MEIPASS") and not os.path.exists(config_path):
                    meipass_cfg = os.path.join(sys._MEIPASS, "user_preferences.json")
                    if os.path.exists(meipass_cfg):
                        import shutil
                        try:
                            shutil.copy2(meipass_cfg, config_path)
                        except Exception:
                            pass
            else:
                base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                config_path = os.path.join(base, "user_preferences.json")
        self.config_path = config_path
        self.prefs = self.load_preferences()

    def load_preferences(self) -> UserPreferences:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    valid_keys = set(UserPreferences.__dataclass_fields__.keys())
                    filtered = {k: v for k, v in data.items() if k in valid_keys}
                    return UserPreferences(**filtered)
            except Exception:
                pass
        return UserPreferences()

    def save_preferences(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(asdict(self.prefs), f, indent=2)
        except Exception as e:
            print(f"Error saving preferences: {e}")
