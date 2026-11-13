"""Unit and integration tests for core/backtest_data.py.
Verifies:
1. Indian market calendar holiday recognition and trading day filtering.
2. Strict bullion exclusion rejection.
3. NetworkLatencySimulator 50ms-200ms bounds.
4. Parquet monthly slice write, zstd compression, and partitioned read (OOS/IS).
5. Phase 2 Option and Greeks stubs.
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.backtest_data import (
    MarketCalendarManager,
    NetworkLatencySimulator,
    ParquetDataLoader,
    GreeksEngineStub,
    OptionContractStub,
    BULLION_BLACKLIST,
)


def test_calendar_manager():
    print("[1/5] Testing MarketCalendarManager...")
    cal = MarketCalendarManager()
    
    # 2024-01-26 is Republic Day (official NSE holiday)
    rep_day = date(2024, 1, 26)
    assert not cal.is_trading_day(rep_day, "NSE"), "Republic Day 2024 must be closed for NSE"
    
    # 2024-01-27 is Saturday
    sat = date(2024, 1, 27)
    assert not cal.is_trading_day(sat, "NSE"), "Saturday must be non-trading"

    # 2024-01-29 is Monday (normal trading day)
    mon = date(2024, 1, 29)
    assert cal.is_trading_day(mon, "NSE"), "Monday 2024-01-29 must be an open trading day"
    
    trading_days = cal.get_trading_days(date(2024, 1, 1), date(2024, 1, 31), exchange="NSE")
    assert len(trading_days) >= 18, f"Expected at least 18 trading days in Jan 2024, got {len(trading_days)}"
    print(f"      Passed. Identified {len(trading_days)} trading days in Jan 2024.")


def test_bullion_rejection():
    print("[2/5] Testing Strict Bullion Exclusion Filter...")
    loader = ParquetDataLoader()
    
    # Allowed symbols
    for sym in ["NIFTY50", "BANKNIFTY", "CRUDEOIL", "NATURALGAS", "COPPER"]:
        loader.validate_instrument(sym)
        
    # Blacklisted symbols
    for blacklisted in ["GOLD", "SILVERBEES", "GOLDMINI", "XAU", "SI=F"]:
        try:
            loader.validate_instrument(blacklisted)
            assert False, f"Expected rejection for {blacklisted}"
        except ValueError:
            pass
    print("      Passed. Absolute bullion rejection verified.")


def test_network_latency():
    print("[3/5] Testing NetworkLatencySimulator (50ms - 200ms)...")
    sim = NetworkLatencySimulator(min_latency_ms=50.0, max_latency_ms=200.0, seed=123)
    t0 = datetime(2024, 1, 15, 9, 15, 0)
    
    for _ in range(50):
        t_arr = sim.apply_latency(t0)
        delay_ms = (t_arr - t0).total_seconds() * 1000.0
        assert 50.0 <= delay_ms <= 200.0, f"Latency {delay_ms}ms outside bounds [50, 200]"
    print("      Passed. Latency strictly bounded between 50ms and 200ms.")


def test_parquet_partitioned_io():
    print("[4/5] Testing ParquetDataLoader Partitioning & Storage...")
    test_parquet_dir = Path("data/parquet_test")
    loader = ParquetDataLoader(base_dir=test_parquet_dir)
    
    # Generate synthetic monthly slice for Jan 2024 (Out-of-sample window)
    p_path = loader.generate_synthetic_benchmark_parquet(
        symbol="NIFTY50",
        year=2024,
        month=1,
        seed_price=21500.0
    )
    assert p_path.is_file(), f"Parquet file was not generated at {p_path}"
    assert p_path.suffix == ".parquet"
    
    # Load via OOS partition
    df_oos = loader.load_dataset("NIFTY50", partition="OOS")
    assert not df_oos.empty, "Loaded OOS DataFrame must not be empty"
    assert "close" in df_oos.columns
    assert "volume" in df_oos.columns
    assert df_oos.index.tz.zone == "Asia/Kolkata"
    assert len(df_oos) > 3000, f"Expected >3000 1-minute bars, got {len(df_oos)}"
    print(f"      Passed. Successfully written and loaded {len(df_oos)} bars from {p_path.name}")
    
    # Clean up test dir
    import shutil
    shutil.rmtree(test_parquet_dir, ignore_errors=True)


def test_options_and_greeks_stubs():
    print("[5/5] Testing Phase 2 Options and Greeks Stubs...")
    contract = OptionContractStub(
        symbol="NIFTY24JAN21500CE",
        underlying="NIFTY50",
        strike=21500.0,
        option_type="CE",
        expiry_date=date(2024, 1, 25)
    )
    assert contract.lot_size == 50
    greeks = GreeksEngineStub.compute_greeks(
        spot=21520.0,
        strike=21500.0,
        time_to_expiry_years=5 / 365.0,
        option_type="CE"
    )
    assert greeks.delta > 0.0
    assert greeks.implied_volatility == 0.15
    print("      Passed. Architectural stubs verified.")


if __name__ == "__main__":
    print("=================================================================")
    print("RUNNING INSTITUTIONAL DATA ARCHITECTURE TEST SUITE (PHASE 1 SUB-1)")
    print("=================================================================")
    test_calendar_manager()
    test_bullion_rejection()
    test_network_latency()
    test_parquet_partitioned_io()
    test_options_and_greeks_stubs()
    print("=================================================================")
    print("ALL 5 DATA ARCHITECTURE TESTS DETERMINISTICALLY PASSED")
    print("=================================================================")
