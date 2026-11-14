"""View 2: Interactive 360° Visual Celestial Harmonic Wheel.

Features:
- 12 Zodiac Houses clearly partitioned (30° each).
- Real-time Planetary Glyphs & Degree Labels plotted on the outer perimeter.
- Dynamic Color-coded Harmonic Aspect Rays:
  - 0° Conjunction (Amber)
  - 45° Semi-Square (Violet)
  - 90° Square (Red)
  - 120° Trine (Green)
  - 180° Opposition (Crimson)
- Real-time Market Price Needle showing where active script's price projects on the wheel.
- Dynamic Harmonic Layer Filtering (Cardinal 90°, Fixed 45°, 50% Eq, Planetary).
- Dynamic DPI transition and 150ms resize debounce.
"""
from __future__ import annotations

import math
import tkinter as tk
from typing import Dict, List, Optional

import customtkinter as ctk
from ui.theme import ThemeTokens

ZODIAC_NAMES_SHORT = ["ARI", "TAU", "GEM", "CAN", "LEO", "VIR", "LIB", "SCO", "SAG", "CAP", "AQU", "PIS"]


class CelestialWheelView(ctk.CTkFrame):
    """Institutional 360° Circular Harmonic Wheel visualizer."""

    def __init__(self, master, theme: ThemeTokens, **kwargs):
        super().__init__(master, fg_color=theme.bg_primary, **kwargs)
        self.theme = theme

        self._build_canvas()
        self.planets_data: dict[str, float] = {}
        self.aspects_data: list[dict] = []
        self.price_needle_deg: Optional[float] = None
        self.active_layer: str = "All Overlays Active"
        self._debounce_id = None

    def _build_canvas(self):
        self.canvas = tk.Canvas(
            self,
            bg=self.theme.wheel_bg,
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(fill="both", expand=True, padx=12, pady=12)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_canvas_configure(self, event=None):
        """150ms Debounced resize & DPI transition handler to eliminate offset artifacts."""
        if self._debounce_id is not None:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(150, self.redraw)

    def apply_theme(self, theme: ThemeTokens):
        """Dynamically update visual colors when theme swaps without app restart."""
        self.theme = theme
        self.configure(fg_color=theme.bg_primary)
        self.canvas.configure(bg=theme.wheel_bg)
        self.redraw()

    def update_wheel_data(
        self,
        planets: dict[str, float],
        aspects: list[dict],
        price_angle: Optional[float] = None,
        active_layer: str = "All Overlays Active"
    ):
        self.planets_data = planets
        self.aspects_data = aspects
        self.price_needle_deg = price_angle
        self.active_layer = active_layer
        self.redraw()

    def redraw(self):
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 100 or h < 100:
            return

        cx = w / 2.0
        cy = h / 2.0
        radius = min(cx, cy) - 30.0
        if radius < 50.0:
            return

        # 1. Draw Outer & Inner Concentric Rings
        self.canvas.create_oval(
            cx - radius, cy - radius, cx + radius, cy + radius,
            outline=self.theme.wheel_ring, width=2
        )
        r_inner = radius * 0.78
        self.canvas.create_oval(
            cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner,
            outline=self.theme.wheel_ring, width=1.5
        )
        r_center = radius * 0.20
        self.canvas.create_oval(
            cx - r_center, cy - r_center, cx + r_center, cy + r_center,
            fill=self.theme.bg_secondary, outline=self.theme.wheel_ring, width=1.5
        )

        # 2. Draw 12 Zodiac House Sectors (every 30°)
        for i in range(12):
            deg = i * 30.0
            rad = math.radians(deg)
            x1 = cx + r_inner * math.cos(rad)
            y1 = cy - r_inner * math.sin(rad)
            x2 = cx + radius * math.cos(rad)
            y2 = cy - radius * math.sin(rad)
            self.canvas.create_line(x1, y1, x2, y2, fill=self.theme.wheel_line, width=1)

            # Label Zodiac name
            mid_rad = math.radians(deg + 15.0)
            r_label = (radius + r_inner) / 2.0
            lx = cx + r_label * math.cos(mid_rad)
            ly = cy - r_label * math.sin(mid_rad)
            self.canvas.create_text(
                lx, ly, text=ZODIAC_NAMES_SHORT[i],
                fill=self.theme.text_secondary, font=("Helvetica", 9, "bold")
            )

        # 3. Draw Cardinal Cross (0°, 90°, 180°, 270°)
        is_cardinal_focus = (self.active_layer == "Only Cardinal (90°)")
        card_color = self.theme.accent_amber if is_cardinal_focus else self.theme.border_color
        card_width = 2.0 if is_cardinal_focus else 1.0
        card_dash = () if is_cardinal_focus else (2, 4)

        for deg in [0.0, 90.0, 180.0, 270.0]:
            rad = math.radians(deg)
            x = cx + r_inner * math.cos(rad)
            y = cy - r_inner * math.sin(rad)
            self.canvas.create_line(cx, cy, x, y, fill=card_color, width=card_width, dash=card_dash)

        # 4. Draw Fixed Cross Diagonals (45°, 135°, 225°, 315°)
        is_fixed_focus = (self.active_layer == "Only Fixed (45°)")
        fixed_color = self.theme.accent_purple if is_fixed_focus else self.theme.border_color
        fixed_width = 2.0 if is_fixed_focus else 1.0
        fixed_dash = () if is_fixed_focus else (1, 5)

        for deg in [45.0, 135.0, 225.0, 315.0]:
            rad = math.radians(deg)
            x = cx + r_inner * math.cos(rad)
            y = cy - r_inner * math.sin(rad)
            self.canvas.create_line(cx, cy, x, y, fill=fixed_color, width=fixed_width, dash=fixed_dash)

        # 5. Draw 50% / 180° Equilibrium Line
        if self.active_layer in ("50% Eq Only", "All Overlays Active"):
            rad_180 = math.radians(180.0)
            x_180 = cx + r_inner * math.cos(rad_180)
            y_180 = cy - r_inner * math.sin(rad_180)
            rad_0 = math.radians(0.0)
            x_0 = cx + r_inner * math.cos(rad_0)
            y_0 = cy - r_inner * math.sin(rad_0)
            self.canvas.create_line(x_0, y_0, x_180, y_180, fill=self.theme.accent_green, width=2 if self.active_layer == "50% Eq Only" else 1)

        # 6. Draw Geometric Aspect Lines between Planets (filtered by active layer)
        aspects_to_draw = self.aspects_data
        if is_cardinal_focus:
            # Filter to 90° (Square) and 180° (Opposition)
            aspects_to_draw = [a for a in self.aspects_data if a.get("color") in (self.theme.accent_red, "#ef4444", "#e11d48")]
        elif is_fixed_focus:
            # Filter to 45° (Semi-square)
            aspects_to_draw = [a for a in self.aspects_data if a.get("color") in (self.theme.accent_purple, "#8b5cf6")]
        elif self.active_layer == "50% Eq Only":
            aspects_to_draw = []

        for asp in aspects_to_draw[:15]:
            b1 = asp.get("b1", "")
            b2 = asp.get("b2", "")
            if b1 in self.planets_data and b2 in self.planets_data:
                rad1 = math.radians(self.planets_data[b1])
                rad2 = math.radians(self.planets_data[b2])
                px1 = cx + (r_inner * 0.95) * math.cos(rad1)
                py1 = cy - (r_inner * 0.95) * math.sin(rad1)
                px2 = cx + (r_inner * 0.95) * math.cos(rad2)
                py2 = cy - (r_inner * 0.95) * math.sin(rad2)
                color = asp.get("color", self.theme.accent_blue)
                w_line = 2 if asp.get("is_exact", False) else 1
                self.canvas.create_line(px1, py1, px2, py2, fill=color, width=w_line)

        # 7. Draw Price Needle (Square of Nine Price-to-Degree projection)
        if self.price_needle_deg is not None:
            p_rad = math.radians(self.price_needle_deg)
            nx = cx + (radius * 0.98) * math.cos(p_rad)
            ny = cy - (radius * 0.98) * math.sin(p_rad)
            needle_w = 3.0 if self.active_layer == "50% Eq Only" else 2.5
            self.canvas.create_line(
                cx, cy, nx, ny, fill=self.theme.accent_blue, width=needle_w, arrow=tk.LAST
            )
            self.canvas.create_text(
                cx, cy, text=f"CMP\n{self.price_needle_deg:.1f}°",
                fill=self.theme.accent_blue, font=("Helvetica", 8, "bold")
            )

        # 8. Draw Planet Markers & Degree Tags on Perimeter
        r_planet = radius * 1.08
        for name, lon in self.planets_data.items():
            rad = math.radians(lon)
            px = cx + r_inner * math.cos(rad)
            py = cy - r_inner * math.sin(rad)
            tx = cx + r_planet * math.cos(rad)
            ty = cy - r_planet * math.sin(rad)

            # Node Dot
            self.canvas.create_oval(px - 4, py - 4, px + 4, py + 4, fill=self.theme.accent_amber, outline="white")
            # Pointer tick
            self.canvas.create_line(px, py, tx, ty, fill=self.theme.text_muted, width=1)
            # Text Tag
            short_name = name[:3]
            self.canvas.create_text(
                tx, ty, text=f"{short_name} {lon:.1f}°",
                fill=self.theme.text_primary, font=("Consolas", 8, "bold")
            )
