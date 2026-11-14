"""Comprehensive Integration Test Suite for:
1. InteractiveTradeInspector Timeframe Variations Dropdown (2, 4, 6, 8, Custom, 5, 10, 15, 1-Hour, Daily, Weekly, Monthly).
2. Dynamic Custom N-minute addition and OptionMenu registration.
3. StateManager preference disk persistence (last used timeframe, custom duration).
4. Viewport exact location tracking (date, timestamp, cursor) and automatic next-day session restoration.
"""
import sys
import os
import unittest
from unittest.mock import patch
import pandas as pd
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import customtkinter as ctk
from ui.state_manager import StateManager
from ui.components.interactive_trade_inspector import InteractiveTradeInspector


def generate_synthetic_3day_data():
    """Generates 3 trading sessions (1,125 1-minute bars) of realistic OHLCV data."""
    rows = []
    base_price = 18000.0
    start_date = pd.Timestamp("2023-01-02", tz="Asia/Kolkata")
    curr = start_date
    for d in range(3):
        while curr.weekday() >= 5:
            curr += pd.Timedelta(days=1)
        session_start = curr.replace(hour=9, minute=15, second=0)
        p = base_price
        for m in range(375):
            ts = session_start + pd.Timedelta(minutes=m)
            o = p
            h = o + np.random.uniform(0.5, 5.0)
            l = o - np.random.uniform(0.5, 5.0)
            c = np.random.uniform(l, h)
            rows.append({
                "timestamp": ts,
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "volume": 300
            })
            p = c
        curr += pd.Timedelta(days=1)
        base_price = p
    return pd.DataFrame(rows)


def run_comprehensive_inspector_tests():
    print("=" * 75)
    print("  RUNNING COMPREHENSIVE INSPECTOR DROPDOWN & PERSISTENCE VERIFICATION")
    print("=" * 75)

    root = ctk.CTk()
    root.withdraw()

    df_sample = generate_synthetic_3day_data()
    print(f"[*] Generated synthetic multi-session sample: {len(df_sample)} bars.")

    # 1. Test Instantiation and initial Dropdown Values
    inspector = InteractiveTradeInspector(root)
    dropdown_vals = inspector.menu_timeframe.cget("values")
    print(f"[*] Dropdown Registered Values:\n    {dropdown_vals}")

    expected_variations = [
        "1-Min", "2-Min", "4-Min", "5-Min", "6-Min", "8-Min",
        "10-Min", "15-Min", "1-Hour", "Daily", "Weekly", "Monthly", "Custom..."
    ]
    for opt in expected_variations:
        assert opt in dropdown_vals, f"Missing expected option '{opt}' in dropdown"
    print("  [OK] All requested time variations are present in dropdown menu.")

    # 2. Ingest Sample Data
    inspector.load_trades_and_data(df_sample)
    assert inspector.raw_1m_df is not None and len(inspector.raw_1m_df) == 1125

    # 3. Test Timeframe Switching across variations
    test_switches = ["2-Min", "4-Min", "6-Min", "8-Min", "5-Min", "10-Min", "15-Min", "1-Hour", "Daily", "Weekly", "Monthly"]
    for tf in test_switches:
        inspector._on_timeframe_changed(tf)
        assert inspector.current_timeframe == tf, f"Current timeframe mismatch: {inspector.current_timeframe} != {tf}"
        assert inspector.timeframe_var.get() == tf, f"StringVar mismatch for {tf}"
        assert inspector.active_df is not None and not inspector.active_df.empty
        # Verify persistence to StateManager
        assert inspector.state_manager.prefs.backtest_timeframe == tf, f"Failed state persistence for {tf}"
        print(f"  [OK] Successfully switched and persisted timeframe: {tf:<10} (Active Bars: {len(inspector.active_df)})")

    # 4. Test Custom... Prompt Handling
    print("[*] Testing dynamic 'Custom...' N-minute timeframe prompt...")
    with patch("customtkinter.CTkInputDialog.get_input", return_value="7"):
        inspector._on_timeframe_changed("Custom...")
    
    assert inspector.current_timeframe == "7-Min", f"Expected '7-Min', got '{inspector.current_timeframe}'"
    assert inspector.custom_minutes == 7
    assert inspector.state_manager.prefs.backtest_custom_minutes == 7
    assert inspector.state_manager.prefs.backtest_timeframe == "7-Min"
    assert "7-Min" in inspector.menu_timeframe.cget("values")
    print(f"  [OK] 'Custom...' dialog successfully injected '7-Min' into dropdown options and persisted setting.")

    # 5. Test Exact Viewport Location Scrubbing & Disk Recording
    print("[*] Testing exact location recording on scrub...")
    # Scrub to bar index 100 in 7-Min active DataFrame
    inspector._on_slider_scrub(100)
    saved_ts = inspector.state_manager.prefs.backtest_saved_timestamp
    saved_dt = inspector.state_manager.prefs.backtest_saved_date
    saved_cursor = inspector.state_manager.prefs.backtest_saved_cursor
    print(f"  [OK] Recorded Location: Timestamp={saved_ts} | Date={saved_dt} | Cursor={saved_cursor}")
    assert saved_ts != "", "Saved timestamp must not be empty"
    assert saved_dt != "", "Saved date must not be empty"
    assert saved_cursor > 0, "Saved cursor must be > 0"

    # 6. Simulate Next-Day App Launch (Re-Opening at Exact Location)
    print("[*] Simulating reopening the app the next day...")
    # Create fresh StateManager and fresh inspector instance
    sm_next_day = StateManager()
    assert sm_next_day.prefs.backtest_timeframe == "7-Min"
    assert sm_next_day.prefs.backtest_custom_minutes == 7
    assert sm_next_day.prefs.backtest_saved_timestamp == saved_ts

    fresh_inspector = InteractiveTradeInspector(root)
    assert fresh_inspector.current_timeframe == "7-Min"
    assert fresh_inspector.timeframe_var.get() == "7-Min"

    # Ingest data into fresh inspector — must auto-restore exact timestamp & cursor
    fresh_inspector.load_trades_and_data(df_sample)
    restored_slice = fresh_inspector.current_slice
    assert restored_slice is not None and not restored_slice.empty
    restored_last_ts = str(restored_slice["timestamp"].iloc[-1])
    print(f"  [OK] Reopened at Exact Location: Restored Viewport Last Bar = {restored_last_ts}")
    assert restored_last_ts == saved_ts, f"Location mismatch: {restored_last_ts} != {saved_ts}"

    root.destroy()
    print("=" * 75)
    print("  ALL COMPREHENSIVE INSPECTOR & PERSISTENCE TESTS PASSED 100%!")
    print("=" * 75)


if __name__ == "__main__":
    run_comprehensive_inspector_tests()
