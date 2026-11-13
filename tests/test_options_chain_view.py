"""Institutional Test Suite for Live Options Chain & Greeks View (Phase 2, Sub-Task 3).

Verifies:
1. Dual-Sided UI Layout and Widget Pool instantiation.
2. Gann Square of Nine Harmonic Angle Classifier (Cardinal, Fixed, Standard).
3. Zero-Memory-Leak Audit (100 rapid refresh ticks with identical widget pool references).
4. Delta-Neutral Hedger & Portfolio Risk Aggregator.
5. Dynamic Theme Adaptation and teardown.
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Windows console encoding safeguard
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import customtkinter as ctk

from core.price_harmonics import PriceHarmonicsEngine
from ui.components.options_chain_view import OptionsChainView
from ui.theme import DARK_THEME, LIGHT_THEME


def run_full_suite():
    print("=" * 65)
    print("RUNNING LIVE OPTIONS CHAIN & GREEKS VIEW TEST SUITE (PHASE 2-3)")
    print("=" * 65)

    # 1. Harmonic Classifier
    print("[1/5] Testing Gann Square of Nine Harmonic Angle Classifier...")
    cat, label, col = OptionsChainView.classify_gann_harmonic(24500.0, orb_deg=6.0)
    assert cat == "CARDINAL", f"Expected CARDINAL for 24500, got {cat} ({label})"
    assert col == "#00f0ff", f"Expected Electric Cyan, got {col}"

    cat, label, col = OptionsChainView.classify_gann_harmonic(24100.0, orb_deg=6.0)
    assert cat == "FIXED", f"Expected FIXED for 24100, got {cat} ({label})"
    assert col == "#f43f5e", f"Expected Neon Ruby, got {col}"

    cat, label, col = OptionsChainView.classify_gann_harmonic(24200.0, orb_deg=6.0)
    assert cat == "STANDARD", f"Expected STANDARD for 24200, got {cat} ({label})"
    print("      Passed. Harmonic classification verified (Cardinal, Fixed, Standard).")

    # Shared Tkinter Root in headless mode
    root = ctk.CTk()
    root.withdraw()

    try:
        # 2. Widget Pool Allocation
        print("[2/5] Testing Dual-Sided Options Chain Widget Pool Allocation...")
        view = OptionsChainView(root, theme=DARK_THEME)
        assert len(view.row_widget_pool) == 21, f"Expected 21 rows in pool, got {len(view.row_widget_pool)}"

        first_row = view.row_widget_pool[0]
        expected_keys = [
            "frame", "ce_vega", "ce_theta", "ce_gamma", "ce_delta", "ce_iv", "ce_ltp",
            "strike", "gann", "pe_ltp", "pe_iv", "pe_delta", "pe_gamma", "pe_theta", "pe_vega"
        ]
        for k in expected_keys:
            assert k in first_row, f"Missing key {k} in row widget pool"

        view._on_strike_range_change("±5 (11)")
        assert len(view.row_widget_pool) == 11, f"Expected 11 rows after range change, got {len(view.row_widget_pool)}"

        view._on_strike_range_change("±15 (31)")
        assert len(view.row_widget_pool) == 31, f"Expected 31 rows after range change, got {len(view.row_widget_pool)}"
        print("      Passed. Widget pool allocates exact row dimensions (11, 21, 31).")

        # 3. Zero-Memory-Leak In-Place Refresh Loop
        print("[3/5] Testing Zero-Memory-Leak In-Place Refresh Loop...")
        time.sleep(0.3)
        view._run_analytical_calculation_worker()

        initial_widget_ids = [id(w["frame"]) for w in view.row_widget_pool]
        initial_cell_ids = [id(w["ce_ltp"]) for w in view.row_widget_pool]
        initial_pool_len = len(view.row_widget_pool)

        # 100 rapid in-place refresh ticks
        for _ in range(100):
            view._ui_refresh_tick()

        current_widget_ids = [id(w["frame"]) for w in view.row_widget_pool]
        current_cell_ids = [id(w["ce_ltp"]) for w in view.row_widget_pool]

        assert len(view.row_widget_pool) == initial_pool_len, "Pool size mutated during refresh!"
        assert initial_widget_ids == current_widget_ids, "Widget frames were re-created! Memory leak detected!"
        assert initial_cell_ids == current_cell_ids, "Cell labels were re-created! Memory leak detected!"
        assert view._ui_update_count >= 100, f"Expected >= 100 updates, got {view._ui_update_count}"
        print(f"      Passed. 100 refresh ticks completed with ZERO widget re-allocations (Pool constant: {initial_pool_len}).")

        # 4. Delta-Neutral Hedger & Portfolio Risk Aggregator
        print("[4/5] Testing Delta-Neutral Hedger & Portfolio Risk Aggregator...")
        # Preset Long Straddle
        view._preset_long_straddle()
        view._ui_refresh_tick()
        straddle_delta = view.lbl_net_delta.cget("text")
        print(f"      Straddle Net Delta: {straddle_delta}")

        # Preset Long CE (+2 Lots)
        view._preset_long_ce()
        view._ui_refresh_tick()
        long_ce_delta = view.lbl_net_delta.cget("text")
        delta_val = float(long_ce_delta.split()[0])
        assert delta_val > 50.0, f"Expected positive delta > 50 for +2 Long CE, got {delta_val}"
        assert "SELL" in view.lbl_hedge_advice.cget("text")
        print(f"      +2 Long CE Net Delta: {long_ce_delta} -> Advice: {view.lbl_hedge_advice.cget('text')}")

        # Apply Neutralizing Hedge via Futures
        view._apply_neutralizing_hedge()
        view._ui_refresh_tick()
        hedged_delta = view.lbl_net_delta.cget("text")
        hedged_val = float(hedged_delta.split()[0])
        print(f"      After Futures Neutralization: {hedged_delta}")
        assert abs(hedged_val) < 20.0, f"Hedge failed to neutralize delta, remaining: {hedged_val}"

        # Clear Positions
        view._preset_clear()
        view._ui_refresh_tick()
        zero_delta = view.lbl_net_delta.cget("text")
        assert "+0.00" in zero_delta or "0.00" in zero_delta
        assert view.lbl_hedge_status.cget("text") == "[✓ DELTA NEUTRAL]"
        print("      Passed. Hedging mathematics, advice dispatch, and neutralization verified.")

        # 5. Dynamic Theme Adaptation & Clean Teardown
        print("[5/5] Testing Theme Dynamic Adaptation & Clean Teardown...")
        view.apply_theme(LIGHT_THEME)
        assert view.theme.name == "LIGHT"
        assert view.cget("fg_color") == LIGHT_THEME.bg_primary

        view.apply_theme(DARK_THEME)
        assert view.theme.name == "DARK"
        assert view.cget("fg_color") == DARK_THEME.bg_primary

        view.destroy()
        assert view._refresh_timer_id is None
        print("      Passed. Dynamic theme propagation and clean teardown verified.")

    finally:
        try:
            root.quit()
        except Exception:
            pass

    print("=" * 65)
    print("ALL 5 OPTIONS CHAIN VIEW TESTS DETERMINISTICALLY PASSED")
    print("=" * 65)


if __name__ == "__main__":
    run_full_suite()
