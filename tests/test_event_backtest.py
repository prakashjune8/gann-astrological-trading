"""Unit tests for Event-Driven Backtester & Indian Reality Models (Sub-Task 2).

Verifies:
1. IndianFeeModel accurate statutory deductions (STT, NSE turnover, SEBI, GST, Stamp duty).
2. SlippageModel bid/ask spread and volume impact dynamics.
3. EventDrivenBacktester zero look-ahead execution loop.
4. MFE and MAE excursion tracking across intra-trade bars.
5. Automated OCO bracket resolution (18-pt hard stop vs targets).
"""
from __future__ import annotations

import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd
import numpy as np

from core.backtest_engine import (
    EventDrivenBacktester,
    ExitReason,
    IndianFeeModel,
    SlippageModel,
    TradeDirection,
    TradeSignal,
)
from core.backtest_data import ParquetDataLoader, NetworkLatencySimulator


def test_indian_fee_model():
    print("[1/4] Testing IndianFeeModel Statutory Deductions...")
    # Example: 1 lot Nifty buy at 20,000 (val = 1,000,000), sell at 20,200 (val = 1,010,000)
    buy_val = 1_000_000.0
    sell_val = 1_010_000.0
    gross_pnl = sell_val - buy_val  # +₹10,000

    net_pnl, fees = IndianFeeModel.compute_net_pnl(gross_pnl, buy_val, sell_val)

    # Assert individual components
    expected_stt = round(sell_val * 0.000125, 2)            # ₹126.25
    expected_turnover = round((buy_val + sell_val) * 0.000019, 2)  # ₹38.19
    expected_sebi = round((buy_val + sell_val) * 0.000001, 2)      # ₹2.01
    expected_stamp = round(buy_val * 0.000020, 2)           # ₹20.00
    expected_brokerage = 40.0                               # ₹40.00
    expected_gst = round((expected_brokerage + expected_turnover + expected_sebi) * 0.18, 2)  # ₹14.44
    expected_total = round(expected_stt + expected_turnover + expected_sebi + expected_stamp + expected_brokerage + expected_gst, 2)

    assert fees.stt == expected_stt, f"STT mismatch: {fees.stt} vs {expected_stt}"
    assert fees.turnover_charges == expected_turnover
    assert fees.sebi_charges == expected_sebi
    assert fees.stamp_duty == expected_stamp
    assert fees.brokerage == expected_brokerage
    assert fees.gst == expected_gst
    assert fees.total_fees == expected_total
    assert net_pnl == round(gross_pnl - expected_total, 2)
    assert net_pnl < gross_pnl, "Net P&L must strictly be less than Gross P&L due to fee deduction"
    print(f"      Passed. Gross P&L: ₹{gross_pnl:,.2f} -> Net P&L: ₹{net_pnl:,.2f} (Total Statutory Fees: ₹{fees.total_fees:.2f})")


def test_slippage_model():
    print("[2/4] Testing SlippageModel Dynamics...")
    model = SlippageModel(half_spread_pts=0.5, impact_coeff=0.1)
    base_p = 22000.0
    
    # Buy order
    fill_buy, slip_buy = model.calculate_fill_price(base_p, is_buy=True, order_qty=50, bar_volume=10000)
    assert fill_buy > base_p, "Buy fill price must include positive slippage above base"
    assert slip_buy >= 0.5, "Slippage must at least equal half spread"

    # Sell order
    fill_sell, slip_sell = model.calculate_fill_price(base_p, is_buy=False, order_qty=50, bar_volume=10000)
    assert fill_sell < base_p, "Sell fill price must include negative slippage below base"
    print(f"      Passed. Base: {base_p} -> Buy Fill: {fill_buy} (+{slip_buy} pts), Sell Fill: {fill_sell} (-{slip_sell} pts)")


def test_event_driven_zero_lookahead_and_mfe():
    print("[3/4] Testing EventDrivenBacktester Zero Look-Ahead & MFE/MAE...")
    # Construct synthetic 1-minute dataframe: 10 bars (09:15 to 09:24)
    start_dt = pd.Timestamp("2024-01-15 09:15:00").tz_localize("Asia/Kolkata")
    bars = []
    prices = [21500.0, 21505.0, 21510.0, 21520.0, 21535.0, 21640.0, 21650.0, 21630.0, 21620.0, 21610.0]
    
    for i, p in enumerate(prices):
        t = start_dt + pd.Timedelta(minutes=i)
        bars.append({
            "timestamp_ist": t,
            "open": p - 2.0,
            "high": p + 5.0,
            "low": p - 4.0,
            "close": p,
            "volume": 5000
        })
    df_1m = pd.DataFrame(bars).set_index("timestamp_ist")

    # Signal triggered at 09:16:00 close (bar index 1)
    sig_time = start_dt + pd.Timedelta(minutes=1)
    signal = TradeSignal(
        signal_id="SIG_001",
        signal_time=sig_time,
        direction=TradeDirection.LONG,
        reference_price=21505.0,
        hard_stop_points=18.0,
        target1_points=125.0,
        target2_points=252.0
    )

    backtester = EventDrivenBacktester(
        slippage_model=SlippageModel(half_spread_pts=0.5, impact_coeff=0.0),
        latency_sim=NetworkLatencySimulator(min_latency_ms=100.0, max_latency_ms=100.0),
        contract_lot_size=50
    )

    trades = backtester.simulate(df_1m, [signal])
    assert len(trades) == 1, "Expected exactly 1 trade to execute"
    trd = trades[0]

    # Verify zero look-ahead: order dispatched at 09:16 bar close, filled at 09:17 open
    expected_fill_bar_time = start_dt + pd.Timedelta(minutes=2)
    assert trd.dispatch_time == sig_time, "Dispatch time must match bar close timestamp"
    assert trd.fill_time > trd.dispatch_time, "Fill time must include network transit delay"
    
    # 09:17 open was 21510.0 - 2.0 = 21508.0 + 0.5 slippage = 21508.5
    assert trd.entry_price == 21508.5
    
    # In bar index 5 (09:20), price spiked to high of 21645.0, triggering Target 1 (+125 pts)
    # Target 1 = 21508.5 + 125.0 = 21633.5
    assert trd.exit_reason == ExitReason.TARGET_1, f"Expected TARGET_1 exit, got {trd.exit_reason}"
    assert trd.exit_price == trd.target1_price
    assert trd.gross_pnl_points == 125.0
    assert trd.mfe_points >= 125.0, f"MFE ({trd.mfe_points}) must be at least target points"
    assert trd.mae_points <= 0.0, f"MAE ({trd.mae_points}) must record negative excursion"
    assert trd.net_pnl_inr < trd.gross_pnl_inr, "Net INR P&L must accurately deduct statutory fees"
    print(f"      Passed. Trade entered @ {trd.entry_price}, exited on TARGET_1 @ {trd.exit_price}. Net P&L: ₹{trd.net_pnl_inr:,.2f}")


def test_short_trade_hard_stop():
    print("[4/4] Testing Short Trade 18-Point Hard Stop Breach...")
    start_dt = pd.Timestamp("2024-01-15 10:00:00").tz_localize("Asia/Kolkata")
    bars = []
    # Upward spike to breach short stop
    prices = [21500.0, 21502.0, 21510.0, 21530.0, 21540.0]
    for i, p in enumerate(prices):
        t = start_dt + pd.Timedelta(minutes=i)
        bars.append({
            "timestamp_ist": t,
            "open": p,
            "high": p + 6.0,
            "low": p - 3.0,
            "close": p,
            "volume": 4000
        })
    df_1m = pd.DataFrame(bars).set_index("timestamp_ist")

    # Short signal at 10:01 bar close
    sig = TradeSignal(
        signal_id="SIG_SHORT_002",
        signal_time=start_dt + pd.Timedelta(minutes=1),
        direction=TradeDirection.SHORT,
        reference_price=21502.0,
        hard_stop_points=18.0,
        target1_points=125.0
    )

    backtester = EventDrivenBacktester(
        slippage_model=SlippageModel(half_spread_pts=0.5, impact_coeff=0.0),
        contract_lot_size=50
    )
    trades = backtester.simulate(df_1m, [sig])
    assert len(trades) == 1
    trd = trades[0]

    # Entry at 10:02 open: 21510.0 - 0.5 = 21509.5
    # Short Stop = 21509.5 + 18.0 = 21527.5
    # Bar index 3 (10:03) high reached 21536.0, breaching 21527.5
    assert trd.exit_reason == ExitReason.HARD_STOP, f"Expected HARD_STOP, got {trd.exit_reason}"
    assert trd.gross_pnl_points == -18.0
    assert trd.net_pnl_inr < 0.0
    print(f"      Passed. Short Hard Stop accurately executed at {trd.exit_price} (-18.0 pts). Loss: ₹{trd.net_pnl_inr:,.2f}")


if __name__ == "__main__":
    print("=================================================================")
    print("RUNNING EVENT-DRIVEN & REALITY MODEL TEST SUITE (SUB-TASK 2)")
    print("=================================================================")
    test_indian_fee_model()
    test_slippage_model()
    test_event_driven_zero_lookahead_and_mfe()
    test_short_trade_hard_stop()
    print("=================================================================")
    print("ALL 4 EVENT-DRIVEN TESTS DETERMINISTICALLY PASSED")
    print("=================================================================")
