"""Root Application Window for Gann Celestial Tracker Pro."""
from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional

import customtkinter as ctk

from audio.alert_audio import AlertAudioEngine
from core.aspect_engine import AspectEngine
from core.backtest_engine import GannBacktestEngine
from core.continuous_tracker import ContinuousCelestialTracker, ContinuousCelestialState
from core.geo_temporal import (
    DEFAULT_STATION, INDIAN_STATIONS, IST, SESSION_FULL_DAY, SESSION_MCX_SUMMER,
    SESSION_MCX_WINTER, SESSION_NSE, calculate_true_solar_noon, get_mcx_session
)
from core.horizons_client import HorizonsClient
from core.market_feed import DEFAULT_SCRIPTS, MarketFeedEngine
from core.price_harmonics import PriceHarmonicsEngine
from reporting.pdf_daily_summary import DailyPdfReportGenerator
from ui.components.academy_guide_view import AcademyGuideView
from ui.components.alert_ledger_view import AlertLedgerView
from ui.components.celestial_wheel_view import CelestialWheelView
from ui.components.control_deck_view import ControlDeckView
from ui.components.custom_script_dialog import CustomScriptDialog
from ui.components.dual_split_view import DualSplitView
from ui.components.top_bar import TopBarComponent
from ui.state_manager import StateManager
from ui.theme import DARK_THEME, LIGHT_THEME, ThemeTokens


class MainWindow(ctk.CTk):
    """Institutional Gann Astro-Harmonic Trading Terminal."""

    def __init__(self):
        super().__init__()

        # State & Preferences
        self.state_mgr = StateManager()
        self.prefs = self.state_mgr.prefs

        # Themes
        self.theme: ThemeTokens = DARK_THEME if self.prefs.theme == "DARK" else LIGHT_THEME
        ctk.set_appearance_mode("dark" if self.prefs.theme == "DARK" else "light")

        self.title("Gann Celestial Tracker Pro • Institutional Astro-Harmonic Terminal")
        self.geometry("1420x920")
        self.minsize(1080, 720)
        self.configure(fg_color=self.theme.bg_primary)

        # Core Engines
        self.feed_engine = MarketFeedEngine()
        self.horizons_client = HorizonsClient()
        self.tracker = ContinuousCelestialTracker(self.horizons_client)
        self.audio_engine = AlertAudioEngine()

        # Restore custom scripts
        if self.prefs.custom_scripts:
            for cs in self.prefs.custom_scripts:
                self.feed_engine.add_custom_script(cs["symbol"], cs["name"])

        # UI Layout Scaffolding
        self._build_layout()

        # Telemetry Cache
        self.latest_trajectory: list[ContinuousCelestialState] = []
        self.latest_aspects: list[dict] = []
        self.latest_price_levels: list[dict] = []
        self.current_cmp = 24200.0

        # Debounce timer for window resizing across DPI scaling boundaries
        self._window_resize_debounce_timer = None
        self.bind("<Configure>", self._on_window_configure)

        # Start Continuous Loop
        self._initial_load()
        self._schedule_live_tick()

    def _build_layout(self):
        # 1. Top Bar
        self.top_bar = TopBarComponent(
            self,
            theme=self.theme,
            on_geo_helio_toggle=self._handle_frame_toggle,
            on_theme_toggle=self._handle_theme_toggle,
            on_view_change=self._handle_view_change,
            on_mode_change=self._handle_mode_change,
            initial_frame=self.prefs.coordinate_frame,
            initial_theme=self.prefs.theme,
            initial_view=self.prefs.active_view,
            initial_mode=self.prefs.operating_mode
        )
        self.top_bar.pack(fill="x", side="top")

        # 2. Sub-Control Strip (Script Selector, Time Granularity, Harmonic Layer Dropdowns, Actions)
        self._build_sub_control_strip()

        # 3. Main Center Workspace (Hosts Views: Control Deck, 360° Wheel, Dual Split, Academy)
        self.center_workspace = ctk.CTkFrame(self, fg_color=self.theme.bg_primary)
        self.center_workspace.pack(fill="both", expand=True)

        self.view_deck = ControlDeckView(self.center_workspace, theme=self.theme)
        self.view_wheel = CelestialWheelView(self.center_workspace, theme=self.theme)
        self.view_split = DualSplitView(self.center_workspace, theme=self.theme)
        self.view_academy = AcademyGuideView(self.center_workspace, theme=self.theme)

        # 4. Bottom Alert Ledger & Status Banner
        self.alert_ledger = AlertLedgerView(self, theme=self.theme)
        self.alert_ledger.pack(fill="x", side="bottom")

        # Activate Saved View
        self._activate_view(self.prefs.active_view)

    def _build_sub_control_strip(self):
        strip = ctk.CTkFrame(self, fg_color=self.theme.bg_secondary, height=44, corner_radius=0)
        strip.pack(fill="x", side="top", pady=(1, 0))

        # Script Selector
        ctk.CTkLabel(strip, text="Instrument:", font=ctk.CTkFont(size=11, weight="bold"), text_color=self.theme.text_secondary).pack(side="left", padx=(14, 4))
        all_scripts = self.feed_engine.get_all_available_scripts()
        script_display_names = [f"{v['name']} ({k})" for k, v in all_scripts.items()]
        self.script_var = ctk.StringVar(value=self.prefs.active_script)

        self.script_menu = ctk.CTkOptionMenu(
            strip,
            values=list(all_scripts.keys()),
            variable=self.script_var,
            command=self._handle_script_change,
            font=ctk.CTkFont(size=11),
            fg_color=self.theme.bg_accent,
            button_color=self.theme.accent_blue,
            width=150,
            height=28
        )
        self.script_menu.pack(side="left", padx=4)

        # Custom Add Button
        ctk.CTkButton(
            strip, text="+ Custom Script", font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=self.theme.bg_accent, text_color=self.theme.accent_green,
            command=self._open_custom_script_dialog, width=105, height=28
        ).pack(side="left", padx=6)

        # Granularity Selector
        ctk.CTkLabel(strip, text="Step:", font=ctk.CTkFont(size=11, weight="bold"), text_color=self.theme.text_secondary).pack(side="left", padx=(12, 4))
        self.step_var = ctk.StringVar(value=self.prefs.time_step)
        ctk.CTkOptionMenu(
            strip,
            values=["1 Min", "5 Mins", "15 Mins", "1 Hour", "Custom"],
            variable=self.step_var,
            command=self._handle_step_change,
            font=ctk.CTkFont(size=11),
            fg_color=self.theme.bg_accent,
            width=90,
            height=28
        ).pack(side="left", padx=4)

        # Custom Time Entry (for exact minute/second inspection)
        self.entry_custom_time = ctk.CTkEntry(
            strip, placeholder_text="13:56", font=ctk.CTkFont(family="Consolas", size=11),
            width=65, height=28
        )
        self.entry_custom_time.insert(0, self.prefs.custom_time)
        self.entry_custom_time.pack(side="left", padx=4)

        ctk.CTkButton(
            strip, text="Inspect", font=ctk.CTkFont(size=10),
            fg_color=self.theme.bg_accent, text_color=self.theme.text_primary,
            command=self._handle_custom_time_inspect, width=60, height=28
        ).pack(side="left", padx=2)

        # Lunar Topocentric Parallax Toggle (Mumbai Observatory 72.88°E, 18.98°N)
        topo_active = getattr(self.prefs, "topocentric_lunar", True)
        self.btn_topo_moon = ctk.CTkButton(
            strip,
            text="Topo Moon (Mumbai)" if topo_active else "Geo Moon",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=self.theme.bg_accent,
            text_color=self.theme.accent_amber if topo_active else self.theme.text_secondary,
            command=self._toggle_topo_moon,
            width=135,
            height=28
        )
        self.btn_topo_moon.pack(side="left", padx=6)

        # Harmonic Layers Dropdown Filter
        ctk.CTkLabel(strip, text="Layers:", font=ctk.CTkFont(size=11, weight="bold"), text_color=self.theme.text_secondary).pack(side="left", padx=(14, 4))
        self.layers_var = ctk.StringVar(value="All Overlays Active")
        ctk.CTkOptionMenu(
            strip,
            values=["All Overlays Active", "Only Cardinal (90°)", "Only Fixed (45°)", "Planetary Lines", "50% Eq Only"],
            variable=self.layers_var,
            command=self._handle_layer_change,
            font=ctk.CTkFont(size=11),
            fg_color=self.theme.bg_accent,
            width=145,
            height=28
        ).pack(side="left", padx=4)

        # Right-side action buttons: Academy Guide & PDF Export
        ctk.CTkButton(
            strip, text="PDF Summary", font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=self.theme.accent_blue, text_color="white",
            command=self._export_pdf_summary, width=95, height=28
        ).pack(side="right", padx=(4, 14))

        ctk.CTkButton(
            strip, text="Academy Guide", font=ctk.CTkFont(size=10),
            fg_color=self.theme.bg_accent, text_color=self.theme.accent_purple,
            command=self._toggle_academy_view, width=95, height=28
        ).pack(side="right", padx=4)

    def _activate_view(self, view_key: str):
        for v in [self.view_deck, self.view_wheel, self.view_split, self.view_academy]:
            v.pack_forget()

        if view_key == "CONTROL_DECK":
            self.view_deck.pack(fill="both", expand=True)
        elif view_key == "CELESTIAL_WHEEL":
            self.view_wheel.pack(fill="both", expand=True)
        elif view_key == "ACADEMY":
            self.view_academy.pack(fill="both", expand=True)
        else:  # DUAL_SPLIT
            self.view_split.pack(fill="both", expand=True)

        self.prefs.active_view = view_key
        self.state_mgr.save_preferences()

    def _handle_view_change(self, view_key: str):
        self._activate_view(view_key)

    def _toggle_academy_view(self):
        if self.prefs.active_view == "ACADEMY":
            self._activate_view("DUAL_SPLIT")
        else:
            self._activate_view("ACADEMY")

    def _handle_frame_toggle(self, new_frame: str):
        self.prefs.coordinate_frame = new_frame
        self.state_mgr.save_preferences()
        self.alert_ledger.add_event("SYSTEM", f"Switched Coordinate Frame to {new_frame}.", datetime.now().strftime("%H:%M:%S IST"))
        self._compute_and_refresh()

    def _handle_theme_toggle(self, new_theme: str):
        self.prefs.theme = new_theme
        self.state_mgr.save_preferences()
        # Inform user to reload for full palette swap
        self.alert_ledger.add_event("SYSTEM", f"Theme set to {new_theme}. Theme preference persisted.", datetime.now().strftime("%H:%M:%S IST"))

    def _handle_mode_change(self, new_mode: str):
        self.prefs.operating_mode = new_mode
        self.state_mgr.save_preferences()
        self.alert_ledger.add_event("MODE", f"Operating Mode changed to {new_mode}.", datetime.now().strftime("%H:%M:%S IST"))
        self._compute_and_refresh()

    def _handle_script_change(self, script_key: str):
        self.prefs.active_script = script_key
        self.state_mgr.save_preferences()
        self.alert_ledger.add_event("SCRIPT", f"Switched active instrument to {script_key}.", datetime.now().strftime("%H:%M:%S IST"))
        self._compute_and_refresh()

    def _handle_step_change(self, step_choice: str):
        self.prefs.time_step = step_choice
        self.state_mgr.save_preferences()
        self._compute_and_refresh()

    def _handle_custom_time_inspect(self):
        t_str = self.entry_custom_time.get().strip()
        self.prefs.custom_time = t_str
        self.state_mgr.save_preferences()
        self.alert_ledger.add_event("TIME", f"Inspecting exact custom time node: {t_str} IST.", datetime.now().strftime("%H:%M:%S IST"))
        self._compute_and_refresh()

    def _handle_layer_change(self, layer_choice: str):
        self._compute_and_refresh()

    def _toggle_topo_moon(self):
        curr = getattr(self.prefs, "topocentric_lunar", True)
        self.prefs.topocentric_lunar = not curr
        self.state_mgr.save_preferences()
        is_topo = self.prefs.topocentric_lunar
        self.btn_topo_moon.configure(
            text="Topo Moon (Mumbai)" if is_topo else "Geo Moon",
            text_color=self.theme.accent_amber if is_topo else self.theme.text_secondary
        )
        mode_str = "Topocentric (Mumbai Parallax 72.88°E, 18.98°N)" if is_topo else "Geocentric (Earth Center 500@399)"
        self.alert_ledger.add_event("LUNAR", f"Switched Moon Ephemeris to {mode_str}.", datetime.now().strftime("%H:%M:%S IST"))
        self._compute_and_refresh()

    def _on_window_configure(self, event):
        """Debounce resize and cross-monitor DPI transition events (150ms)."""
        if event.widget == self:
            if self._window_resize_debounce_timer is not None:
                self.after_cancel(self._window_resize_debounce_timer)
            self._window_resize_debounce_timer = self.after(150, self._handle_debounced_window_resize)

    def _handle_debounced_window_resize(self):
        self._window_resize_debounce_timer = None
        # Redraw celestial wheel at the new monitor's native geometry / DPI
        if hasattr(self, "view_wheel") and self.view_wheel.winfo_exists():
            self.view_wheel.redraw()
        if hasattr(self, "view_split") and self.view_split.winfo_exists():
            self.view_split.wheel_view.redraw()

    def _open_custom_script_dialog(self):
        def _on_add(symbol: str, name: str) -> tuple[bool, str]:
            ok, msg = self.feed_engine.add_custom_script(symbol, name)
            if ok:
                # Update prefs
                self.prefs.custom_scripts = [
                    {"symbol": v["symbol"], "name": v["name"]}
                    for v in self.feed_engine.custom_scripts.values()
                ]
                self.state_mgr.save_preferences()
                # Update menu
                all_s = self.feed_engine.get_all_available_scripts()
                self.script_menu.configure(values=list(all_s.keys()))
                self.alert_ledger.add_event("SCRIPT", f"Added custom script: {symbol}.", datetime.now().strftime("%H:%M:%S IST"))
            return ok, msg

        CustomScriptDialog(self, theme=self.theme, on_add_callback=_on_add)

    def _initial_load(self):
        self._compute_and_refresh()

    def _schedule_live_tick(self):
        now_ist = datetime.now(IST)
        self.top_bar.update_clock(now_ist)

        # Periodic refresh every 60 seconds
        self.after(1000, self._schedule_live_tick)

    def _compute_and_refresh(self):
        now_ist = datetime.now(IST)
        target_date = now_ist.date()

        # 1. Fetch Market Snapshot
        snap = self.feed_engine.fetch_snapshot(self.prefs.active_script)
        self.current_cmp = snap.last_price

        # Check if exchange is closed (Trading Holiday or Weekend)
        if snap.market_status in ("EXCHANGE_CLOSED", "WEEKEND_CLOSED"):
            self.alert_ledger.add_event(
                "EXCHANGE",
                f"{snap.symbol} ({snap.name}): {snap.status_message}",
                now_ist.strftime("%H:%M:%S IST")
            )

        # 2. Determine session
        session = SESSION_NSE
        if "MCX" in snap.name or "CRUDE" in self.prefs.active_script or "COPPER" in self.prefs.active_script:
            session = get_mcx_session(target_date)

        # 3. Calculate True Solar Noon
        station = INDIAN_STATIONS.get(self.prefs.station_key, DEFAULT_STATION)
        solar_noon = calculate_true_solar_noon(target_date, station)

        # 4. Planetary Telemetry (Earth or Sun Center)
        is_helio = (self.prefs.coordinate_frame == "HELIOCENTRIC")
        bodies_to_track = ["MERCURY", "VENUS", "MARS", "JUPITER", "SATURN", "URANUS", "NEPTUNE", "PLUTO"]
        if is_helio:
            bodies_to_track.insert(0, "EARTH")
        else:
            bodies_to_track.insert(0, "MOON")
            bodies_to_track.insert(0, "SUN")

        planets_telemetry = {}
        wheel_planets = {}
        topo_lunar = getattr(self.prefs, "topocentric_lunar", True)
        for b in bodies_to_track[:10]:
            try:
                traj = self.tracker.track_body(
                    b,
                    target_date,
                    session=session,
                    step_minutes=30,
                    topocentric_lunar=topo_lunar
                )
                if traj:
                    last_pt = traj[-1]
                    lon = last_pt.helio_longitude if is_helio else last_pt.geo_longitude
                    zod = last_pt.helio_zodiac if is_helio else last_pt.geo_zodiac
                    vel = last_pt.helio_velocity_deg_per_hour if is_helio else last_pt.geo_velocity_deg_per_hour
                    state_str = "DIRECT" if is_helio else last_pt.geo_motion_state

                    if lon is not None and zod is not None:
                        planets_telemetry[b] = {
                            "lon": lon,
                            "zodiac": zod.format_dms(),
                            "speed": vel or 0.0,
                            "state": state_str
                        }
                        wheel_planets[b] = lon
            except Exception:
                pass

        # 5. Harmonic Price Levels
        price_lons = {k: v["lon"] for k, v in planets_telemetry.items()}
        raw_price_levels: list[dict] = []

        layer_choice = self.layers_var.get()

        if layer_choice in ["All Overlays Active", "Only Cardinal (90°)"]:
            for pl in PriceHarmonicsEngine.calculate_cardinal_cross(self.current_cmp):
                raw_price_levels.append({"label": pl.label, "type": pl.level_type, "price": pl.price, "distance": pl.distance_from_cmp})

        if layer_choice in ["All Overlays Active", "Only Fixed (45°)"]:
            for pl in PriceHarmonicsEngine.calculate_fixed_cross(self.current_cmp):
                raw_price_levels.append({"label": pl.label, "type": pl.level_type, "price": pl.price, "distance": pl.distance_from_cmp})

        if layer_choice in ["All Overlays Active", "Planetary Lines"]:
            for pl in PriceHarmonicsEngine.calculate_planetary_price_levels(price_lons, self.current_cmp):
                raw_price_levels.append({"label": pl.label, "type": pl.level_type, "price": pl.price, "distance": pl.distance_from_cmp})

        if layer_choice in ["All Overlays Active", "50% Eq Only"]:
            eq = PriceHarmonicsEngine.calculate_daily_equilibrium(snap.high_price, snap.low_price, self.current_cmp)
            raw_price_levels.insert(0, {"label": eq.label, "type": eq.level_type, "price": eq.price, "distance": eq.distance_from_cmp})

        raw_price_levels.sort(key=lambda x: abs(x["distance"]))
        self.latest_price_levels = raw_price_levels

        # 6. Aspects
        aspects_list = AspectEngine.find_aspects_between_bodies(wheel_planets, max_orb=3.5, timestamp_ist=now_ist)
        wheel_aspects = [
            {"b1": a.body_a, "b2": a.body_b, "color": a.color_hex, "is_exact": a.is_exact}
            for a in aspects_list
        ]
        self.latest_aspects = wheel_aspects

        # 7. Price Needle Degree on Wheel
        price_angle = PriceHarmonicsEngine.price_to_wheel_angle(self.current_cmp)

        # 8. Assemble Snapshot Dictionary
        start_dt = datetime.combine(target_date, session.start_time, tzinfo=IST)
        end_dt = datetime.combine(target_date, session.end_time, tzinfo=IST)
        total_sec = max(1.0, (end_dt - start_dt).total_seconds())
        elapsed_sec = max(0.0, min(total_sec, (now_ist - start_dt).total_seconds()))
        prog_pct = (elapsed_sec / total_sec) * 100.0
        prog_deg = (prog_pct / 100.0) * 360.0

        snapshot = {
            "cmp": self.current_cmp,
            "script_name": snap.name,
            "market_status": snap.market_status,
            "status_message": snap.status_message,
            "session_pct": prog_pct,
            "session_deg": prog_deg,
            "noon_time": solar_noon.strftime("%H:%M:%S IST"),
            "equilibrium_price": (snap.high_price + snap.low_price) / 2.0,
            "planets": planets_telemetry,
            "price_levels": self.latest_price_levels
        }

        # 9. Update Active Views
        self.view_deck.update_telemetry(snapshot)
        self.view_wheel.update_wheel_data(wheel_planets, wheel_aspects, price_angle)
        self.view_split.update_all(snapshot, wheel_planets, wheel_aspects, price_angle)

    def _export_pdf_summary(self):
        target_date = datetime.now(IST).date()
        out_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pdf_path = os.path.join(out_dir, f"Gann_Daily_Summary_{self.prefs.active_script}_{target_date.strftime('%Y%m%d')}.pdf")

        snap = self.feed_engine.fetch_snapshot(self.prefs.active_script)
        planets_data = [
            {"name": k, "longitude": v.get("lon", 0.0), "zodiac": v.get("zodiac", ""), "velocity": v.get("speed", 0.0), "state": v.get("state", "DIRECT")}
            for k, v in getattr(self.view_deck, "planet_cards", {}).items()
        ]

        timing_nodes = [
            {"label": "180° Session Midpoint", "time_ist": "12:22:30 IST", "circle_deg": "180.0°", "significance": "50% Temporal Equilibrium"},
            {"label": "True Solar Noon (Mumbai)", "time_ist": "12:22:12 IST", "circle_deg": "180.0°", "significance": "Astronomical Meridian Transit"},
            {"label": "90° Square Harmonic Node", "time_ist": "13:56:15 IST", "circle_deg": "270.0°", "significance": "Major Price-Time Squaring Pivot"},
            {"label": "120° Trine Harmonic Node", "time_ist": "14:27:30 IST", "circle_deg": "300.0°", "significance": "Harmonic Cycle Equilibrium"}
        ]

        try:
            DailyPdfReportGenerator.generate_report(
                output_pdf_path=pdf_path,
                target_date=target_date,
                script_name=snap.name,
                market_cmp=self.current_cmp,
                day_high=snap.high_price,
                day_low=snap.low_price,
                coord_frame=self.prefs.coordinate_frame,
                planetary_data=planets_data,
                price_levels=self.latest_price_levels,
                timing_nodes=timing_nodes
            )
            self.alert_ledger.add_event("PDF", f"Summary PDF generated successfully at: {os.path.basename(pdf_path)}", datetime.now().strftime("%H:%M:%S IST"))
            self.audio_engine.trigger_alert("CHIME", "Daily PDF Summary Generated")
        except Exception as e:
            self.alert_ledger.add_event("ERROR", f"PDF compilation error: {e}", datetime.now().strftime("%H:%M:%S IST"))
