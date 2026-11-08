"""Market Data Acquisition Feed with Strict Bullion Exclusion & Custom Script Support.

Features:
1. Default Universe:
   - Broad Indices: Nifty 50 (^NSEI), Sensex (^BSESN), Bank Nifty (^NSEBANK)
   - MCX Energy: Crude Oil (CL=F / MCX synthetic proxy), Natural Gas (NG=F)
   - MCX Base Metals: Copper (HG=F), Zinc (ZN=F / proxy), Aluminium (ALI=F)
2. Hard Exclusion Directive:
   - Under no circumstances will Gold or Silver (GC=F, SI=F, GOLD, SILVER) be accepted.
3. Custom Add Script:
   - Users can dynamically add any NSE equity/index ticker (e.g., RELIANCE.NS, TATAMOTORS.NS).
4. Auto-Fetch via yfinance with realistic offline failsafe fallback.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import yfinance as yf

# Rigid Bullion Exclusion Keywords
BULLION_BLACKLIST = {
    "GOLD", "SILVER", "GOLDPETAL", "GOLDM", "SILVERM", "SILVERMIC",
    "GC=F", "SI=F", "GLD", "SLV", "XAU", "XAG", "GOLD1!", "SILVER1!"
}

# Standard Default Instruments
DEFAULT_SCRIPTS: dict[str, dict[str, str]] = {
    "NIFTY_50": {
        "symbol": "^NSEI",
        "name": "Nifty 50 Index",
        "exchange": "NSE",
        "category": "INDEX",
        "default_price": 24200.0,
        "tick_size": 0.05
    },
    "SENSEX": {
        "symbol": "^BSESN",
        "name": "BSE Sensex Index",
        "exchange": "BSE",
        "category": "INDEX",
        "default_price": 79500.0,
        "tick_size": 0.05
    },
    "BANK_NIFTY": {
        "symbol": "^NSEBANK",
        "name": "Nifty Bank Index",
        "exchange": "NSE",
        "category": "INDEX",
        "default_price": 51800.0,
        "tick_size": 0.05
    },
    "CRUDE_OIL": {
        "symbol": "CL=F",
        "name": "MCX Crude Oil",
        "exchange": "MCX",
        "category": "ENERGY",
        "default_price": 6050.0,
        "tick_size": 1.0
    },
    "NATURAL_GAS": {
        "symbol": "NG=F",
        "name": "MCX Natural Gas",
        "exchange": "MCX",
        "category": "ENERGY",
        "default_price": 240.0,
        "tick_size": 0.1
    },
    "COPPER": {
        "symbol": "HG=F",
        "name": "MCX Copper",
        "exchange": "MCX",
        "category": "BASE_METALS",
        "default_price": 825.0,
        "tick_size": 0.05
    },
    "ALUMINIUM": {
        "symbol": "ALI=F",
        "name": "MCX Aluminium",
        "exchange": "MCX",
        "category": "BASE_METALS",
        "default_price": 235.0,
        "tick_size": 0.05
    },
    "ZINC": {
        "symbol": "ZN=F",
        "name": "MCX Zinc",
        "exchange": "MCX",
        "category": "BASE_METALS",
        "default_price": 275.0,
        "tick_size": 0.05
    },
}


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    name: str
    last_price: float
    open_price: float
    high_price: float
    low_price: float
    change_points: float
    change_pct: float
    timestamp: datetime
    is_live: bool
    market_status: str = "OPEN"           # "OPEN", "EXCHANGE_CLOSED", "WEEKEND_CLOSED"
    status_message: str = "Normal Trading"


class MarketFeedEngine:
    """Acquires live and historical price data with strict bullion protection and holiday awareness."""

    def __init__(self, holidays_file: Optional[str] = None):
        self.custom_scripts: dict[str, dict[str, str]] = {}
        self.holidays: list[dict] = []
        self._load_holidays(holidays_file)

    def _load_holidays(self, custom_path: Optional[str] = None):
        """Loads Indian trading holiday calendar from JSON."""
        search_paths = []
        if custom_path:
            search_paths.append(custom_path)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        search_paths.extend([
            os.path.join(base_dir, "data", "holidays_india.json"),
            os.path.join(base_dir, "holidays_india.json"),
            "holidays_india.json"
        ])

        for p in search_paths:
            if os.path.isfile(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.holidays = data.get("holidays", [])
                        return
                except Exception:
                    pass

    def is_holiday(self, target_date: date, exchange: str = "NSE") -> Tuple[bool, Optional[str]]:
        """Determines whether a given date is an official trading holiday for the exchange."""
        date_str = target_date.strftime("%Y-%m-%d")
        for h in self.holidays:
            if h.get("date") == date_str:
                ex_clean = exchange.upper()
                if ex_clean in ("NSE", "BSE", "INDEX", "CUSTOM"):
                    if h.get("nse", True):
                        return True, h.get("holiday", "Exchange Holiday")
                elif ex_clean == "MCX":
                    if h.get("mcx_morning") and h.get("mcx_evening"):
                        return True, h.get("holiday", "MCX Holiday (Full Day)")
                    elif h.get("mcx_morning"):
                        return True, f"{h.get('holiday', 'MCX Holiday')} (Morning Session Closed)"
                else:
                    return True, h.get("holiday", "Trading Holiday")
        return False, None

    def is_bullion_forbidden(self, symbol_or_name: str) -> bool:
        """Enforces the strict, non-negotiable bullion exclusion."""
        cleaned = symbol_or_name.upper().strip()
        for bl in BULLION_BLACKLIST:
            if bl in cleaned:
                return True
        return False

    def add_custom_script(self, symbol: str, name: Optional[str] = None) -> Tuple[bool, str]:
        """Registers a user-added custom script with bullion validation."""
        sym_clean = symbol.upper().strip()
        if self.is_bullion_forbidden(sym_clean):
            return False, "HARD REJECTION: Gold and Silver (bullion) instruments are strictly forbidden."

        if not name:
            name = sym_clean

        # Auto-append .NS for NSE equities if lacking suffix
        fetch_symbol = sym_clean
        if not fetch_symbol.startswith("^") and not fetch_symbol.endswith(".NS") and not fetch_symbol.endswith(".BO") and not "=F" in fetch_symbol:
            fetch_symbol = f"{sym_clean}.NS"

        self.custom_scripts[sym_clean] = {
            "symbol": fetch_symbol,
            "name": name,
            "exchange": "NSE" if fetch_symbol.endswith(".NS") else "CUSTOM",
            "category": "CUSTOM",
            "default_price": 1000.0,
            "tick_size": 0.05
        }
        return True, f"Successfully registered custom script: {name} ({fetch_symbol})"

    def get_all_available_scripts(self) -> dict[str, dict[str, str]]:
        """Returns union of default scripts and user-added custom scripts."""
        all_scripts = dict(DEFAULT_SCRIPTS)
        all_scripts.update(self.custom_scripts)
        return all_scripts

    def fetch_snapshot(self, script_key: str, check_date: Optional[date] = None) -> MarketSnapshot:
        """Fetches the latest market snapshot via yfinance with holiday interception and fallback."""
        scripts = self.get_all_available_scripts()
        meta = scripts.get(script_key.upper(), DEFAULT_SCRIPTS["NIFTY_50"])
        symbol = meta["symbol"]
        exchange = meta.get("exchange", "NSE")
        now = datetime.now()
        target_d = check_date or now.date()

        # 1. Holiday Interception: Check if exchange is closed on target date
        is_hol, hol_name = self.is_holiday(target_d, exchange=exchange)
        if is_hol:
            default_p = float(meta["default_price"])
            return MarketSnapshot(
                symbol=symbol,
                name=meta["name"],
                last_price=default_p,
                open_price=default_p,
                high_price=default_p,
                low_price=default_p,
                change_points=0.0,
                change_pct=0.0,
                timestamp=now,
                is_live=False,
                market_status="EXCHANGE_CLOSED",
                status_message=f"Exchange Closed - {hol_name}"
            )

        # 2. Weekend Check
        if target_d.weekday() in (5, 6):
            default_p = float(meta["default_price"])
            return MarketSnapshot(
                symbol=symbol,
                name=meta["name"],
                last_price=default_p,
                open_price=default_p,
                high_price=default_p,
                low_price=default_p,
                change_points=0.0,
                change_pct=0.0,
                timestamp=now,
                is_live=False,
                market_status="WEEKEND_CLOSED",
                status_message="Exchange Closed - Weekend"
            )

        # 3. Normal Trading Session: Fetch via yfinance
        try:
            ticker = yf.Ticker(symbol)
            # Fetch recent 1-day or 5-day history
            df = ticker.history(period="2d", interval="1m")
            if not df.empty:
                last_bar = df.iloc[-1]
                prev_close = df["Close"].iloc[0] if len(df) > 1 else last_bar["Open"]
                lp = float(last_bar["Close"])
                hp = float(df["High"].max())
                lop = float(df["Low"].min())
                op = float(df["Open"].iloc[0])
                chg = lp - prev_close
                chg_pct = (chg / prev_close) * 100.0 if prev_close else 0.0

                return MarketSnapshot(
                    symbol=symbol,
                    name=meta["name"],
                    last_price=round(lp, 2),
                    open_price=round(op, 2),
                    high_price=round(hp, 2),
                    low_price=round(lop, 2),
                    change_points=round(chg, 2),
                    change_pct=round(chg_pct, 2),
                    timestamp=now,
                    is_live=True,
                    market_status="OPEN",
                    status_message="Live Market Data"
                )
        except Exception:
            pass

        # Failsafe fallback
        default_p = float(meta["default_price"])
        return MarketSnapshot(
            symbol=symbol,
            name=meta["name"],
            last_price=default_p,
            open_price=default_p * 0.998,
            high_price=default_p * 1.006,
            low_price=default_p * 0.994,
            change_points=round(default_p * 0.002, 2),
            change_pct=0.20,
            timestamp=now,
            is_live=False,
            market_status="OPEN",
            status_message="Offline Reference Model"
        )

    def fetch_historical_intraday(self, script_key: str, target_date: date) -> pd.DataFrame:
        """Fetches 1-minute historical OHLC bars for backtesting."""
        scripts = self.get_all_available_scripts()
        meta = scripts.get(script_key.upper(), DEFAULT_SCRIPTS["NIFTY_50"])
        symbol = meta["symbol"]

        try:
            ticker = yf.Ticker(symbol)
            start_str = target_date.strftime("%Y-%m-%d")
            end_str = (target_date + timedelta(days=1)).strftime("%Y-%m-%d")
            df = ticker.history(start=start_str, end=end_str, interval="1m")
            if not df.empty:
                df = df[["Open", "High", "Low", "Close"]].copy()
                df.columns = ["open", "high", "low", "close"]
                if df.index.tz is None:
                    df.index = df.index.tz_localize("UTC").tz_convert("Asia/Kolkata")
                else:
                    df.index = df.index.tz_convert("Asia/Kolkata")
                return df
        except Exception:
            pass

        return pd.DataFrame()
