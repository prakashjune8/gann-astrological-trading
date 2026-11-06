"""View 3: Dual Split View (Side-by-Side Control Deck & 360° Celestial Wheel)."""
from __future__ import annotations

from typing import Optional
import customtkinter as ctk

from ui.components.celestial_wheel_view import CelestialWheelView
from ui.components.control_deck_view import ControlDeckView
from ui.theme import ThemeTokens


class DualSplitView(ctk.CTkFrame):
    """Institutional Side-by-Side trading terminal view."""

    def __init__(self, master, theme: ThemeTokens, **kwargs):
        super().__init__(master, fg_color=theme.bg_primary, **kwargs)
        self.theme = theme

        # Left Column: Master Control Deck (width ~55%)
        self.deck_view = ControlDeckView(self, theme=theme)
        self.deck_view.pack(side="left", fill="both", expand=True, padx=(8, 4), pady=8)

        # Right Column: 360° Visual Harmonic Wheel (width ~45%)
        self.wheel_view = CelestialWheelView(self, theme=theme)
        self.wheel_view.pack(side="right", fill="both", expand=True, padx=(4, 8), pady=8)

    def apply_theme(self, theme: ThemeTokens):
        """Propagate theme updates dynamically."""
        self.theme = theme
        self.configure(fg_color=theme.bg_primary)
        self.deck_view.apply_theme(theme)
        self.wheel_view.apply_theme(theme)

    def update_all(
        self,
        state_snapshot: dict,
        wheel_planets: dict[str, float],
        wheel_aspects: list[dict],
        price_angle: float,
        active_layer: str = "All Overlays Active"
    ):
        self.deck_view.update_telemetry(state_snapshot)
        self.wheel_view.update_wheel_data(wheel_planets, wheel_aspects, price_angle, active_layer=active_layer)
