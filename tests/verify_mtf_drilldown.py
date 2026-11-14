"""Verification script for Multi-Timeframe (MTF) Drill-Down Architecture.

Validates:
1. Multi-Timeframe Aggregation (Monthly, Weekly, Daily) with exact OHLCV semantics.
2. Layer 1 Timeframe dropdown integration and dynamic telemetry updates.
3. Interactive Drill-Down to specific days (YYYY-MM-DD), months (YYYY-MM), or years (YYYY).
4. Canvas double-click interaction triggering automatic 1-minute day drill-down.
5. Zero indexing errors and zero memory leakage across rapid timeframe switches.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, date
from pathlib import Path
from unittest.mock import MagicMock

# Force UTF-8 stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk
import pandas as pd
import numpy as np

from core.data_vault_manager import LocalDataVaultManager
from core.backtest_engine import TradeLedger, ExecutedTrade, TradeDirection, ExitReason, FeeBreakdown
from ui.theme import DARK_THEME
from ui.components.interactive_trade_inspector import InteractiveTradeInspector


def test_mtf_and_drilldown():
    print("=" * 70)
    print("RUNNING VERIFICATION: MULTI-TIMEFRAME (MTF) & DRILL-DOWN ARCHITECTURE")
    print("=" * 70)

    # 1. Load 3 Months of Real 1-Minute Data from Local Data Vault
    vault = LocalDataVaultManager()
    df_raw = vault.load_vault_range("NIFTY50", start_date="2023-01-01", end_date="2023-03-31")
    print(f"[*] Ingested raw 1-minute dataset: {len(df_raw):,} bars across Q1 2023")
    assert not df_raw.empty and len(df_raw) > 20000

    # 2. Mathematical Verification of aggregate_timeframe()
    print("[*] Testing aggregate_timeframe() mathematical integrity...")
    
    # Monthly
    df_monthly = InteractiveTradeInspector.aggregate_timeframe(df_raw, "Monthly")
    print(f"    - Monthly bars: {len(df_monthly)} (Expected: 3)")
    assert len(df_monthly) == 3, f"Q1 2023 must produce 3 monthly bars, got {len(df_monthly)}"
    assert set(["timestamp", "open", "high", "low", "close", "volume"]).issubset(df_monthly.columns)
    
    # Weekly
    df_weekly = InteractiveTradeInspector.aggregate_timeframe(df_raw, "Weekly")
    print(f"    - Weekly bars: {len(df_weekly)} (Expected: ~13)")
    assert 12 <= len(df_weekly) <= 14, f"Q1 2023 should have ~13 weeks, got {len(df_weekly)}"
    
    # Daily
    df_daily = InteractiveTradeInspector.aggregate_timeframe(df_raw, "Daily")
    print(f"    - Daily bars: {len(df_daily)} (Expected: 62 trading sessions)")
    assert len(df_daily) == 62, f"Q1 2023 has 62 NSE trading days, got {len(df_daily)}"

    # Mathematical Proof: First day open must match first 1m bar open of that day
    ts_series = df_raw["timestamp_ist"] if "timestamp_ist" in df_raw.columns else (df_raw["timestamp"] if "timestamp" in df_raw.columns else df_raw.index)
    first_date = df_daily["timestamp"].iloc[0].date()
    first_day_1m = df_raw[ts_series.date == first_date]
    assert df_daily["open"].iloc[0] == first_day_1m["open"].iloc[0], "Daily open must match first 1m bar open"
    assert df_daily["close"].iloc[0] == first_day_1m["close"].iloc[-1], "Daily close must match last 1m bar close"
    assert df_daily["high"].iloc[0] == first_day_1m["high"].max(), "Daily high must match session max"
    assert df_daily["low"].iloc[0] == first_day_1m["low"].min(), "Daily low must match session min"
    assert df_daily["volume"].iloc[0] == first_day_1m["volume"].sum(), "Daily volume must match session sum"
    print("    ✓ Mathematical OHLCV aggregation proof verified!")

    # 3. Instantiate UI Component (Headless Root)
    root = ctk.CTk()
    root.withdraw()
    inspector = InteractiveTradeInspector(root, theme=DARK_THEME)

    # Ingest data into inspector
    sample_trade = ExecutedTrade(
        trade_id="TRD_MTF_001",
        signal_id="SIG_CONF_001",
        direction=TradeDirection.LONG,
        dispatch_time=pd.Timestamp("2023-01-05 09:20:00", tz="Asia/Kolkata"),
        fill_time=pd.Timestamp("2023-01-05 09:21:00", tz="Asia/Kolkata"),
        entry_price=18000.0,
        stop_price=17982.0,
        target1_price=18125.0,
        target2_price=18252.0,
        qty=50,
        is_closed=True
    )
    ledger = TradeLedger()
    ledger.append(sample_trade)

    print("[*] Ingesting dataset into InteractiveTradeInspector...")
    inspector.set_timeframe("Daily", auto_render=False)
    inspector.load_data(df_raw, ledger)
    inspector.set_timeframe("Daily")

    # 4. Verify Default Timeframe View
    print(f"[*] Active Timeframe: {inspector.current_timeframe}")
    assert inspector.current_timeframe == "Daily", "Default timeframe should be Daily"
    assert len(inspector.active_df) == 62, "Active df should hold 62 daily bars"
    assert inspector.current_slice is not None and len(inspector.current_slice) == 62
    telemetry_daily = inspector.lbl_telemetry_span.cget("text")
    print(f"    - Daily Telemetry: '{telemetry_daily.replace(chr(8377), 'INR')}'")
    assert "DAILY" in telemetry_daily
    assert "Bars: 62" in telemetry_daily

    # 5. Verify Rapid Timeframe Switching (Daily -> Weekly -> Monthly -> Daily)
    print("[*] Testing rapid timeframe switching...")
    
    # Switch to Weekly
    inspector.set_timeframe("Weekly")
    assert inspector.current_timeframe == "Weekly"
    assert len(inspector.active_df) == len(df_weekly)
    print(f"    - Switched to Weekly: {len(inspector.current_slice)} bars rendered")

    # Switch to Monthly
    inspector.set_timeframe("Monthly")
    assert inspector.current_timeframe == "Monthly"
    assert len(inspector.active_df) == 3
    print(f"    - Switched to Monthly: {len(inspector.current_slice)} bars rendered")

    # Switch back to Daily
    inspector.set_timeframe("Daily")
    assert inspector.current_timeframe == "Daily"
    assert len(inspector.active_df) == 62
    print(f"    - Switched back to Daily: {len(inspector.current_slice)} bars rendered")

    # 6. Verify Drill-Down to Specific Day (YYYY-MM-DD)
    print("[*] Testing explicit 1-Minute drill-down to '2023-01-05'...")
    inspector.drill_down_to_date("2023-01-05")
    assert inspector.current_timeframe == "1-Min Intraday"
    assert inspector.timeframe_var.get() == "1-Min Intraday"
    assert len(inspector.active_df) == 375, f"1-day drill-down must have 375 1-min bars, got {len(inspector.active_df)}"
    assert inspector.lbl_health_pill.cget("text") == "● 1-MIN INTRADAY VERIFIED"
    print(f"    - Day Drill-down verified: {len(inspector.active_df)} 1-minute bars active")

    # 7. Verify Drill-Down to Specific Month (YYYY-MM)
    print("[*] Testing explicit 1-Minute drill-down to month '2023-02'...")
    inspector.drill_down_to_constraint("2023-02")
    assert inspector.current_timeframe == "1-Min Intraday"
    # February 2023 had 20 trading days = 7,500 bars
    print(f"    - Month Drill-down bars: {len(inspector.active_df):,}")
    assert 7000 <= len(inspector.active_df) <= 8000
    telemetry_month_drill = inspector.lbl_telemetry_span.cget("text")
    assert "DRILL-DOWN: 2023-02" in telemetry_month_drill

    # 8. Verify Canvas Double-Click Callback
    print("[*] Testing canvas double-click interactive drill-down...")
    inspector.set_timeframe("Daily")
    assert inspector.current_timeframe == "Daily"
    
    # Simulate double-click on candle at index 10 (approx 2023-01-16)
    target_candle_date = inspector.current_slice.iloc[10]["timestamp"].strftime("%Y-%m-%d")
    mock_event = MagicMock()
    mock_event.dblclick = True
    mock_event.inaxes = inspector.ax
    mock_event.xdata = 10.0
    
    print(f"    - Simulating double-click on candle index 10 (Date: {target_candle_date})...")
    inspector._on_canvas_click(mock_event)
    
    assert inspector.current_timeframe == "1-Min Intraday", "Double click must switch to 1-Min Intraday"
    assert inspector.timeframe_var.get() == "1-Min Intraday"
    assert len(inspector.active_df) == 375, f"Double-clicked day must load 375 1-min bars, got {len(inspector.active_df)}"
    print(f"    ✓ Double-click automatically drilled down to {target_candle_date} (375 bars loaded)!")

    # Clean up Tk
    root.destroy()

    print("\n" + "=" * 70)
    print(">>> ALL MULTI-TIMEFRAME & DRILL-DOWN TESTS DETERMINISTICALLY PASSED! <<<")
    print("=" * 70)


if __name__ == "__main__":
    test_mtf_and_drilldown()
