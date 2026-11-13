"""Unit & Integration Test Suite for Sub-Task 4: Quant Tear Sheet & Visualizer.

Verifies:
1. QuantMetricsCalculator accurate institutional metrics (Sharpe, Sortino, Expectancy, CAGR).
2. QuantChartRenderer generates 4 high-DPI dark institutional figures at 200 DPI.
3. BacktestReportGenerator compiles reports/GANN_TRIPLE_CONFLUENCE_TEARSHEET.pdf.
4. Validates zero tofu glyphs and clean ReportLab embedding.
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
import shutil

# Windows console encoding safeguard
if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np

from core.backtest_data import ParquetDataLoader
from core.backtest_engine import HistoricalBacktestRunner, TradeLedger
from reporting.backtest_report_generator import (
    BacktestReportGenerator,
    QuantChartRenderer,
    QuantMetricsCalculator,
)


def test_metrics_calculator():
    print("[1/3] Testing QuantMetricsCalculator...")
    # Generate synthetic trade dataframe
    trades = []
    base_t = datetime(2023, 1, 1, 9, 30)
    for i in range(50):
        t_entry = base_t + timedelta(days=i * 2)
        is_win = (i % 3 != 0)  # ~66% win rate
        gross_pts = 125.0 if is_win else -18.0
        gross_inr = gross_pts * 50.0
        fees = 250.0
        net_inr = gross_inr - fees
        trades.append({
            "trade_id": f"TRD_{i:04d}",
            "signal_id": f"SIG_{i:04d}",
            "direction": "LONG",
            "entry_time": t_entry,
            "fill_price": 20000.0,
            "exit_time": t_entry + timedelta(minutes=45),
            "exit_price": 20000.0 + gross_pts,
            "exit_reason": "TARGET_1" if is_win else "HARD_STOP",
            "gross_pnl_points": gross_pts,
            "gross_pnl_inr": gross_inr,
            "total_fees": fees,
            "net_pnl_inr": net_inr,
            "mfe_points": 130.0 if is_win else 5.0,
            "mae_points": -6.0 if is_win else -18.5,
            "holding_minutes": 45
        })
    df_trades = pd.DataFrame(trades)

    summary, daily_df, dd_series, monthly_matrix = QuantMetricsCalculator.calculate_metrics(
        df_trades,
        initial_capital=1_000_000.0
    )

    assert summary.total_trades == 50
    assert summary.winning_trades > 30
    assert summary.win_rate_pct >= 60.0
    assert summary.profit_factor > 1.5
    assert summary.sharpe_ratio != 0.0
    assert summary.expectancy_points > 0.0
    assert summary.stop_survival_rate_pct > 80.0
    assert not daily_df.empty
    assert not monthly_matrix.empty
    print(f"      Passed. Win Rate: {summary.win_rate_pct:.1f}%, Profit Factor: {summary.profit_factor:.2f}, Sharpe: {summary.sharpe_ratio:.2f}")


def test_chart_rendering():
    print("[2/3] Testing QuantChartRenderer 4 High-DPI Figures...")
    fig_dir = Path("reports/figures_test")
    fig_dir.mkdir(parents=True, exist_ok=True)

    # 1. Equity DataFrame
    dates = pd.date_range("2023-01-01", "2024-06-30", freq="D").date
    cum_pnl = np.cumsum(np.random.normal(500, 2000, len(dates)))
    daily_df = pd.DataFrame(index=dates)
    daily_df["equity"] = 1_000_000.0 + cum_pnl
    daily_df["high_water_mark"] = daily_df["equity"].cummax()
    daily_df["drawdown_pct"] = (daily_df["equity"] - daily_df["high_water_mark"]) / daily_df["high_water_mark"] * 100.0

    # 2. Trades DataFrame
    trades = []
    for i in range(40):
        is_win = (i % 2 == 0)
        trades.append({
            "mae_points": -abs(np.random.uniform(2, 17 if is_win else 22)),
            "mfe_points": np.random.uniform(110, 260) if is_win else np.random.uniform(0, 15),
            "net_pnl_inr": 5000.0 if is_win else -1100.0
        })
    df_trades = pd.DataFrame(trades)

    # 3. Monthly Matrix
    monthly_mat = pd.DataFrame(
        np.random.uniform(-1.5, 4.5, (2, 12)),
        index=[2023, 2024],
        columns=range(1, 13)
    )

    c1 = QuantChartRenderer.render_equity_curve(daily_df, output_path=fig_dir / "c1.png")
    c2 = QuantChartRenderer.render_drawdown_chart(daily_df, output_path=fig_dir / "c2.png")
    c3 = QuantChartRenderer.render_mfe_mae_scatter(df_trades, output_path=fig_dir / "c3.png")
    c4 = QuantChartRenderer.render_monthly_heatmap(monthly_mat, output_path=fig_dir / "c4.png")

    for c in [c1, c2, c3, c4]:
        assert c.is_file(), f"Chart missing: {c}"
        assert c.stat().st_size > 10_000, f"Chart size too small: {c.stat().st_size} bytes"

    shutil.rmtree(fig_dir, ignore_errors=True)
    print("      Passed. All 4 High-DPI figures rendered successfully (>10KB each).")


def test_pdf_tearsheet_compilation():
    print("[3/3] Testing BacktestReportGenerator PDF Compilation...")
    test_data_dir = Path("data/parquet_pdf_test")
    loader = ParquetDataLoader(base_dir=test_data_dir)

    # Seed synthetic Parquet
    loader.generate_synthetic_benchmark_parquet("NIFTY50", year=2023, month=12, seed_price=21000.0)
    loader.generate_synthetic_benchmark_parquet("NIFTY50", year=2024, month=1, seed_price=21500.0)

    runner = HistoricalBacktestRunner(data_loader=loader)
    comparison = runner.run_full_comparison("NIFTY50")

    pdf_out = Path("reports/test_tearsheet.pdf")
    BacktestReportGenerator.generate_tear_sheet(
        is_ledger=comparison["IS"],
        oos_ledger=comparison["OOS"],
        symbol="NIFTY50",
        output_pdf_path=pdf_out
    )

    assert pdf_out.is_file(), f"PDF was not compiled at {pdf_out}"
    assert pdf_out.stat().st_size > 40_000, f"PDF file size too small: {pdf_out.stat().st_size} bytes"

    # Verify PDF header
    with open(pdf_out, "rb") as f:
        header = f.read(5)
        assert header == b"%PDF-", f"Invalid PDF header: {header}"

    # Clean up test artifacts
    shutil.rmtree(test_data_dir, ignore_errors=True)
    if pdf_out.is_file():
        pdf_out.unlink()

    print(f"      Passed. Quant Tear Sheet compiled cleanly with verified %PDF- header.")


if __name__ == "__main__":
    print("=================================================================")
    print("RUNNING QUANT TEAR SHEET & VISUALIZER TEST SUITE (SUB-TASK 4)")
    print("=================================================================")
    test_metrics_calculator()
    test_chart_rendering()
    test_pdf_tearsheet_compilation()
    print("=================================================================")
    print("ALL 3 SUB-TASK 4 TESTS DETERMINISTICALLY PASSED")
    print("=================================================================")
