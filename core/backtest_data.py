"""Institutional Parquet Data Ingest, Calendar Management & Reality Simulation Stubs.

Part of Phase 1 of the Gann Celestial Tracker Pro Quantitative Verification Engine.
Enforces:
1. Columnar Apache Parquet I/O with In-Sample (2020-2023) and Out-of-Sample (2024-2025) partitioning.
2. MarketCalendarManager parsing holidays_india.json for NSE and MCX sessions.
3. Permanent hard exclusion of all Gold and Silver instruments.
4. NetworkLatencySimulator modeling 50ms - 200ms transit jitter.
5. Architectural stubs for Nifty Weekly Options and Greeks Engine (Phase 2).
"""
from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Dict, List, Literal, Optional, Set, Tuple

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger("backtest_data")

# Strict Bullion Exclusion Blacklist
BULLION_BLACKLIST: Set[str] = {
    "GOLD", "GOLDBEES", "GOLDGUINEA", "GOLDMINI", "GOLDM", "GOLD1KG",
    "SILVER", "SILVERBEES", "SILVERMIC", "SILVERMINI", "SILVERM", "SILVER1KG",
    "XAU", "XAG", "GC=F", "SI=F"
}

# In-Sample and Out-of-Sample Partition Windows
IN_SAMPLE_START = date(2020, 1, 1)
IN_SAMPLE_END = date(2023, 12, 31)

OUT_OF_SAMPLE_START = date(2024, 1, 1)
OUT_OF_SAMPLE_END = date(2025, 12, 31)


class MarketCalendarManager:
    """Manages Indian market trading calendars (NSE/MCX) with official holiday reconciliation."""

    def __init__(self, holidays_file: Optional[Path] = None):
        self.holidays_file = holidays_file or self._find_holidays_file()
        self.nse_holidays: Set[date] = set()
        self.mcx_morning_holidays: Set[date] = set()
        self.mcx_evening_holidays: Set[date] = set()
        self._load_holidays()

    def _find_holidays_file(self) -> Path:
        """Locates holidays_india.json in workspace or fallback locations."""
        candidates = [
            Path("holidays_india.json"),
            Path("data/holidays_india.json"),
            Path(__file__).resolve().parent.parent / "holidays_india.json",
            Path(__file__).resolve().parent.parent / "data" / "holidays_india.json",
        ]
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            candidates.insert(0, Path(sys._MEIPASS) / "holidays_india.json")
            candidates.insert(1, Path(sys._MEIPASS) / "data" / "holidays_india.json")
        for p in candidates:
            if p.is_file():
                return p
        raise FileNotFoundError("holidays_india.json not found in workspace hierarchy.")

    def _load_holidays(self) -> None:
        """Parses holiday json into structured date sets."""
        if not self.holidays_file.is_file():
            logger.warning(f"Holiday calendar file missing: {self.holidays_file}")
            return

        with open(self.holidays_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        for h in data.get("holidays", []):
            try:
                h_date = datetime.strptime(h["date"], "%Y-%m-%d").date()
                if h.get("nse", False):
                    self.nse_holidays.add(h_date)
                if h.get("mcx_morning", False):
                    self.mcx_morning_holidays.add(h_date)
                if h.get("mcx_evening", False):
                    self.mcx_evening_holidays.add(h_date)
            except Exception as e:
                logger.debug(f"Skipping malformed holiday entry {h}: {e}")

    def is_trading_day(self, target_date: date, exchange: Literal["NSE", "MCX"] = "NSE") -> bool:
        """Determines if a given calendar date is an open trading day."""
        # Weekend check: 5 = Saturday, 6 = Sunday
        if target_date.weekday() in (5, 6):
            return False

        if exchange == "NSE":
            return target_date not in self.nse_holidays
        elif exchange == "MCX":
            # MCX is open if at least one session is operational
            both_closed = (target_date in self.mcx_morning_holidays) and (target_date in self.mcx_evening_holidays)
            return not both_closed

        return False

    def get_trading_days(self, start_date: date, end_date: date, exchange: Literal["NSE", "MCX"] = "NSE") -> List[date]:
        """Returns ordered list of active trading dates between start_date and end_date."""
        trading_days: List[date] = []
        curr = start_date
        while curr <= end_date:
            if self.is_trading_day(curr, exchange=exchange):
                trading_days.append(curr)
            curr += timedelta(days=1)
        return trading_days

    def get_session_times(self, target_date: date, exchange: Literal["NSE", "MCX"] = "NSE") -> Tuple[time, time]:
        """Returns standard open and close time for the given exchange."""
        if exchange == "NSE":
            return time(9, 15), time(15, 30)
        else:
            return time(9, 0), time(23, 55)


class NetworkLatencySimulator:
    """Models stochastic order dispatch, transit, and execution queue latency.
    
    Default delay bounds: 50ms to 200ms transit jitter.
    """

    def __init__(self, min_latency_ms: float = 50.0, max_latency_ms: float = 200.0, seed: Optional[int] = 42):
        self.min_latency_ms = min_latency_ms
        self.max_latency_ms = max_latency_ms
        self.rng = np.random.default_rng(seed)

    def sample_latency(self) -> timedelta:
        """Draws a random uniform transit delay in milliseconds."""
        ms = self.rng.uniform(self.min_latency_ms, self.max_latency_ms)
        return timedelta(milliseconds=float(ms))

    def apply_latency(self, dispatch_timestamp: datetime) -> datetime:
        """Computes effective arrival timestamp at exchange matching engine."""
        return dispatch_timestamp + self.sample_latency()


class ParquetDataLoader:
    """Institutional Columnar Data Loader & Partition Manager for High-Frequency OHLCV Data.
    
    Stores and queries data partitioned by instrument and calendar year/month.
    Strictly enforces zero bullion policy and In-Sample / Out-of-Sample boundaries.
    """

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or (Path(__file__).resolve().parent.parent / "data" / "parquet")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.calendar = MarketCalendarManager()

    @staticmethod
    def validate_instrument(symbol: str) -> None:
        """Enforces permanent architectural exclusion of Gold and Silver derivatives."""
        cleaned = symbol.strip().upper()
        for b in BULLION_BLACKLIST:
            if b in cleaned:
                raise ValueError(
                    f"CRITICAL REJECTION: Symbol '{symbol}' matches bullion blacklist '{b}'. "
                    "Gold and Silver instruments are strictly excluded by system mandate."
                )

    def get_partition_path(self, symbol: str, year: int, month: int) -> Path:
        """Returns path for partitioned monthly parquet file."""
        self.validate_instrument(symbol)
        clean_symbol = symbol.strip().upper().replace("^", "").replace("=F", "")
        month_str = f"{month:02d}"
        dir_path = self.base_dir / f"instrument={clean_symbol}" / f"year={year}"
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path / f"month={month_str}.parquet"

    def write_monthly_slice(self, df_1m: pd.DataFrame, symbol: str, year: int, month: int) -> Path:
        """Writes 1-minute OHLCV data to a monthly parquet file with zstd compression."""
        self.validate_instrument(symbol)
        file_path = self.get_partition_path(symbol, year, month)

        # Standardize schema
        df = df_1m.copy()
        if "timestamp_ist" not in df.columns and isinstance(df.index, pd.DatetimeIndex):
            df["timestamp_ist"] = df.index
        
        # Ensure timestamp is datetime64[ns, Asia/Kolkata]
        if df["timestamp_ist"].dt.tz is None:
            df["timestamp_ist"] = df["timestamp_ist"].dt.tz_localize("Asia/Kolkata")
        else:
            df["timestamp_ist"] = df["timestamp_ist"].dt.tz_convert("Asia/Kolkata")

        required_cols = ["timestamp_ist", "open", "high", "low", "close", "volume"]
        for col in required_cols:
            if col not in df.columns:
                raise KeyError(f"Missing required OHLCV column: {col}")

        # Cast to optimal types
        df["open"] = df["open"].astype("float64")
        df["high"] = df["high"].astype("float64")
        df["low"] = df["low"].astype("float64")
        df["close"] = df["close"].astype("float64")
        df["volume"] = df["volume"].astype("uint64")

        table = pa.Table.from_pandas(df[required_cols], preserve_index=False)
        pq.write_table(table, file_path, compression="zstd", compression_level=3)
        return file_path

    def load_dataset(
        self,
        symbol: str,
        partition: Literal["IS", "OOS", "FULL"] = "FULL",
        custom_range: Optional[Tuple[date, date]] = None
    ) -> pd.DataFrame:
        """Loads partitioned Parquet data into a contiguous, time-indexed DataFrame.
        
        Partitions:
        - 'IS'   : In-Sample (2020-01-01 to 2023-12-31)
        - 'OOS'  : Out-of-Sample (2024-01-01 to 2025-12-31)
        - 'FULL' : Entire historical series
        """
        self.validate_instrument(symbol)
        clean_symbol = symbol.strip().upper().replace("^", "").replace("=F", "")
        symbol_dir = self.base_dir / f"instrument={clean_symbol}"

        if not symbol_dir.is_dir():
            logger.warning(f"No parquet directory found at {symbol_dir}")
            return pd.DataFrame()

        # Determine target date bounds
        if custom_range is not None:
            d_start, d_end = custom_range
        elif partition == "IS":
            d_start, d_end = IN_SAMPLE_START, IN_SAMPLE_END
        elif partition == "OOS":
            d_start, d_end = OUT_OF_SAMPLE_START, OUT_OF_SAMPLE_END
        else:
            d_start, d_end = IN_SAMPLE_START, OUT_OF_SAMPLE_END

        # Collect relevant files
        parquet_files: List[Path] = []
        for year in range(d_start.year, d_end.year + 1):
            for month in range(1, 13):
                # Boundary month checks
                m_date_start = date(year, month, 1)
                m_date_end = date(year, month, 28)
                if m_date_end < d_start or m_date_start > d_end:
                    continue
                p_file = self.get_partition_path(symbol, year, month)
                if p_file.is_file():
                    parquet_files.append(p_file)

        if not parquet_files:
            logger.warning(f"No parquet slices match range [{d_start} to {d_end}] for {symbol}")
            return pd.DataFrame()

        tables = [pq.read_table(f) for f in parquet_files]
        master_table = pa.concat_tables(tables)
        df = master_table.to_pandas()
        df.sort_values("timestamp_ist", inplace=True)
        df.set_index("timestamp_ist", inplace=True)

        # Slice exact date boundaries
        ts_start = pd.Timestamp(d_start).tz_localize("Asia/Kolkata")
        ts_end = (pd.Timestamp(d_end) + pd.Timedelta(days=1)).tz_localize("Asia/Kolkata")
        df_sliced = df.loc[(df.index >= ts_start) & (df.index < ts_end)]
        return df_sliced

    def generate_synthetic_benchmark_parquet(
        self,
        symbol: str = "NIFTY50",
        year: int = 2024,
        month: int = 1,
        seed_price: float = 21500.0,
        volatility_daily: float = 0.012
    ) -> Path:
        """Generates realistic 1-minute OHLCV Parquet test dataset aligned with NSE trading days."""
        self.validate_instrument(symbol)
        trading_days = self.calendar.get_trading_days(
            date(year, month, 1),
            date(year, month, 28),
            exchange="NSE"
        )
        all_bars: List[dict] = []
        curr_price = seed_price

        sigma_1m = (volatility_daily / np.sqrt(375))
        rng = np.random.default_rng(year * 100 + month)

        for t_date in trading_days:
            # 375 continuous minutes: 09:15 to 15:29 inclusive
            open_dt = datetime.combine(t_date, time(9, 15))
            for i in range(375):
                bar_time = open_dt + timedelta(minutes=i)
                ret = rng.normal(0.0, sigma_1m)
                bar_open = curr_price
                curr_price = bar_open * (1.0 + ret)
                bar_close = curr_price
                high_wiggle = abs(rng.normal(0.0, sigma_1m * 0.5)) * bar_open
                low_wiggle = abs(rng.normal(0.0, sigma_1m * 0.5)) * bar_open
                bar_high = max(bar_open, bar_close) + high_wiggle
                bar_low = min(bar_open, bar_close) - low_wiggle
                bar_vol = int(rng.integers(2000, 15000))

                all_bars.append({
                    "timestamp_ist": pd.Timestamp(bar_time).tz_localize("Asia/Kolkata"),
                    "open": round(bar_open, 2),
                    "high": round(bar_high, 2),
                    "low": round(bar_low, 2),
                    "close": round(bar_close, 2),
                    "volume": bar_vol
                })

        df = pd.DataFrame(all_bars)
        return self.write_monthly_slice(df, symbol, year, month)


# ==============================================================================
# PHASE 2 ARCHITECTURAL STUBS: NIFTY WEEKLY OPTIONS & GREEKS ENGINE
# ==============================================================================

@dataclass(frozen=True)
class OptionContractStub:
    """Architectural stub representing a Nifty 50 weekly European option contract."""
    symbol: str
    underlying: str
    strike: float
    option_type: Literal["CE", "PE"]
    expiry_date: date
    lot_size: int = 50


@dataclass(frozen=True)
class GreeksResultStub:
    """Architectural stub for option pricing and Greeks outputs."""
    theoretical_price: float
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float
    implied_volatility: float


class GreeksEngineStub:
    """Architectural placeholder for Phase 2 Black-Scholes-Merton and Greeks computation."""

    @classmethod
    def compute_greeks(
        cls,
        spot: float,
        strike: float,
        time_to_expiry_years: float,
        risk_free_rate: float = 0.065,  # 6.5% RBI repo rate
        volatility: float = 0.15,
        option_type: Literal["CE", "PE"] = "CE"
    ) -> GreeksResultStub:
        """Phase 2 stub: returns indicative Greeks structure."""
        # Indicative delta placeholder
        approx_delta = 0.50 if option_type == "CE" else -0.50
        return GreeksResultStub(
            theoretical_price=round(abs(spot - strike) * 0.5 + 50.0, 2),
            delta=approx_delta,
            gamma=0.0015,
            vega=12.50,
            theta=-8.20,
            rho=0.045,
            implied_volatility=volatility
        )
