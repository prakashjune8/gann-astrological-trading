"""Dedicated Maximized Secondary Window for Institutional Backtesting & Visual Suite.

Provides 100% unconstrained screen real estate for the full interactive visual suite:
1. Dataset Telemetry & Health Audit Header.
2. High-Performance Vectorized Candlestick Canvas with Square of Nine & Solar Noon Overlays.
3. Interactive Trade Stepper, Timeline Scrubber, and Simulation Playback Engine.
4. Cumulative Equity Curve, Drawdown Profile, 2D MFE/MAE Excursion, and Monthly Heatmap.
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Optional

import customtkinter as ctk

from ui.components.backtest_dashboard_view import BacktestDashboardView
from ui.theme import DARK_THEME, ThemeTokens

logger = logging.getLogger("backtest_window")


class BacktestQuantWorkstationWindow(ctk.CTkToplevel):
    """Institutional Quant Workstation Window (Maximized CTkToplevel).
    
    Automatically maximizes upon launch (state='zoomed') to provide full multi-monitor
    or full-screen workspace for deep chart inspection and backtesting.
    """

    def __init__(self, master, theme: Optional[ThemeTokens] = None, **kwargs):
        super().__init__(master, **kwargs)
        self.theme = theme or DARK_THEME

        # Window Branding & Geometry
        self.title("Gann Quant Workstation & Visual Suite • Institutional Multi-Year Backtester")
        self.geometry("1600x960")
        self.minsize(1180, 720)
        self.configure(fg_color=self.theme.bg_primary)

        # App Icon Attachment
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        icon_path = os.path.join(base_dir, "assets", "app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.after(200, lambda: self.iconbitmap(icon_path))
            except Exception:
                pass

        # CRUCIAL UX MANDATE: Maximize window to 100% screen real estate
        self.after(0, lambda: self.state("zoomed"))

        # Embed Complete Backtest Dashboard View
        self.dashboard_view = BacktestDashboardView(self, theme=self.theme)
        self.dashboard_view.pack(fill="both", expand=True)

        # Handle Clean Lifecycle Protocol
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

    def bring_to_front(self):
        """Restores and focuses the workstation window when user re-clicks launch."""
        try:
            self.deiconify()
            self.state("zoomed")
            self.lift()
            self.focus_force()
        except Exception as e:
            logger.warning(f"Failed to focus workstation window: {e}")

    def _on_window_close(self):
        """Notifies master window before destroying."""
        try:
            if hasattr(self.master, "on_backtest_window_closed"):
                self.master.on_backtest_window_closed()
        except Exception:
            pass
        self.destroy()
