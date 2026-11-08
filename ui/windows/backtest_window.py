"""Dedicated Maximized Secondary Window for Institutional Backtesting & Visual Suite.

Provides 100% unconstrained screen real estate for the full interactive visual suite:
1. Local Data Vault Status Panel (Real-Time Disk Scans & Multi-Year Ingestion Trigger).
2. Dataset Telemetry & Health Audit Header.
3. High-Performance Vectorized Candlestick Canvas with Square of Nine & Solar Noon Overlays.
4. Interactive Trade Stepper, Timeline Scrubber, and Simulation Playback Engine.
5. Cumulative Equity Curve, Drawdown Profile, 2D MFE/MAE Excursion, and Monthly Heatmap.
"""
from __future__ import annotations

import logging
import os
import sys
import threading
from typing import Optional

import customtkinter as ctk

from core.data_vault_manager import LocalDataVaultManager
from ui.components.backtest_dashboard_view import BacktestDashboardView
from ui.theme import DARK_THEME, ThemeTokens

logger = logging.getLogger("backtest_window")


class BacktestQuantWorkstationWindow(ctk.CTkToplevel):
    """Institutional Quant Workstation Window (Maximized CTkToplevel).
    
    Automatically maximizes upon launch (state='zoomed') to provide full multi-monitor
    or full-screen workspace for deep chart inspection, backtesting, and local data vault management.
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

        # Initialize Local Data Vault Manager
        self.vault = LocalDataVaultManager()

        # 1. Top Local Data Vault Status Strip
        self._build_vault_panel()

        # 2. Embed Complete Backtest Dashboard View
        self.dashboard_view = BacktestDashboardView(self, theme=self.theme)
        self.dashboard_view.pack(fill="both", expand=True)

        # Handle Clean Lifecycle Protocol
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

    def _build_vault_panel(self):
        """Top strip displaying local Data Vault telemetry and one-click download controls."""
        self.vault_panel = ctk.CTkFrame(
            self, fg_color=self.theme.bg_secondary, height=44, corner_radius=0
        )
        self.vault_panel.pack(fill="x", side="top", pady=(0, 1))

        # Title / Icon badge
        ctk.CTkLabel(
            self.vault_panel,
            text="🗄 DATA VAULT:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.theme.accent_blue
        ).pack(side="left", padx=(14, 6))

        # Telemetry Text
        self.lbl_vault_telemetry = ctk.CTkLabel(
            self.vault_panel,
            text="Scanning vault on disk...",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=self.theme.text_primary
        )
        self.lbl_vault_telemetry.pack(side="left", padx=4)

        # Status badge indicator
        self.lbl_vault_badge = ctk.CTkLabel(
            self.vault_panel,
            text="● INITIALIZING",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.theme.accent_amber
        )
        self.lbl_vault_badge.pack(side="left", padx=(8, 12))

        # Right side: Download and Rescan controls
        self.btn_download_vault = ctk.CTkButton(
            self.vault_panel,
            text="⬇ Download 2020-2023 Nifty 50 Data",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=self.theme.accent_blue,
            hover_color=self.theme.border_color,
            text_color="#ffffff",
            command=self._start_historical_download,
            width=230,
            height=28
        )
        self.btn_download_vault.pack(side="right", padx=(6, 14))

        self.btn_rescan_vault = ctk.CTkButton(
            self.vault_panel,
            text="🔄 Rescan",
            font=ctk.CTkFont(size=10),
            fg_color=self.theme.bg_accent,
            text_color=self.theme.text_primary,
            command=self.refresh_vault_status,
            width=70,
            height=28
        )
        self.btn_rescan_vault.pack(side="right", padx=4)

        self.lbl_download_progress = ctk.CTkLabel(
            self.vault_panel,
            text="",
            font=ctk.CTkFont(size=10),
            text_color=self.theme.accent_amber
        )
        self.lbl_download_progress.pack(side="right", padx=(8, 4))

        # Initial scan
        self.refresh_vault_status()

    def refresh_vault_status(self):
        """Scans disk and updates vault telemetry."""
        try:
            st = self.vault.get_vault_status("NIFTY50")
            if st["is_ready"]:
                self.lbl_vault_telemetry.configure(
                    text=f"NIFTY50 • Range: {st['date_range']} • Size: {st['total_mb']} MB ({st['total_bars']:,} bars across {st['total_files']} monthly files)"
                )
                self.lbl_vault_badge.configure(text="● VAULT READY", text_color=self.theme.accent_green)
            else:
                self.lbl_vault_telemetry.configure(
                    text="NIFTY50 • No local Parquet files found in data/backtest_vault/"
                )
                self.lbl_vault_badge.configure(text="● NO DATA", text_color=self.theme.accent_red)
        except Exception as e:
            self.lbl_vault_telemetry.configure(text=f"Vault Scan Error: {e}")

    def _start_historical_download(self):
        """Spawns background daemon thread to ingest multi-year data into local vault."""
        self.btn_download_vault.configure(state="disabled", text="⏳ Downloading...")
        self.lbl_download_progress.configure(
            text="Starting yfinance download...",
            text_color=self.theme.accent_amber
        )

        def _worker():
            def _progress(msg: str, pct: float):
                self.after(0, lambda: self._on_download_progress(msg, pct))

            try:
                res = self.vault.download_and_store_historical_data(
                    symbol="NIFTY50",
                    start_date="2020-01-01",
                    end_date="2023-12-31",
                    progress_callback=_progress
                )
                self.after(0, lambda: self._on_download_finished(True, res))
            except Exception as e:
                self.after(0, lambda: self._on_download_finished(False, str(e)))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_download_progress(self, msg: str, pct: float):
        try:
            self.lbl_download_progress.configure(text=f"[{int(pct*100)}%] {msg[:42]}")
        except Exception:
            pass

    def _on_download_finished(self, success: bool, result):
        try:
            self.btn_download_vault.configure(state="normal", text="⬇ Download 2020-2023 Nifty 50 Data")
            if success:
                self.lbl_download_progress.configure(
                    text=f"✓ Ingested {result['files_saved']} files ({result['total_bars']:,} bars)!",
                    text_color=self.theme.accent_green
                )
                self.refresh_vault_status()
            else:
                self.lbl_download_progress.configure(
                    text=f"✖ Download Failed: {str(result)[:35]}",
                    text_color=self.theme.accent_red
                )
        except Exception:
            pass

    def bring_to_front(self):
        """Restores and focuses the workstation window when user re-clicks launch."""
        try:
            self.deiconify()
            self.state("zoomed")
            self.lift()
            self.focus_force()
            self.refresh_vault_status()
        except Exception as e:
            logger.warning(f"Failed to focus workstation window: {e}")

    def apply_theme(self, theme: ThemeTokens):
        """Applies dynamic theme swaps to window and child components."""
        self.theme = theme
        self.configure(fg_color=self.theme.bg_primary)
        if hasattr(self, "vault_panel"):
            self.vault_panel.configure(fg_color=self.theme.bg_secondary)
        if hasattr(self, "dashboard_view"):
            self.dashboard_view.apply_theme(theme)

    def _on_window_close(self):
        """Notifies master window before destroying."""
        try:
            if hasattr(self.master, "on_backtest_window_closed"):
                self.master.on_backtest_window_closed()
        except Exception:
            pass
        self.destroy()
