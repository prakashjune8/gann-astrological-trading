"""Root Application Window for Gann Celestial Tracker Pro."""
from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional

import customtkinter as ctk

from audio.alert_audio import AlertAudioEngine
from core.aspect_engine import AspectEngine
from core.backtest_engine import GannBacktestEngine
from core.broker_client import BrokerAuthManager, OrderManagementSystem, RealTimeConfluenceRouter
from core.confluence_engine import ConfluenceEngine
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
from ui.components.backtest_dashboard_view import BacktestDashboardView
from ui.components.celestial_wheel_view import CelestialWheelView
from ui.components.control_deck_view import ControlDeckView
from ui.components.custom_script_dialog import CustomScriptDialog
from ui.components.dual_split_view import DualSplitView
from ui.components.options_chain_view import OptionsChainView
from ui.components.top_bar import TopBarComponent
from ui.state_manager import StateManager
from ui.theme import DARK_THEME, LIGHT_THEME, ThemeTokens

STATION_MAP = {
    "Mumbai (NSE)": "MUMBAI_NSE",
    "New Delhi": "DELHI_NORTH",
    "Ujjain (Prime Meridian)": "UJJAIN_ZERO",
    "Mirzapur (IST Axis)": "IST_MERIDIAN"
}
STATION_MAP_REV = {v: k for k, v in STATION_MAP.items()}


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
        self.geometry("1440x940")
        self.minsize(1120, 740)
        self.configure(fg_color=self.theme.bg_primary)

        # Core Engines
        self.feed_engine = MarketFeedEngine()
        self.horizons_client = HorizonsClient()
        self.tracker = ContinuousCelestialTracker(self.horizons_client)
        self.audio_engine = AlertAudioEngine()
        self.auth_mgr = BrokerAuthManager()
        self.oms = OrderManagementSystem(auth_mgr=self.auth_mgr)
        self.confluence_router = RealTimeConfluenceRouter(oms=self.oms)

        # Operational States
        self.is_custom_time_active: bool = False
        self.custom_eval_time: Optional[datetime] = None
        self.simulated_cmp: Optional[float] = None
        self.is_simulation_playing: bool = False
        self.simulation_timer_id = None
        self.backtest_window = None

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

        # 2. Primary Sub-Control Strip (Instrument, Station, Layers, Parallax)
        self._build_sub_control_strip()

        # 3. Secondary Temporal Stepper & Simulation Strip (Time Travel, Steppers, Simulation)
        self._build_temporal_strip()

        # 4. Main Center Workspace (Hosts Views: Control Deck, 360° Wheel, Dual Split, Academy)
        self.center_workspace = ctk.CTkFrame(self, fg_color=self.theme.bg_primary)
        self.center_workspace.pack(fill="both", expand=True)

        self.view_deck = ControlDeckView(self.center_workspace, theme=self.theme)
        self.view_wheel = CelestialWheelView(self.center_workspace, theme=self.theme)
        self.view_split = DualSplitView(self.center_workspace, theme=self.theme)
        self.view_academy = AcademyGuideView(self.center_workspace, theme=self.theme)
        self.view_options = OptionsChainView(self.center_workspace, theme=self.theme)

        # 5. Bottom Alert Ledger & Status Banner
        self.alert_ledger = AlertLedgerView(self, theme=self.theme)
        self.alert_ledger.pack(fill="x", side="bottom")

        # Activate Saved View
        self._activate_view(self.prefs.active_view)

    def _build_sub_control_strip(self):
        self.strip = ctk.CTkFrame(self, fg_color=self.theme.bg_secondary, height=44, corner_radius=0)
        self.strip.pack(fill="x", side="top", pady=(1, 0))

        # Script Selector
        ctk.CTkLabel(self.strip, text="Instrument:", font=ctk.CTkFont(size=11, weight="bold"), text_color=self.theme.text_secondary).pack(side="left", padx=(14, 4))
        all_scripts = self.feed_engine.get_all_available_scripts()
        self.script_var = ctk.StringVar(value=self.prefs.active_script)

        self.script_menu = ctk.CTkOptionMenu(
            self.strip,
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
            self.strip, text="+ Custom Script", font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=self.theme.bg_accent, text_color=self.theme.accent_green,
            command=self._open_custom_script_dialog, width=105, height=28
        ).pack(side="left", padx=4)

        # Station Selector Dropdown
        ctk.CTkLabel(self.strip, text="Station:", font=ctk.CTkFont(size=11, weight="bold"), text_color=self.theme.text_secondary).pack(side="left", padx=(10, 4))
        curr_station_key = getattr(self.prefs, "station_key", "MUMBAI_NSE")
        curr_station_name = STATION_MAP_REV.get(curr_station_key, "Mumbai (NSE)")
        self.station_var = ctk.StringVar(value=curr_station_name)

        self.station_menu = ctk.CTkOptionMenu(
            self.strip,
            values=list(STATION_MAP.keys()),
            variable=self.station_var,
            command=self._handle_station_change,
            font=ctk.CTkFont(size=11),
            fg_color=self.theme.bg_accent,
            button_color=self.theme.accent_blue,
            width=140,
            height=28
        )
        self.station_menu.pack(side="left", padx=4)

        # Harmonic Layers Dropdown Filter
        ctk.CTkLabel(self.strip, text="Layers:", font=ctk.CTkFont(size=11, weight="bold"), text_color=self.theme.text_secondary).pack(side="left", padx=(10, 4))
        self.layers_var = ctk.StringVar(value="All Overlays Active")
        self.layer_menu = ctk.CTkOptionMenu(
            self.strip,
            values=["All Overlays Active", "Only Cardinal (90°)", "Only Fixed (45°)", "Planetary Lines", "50% Eq Only", "8-Octaves (Cymatic)"],
            variable=self.layers_var,
            command=self._handle_layer_change,
            font=ctk.CTkFont(size=11),
            fg_color=self.theme.bg_accent,
            width=150,
            height=28
        )
        self.layer_menu.pack(side="left", padx=4)

        # Lunar Topocentric Parallax Toggle (Mumbai Observatory 72.88°E, 18.98°N)
        topo_active = getattr(self.prefs, "topocentric_lunar", True)
        self.btn_topo_moon = ctk.CTkButton(
            self.strip,
            text="Topo Moon (Parallax)" if topo_active else "Geo Moon (Core)",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=self.theme.bg_accent,
            text_color=self.theme.accent_amber if topo_active else self.theme.text_secondary,
            command=self._toggle_topo_moon,
            width=135,
            height=28
        )
        self.btn_topo_moon.pack(side="left", padx=6)

        # Right-side action buttons: Quant Workstation Launch, Live Switch Toggle, Academy Guide & PDF Export
        self.btn_launch_quant = ctk.CTkButton(
            self.strip,
            text="📈 Launch Quant Workstation",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=self.theme.accent_blue,
            hover_color=self.theme.border_color,
            text_color="#ffffff",
            command=self.launch_quant_workstation,
            width=185,
            height=28
        )
        self.btn_launch_quant.pack(side="right", padx=(4, 12))

        self.btn_live_exec_toggle = ctk.CTkButton(
            self.strip,
            text="🛡 LIVE BLOCKED",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=self.theme.bg_accent,
            hover_color=self.theme.border_color,
            text_color=self.theme.accent_amber,
            command=self._toggle_live_execution_switch,
            width=140,
            height=28
        )
        self.btn_live_exec_toggle.pack(side="right", padx=(4, 6))

        ctk.CTkButton(
            self.strip, text="PDF Summary", font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=self.theme.accent_blue, text_color="white",
            command=self._export_pdf_summary, width=95, height=28
        ).pack(side="right", padx=4)

        ctk.CTkButton(
            self.strip, text="Academy Guide", font=ctk.CTkFont(size=10),
            fg_color=self.theme.bg_accent, text_color=self.theme.accent_purple,
            command=self._toggle_academy_view, width=95, height=28
        ).pack(side="right", padx=4)

    def _build_temporal_strip(self):
        """Secondary strip dedicated to Time Stepping, Node Inspection, and Simulation controls."""
        self.temporal_strip = ctk.CTkFrame(self, fg_color=self.theme.bg_card, height=40, corner_radius=0)
        self.temporal_strip.pack(fill="x", side="top", pady=(1, 0))

        # Granularity Selector
        ctk.CTkLabel(self.temporal_strip, text="Step:", font=ctk.CTkFont(size=11, weight="bold"), text_color=self.theme.text_secondary).pack(side="left", padx=(14, 4))
        self.step_var = ctk.StringVar(value=self.prefs.time_step)
        ctk.CTkOptionMenu(
            self.temporal_strip,
            values=["1 Min", "5 Mins", "15 Mins", "1 Hour"],
            variable=self.step_var,
            command=self._handle_step_change,
            font=ctk.CTkFont(size=11),
            fg_color=self.theme.bg_accent,
            width=85,
            height=26
        ).pack(side="left", padx=4)

        # Custom Time Entry (for exact minute/second inspection)
        ctk.CTkLabel(self.temporal_strip, text="Inspect Time:", font=ctk.CTkFont(size=11, weight="bold"), text_color=self.theme.text_secondary).pack(side="left", padx=(8, 4))
        self.entry_custom_time = ctk.CTkEntry(
            self.temporal_strip, placeholder_text="13:56", font=ctk.CTkFont(family="Consolas", size=11),
            width=65, height=26
        )
        self.entry_custom_time.insert(0, self.prefs.custom_time)
        self.entry_custom_time.pack(side="left", padx=2)
        self.entry_custom_time.bind("<Return>", lambda e: self._handle_custom_time_inspect())

        ctk.CTkButton(
            self.temporal_strip, text="Inspect", font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=self.theme.accent_blue, text_color="white",
            command=self._handle_custom_time_inspect, width=58, height=26
        ).pack(side="left", padx=2)

        # Time Steppers
        for label, delta in [("-15m", -15), ("-5m", -5), ("+5m", 5), ("+15m", 15)]:
            ctk.CTkButton(
                self.temporal_strip, text=label, font=ctk.CTkFont(size=10),
                fg_color=self.theme.bg_accent, text_color=self.theme.text_primary,
                command=lambda d=delta: self._step_time(d), width=42, height=26
            ).pack(side="left", padx=2)

        # Reset to Live Button / Mode Indicator
        self.btn_live_toggle = ctk.CTkButton(
            self.temporal_strip,
            text="[LIVE NOW]",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=self.theme.bg_accent,
            text_color=self.theme.accent_green,
            command=self._reset_to_live_time,
            width=90,
            height=26
        )
        self.btn_live_toggle.pack(side="left", padx=6)

        # Simulation Controls Frame
        self.sim_frame = ctk.CTkFrame(self.temporal_strip, fg_color="transparent")
        self.sim_frame.pack(side="left", padx=8)

        self.btn_sim_play = ctk.CTkButton(
            self.sim_frame,
            text="▶ Play Day",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=self.theme.accent_amber,
            text_color="#0f172a",
            command=self._toggle_simulation_play,
            width=75,
            height=26
        )
        self.btn_sim_play.pack(side="left", padx=4)

        # Simulated CMP Overrider
        ctk.CTkLabel(self.sim_frame, text="Sim CMP:", font=ctk.CTkFont(size=10), text_color=self.theme.text_secondary).pack(side="left", padx=(6, 2))
        self.entry_sim_cmp = ctk.CTkEntry(
            self.sim_frame, placeholder_text="24500", font=ctk.CTkFont(family="Consolas", size=10),
            width=70, height=26
        )
        self.entry_sim_cmp.pack(side="left", padx=2)
        self.entry_sim_cmp.bind("<Return>", lambda e: self._handle_set_sim_cmp())

        ctk.CTkButton(
            self.sim_frame, text="Set CMP", font=ctk.CTkFont(size=9),
            fg_color=self.theme.bg_accent, text_color=self.theme.text_primary,
            command=self._handle_set_sim_cmp, width=54, height=26
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            self.sim_frame, text="Reset", font=ctk.CTkFont(size=9),
            fg_color=self.theme.bg_accent, text_color=self.theme.accent_red,
            command=self._handle_reset_sim_cmp, width=44, height=26
        ).pack(side="left", padx=2)

    def _activate_view(self, view_key: str):
        for v in [self.view_deck, self.view_wheel, self.view_split, self.view_academy, self.view_options]:
            v.pack_forget()

        if view_key == "CONTROL_DECK":
            self.view_deck.pack(fill="both", expand=True)
        elif view_key == "CELESTIAL_WHEEL":
            self.view_wheel.pack(fill="both", expand=True)
        elif view_key == "ACADEMY":
            self.view_academy.pack(fill="both", expand=True)
        elif view_key == "BACKTEST":
            self.view_split.pack(fill="both", expand=True)
            self.launch_quant_workstation()
            view_key = "DUAL_SPLIT"
        elif view_key == "OPTIONS_CHAIN":
            self.view_options.pack(fill="both", expand=True)
        else:  # DUAL_SPLIT
            self.view_split.pack(fill="both", expand=True)

        self.prefs.active_view = view_key
        self.state_mgr.save_preferences()

    def launch_quant_workstation(self):
        """Launches the dedicated maximized CTkToplevel Quant Workstation."""
        from ui.windows.backtest_window import BacktestQuantWorkstationWindow
        if self.backtest_window is not None and self.backtest_window.winfo_exists():
            self.backtest_window.bring_to_front()
            self.alert_ledger.add_event("SYSTEM", "Quant Workstation brought to foreground.", datetime.now().strftime("%H:%M:%S IST"))
        else:
            self.backtest_window = BacktestQuantWorkstationWindow(
                self,
                theme=self.theme
            )
            self.alert_ledger.add_event("SYSTEM", "Quant Workstation launched in dedicated maximized window.", datetime.now().strftime("%H:%M:%S IST"))

    def on_backtest_window_closed(self):
        """Callback invoked when BacktestQuantWorkstationWindow is closed."""
        self.backtest_window = None
        self.alert_ledger.add_event("SYSTEM", "Quant Workstation session closed.", datetime.now().strftime("%H:%M:%S IST"))

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
        """Dynamic real-time theme swapping across all views without requiring app restart."""
        self.prefs.theme = new_theme
        self.state_mgr.save_preferences()
        self.theme = DARK_THEME if new_theme == "DARK" else LIGHT_THEME
        ctk.set_appearance_mode("dark" if new_theme == "DARK" else "light")
        self.configure(fg_color=self.theme.bg_primary)
        self.center_workspace.configure(fg_color=self.theme.bg_primary)

        # Propagate theme dynamically across all UI components
        if hasattr(self, "top_bar"):
            self.top_bar.apply_theme(self.theme)
        if hasattr(self, "strip"):
            self.strip.configure(fg_color=self.theme.bg_secondary)
        if hasattr(self, "temporal_strip"):
            self.temporal_strip.configure(fg_color=self.theme.bg_card)
        if hasattr(self, "view_deck"):
            self.view_deck.apply_theme(self.theme)
        if hasattr(self, "view_wheel"):
            self.view_wheel.apply_theme(self.theme)
        if hasattr(self, "view_split"):
            self.view_split.apply_theme(self.theme)
        if hasattr(self, "view_options"):
            self.view_options.apply_theme(self.theme)
        if self.backtest_window is not None and self.backtest_window.winfo_exists():
            try:
                self.backtest_window.configure(fg_color=self.theme.bg_primary)
                if hasattr(self.backtest_window, "dashboard_view"):
                    self.backtest_window.dashboard_view.apply_theme(self.theme)
            except Exception:
                pass
        if hasattr(self, "alert_ledger"):
            self.alert_ledger.apply_theme(self.theme)

        self.alert_ledger.add_event("THEME", f"Dynamic theme swap applied: {new_theme} Mode.", datetime.now().strftime("%H:%M:%S IST"))
        self._compute_and_refresh()

    def _handle_mode_change(self, new_mode: str):
        self.prefs.operating_mode = new_mode
        self.state_mgr.save_preferences()
        self.alert_ledger.add_event("MODE", f"Operating Mode changed to {new_mode}.", datetime.now().strftime("%H:%M:%S IST"))
        self._compute_and_refresh()

    def _handle_script_change(self, script_key: str):
        self.prefs.active_script = script_key
        self.state_mgr.save_preferences()
        self.simulated_cmp = None  # Reset simulation CMP on script change
        self.alert_ledger.add_event("SCRIPT", f"Switched active instrument to {script_key}.", datetime.now().strftime("%H:%M:%S IST"))
        self._compute_and_refresh()

    def _handle_station_change(self, station_name: str):
        station_key = STATION_MAP.get(station_name, "MUMBAI_NSE")
        self.prefs.station_key = station_key
        self.state_mgr.save_preferences()
        self.alert_ledger.add_event("STATION", f"Active Observer Station set to: {station_name}.", datetime.now().strftime("%H:%M:%S IST"))
        self._compute_and_refresh()

    def _handle_step_change(self, step_choice: str):
        self.prefs.time_step = step_choice
        self.state_mgr.save_preferences()
        self._compute_and_refresh()

    def _handle_custom_time_inspect(self):
        t_str = self.entry_custom_time.get().strip()
        now_ist = datetime.now(IST)
        try:
            parts = [int(p) for p in t_str.split(":")]
            h = parts[0]
            m = parts[1] if len(parts) > 1 else 0
            s = parts[2] if len(parts) > 2 else 0
            inspected_time = time(h, m, s)
            self.custom_eval_time = datetime.combine(now_ist.date(), inspected_time, tzinfo=IST)
            self.is_custom_time_active = True
            self.prefs.custom_time = f"{h:02d}:{m:02d}"
            self.state_mgr.save_preferences()

            self.btn_live_toggle.configure(text=f"[NODE] {h:02d}:{m:02d} IST", text_color=self.theme.accent_amber)
            self.alert_ledger.add_event("TIME", f"Inspecting exact custom time node: {h:02d}:{m:02d}:{s:02d} IST.", now_ist.strftime("%H:%M:%S IST"))
            self._compute_and_refresh()
        except Exception as e:
            self.alert_ledger.add_event("ERROR", f"Invalid time format '{t_str}': use HH:MM.", now_ist.strftime("%H:%M:%S IST"))

    def _step_time(self, delta_minutes: int):
        now_ist = datetime.now(IST)
        base = self.custom_eval_time if (self.is_custom_time_active and self.custom_eval_time) else now_ist
        new_time = base + timedelta(minutes=delta_minutes)
        self.custom_eval_time = new_time
        self.is_custom_time_active = True

        time_str = new_time.strftime("%H:%M")
        self.entry_custom_time.delete(0, "end")
        self.entry_custom_time.insert(0, time_str)
        self.prefs.custom_time = time_str
        self.state_mgr.save_preferences()

        self.btn_live_toggle.configure(text=f"[NODE] {time_str} IST", text_color=self.theme.accent_amber)
        self.alert_ledger.add_event("STEP", f"Stepped time by {delta_minutes:+d}m -> {time_str} IST.", now_ist.strftime("%H:%M:%S IST"))
        self._compute_and_refresh()

    def _reset_to_live_time(self):
        self.is_custom_time_active = False
        self.custom_eval_time = None
        now_ist = datetime.now(IST)
        self.entry_custom_time.delete(0, "end")
        self.entry_custom_time.insert(0, now_ist.strftime("%H:%M"))
        self.btn_live_toggle.configure(text="[LIVE NOW]", text_color=self.theme.accent_green)
        self.alert_ledger.add_event("TIME", "Reset evaluation to Live Real-Time Stream.", now_ist.strftime("%H:%M:%S IST"))
        self._compute_and_refresh()

    def _toggle_simulation_play(self):
        self.is_simulation_playing = not self.is_simulation_playing
        if self.is_simulation_playing:
            self.btn_sim_play.configure(text="⏸ Pause", fg_color=self.theme.accent_red, text_color="white")
            self.alert_ledger.add_event("SIM", "Simulation playback started (+5m / sec).", datetime.now().strftime("%H:%M:%S IST"))
        else:
            self.btn_sim_play.configure(text="▶ Play Day", fg_color=self.theme.accent_amber, text_color="#0f172a")
            self.alert_ledger.add_event("SIM", "Simulation playback paused.", datetime.now().strftime("%H:%M:%S IST"))

    def _handle_set_sim_cmp(self):
        val_str = self.entry_sim_cmp.get().strip()
        try:
            val = float(val_str.replace(",", ""))
            self.simulated_cmp = val
            self.alert_ledger.add_event("SIM_PRICE", f"Simulated CMP set to {val:,.2f} pts.", datetime.now().strftime("%H:%M:%S IST"))
            self._compute_and_refresh()
        except ValueError:
            self.alert_ledger.add_event("ERROR", f"Invalid CMP value: {val_str}", datetime.now().strftime("%H:%M:%S IST"))

    def _handle_reset_sim_cmp(self):
        self.simulated_cmp = None
        self.entry_sim_cmp.delete(0, "end")
        self.alert_ledger.add_event("SIM_PRICE", "Reset CMP to live market data feed.", datetime.now().strftime("%H:%M:%S IST"))
        self._compute_and_refresh()

    def _handle_layer_change(self, layer_choice: str):
        self._compute_and_refresh()

    def _toggle_topo_moon(self):
        curr = getattr(self.prefs, "topocentric_lunar", True)
        self.prefs.topocentric_lunar = not curr
        self.state_mgr.save_preferences()
        is_topo = self.prefs.topocentric_lunar
        self.btn_topo_moon.configure(
            text="Topo Moon (Parallax)" if is_topo else "Geo Moon (Core)",
            text_color=self.theme.accent_amber if is_topo else self.theme.text_secondary
        )
        mode_str = "Topocentric (Mumbai Parallax 72.88°E, 18.98°N)" if is_topo else "Geocentric (Earth Center 500@399)"
        self.alert_ledger.add_event("LUNAR", f"Switched Moon Ephemeris to {mode_str}.", datetime.now().strftime("%H:%M:%S IST"))
        self._compute_and_refresh()

    def _toggle_live_execution_switch(self):
        """Strictly enforces Safety Lockout: real broker orders cannot be armed while backtesting."""
        now_ist = datetime.now(IST)
        self.oms.disarm_live_execution()
        self.btn_live_exec_toggle.configure(
            text="🛡 LIVE BLOCKED",
            fg_color=self.theme.bg_accent,
            hover_color=self.theme.border_color,
            text_color=self.theme.accent_amber
        )
        self.alert_ledger.set_banner_alert("🛡 SAFETY LOCK ACTIVE: Live Market Orders Blocked | 100% Simulation Mode", is_critical=False)
        self.alert_ledger.add_event(
            "SAFETY",
            "Live market order placement is strictly BLOCKED by safety directive. All trades remain in 100% Simulation Mode to protect account capital.",
            now_ist.strftime("%H:%M:%S IST")
        )

    def _on_window_configure(self, event):
        """Debounce resize and cross-monitor DPI transition events (150ms)."""
        if event.widget == self:
            if self._window_resize_debounce_timer is not None:
                self.after_cancel(self._window_resize_debounce_timer)
            self._window_resize_debounce_timer = self.after(150, self._handle_debounced_window_resize)

    def _handle_debounced_window_resize(self):
        self._window_resize_debounce_timer = None
        if hasattr(self, "view_wheel") and self.view_wheel.winfo_exists():
            self.view_wheel.redraw()
        if hasattr(self, "view_split") and self.view_split.winfo_exists():
            self.view_split.wheel_view.redraw()

    def _open_custom_script_dialog(self):
        def _on_add(symbol: str, name: str) -> tuple[bool, str]:
            ok, msg = self.feed_engine.add_custom_script(symbol, name)
            if ok:
                self.prefs.custom_scripts = [
                    {"symbol": v["symbol"], "name": v["name"]}
                    for v in self.feed_engine.custom_scripts.values()
                ]
                self.state_mgr.save_preferences()
                all_s = self.feed_engine.get_all_available_scripts()
                self.script_menu.configure(values=list(all_s.keys()))
                self.alert_ledger.add_event("SCRIPT", f"Added custom script: {symbol}.", datetime.now().strftime("%H:%M:%S IST"))
            return ok, msg

        CustomScriptDialog(self, theme=self.theme, on_add_callback=_on_add)

    def _initial_load(self):
        self.alert_ledger.set_banner_alert(
            "🛡 SAFETY LOCK ACTIVE: Live Market Orders Blocked | 100% Simulation Mode",
            is_critical=False
        )
        self.alert_ledger.add_event(
            "SAFETY",
            "Live market order placement temporarily blocked by user directive. System locked to Simulation Mode.",
            datetime.now(IST).strftime("%H:%M:%S IST")
        )
        self._compute_and_refresh()

    def _schedule_live_tick(self):
        now_ist = datetime.now(IST)
        self.top_bar.update_clock(now_ist)

        # Simulation playback tick
        if self.is_simulation_playing:
            self._step_time(5)

        self.after(1000, self._schedule_live_tick)

    def _compute_and_refresh(self):
        now_ist = datetime.now(IST)
        target_date = now_ist.date()

        # Determine active evaluation time (Live vs Custom/Inspected)
        if self.is_custom_time_active and self.custom_eval_time is not None:
            eval_time_ist = self.custom_eval_time
        else:
            eval_time_ist = now_ist

        # 1. Fetch Market Snapshot & resolve CMP
        snap = self.feed_engine.fetch_snapshot(self.prefs.active_script)
        if self.simulated_cmp is not None:
            self.current_cmp = self.simulated_cmp
        else:
            self.current_cmp = snap.last_price

        # Check if exchange is closed
        if snap.market_status in ("EXCHANGE_CLOSED", "WEEKEND_CLOSED") and self.simulated_cmp is None:
            self.alert_ledger.add_event(
                "EXCHANGE",
                f"{snap.symbol} ({snap.name}): {snap.status_message}",
                now_ist.strftime("%H:%M:%S IST")
            )

        # 2. Determine session
        session = SESSION_NSE
        if "MCX" in snap.name or "CRUDE" in self.prefs.active_script or "COPPER" in self.prefs.active_script:
            session = get_mcx_session(target_date)

        # 3. Calculate True Solar Noon for selected Station
        station_key = getattr(self.prefs, "station_key", "MUMBAI_NSE")
        station = INDIAN_STATIONS.get(station_key, DEFAULT_STATION)
        solar_noon = calculate_true_solar_noon(target_date, station)

        # 4. Planetary Telemetry (Earth or Sun Center) sampled at eval_time_ist
        is_helio = (self.prefs.coordinate_frame == "HELIOCENTRIC")
        bodies_to_track = ["MERCURY", "VENUS", "MARS", "JUPITER", "SATURN", "URANUS", "NEPTUNE", "PLUTO"]
        if is_helio:
            bodies_to_track.insert(0, "EARTH")
        else:
            bodies_to_track.insert(0, "MOON")
            bodies_to_track.insert(0, "SUN")

        # Step minutes from UI preference
        step_map = {"1 Min": 1, "5 Mins": 5, "15 Mins": 15, "1 Hour": 60}
        step_min = step_map.get(self.step_var.get(), 5)

        planets_telemetry = {}
        wheel_planets = {}
        topo_lunar = getattr(self.prefs, "topocentric_lunar", True)
        station_site_coord = f"{station.longitude:.4f},{station.latitude:.4f},{station.elevation_m / 1000.0:.3f}"

        for b in bodies_to_track[:10]:
            try:
                traj = self.tracker.track_body(
                    b,
                    target_date,
                    session=session,
                    step_minutes=step_min,
                    topocentric_lunar=topo_lunar,
                    station_coord=station_site_coord
                )
                if traj:
                    # Sample closest point to eval_time_ist
                    best_pt = min(traj, key=lambda pt: abs((pt.timestamp_ist - eval_time_ist).total_seconds()))
                    lon = best_pt.helio_longitude if is_helio else best_pt.geo_longitude
                    zod = best_pt.helio_zodiac if is_helio else best_pt.geo_zodiac
                    vel = best_pt.helio_velocity_deg_per_hour if is_helio else best_pt.geo_velocity_deg_per_hour
                    state_str = "DIRECT" if is_helio else best_pt.geo_motion_state

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

        # 5. Harmonic Price Levels & 8-Octave Cymatic Grid
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

        if layer_choice in ["All Overlays Active", "8-Octaves (Cymatic)"]:
            oct_levels = ConfluenceEngine.calculate_8_octaves(snap.low_price, snap.high_price, self.current_cmp)
            for ol in oct_levels:
                raw_price_levels.append({"label": f"Octave {ol.ratio_label} ({ol.musical_note})", "type": "Cymatic Octave", "price": ol.price, "distance": ol.distance})

        raw_price_levels.sort(key=lambda x: abs(x["distance"]))
        self.latest_price_levels = raw_price_levels

        # 6. Aspects at active evaluation time
        aspects_list = AspectEngine.find_aspects_between_bodies(wheel_planets, max_orb=3.5, timestamp_ist=eval_time_ist)
        wheel_aspects = [
            {"b1": a.body_a, "b2": a.body_b, "color": a.color_hex, "is_exact": a.is_exact}
            for a in aspects_list
        ]
        self.latest_aspects = wheel_aspects

        # 7. Level 3 Advanced Telemetry: Declination Parallels, 1x1 Velocity, and Triple Confluence
        declination_parallels = ConfluenceEngine.find_declination_parallels(price_lons, max_orb_deg=0.35)

        start_dt = datetime.combine(target_date, session.start_time, tzinfo=IST)
        end_dt = datetime.combine(target_date, session.end_time, tzinfo=IST)
        total_sec = max(1.0, (end_dt - start_dt).total_seconds())
        elapsed_sec = max(0.0, min(total_sec, (eval_time_ist - start_dt).total_seconds()))
        prog_pct = (elapsed_sec / total_sec) * 100.0
        prog_deg = (prog_pct / 100.0) * 360.0

        elapsed_hours = max(0.01, elapsed_sec / 3600.0)
        vel_1x1 = ConfluenceEngine.evaluate_1x1_velocity(self.current_cmp, snap.low_price, elapsed_hours)

        key_prices = [p["price"] for p in raw_price_levels]
        is_all, g_p, g_t, g_a, setup = ConfluenceEngine.evaluate_triple_confluence(
            cmp=self.current_cmp,
            eval_time_ist=eval_time_ist,
            solar_noon_dt=solar_noon,
            key_price_levels=key_prices,
            active_aspects=wheel_aspects,
            declination_parallels=declination_parallels
        )

        if is_all and setup:
            self.audio_engine.trigger_alert("CHIME", "Triple Confluence Triggered")
            self.alert_ledger.set_banner_alert(f"TRIPLE CONFLUENCE SNIPER: {setup.direction} @ {setup.entry_price:,.1f}", is_critical=True)
            self.alert_ledger.add_event("SNIPER", f"🎯 {setup.direction} @ {setup.entry_price:,.1f} | Hard Stop: {setup.hard_stop_loss:,.1f} (-{setup.risk_pts:.0f} pts) | T1: {setup.target_1:,.1f} | R:R 1:{setup.risk_reward_ratio:.1f}", eval_time_ist.strftime("%H:%M:%S IST"))

            # Route to OMS via RealTimeConfluenceRouter
            success, order_or_reason = self.confluence_router.route_setup(
                setup=setup,
                symbol=self.prefs.active_script,
                eval_time=eval_time_ist
            )
            if success:
                mode_str = "LIVE BROKER" if self.oms.is_live_execution_armed else "SIMULATION"
                self.alert_ledger.add_event("ORDER", f"🚀 [{mode_str}] {order_or_reason} DISPATCHED: {setup.direction} @ {setup.entry_price:,.1f}", eval_time_ist.strftime("%H:%M:%S IST"))
            else:
                self.alert_ledger.add_event("LOCKOUT", f"🔒 {order_or_reason}", eval_time_ist.strftime("%H:%M:%S IST"))

        # 8. Price Needle Degree on Wheel
        price_angle = PriceHarmonicsEngine.price_to_wheel_angle(self.current_cmp)

        # 9. Assemble Snapshot Dictionary for Active Eval Time
        st_short_name = station.name.split("(")[0].strip()
        snapshot = {
            "cmp": self.current_cmp,
            "script_name": f"{snap.name} [SIM]" if self.simulated_cmp is not None else snap.name,
            "market_status": "SIMULATION" if self.simulated_cmp is not None else snap.market_status,
            "status_message": f"Active Node: {eval_time_ist.strftime('%H:%M:%S IST')}" if self.is_custom_time_active else snap.status_message,
            "session_pct": prog_pct,
            "session_deg": prog_deg,
            "noon_time": f"{solar_noon.strftime('%H:%M:%S IST')} ({st_short_name})",
            "equilibrium_price": (snap.high_price + snap.low_price) / 2.0,
            "planets": planets_telemetry,
            "price_levels": self.latest_price_levels,
            "confluence": {
                "is_all_confluent": is_all,
                "gate_price": g_p.is_active,
                "gate_time": g_t.is_active,
                "gate_astro": g_a.is_active,
                "price_desc": g_p.description,
                "time_desc": g_t.description,
                "astro_desc": g_a.description,
                "trade_setup": setup
            },
            "velocity_1x1": vel_1x1,
            "declination_parallels": declination_parallels
        }

        # 10. Update Active Views with Layer Filter
        self.view_deck.update_telemetry(snapshot)
        self.view_wheel.update_wheel_data(wheel_planets, wheel_aspects, price_angle, active_layer=layer_choice)
        self.view_split.update_all(snapshot, wheel_planets, wheel_aspects, price_angle, active_layer=layer_choice)
        if hasattr(self, "view_options"):
            self.view_options.on_live_tick_update(self.current_cmp)

    def _export_pdf_summary(self):
        now_ist = datetime.now(IST)
        target_date = now_ist.date()
        out_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pdf_path = os.path.join(out_dir, f"Gann_Daily_Summary_{self.prefs.active_script}_{target_date.strftime('%Y%m%d')}.pdf")

        snap = self.feed_engine.fetch_snapshot(self.prefs.active_script)
        planets_data = [
            {"name": k, "longitude": v.get("lon", 0.0), "zodiac": v.get("zodiac", ""), "velocity": v.get("speed", 0.0), "state": v.get("state", "DIRECT")}
            for k, v in getattr(self.view_deck, "planet_cards", {}).items()
        ]

        station_key = getattr(self.prefs, "station_key", "MUMBAI_NSE")
        st_name = INDIAN_STATIONS.get(station_key, DEFAULT_STATION).name

        timing_nodes = [
            {"label": "180° Session Midpoint", "time_ist": "12:22:30 IST", "circle_deg": "180.0°", "significance": "50% Temporal Equilibrium"},
            {"label": f"True Solar Noon ({st_name})", "time_ist": self.view_deck.lbl_noon_time.cget("text"), "circle_deg": "180.0°", "significance": "Astronomical Meridian Transit"},
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
            self.alert_ledger.add_event("PDF", f"Summary PDF generated successfully at: {os.path.basename(pdf_path)}", now_ist.strftime("%H:%M:%S IST"))
            self.audio_engine.trigger_alert("CHIME", "Daily PDF Summary Generated")
            if os.path.exists(pdf_path):
                try:
                    os.startfile(pdf_path)
                except Exception:
                    pass
        except Exception as e:
            self.alert_ledger.add_event("ERROR", f"PDF compilation error: {e}", now_ist.strftime("%H:%M:%S IST"))
