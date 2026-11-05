"""View 3: Dual Split View (Side-by-Side Control Deck & 360° Celestial Wheel)."""
from __future__ import annotations

import customtkinter as ctk

from ui.components.celestial_wheel_view import CelestialWheelView
from ui.components.control_deck_view import ControlDeckView
from ui.theme import ThemeTokens


class DualSplitView(ctk.CTkFrame):
    """Institutional Side-by-Side trading terminal view."""

    def __init__(self, master, theme: ThemeTokens, **kwargs):
        super().__init__(master, fg_color=theme.bg_primary, **kwargs)
        self.theme = theme

        # Left Column: Master Control Deck (width 58%)
        self.deck_view = ControlDeckView(self, theme=theme)
        self.deck_view.pack(side="left", fill="both", expand=True, padx=(8, 4), pady=8)

        # Right Column: 360° Visual Harmonic Wheel (width 42%)
        self.wheel_view = CelestialWheelView(self, theme=theme)
        self.wheel_view.pack(side="right", fill="both", expand=True, padx=(4, 8), pady=8)

    def update_all(
        self,
        state_snapshot: dict,
        wheel_planets: dict[str, float],
        wheel_aspects: list[dict],
        price_angle: float
    ):
        self.deck_view.update_telemetry(state_snapshot)
        self.wheel_view.update_wheel_data(wheel_planets, wheel_aspects, price_angle)
