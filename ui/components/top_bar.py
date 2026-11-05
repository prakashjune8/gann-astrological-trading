"""Top Bar Navigation & Global Control Deck Header."""
from __future__ import annotations

from datetime import datetime
import customtkinter as ctk

from core.geo_temporal import IST
from ui.theme import ThemeTokens


class TopBarComponent(ctk.CTkFrame):
    """Global header providing Geo/Helio toggle, Theme toggle, View switcher, and live clock."""

    def __init__(
        self,
        master,
        theme: ThemeTokens,
        on_geo_helio_toggle,
        on_theme_toggle,
        on_view_change,
        on_mode_change,
        initial_frame: str = "GEOCENTRIC",
        initial_theme: str = "DARK",
        initial_view: str = "DUAL_SPLIT",
        initial_mode: str = "LIVE"
    ):
        super().__init__(master, fg_color=theme.bg_secondary, corner_radius=0, height=52)
        self.theme = theme
        self.on_geo_helio_toggle = on_geo_helio_toggle
        self.on_theme_toggle = on_theme_toggle
        self.on_view_change = on_view_change
        self.on_mode_change = on_mode_change

        self.current_frame = initial_frame
        self.current_theme = initial_theme

        self._build_ui(initial_frame, initial_theme, initial_view, initial_mode)

    def _build_ui(self, initial_frame: str, initial_theme: str, initial_view: str, initial_mode: str):
        # App Branding
        brand_frame = ctk.CTkFrame(self, fg_color="transparent")
        brand_frame.pack(side="left", padx=16)

        title_lbl = ctk.CTkLabel(
            brand_frame,
            text="GANN CELESTIAL TRACKER PRO",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.theme.accent_blue
        )
        title_lbl.pack(side="top", anchor="w")

        sub_lbl = ctk.CTkLabel(
            brand_frame,
            text="Institutional Astro-Harmonic Terminal • India (IST)",
            font=ctk.CTkFont(size=10),
            text_color=self.theme.text_muted
        )
        sub_lbl.pack(side="top", anchor="w")

        # Live IST Clock
        self.clock_lbl = ctk.CTkLabel(
            self,
            text="--:--:-- IST",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            text_color=self.theme.text_primary
        )
        self.clock_lbl.pack(side="left", padx=20)

        # Right-side controls
        right_frame = ctk.CTkFrame(self, fg_color="transparent")
        right_frame.pack(side="right", padx=16)

        # Operating Mode Switcher (Live vs Simulation)
        self.mode_var = ctk.StringVar(value=initial_mode)
        mode_seg = ctk.CTkSegmentedButton(
            right_frame,
            values=["LIVE", "SIMULATION"],
            variable=self.mode_var,
            command=self.on_mode_change,
            selected_color=self.theme.accent_blue,
            font=ctk.CTkFont(size=11, weight="bold"),
            height=28
        )
        mode_seg.pack(side="left", padx=8)

        # View Switcher Dropdown
        view_map_rev = {
            "CONTROL_DECK": "Master Control Deck",
            "CELESTIAL_WHEEL": "360° Celestial Wheel",
            "DUAL_SPLIT": "Dual Split View"
        }
        self.view_var = ctk.StringVar(value=view_map_rev.get(initial_view, "Dual Split View"))
        view_menu = ctk.CTkOptionMenu(
            right_frame,
            values=["Master Control Deck", "360° Celestial Wheel", "Dual Split View"],
            variable=self.view_var,
            command=self._handle_view_select,
            font=ctk.CTkFont(size=11),
            fg_color=self.theme.bg_accent,
            button_color=self.theme.accent_blue,
            text_color=self.theme.text_primary,
            height=28,
            width=165
        )
        view_menu.pack(side="left", padx=8)

        # Global Geo / Helio Toggle Button
        self.frame_btn = ctk.CTkButton(
            right_frame,
            text=f"Frame: {initial_frame.title()}",
            command=self._toggle_frame,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=self.theme.bg_accent,
            hover_color=self.theme.border_color,
            text_color=self.theme.accent_amber if initial_frame == "HELIOCENTRIC" else self.theme.accent_blue,
            height=28,
            width=135
        )
        self.frame_btn.pack(side="left", padx=8)

        # Theme Toggle Button (Dark / Light)
        theme_icon = "☀ Light" if initial_theme == "DARK" else "🌙 Dark"
        self.theme_btn = ctk.CTkButton(
            right_frame,
            text=theme_icon,
            command=self._toggle_theme,
            font=ctk.CTkFont(size=11),
            fg_color=self.theme.bg_accent,
            text_color=self.theme.text_primary,
            height=28,
            width=80
        )
        self.theme_btn.pack(side="left", padx=8)

    def _handle_view_select(self, choice: str):
        v_map = {
            "Master Control Deck": "CONTROL_DECK",
            "360° Celestial Wheel": "CELESTIAL_WHEEL",
            "Dual Split View": "DUAL_SPLIT"
        }
        self.on_view_change(v_map.get(choice, "DUAL_SPLIT"))

    def _toggle_frame(self):
        new_frame = "HELIOCENTRIC" if self.current_frame == "GEOCENTRIC" else "GEOCENTRIC"
        self.current_frame = new_frame
        self.frame_btn.configure(
            text=f"Frame: {new_frame.title()}",
            text_color=self.theme.accent_amber if new_frame == "HELIOCENTRIC" else self.theme.accent_blue
        )
        self.on_geo_helio_toggle(new_frame)

    def _toggle_theme(self):
        new_theme = "LIGHT" if self.current_theme == "DARK" else "DARK"
        self.current_theme = new_theme
        self.on_theme_toggle(new_theme)

    def update_clock(self, dt_ist: datetime):
        self.clock_lbl.configure(text=dt_ist.strftime("%H:%M:%S IST"))
