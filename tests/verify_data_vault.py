"""Verification Suite for Local Data Vault Manager & Backtest Window Vault Status Panel.

Validates:
1. Directory partition scaffolding: `data/backtest_vault/{INSTRUMENT}/{YEAR}/`.
2. Bullion exclusion validation (strict hard-rejection of GOLD/SILVER).
3. Data ingestion via yfinance with Snappy compression and IST timezone formatting.
4. Instantaneous metadata scanning (`pq.read_metadata`) and status reporting.
5. Columnar retrieval via `load_vault_range`.
6. UI integration in `BacktestQuantWorkstationWindow` (panel, telemetry label, button).
"""
import os
import sys
from datetime import date
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pyarrow.parquet as pq
import customtkinter as ctk

from core.data_vault_manager import LocalDataVaultManager, BULLION_BLACKLIST
from ui.windows.backtest_window import BacktestQuantWorkstationWindow


def test_data_vault_architecture_and_ui():
    print("=" * 65)
    print("  VERIFYING LOCAL DATA VAULT ARCHITECTURE & WORKSTATION UI")
    print("=" * 65)

    vault = LocalDataVaultManager()
    print(f"[1/6] Vault root initialized at: {vault.base_dir}")
    assert vault.base_dir.is_dir(), "Vault base directory must exist"

    # [2] Test Bullion Exclusion
    print("[2/6] Auditing bullion hard-exclusion enforcement...")
    for sym in ["GOLD", "GOLDBEES", "SILVER", "XAU", "GC=F"]:
        rejected = False
        try:
            vault.validate_instrument(sym)
        except ValueError:
            rejected = True
        assert rejected, f"Bullion symbol '{sym}' must be rejected with ValueError"
    print("  [OK] Bullion blacklist strictly enforced (100% rejection rate).")

    # [3] Test Data Ingestion & Snappy Parquet Generation
    print("[3/6] Testing historical ingestion & Snappy Parquet generation for NIFTY50 (2023-01)...")
    progress_updates = []
    def on_prog(msg, pct):
        progress_updates.append((msg, pct))

    res = vault.download_and_store_historical_data(
        symbol="NIFTY50",
        start_date="2023-01-01",
        end_date="2023-01-31",
        progress_callback=on_prog
    )
    print(f"  Ingestion Result: {res['files_saved']} files, {res['total_bars']:,} bars, {res['total_mb']} MB")
    assert res["files_saved"] >= 1, "Must generate at least 1 monthly parquet file"
    assert res["total_bars"] > 5000, f"Expected >5,000 minute bars for January, got {res['total_bars']}"

    target_file = vault.get_month_filepath("NIFTY50", 2023, 1)
    assert target_file.is_file(), f"Target parquet file must exist at {target_file}"
    print(f"  [OK] Parquet file confirmed: {target_file}")

    # Inspect Compression & Schema
    meta = pq.read_metadata(target_file)
    assert meta.num_rows == res["total_bars"]
    col_compression = meta.row_group(0).column(0).compression
    assert col_compression == "SNAPPY", f"Compression must be SNAPPY, got {col_compression}"
    print(f"  [OK] Compression verified: {col_compression}")

    # [4] Test Vault Telemetry Scanning
    print("[4/6] Testing instantaneous disk telemetry scanning...")
    status = vault.get_vault_status("NIFTY50")
    print(f"  Vault Status: {status['date_range']} | {status['total_mb']} MB | {status['total_bars']:,} bars")
    assert status["is_ready"] is True
    assert status["total_files"] >= 1
    assert "2023" in status["months"][0]
    print("  [OK] Vault status scan verified.")

    # [5] Test Columnar Fast Retrieval
    print("[5/6] Testing columnar fast retrieval via load_vault_range...")
    df = vault.load_vault_range("NIFTY50", "2023-01-01", "2023-01-31")
    assert not df.empty, "Loaded dataframe must not be empty"
    assert df.index.tz is not None and "Kolkata" in str(df.index.tz), "Index must be localized to Asia/Kolkata"
    for col in ["open", "high", "low", "close", "volume"]:
        assert col in df.columns, f"Required column '{col}' missing from loaded dataframe"
    print(f"  [OK] Loaded {len(df):,} rows with columns {df.columns.tolist()} in IST.")

    # [6] Test UI Integration in BacktestQuantWorkstationWindow
    print("[6/6] Testing UI integration in BacktestQuantWorkstationWindow...")
    root = ctk.CTk()
    root.withdraw()
    try:
        workstation = BacktestQuantWorkstationWindow(root)
        workstation.withdraw()

        assert hasattr(workstation, "vault_panel"), "Must have vault_panel frame"
        assert hasattr(workstation, "lbl_vault_telemetry"), "Must have lbl_vault_telemetry label"
        assert hasattr(workstation, "btn_download_vault"), "Must have btn_download_vault button"
        assert hasattr(workstation, "refresh_vault_status"), "Must have refresh_vault_status method"

        telemetry_text = workstation.lbl_vault_telemetry.cget("text")
        print(f"  Rendered UI Telemetry: '{telemetry_text}'")
        assert "NIFTY50" in telemetry_text, "Telemetry label must display instrument"
        assert "MB" in telemetry_text or "bars" in telemetry_text, "Telemetry must display size/bars"
        print("  [OK] Data Vault Status panel and telemetry successfully rendered in Workstation UI.")

        workstation.destroy()
    finally:
        root.destroy()

    print("\n" + "=" * 65)
    print(" [SUCCESS] ALL 6 DATA VAULT & WORKSTATION UI VERIFICATIONS PASSED!")
    print("=" * 65)


if __name__ == "__main__":
    test_data_vault_architecture_and_ui()
