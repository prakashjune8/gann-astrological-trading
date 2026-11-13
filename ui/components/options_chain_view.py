"""Institutional Live Options Chain & Analytical Greeks Terminal View.

Phase 2, Sub-Task 3 of the Gann Celestial Tracker Pro Architecture.
Implements:
1. Dual-Sided Tabular UI Architecture:
   - Calls (CE) on the left: Vega, Theta, Gamma, Delta, IV, LTP.
   - Center column: Strike Price with [★ ATM] focus, and dedicated Gann Square of Nine Angle/Harmonic Badge.
   - Puts (PE) on the right: LTP, IV, Delta, Gamma, Theta, Vega.
2. High-Frequency Non-Blocking Refresh Loop:
   - Background thread for BSM option chain matrix calculations.
   - Batched 500ms UI update cycle via .after() with ZERO memory leakage through widget pooling.
3. Visual Gann Harmonic Highlighting:
   - Cardinal Cross (0°, 90°, 180°, 270°, 360°) highlighted in Electric Cyan (#00f0ff).
   - Fixed Cross (45°, 135°, 225°, 315°) highlighted in Neon Ruby (#f43f5e).
   - In-The-Money (ITM) contrast shading for both CE and PE chains.
4. Real-Time Delta-Neutral Hedger Widget:
   - Portfolio net delta aggregator summing CE, PE, and Futures positions.
   - Actionable hedging suggestions (exact lots of Nifty Futures/Options to reach Delta = 0.0).
   - One-click "[⚡ Neutralize Delta]" simulation.
5. Dynamic Theme Adaptation across Dark (Obsidian) and Light institutional modes.
"""
from __future__ import annotations

import logging
import math
import threading
from dataclasses import dataclass
from datetime import datetime, time
from typing import Any, Dict, List, Optional, Tuple

import customtkinter as ctk

from core.geo_temporal import IST
from core.options_engine import (
    BSMOptionEngine,
    ExpiryCalendarEngine,
    NiftyOptionChainEngine,
    OptionStrikeRow,
)
from core.price_harmonics import PriceHarmonicsEngine
from ui.theme import DARK_THEME, ThemeTokens

logger = logging.getLogger("options_chain_view")


@dataclass
class PositionItem:
    """Represents an active or simulated portfolio option/futures position."""
    pos_type: str      # 'CE', 'PE', 'FUT'
    strike: float      # Strike price for options (0.0 for futures)
    lots: int          # Quantity in lots (positive = Long, negative = Short)
    lot_size: int = 65


class OptionsChainView(ctk.CTkFrame):
    """Institutional Nifty 50 live options chain, analytical Greeks, and delta hedger."""

    DEFAULT_LOT_SIZE: int = 65
    REFRESH_INTERVAL_MS: int = 500  # 2 Hz batched UI refresh rate

    def __init__(self, master, theme: ThemeTokens = DARK_THEME, **kwargs):
        super().__init__(master, fg_color=theme.bg_primary, **kwargs)
        self.theme = theme

        # Analytical Engines
        self.bsm_engine = BSMOptionEngine(r=0.065, q=0.0125)
        self.expiry_engine = ExpiryCalendarEngine()
        self.chain_engine = NiftyOptionChainEngine(bsm_engine=self.bsm_engine, expiry_engine=self.expiry_engine)

        # Operational Parameters
        self.spot_cmp: float = 24200.0
        self.base_iv: float = 0.145
        self.strikes_above_below: int = 10  # 21 strikes total (10 OTM, ATM, 10 ITM)
        self.r_rate: float = 0.065
        self.q_yield: float = 0.0125
        self.lot_size: int = self.DEFAULT_LOT_SIZE

        # Threading & Batching State
        self._calc_lock = threading.Lock()
        self._is_calculating: bool = False
        self._latest_chain_rows: List[OptionStrikeRow] = []
        self._latest_expiry_info: Dict[str, Any] = {}
        self._is_stream_active: bool = True
        self._refresh_timer_id: Optional[str] = None
        self._ui_update_count: int = 0

        # Portfolio Positions for Delta Hedger
        self.positions: Dict[str, PositionItem] = {
            "ATM_CE": PositionItem("CE", 24200.0, 2, self.lot_size),  # Example 2 lots long ATM CE
            "ATM_PE": PositionItem("PE", 24200.0, 0, self.lot_size),
            "FUTURES": PositionItem("FUT", 0.0, 0, self.lot_size),
        }

        # Row Widget Pool for zero-memory-leak in-place updates
        self.row_widget_pool: List[Dict[str, Any]] = []

        # UI Scaffold
        self._build_top_control_panel()
        self._build_table_header()
        self._build_table_body()
        self._build_hedger_panel()

        # Trigger Initial Async Calculation & Start Periodic Timer
        self._request_async_recalculation()
        self._schedule_periodic_refresh()

    # ==========================================================================
    # 1. UI SCAFFOLDING
    # ==========================================================================

    def _build_top_control_panel(self):
        """Builds top telemetry and control bar."""
        self.top_panel = ctk.CTkFrame(self, fg_color=self.theme.bg_secondary, height=54, corner_radius=6)
        self.top_panel.pack(fill="x", padx=12, pady=(10, 4))

        # Brand / Title & Status
        brand_frame = ctk.CTkFrame(self.top_panel, fg_color="transparent")
        brand_frame.pack(side="left", padx=(14, 10))

        self.lbl_title = ctk.CTkLabel(
            brand_frame,
            text="NIFTY 50 OPTIONS CHAIN & GREEKS",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.theme.accent_blue
        )
        self.lbl_title.pack(anchor="w")

        self.lbl_stream_badge = ctk.CTkLabel(
            brand_frame,
            text="● BSM ANALYTICAL STREAM ACTIVE (2 Hz)",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=self.theme.accent_green
        )
        self.lbl_stream_badge.pack(anchor="w")

        # Spot CMP Display & Steppers
        cmp_frame = ctk.CTkFrame(self.top_panel, fg_color=self.theme.bg_card, corner_radius=5)
        cmp_frame.pack(side="left", padx=8, pady=6)

        ctk.CTkLabel(
            cmp_frame, text="SPOT CMP:", font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.theme.text_secondary
        ).pack(side="left", padx=(8, 4))

        self.lbl_cmp = ctk.CTkLabel(
            cmp_frame,
            text=f"{self.spot_cmp:,.2f}",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            text_color=self.theme.text_primary
        )
        self.lbl_cmp.pack(side="left", padx=(0, 6))

        # Quick CMP nudgers (-50, +50, Reset)
        ctk.CTkButton(
            cmp_frame, text="-50", font=ctk.CTkFont(size=9), width=32, height=22,
            fg_color=self.theme.bg_accent, text_color=self.theme.accent_red,
            command=lambda: self._adjust_cmp(-50.0)
        ).pack(side="left", padx=1)

        ctk.CTkButton(
            cmp_frame, text="+50", font=ctk.CTkFont(size=9), width=32, height=22,
            fg_color=self.theme.bg_accent, text_color=self.theme.accent_green,
            command=lambda: self._adjust_cmp(+50.0)
        ).pack(side="left", padx=1)

        # Expiry & Countdown Frame
        exp_frame = ctk.CTkFrame(self.top_panel, fg_color=self.theme.bg_card, corner_radius=5)
        exp_frame.pack(side="left", padx=8, pady=6)

        ctk.CTkLabel(
            exp_frame, text="EXPIRY:", font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.theme.text_secondary
        ).pack(side="left", padx=(8, 4))

        self.lbl_expiry = ctk.CTkLabel(
            exp_frame,
            text="Calculating...",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=self.theme.accent_amber
        )
        self.lbl_expiry.pack(side="left", padx=(0, 8))

        # Right Controls: IV Slider & Strike Count
        right_frame = ctk.CTkFrame(self.top_panel, fg_color="transparent")
        right_frame.pack(side="right", padx=12)

        ctk.CTkLabel(
            right_frame, text="Base IV:", font=ctk.CTkFont(size=10),
            text_color=self.theme.text_secondary
        ).pack(side="left", padx=(6, 2))

        self.lbl_iv_val = ctk.CTkLabel(
            right_frame, text=f"{self.base_iv*100:.1f}%", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=self.theme.text_primary, width=38
        )
        self.lbl_iv_val.pack(side="left", padx=(0, 4))

        self.iv_slider = ctk.CTkSlider(
            right_frame, from_=0.08, to=0.35, number_of_steps=54,
            command=self._on_iv_slider_change, width=90, height=16
        )
        self.iv_slider.set(self.base_iv)
        self.iv_slider.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            right_frame, text="Strikes:", font=ctk.CTkFont(size=10),
            text_color=self.theme.text_secondary
        ).pack(side="left", padx=(6, 2))

        self.strike_range_var = ctk.StringVar(value="±10 (21)")
        self.strike_menu = ctk.CTkOptionMenu(
            right_frame,
            values=["±5 (11)", "±10 (21)", "±15 (31)"],
            variable=self.strike_range_var,
            command=self._on_strike_range_change,
            font=ctk.CTkFont(size=10),
            fg_color=self.theme.bg_accent,
            button_color=self.theme.accent_blue,
            width=78, height=24
        )
        self.strike_menu.pack(side="left", padx=2)

    def _build_table_header(self):
        """Constructs fixed column header strip with Calls, Strike/Gann, and Puts."""
        self.header_frame = ctk.CTkFrame(self, fg_color=self.theme.bg_secondary, height=36, corner_radius=4)
        self.header_frame.pack(fill="x", padx=12, pady=(4, 0))

        # Column definitions: (Name, Width, Anchor, Color)
        self.columns_def = [
            # CALLS (CE)
            ("Vega", 55, "e", self.theme.accent_purple),
            ("Theta", 60, "e", self.theme.accent_red),
            ("Gamma", 65, "e", self.theme.accent_blue),
            ("Delta", 55, "e", self.theme.accent_green),
            ("IV", 55, "e", self.theme.text_secondary),
            ("CE LTP", 75, "e", self.theme.accent_green),
            # CENTER: STRIKE & GANN
            ("STRIKE", 80, "center", self.theme.accent_amber),
            ("GANN HARMONIC", 145, "center", "#00f0ff"),
            # PUTS (PE)
            ("PE LTP", 75, "w", self.theme.accent_red),
            ("IV", 55, "w", self.theme.text_secondary),
            ("Delta", 55, "w", self.theme.accent_red),
            ("Gamma", 65, "w", self.theme.accent_blue),
            ("Theta", 60, "w", self.theme.accent_red),
            ("Vega", 55, "w", self.theme.accent_purple),
        ]

        # Top section category headers
        cat_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        cat_frame.pack(fill="x", padx=6, pady=(2, 0))

        lbl_calls_cat = ctk.CTkLabel(
            cat_frame, text="◀ CALL OPTIONS (CE)", font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.theme.accent_green
        )
        lbl_calls_cat.pack(side="left", padx=(30, 0))

        lbl_gann_cat = ctk.CTkLabel(
            cat_frame, text="◆ SQUARE OF NINE HARMONIC CROSS ◆", font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.theme.accent_amber
        )
        lbl_gann_cat.pack(side="left", expand=True)

        lbl_puts_cat = ctk.CTkLabel(
            cat_frame, text="PUT OPTIONS (PE) ▶", font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.theme.accent_red
        )
        lbl_puts_cat.pack(side="right", padx=(0, 30))

        # Individual column titles
        cols_row = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        cols_row.pack(fill="x", padx=6, pady=(1, 4))

        for name, width, anchor, col in self.columns_def:
            lbl = ctk.CTkLabel(
                cols_row, text=name, width=width, anchor=anchor,
                font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
                text_color=col
            )
            lbl.pack(side="left", padx=2)

    def _build_table_body(self):
        """Constructs scrollable container and initializes row widget pool."""
        self.scroll_container = ctk.CTkScrollableFrame(
            self,
            fg_color=self.theme.bg_card,
            corner_radius=4,
            height=390
        )
        self.scroll_container.pack(fill="both", expand=True, padx=12, pady=(2, 6))

        # Instantiate row widget pool for zero-memory-leak in-place updates
        self._reallocate_widget_pool()

    def _reallocate_widget_pool(self):
        """Instantiates or adjusts the pool of CTkLabel widgets inside the scrollable container."""
        required_rows = (self.strikes_above_below * 2) + 1

        # Clear existing pool if size differs
        for row in self.row_widget_pool:
            row["frame"].destroy()
        self.row_widget_pool.clear()

        for idx in range(required_rows):
            rf = ctk.CTkFrame(self.scroll_container, fg_color="transparent", height=24, corner_radius=3)
            rf.pack(fill="x", pady=1)

            # Dictionary to store references to every label in this row
            row_dict: Dict[str, Any] = {"frame": rf}

            col_keys = [
                ("ce_vega", 55, "e"),
                ("ce_theta", 60, "e"),
                ("ce_gamma", 65, "e"),
                ("ce_delta", 55, "e"),
                ("ce_iv", 55, "e"),
                ("ce_ltp", 75, "e"),
                ("strike", 80, "center"),
                ("gann", 145, "center"),
                ("pe_ltp", 75, "w"),
                ("pe_iv", 55, "w"),
                ("pe_delta", 55, "w"),
                ("pe_gamma", 65, "w"),
                ("pe_theta", 60, "w"),
                ("pe_vega", 55, "w"),
            ]

            for key, width, anchor in col_keys:
                lbl = ctk.CTkLabel(
                    rf, text="--", width=width, anchor=anchor,
                    font=ctk.CTkFont(family="Consolas", size=10),
                    text_color=self.theme.text_secondary
                )
                lbl.pack(side="left", padx=2)
                row_dict[key] = lbl

            self.row_widget_pool.append(row_dict)

    # ==========================================================================
    # 2. DELTA-NEUTRAL HEDGER & PORTFOLIO RISK SHIELD WIDGET
    # ==========================================================================

    def _build_hedger_panel(self):
        """Constructs interactive Delta-Neutral Hedger & Portfolio Risk Calculator."""
        self.hedger_frame = ctk.CTkFrame(self, fg_color=self.theme.bg_secondary, corner_radius=6)
        self.hedger_frame.pack(fill="x", padx=12, pady=(0, 10))

        # Header Title
        h_title = ctk.CTkFrame(self.hedger_frame, fg_color="transparent")
        h_title.pack(fill="x", padx=12, pady=(6, 2))

        ctk.CTkLabel(
            h_title,
            text="⚡ INSTITUTIONAL DELTA-NEUTRAL HEDGER & RISK SHIELD",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.theme.accent_blue
        ).pack(side="left")

        self.lbl_hedge_status = ctk.CTkLabel(
            h_title,
            text="[POSITION: UNHEDGED]",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.theme.accent_amber
        )
        self.lbl_hedge_status.pack(side="right")

        # Content Grid: Left (Positions) | Center (Aggregate Greeks) | Right (Actionable Advice)
        content_frame = ctk.CTkFrame(self.hedger_frame, fg_color="transparent")
        content_frame.pack(fill="x", padx=12, pady=(2, 8))

        # 1. Left: Position Sliders / Steppers
        pos_frame = ctk.CTkFrame(content_frame, fg_color=self.theme.bg_card, corner_radius=5)
        pos_frame.pack(side="left", fill="both", padx=(0, 6), pady=2)

        p_inner = ctk.CTkFrame(pos_frame, fg_color="transparent")
        p_inner.pack(padx=8, pady=4)

        # CE Lots
        ctk.CTkLabel(p_inner, text="ATM CE Lots:", font=ctk.CTkFont(size=10), text_color=self.theme.text_secondary).grid(row=0, column=0, sticky="w", padx=2)
        self.entry_ce_lots = ctk.CTkEntry(p_inner, width=44, height=22, font=ctk.CTkFont(family="Consolas", size=10))
        self.entry_ce_lots.insert(0, str(self.positions["ATM_CE"].lots))
        self.entry_ce_lots.grid(row=0, column=1, padx=4, pady=2)
        self.entry_ce_lots.bind("<KeyRelease>", lambda e: self._on_position_inputs_changed())

        # PE Lots
        ctk.CTkLabel(p_inner, text="ATM PE Lots:", font=ctk.CTkFont(size=10), text_color=self.theme.text_secondary).grid(row=0, column=2, sticky="w", padx=6)
        self.entry_pe_lots = ctk.CTkEntry(p_inner, width=44, height=22, font=ctk.CTkFont(family="Consolas", size=10))
        self.entry_pe_lots.insert(0, str(self.positions["ATM_PE"].lots))
        self.entry_pe_lots.grid(row=0, column=3, padx=4, pady=2)
        self.entry_pe_lots.bind("<KeyRelease>", lambda e: self._on_position_inputs_changed())

        # Futures Lots
        ctk.CTkLabel(p_inner, text="Futures Lots:", font=ctk.CTkFont(size=10), text_color=self.theme.text_secondary).grid(row=1, column=0, sticky="w", padx=2)
        self.entry_fut_lots = ctk.CTkEntry(p_inner, width=44, height=22, font=ctk.CTkFont(family="Consolas", size=10))
        self.entry_fut_lots.insert(0, str(self.positions["FUTURES"].lots))
        self.entry_fut_lots.grid(row=1, column=1, padx=4, pady=2)
        self.entry_fut_lots.bind("<KeyRelease>", lambda e: self._on_position_inputs_changed())

        # Lot Size (Default 65)
        ctk.CTkLabel(p_inner, text="Lot Size:", font=ctk.CTkFont(size=10), text_color=self.theme.text_muted).grid(row=1, column=2, sticky="w", padx=6)
        self.lbl_lot_size = ctk.CTkLabel(p_inner, text=f"{self.lot_size}", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color=self.theme.text_primary)
        self.lbl_lot_size.grid(row=1, column=3, padx=4, pady=2, sticky="w")

        # Quick Preset Buttons
        preset_frame = ctk.CTkFrame(pos_frame, fg_color="transparent")
        preset_frame.pack(fill="x", padx=8, pady=(0, 4))

        ctk.CTkButton(
            preset_frame, text="+Straddle", font=ctk.CTkFont(size=9), width=55, height=20,
            fg_color=self.theme.bg_accent, text_color=self.theme.accent_blue,
            command=self._preset_long_straddle
        ).pack(side="left", padx=1)

        ctk.CTkButton(
            preset_frame, text="+2 Long CE", font=ctk.CTkFont(size=9), width=60, height=20,
            fg_color=self.theme.bg_accent, text_color=self.theme.accent_green,
            command=self._preset_long_ce
        ).pack(side="left", padx=1)

        ctk.CTkButton(
            preset_frame, text="Clear", font=ctk.CTkFont(size=9), width=42, height=20,
            fg_color=self.theme.bg_accent, text_color=self.theme.accent_red,
            command=self._preset_clear
        ).pack(side="left", padx=1)

        # 2. Center: Aggregate Greeks Display
        greeks_frame = ctk.CTkFrame(content_frame, fg_color=self.theme.bg_card, corner_radius=5)
        greeks_frame.pack(side="left", fill="both", expand=True, padx=4, pady=2)

        g_inner = ctk.CTkFrame(greeks_frame, fg_color="transparent")
        g_inner.pack(fill="both", expand=True, padx=10, pady=6)

        # Net Delta
        ctk.CTkLabel(g_inner, text="Net Portfolio Delta (Δ):", font=ctk.CTkFont(size=10), text_color=self.theme.text_secondary).grid(row=0, column=0, sticky="w")
        self.lbl_net_delta = ctk.CTkLabel(g_inner, text="+0.00", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), text_color=self.theme.accent_green)
        self.lbl_net_delta.grid(row=0, column=1, sticky="e", padx=10)

        # Net Gamma
        ctk.CTkLabel(g_inner, text="Net Portfolio Gamma (Γ):", font=ctk.CTkFont(size=10), text_color=self.theme.text_secondary).grid(row=0, column=2, sticky="w")
        self.lbl_net_gamma = ctk.CTkLabel(g_inner, text="0.0000", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), text_color=self.theme.accent_blue)
        self.lbl_net_gamma.grid(row=0, column=3, sticky="e", padx=10)

        # Net Theta
        ctk.CTkLabel(g_inner, text="Net Portfolio Theta (Θ):", font=ctk.CTkFont(size=10), text_color=self.theme.text_secondary).grid(row=1, column=0, sticky="w")
        self.lbl_net_theta = ctk.CTkLabel(g_inner, text="0.0 pts/day", font=ctk.CTkFont(family="Consolas", size=11), text_color=self.theme.accent_red)
        self.lbl_net_theta.grid(row=1, column=1, sticky="e", padx=10)

        # Net Vega
        ctk.CTkLabel(g_inner, text="Net Portfolio Vega (𝒱):", font=ctk.CTkFont(size=10), text_color=self.theme.text_secondary).grid(row=1, column=2, sticky="w")
        self.lbl_net_vega = ctk.CTkLabel(g_inner, text="0.0 pts/1%", font=ctk.CTkFont(family="Consolas", size=11), text_color=self.theme.accent_purple)
        self.lbl_net_vega.grid(row=1, column=3, sticky="e", padx=10)

        # 3. Right: Actionable Hedging Advice & Simulation Button
        action_frame = ctk.CTkFrame(content_frame, fg_color=self.theme.bg_card, corner_radius=5)
        action_frame.pack(side="right", fill="both", padx=(4, 0), pady=2)

        a_inner = ctk.CTkFrame(action_frame, fg_color="transparent")
        a_inner.pack(padx=8, pady=4)

        ctk.CTkLabel(
            a_inner, text="HEDGE RECOMMENDATION:", font=ctk.CTkFont(size=9, weight="bold"),
            text_color=self.theme.text_secondary
        ).pack(anchor="w")

        self.lbl_hedge_advice = ctk.CTkLabel(
            a_inner,
            text="No active directional exposure.",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.theme.text_primary,
            wraplength=210,
            justify="left"
        )
        self.lbl_hedge_advice.pack(anchor="w", pady=(2, 4))

        self.btn_neutralize = ctk.CTkButton(
            a_inner,
            text="⚡ Neutralize Delta Now",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=self.theme.accent_blue,
            hover_color=self.theme.accent_green,
            height=22,
            command=self._apply_neutralizing_hedge
        )
        self.btn_neutralize.pack(fill="x")

    # ==========================================================================
    # 3. GANN SQUARE OF NINE HARMONIC CLASSIFIER
    # ==========================================================================

    @staticmethod
    def classify_gann_harmonic(strike: float, orb_deg: float = 6.0) -> Tuple[str, str, str]:
        """Classifies a strike price relative to Square of Nine Cardinal and Fixed crosses.

        Derivation:
            theta(P) = [(sqrt(P) - 1.0) mod 2.0] * 180.0
            Cardinal Cross: 0° (Equinox), 90° (Solstice), 180° (Opposition), 270° (Solstice), 360°
            Fixed Cross: 45°, 135°, 225°, 315°
        Returns:
            (category, label_text, color_code)
            category in ('CARDINAL', 'FIXED', 'STANDARD')
        """
        angle = PriceHarmonicsEngine.price_to_wheel_angle(strike)

        cardinals = [
            (0.0, "0° Equinox"),
            (90.0, "90° Solstice"),
            (180.0, "180° Opposition"),
            (270.0, "270° Solstice"),
            (360.0, "360° Root"),
        ]
        fixeds = [
            (45.0, "45° Fixed"),
            (135.0, "135° Fixed"),
            (225.0, "225° Fixed"),
            (315.0, "315° Fixed"),
        ]

        # 1. Check Cardinal Cross
        for ref_ang, name in cardinals:
            if ref_ang in (0.0, 360.0):
                diff = min(angle, abs(360.0 - angle))
            else:
                diff = abs(angle - ref_ang)
            if diff <= orb_deg:
                return ("CARDINAL", f"CARDINAL {name} ({angle:.1f}°)", "#00f0ff")

        # 2. Check Fixed Cross
        for ref_ang, name in fixeds:
            diff = abs(angle - ref_ang)
            if diff <= orb_deg:
                return ("FIXED", f"FIXED {name} ({angle:.1f}°)", "#f43f5e")

        # 3. Standard Harmonic Strike
        return ("STANDARD", f"{angle:.1f}° Standard", "#64748b")

    # ==========================================================================
    # 4. ASYNCHRONOUS RECALCULATION & NON-BLOCKING REFRESH
    # ==========================================================================

    def _adjust_cmp(self, delta: float):
        """Nudges spot CMP and triggers recalculation."""
        self.spot_cmp = max(1000.0, self.spot_cmp + delta)
        self.lbl_cmp.configure(text=f"{self.spot_cmp:,.2f}")
        self._request_async_recalculation()

    def _on_iv_slider_change(self, val: float):
        """Handles base IV slider adjustments."""
        self.base_iv = round(val, 3)
        self.lbl_iv_val.configure(text=f"{self.base_iv*100:.1f}%")
        self._request_async_recalculation()

    def _on_strike_range_change(self, choice: str):
        """Adjusts number of strikes and reallocates row widget pool."""
        if "±5" in choice:
            self.strikes_above_below = 5
        elif "±15" in choice:
            self.strikes_above_below = 15
        else:
            self.strikes_above_below = 10

        self._reallocate_widget_pool()
        self._request_async_recalculation()

    def _request_async_recalculation(self):
        """Dispatches analytical BSM option chain calculation to background thread."""
        if self._is_calculating:
            return  # Computation already running, will catch up on next tick

        worker = threading.Thread(target=self._run_analytical_calculation_worker, daemon=True)
        worker.start()

    def _run_analytical_calculation_worker(self):
        """Worker thread executing BSM option chain pricing and Greeks synthesis."""
        with self._calc_lock:
            self._is_calculating = True

        try:
            now_ist = datetime.now(IST)
            t_years = self.expiry_engine.calculate_time_to_maturity_years(now_ist)
            exp_date = self.expiry_engine.get_upcoming_weekly_expiry(now_ist.date(), now_ist.time())
            exp_dt = datetime.combine(exp_date, time(15, 30, 0), tzinfo=IST)
            mins_left = max(0.0, (exp_dt - now_ist).total_seconds() / 60.0)
            days_left = mins_left / 1440.0

            rows = self.chain_engine.generate_option_chain(
                spot=self.spot_cmp,
                eval_datetime=now_ist,
                base_iv=self.base_iv,
                strikes_above_below=self.strikes_above_below,
                r=self.r_rate,
                q=self.q_yield
            )

            with self._calc_lock:
                self._latest_chain_rows = rows
                self._latest_expiry_info = {
                    "exp_date": exp_date.strftime("%d-%b-%Y (%a)").upper(),
                    "mins_left": int(mins_left),
                    "days_left": round(days_left, 1),
                    "t_years": t_years
                }
        except Exception as e:
            logger.error(f"Error in options chain analytical worker: {e}", exc_info=True)
        finally:
            with self._calc_lock:
                self._is_calculating = False

    def _schedule_periodic_refresh(self):
        """Batched 500ms UI update cycle running safely on the Tkinter main thread."""
        self._ui_refresh_tick()
        self._refresh_timer_id = self.after(self.REFRESH_INTERVAL_MS, self._schedule_periodic_refresh)

    def _ui_refresh_tick(self):
        """Refreshes table cells in-place with zero widget instantiation."""
        with self._calc_lock:
            rows = list(self._latest_chain_rows)
            exp_info = dict(self._latest_expiry_info)

        if not rows:
            return

        self._ui_update_count += 1

        # 1. Update Expiry Header
        if exp_info:
            self.lbl_expiry.configure(
                text=f"{exp_info['exp_date']} | 15:30 IST ({exp_info['days_left']}d / {exp_info['mins_left']:,}m)"
            )

        # 2. Update Table Rows In-Place
        num_rows = min(len(rows), len(self.row_widget_pool))
        atm_strike = round(self.spot_cmp / 50.0) * 50.0

        for i in range(num_rows):
            r = rows[i]
            w = self.row_widget_pool[i]
            rf = w["frame"]

            is_atm = (r.strike == atm_strike)
            is_ce_itm = (r.strike < self.spot_cmp)
            is_pe_itm = (r.strike > self.spot_cmp)

            # Row background tinting for ITM moneyness
            if is_atm:
                rf.configure(fg_color=self.theme.bg_accent)
            else:
                rf.configure(fg_color="transparent")

            # Gann Angle Harmonic Classification
            cat, gann_label, gann_color = self.classify_gann_harmonic(r.strike)

            # Central Strike Formatting
            strike_str = f"★ {r.strike:,.0f}" if is_atm else f"{r.strike:,.0f}"
            strike_color = self.theme.accent_amber if is_atm else self.theme.text_primary

            # In-place cell text updates
            w["ce_vega"].configure(text=f"{r.call_vega:.2f}")
            w["ce_theta"].configure(text=f"{r.call_theta:.1f}")
            w["ce_gamma"].configure(text=f"{r.call_gamma:.4f}")
            w["ce_delta"].configure(
                text=f"{r.call_delta:+.2f}",
                text_color=self.theme.accent_green if is_ce_itm else self.theme.text_secondary
            )
            w["ce_iv"].configure(text=f"{r.call_iv*100:.1f}%")
            w["ce_ltp"].configure(
                text=f"₹{r.call_price:.2f}",
                font=ctk.CTkFont(family="Consolas", size=10, weight="bold" if is_ce_itm else "normal"),
                text_color=self.theme.accent_green if is_ce_itm else self.theme.text_primary
            )

            w["strike"].configure(
                text=strike_str,
                text_color=strike_color,
                font=ctk.CTkFont(family="Consolas", size=10, weight="bold" if is_atm else "normal")
            )

            # Gann Angle Highlight
            w["gann"].configure(
                text=gann_label,
                text_color=gann_color,
                font=ctk.CTkFont(family="Consolas", size=9, weight="bold" if cat in ("CARDINAL", "FIXED") else "normal")
            )

            w["pe_ltp"].configure(
                text=f"₹{r.put_price:.2f}",
                font=ctk.CTkFont(family="Consolas", size=10, weight="bold" if is_pe_itm else "normal"),
                text_color=self.theme.accent_red if is_pe_itm else self.theme.text_primary
            )
            w["pe_iv"].configure(text=f"{r.put_iv*100:.1f}%")
            w["pe_delta"].configure(
                text=f"{r.put_delta:+.2f}",
                text_color=self.theme.accent_red if is_pe_itm else self.theme.text_secondary
            )
            w["pe_gamma"].configure(text=f"{r.put_gamma:.4f}")
            w["pe_theta"].configure(text=f"{r.put_theta:.1f}")
            w["pe_vega"].configure(text=f"{r.put_vega:.2f}")

        # 3. Recalculate Portfolio Delta & Hedger Recommendation
        self._recalculate_hedger_metrics(rows, atm_strike)

    # ==========================================================================
    # 5. DELTA-NEUTRAL HEDGE CALCULATIONS
    # ==========================================================================

    def _on_position_inputs_changed(self):
        """Reads user position inputs and updates position state."""
        try:
            ce_val = int(self.entry_ce_lots.get().strip() or "0")
            pe_val = int(self.entry_pe_lots.get().strip() or "0")
            fut_val = int(self.entry_fut_lots.get().strip() or "0")

            self.positions["ATM_CE"].lots = ce_val
            self.positions["ATM_PE"].lots = pe_val
            self.positions["FUTURES"].lots = fut_val
        except ValueError:
            pass

    def _preset_long_straddle(self):
        """Sets position to +1 ATM Call and +1 ATM Put."""
        self.entry_ce_lots.delete(0, "end")
        self.entry_ce_lots.insert(0, "1")
        self.entry_pe_lots.delete(0, "end")
        self.entry_pe_lots.insert(0, "1")
        self.entry_fut_lots.delete(0, "end")
        self.entry_fut_lots.insert(0, "0")
        self._on_position_inputs_changed()

    def _preset_long_ce(self):
        """Sets position to +2 ATM Calls."""
        self.entry_ce_lots.delete(0, "end")
        self.entry_ce_lots.insert(0, "2")
        self.entry_pe_lots.delete(0, "end")
        self.entry_pe_lots.insert(0, "0")
        self.entry_fut_lots.delete(0, "end")
        self.entry_fut_lots.insert(0, "0")
        self._on_position_inputs_changed()

    def _preset_clear(self):
        """Clears all positions."""
        self.entry_ce_lots.delete(0, "end")
        self.entry_ce_lots.insert(0, "0")
        self.entry_pe_lots.delete(0, "end")
        self.entry_pe_lots.insert(0, "0")
        self.entry_fut_lots.delete(0, "end")
        self.entry_fut_lots.insert(0, "0")
        self._on_position_inputs_changed()

    def _recalculate_hedger_metrics(self, rows: List[OptionStrikeRow], atm_strike: float):
        """Computes total net portfolio Greeks and generates exact neutralizing order."""
        atm_row = next((r for r in rows if r.strike == atm_strike), None)
        if not atm_row and rows:
            atm_row = rows[len(rows) // 2]
        if not atm_row:
            return

        ce_lots = self.positions["ATM_CE"].lots
        pe_lots = self.positions["ATM_PE"].lots
        fut_lots = self.positions["FUTURES"].lots

        # Standard Nifty European Greeks
        # Futures Delta = 1.0 (exact underlying exposure per contract)
        total_delta = (
            (ce_lots * self.lot_size * atm_row.call_delta) +
            (pe_lots * self.lot_size * atm_row.put_delta) +
            (fut_lots * self.lot_size * 1.0)
        )
        total_gamma = (ce_lots * self.lot_size * atm_row.call_gamma) + (pe_lots * self.lot_size * atm_row.put_gamma)
        total_theta = (ce_lots * self.lot_size * atm_row.call_theta) + (pe_lots * self.lot_size * atm_row.put_theta)
        total_vega = (ce_lots * self.lot_size * atm_row.call_vega) + (pe_lots * self.lot_size * atm_row.put_vega)

        # Update Greek Labels
        delta_color = self.theme.accent_green if abs(total_delta) <= 2.0 else (
            self.theme.accent_blue if total_delta > 0 else self.theme.accent_red
        )
        self.lbl_net_delta.configure(text=f"{total_delta:+.2f} Δ", text_color=delta_color)
        self.lbl_net_gamma.configure(text=f"{total_gamma:.4f} Γ")
        self.lbl_net_theta.configure(text=f"{total_theta:,.1f} ₹/day")
        self.lbl_net_vega.configure(text=f"{total_vega:,.1f} ₹/1%")

        # Generate Hedging Recommendation
        # Neutralizing with Nifty Futures:
        # Needed Futures Contracts = - round(total_delta / lot_size)
        contracts_needed = -round(total_delta / self.lot_size)

        if abs(total_delta) <= 2.0:
            self.lbl_hedge_status.configure(text="[✓ DELTA NEUTRAL]", text_color=self.theme.accent_green)
            self.lbl_hedge_advice.configure(
                text="Portfolio is Delta-Neutral (|Δ| ≤ 2.0). Directional risk is fully immunized.",
                text_color=self.theme.accent_green
            )
            self.btn_neutralize.configure(state="disabled")
        elif total_delta > 2.0:
            self.lbl_hedge_status.configure(text="[LONG DIRECTIONAL BIAS]", text_color=self.theme.accent_blue)
            advice_str = f"SELL {abs(contracts_needed)} Lot(s) Nifty Futures (or Buy ATM Puts) to neutralize +{total_delta:.1f} Delta."
            self.lbl_hedge_advice.configure(text=advice_str, text_color=self.theme.accent_blue)
            self.btn_neutralize.configure(state="normal")
        else:
            self.lbl_hedge_status.configure(text="[SHORT DIRECTIONAL BIAS]", text_color=self.theme.accent_red)
            advice_str = f"BUY {abs(contracts_needed)} Lot(s) Nifty Futures (or Buy ATM Calls) to neutralize {total_delta:.1f} Delta."
            self.lbl_hedge_advice.configure(text=advice_str, text_color=self.theme.accent_red)
            self.btn_neutralize.configure(state="normal")

    def _apply_neutralizing_hedge(self):
        """Applies exact offsetting futures lots to bring net delta to zero."""
        try:
            curr_fut = int(self.entry_fut_lots.get().strip() or "0")
            delta_str = self.lbl_net_delta.cget("text").split()[0]
            current_net_delta = float(delta_str)

            needed_fut_lots = -round(current_net_delta / self.lot_size)
            new_fut_lots = curr_fut + needed_fut_lots

            self.entry_fut_lots.delete(0, "end")
            self.entry_fut_lots.insert(0, str(new_fut_lots))
            self._on_position_inputs_changed()
        except Exception as e:
            logger.error(f"Failed to apply neutralizing hedge: {e}")

    # ==========================================================================
    # 6. EXTERNAL DATA INTEGRATION & THEME PROPAGATION
    # ==========================================================================

    def on_live_tick_update(self, ltp: float):
        """Called by live broker WebSocket pump when a new Nifty index tick arrives."""
        if abs(ltp - self.spot_cmp) >= 0.05:
            self.spot_cmp = ltp
            self.lbl_cmp.configure(text=f"{self.spot_cmp:,.2f}")
            self._request_async_recalculation()

    def apply_theme(self, theme: ThemeTokens):
        """Propagates updated theme tokens across all view elements."""
        self.theme = theme
        self.configure(fg_color=theme.bg_primary)
        self.top_panel.configure(fg_color=theme.bg_secondary)
        self.header_frame.configure(fg_color=theme.bg_secondary)
        self.scroll_container.configure(fg_color=theme.bg_card)
        self.hedger_frame.configure(fg_color=theme.bg_secondary)

        self.lbl_title.configure(text_color=theme.accent_blue)
        self.lbl_cmp.configure(text_color=theme.text_primary)
        self.lbl_expiry.configure(text_color=theme.accent_amber)

    def destroy(self):
        """Safely terminates timers and background thread states upon widget disposal."""
        if self._refresh_timer_id is not None:
            try:
                self.after_cancel(self._refresh_timer_id)
            except Exception:
                pass
            self._refresh_timer_id = None
        super().destroy()
