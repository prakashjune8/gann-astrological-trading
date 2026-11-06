"""Institutional Event-Driven Backtesting Engine for Gann Celestial Cycles.

Upgraded to V3.0 Quantum Architecture:
1. Reality Models:
   - SlippageModel: Half-spread + volume-weighted impact slippage.
   - IndianFeeModel: Exact statutory deductions (STT, NSE turnover, SEBI, GST, Stamp Duty).
   - NetworkLatencySimulator integration (50ms - 200ms queue transit).
2. Zero Look-Ahead Event-Driven State Machine:
   - Signals evaluated strictly on bar close T_t.
   - Dispatch routed through latency simulator to fill on bar T_{t+1}.
   - Accurate bar-by-bar intra-session bracket monitoring (18pt stop vs targets).
3. Backward Compatibility:
   - Preserves PivotBacktestResult and GannBacktestEngine.evaluate_node for existing test suites.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Dict, List, Literal, Optional, Tuple

import numpy as np
import pandas as pd

from core.backtest_data import (
    BULLION_BLACKLIST,
    MarketCalendarManager,
    NetworkLatencySimulator,
    ParquetDataLoader,
)

logger = logging.getLogger("backtest_engine")


# ==============================================================================
# 1. REALITY MODELS: SLIPPAGE & INDIAN STATUTORY TAXES
# ==============================================================================

@dataclass(frozen=True)
class FeeBreakdown:
    """Exact statutory fee components for Indian exchange trades."""
    stt: float
    turnover_charges: float
    sebi_charges: float
    stamp_duty: float
    brokerage: float
    gst: float
    total_fees: float


class IndianFeeModel:
    """Models exact Indian exchange trading costs for Equity Futures & Intraday Indices.
    
    Statutory Rates (NSE Futures Standard):
    - STT (Securities Transaction Tax): 0.0125% on sell-side turnover.
    - NSE Exchange Turnover Charges: 0.0019% on total turnover (buy + sell).
    - SEBI Turnover Charges: ₹10 per crore (0.0001% of total turnover).
    - Stamp Duty: 0.002% on buy-side turnover.
    - Institutional Brokerage: Flat ₹20 per executed leg (₹40 round trip).
    - GST: 18% on (Brokerage + Exchange Turnover + SEBI charges).
    """

    STT_RATE: float = 0.000125          # 0.0125% on sell side
    NSE_TURNOVER_RATE: float = 0.000019 # 0.0019% on total turnover
    SEBI_RATE: float = 0.000001         # 0.0001% (₹10 / crore)
    STAMP_DUTY_RATE: float = 0.000020   # 0.002% on buy side
    BROKERAGE_PER_ORDER: float = 20.0   # ₹20 flat per order leg
    GST_RATE: float = 0.18              # 18% GST

    @classmethod
    def calculate_fees(cls, buy_value: float, sell_value: float) -> FeeBreakdown:
        """Calculates itemized statutory fees for a completed round-trip trade."""
        total_turnover = buy_value + sell_value
        stt = round(sell_value * cls.STT_RATE, 2)
        turnover_charges = round(total_turnover * cls.NSE_TURNOVER_RATE, 2)
        sebi_charges = round(total_turnover * cls.SEBI_RATE, 2)
        stamp_duty = round(buy_value * cls.STAMP_DUTY_RATE, 2)
        brokerage = round(cls.BROKERAGE_PER_ORDER * 2.0, 2)  # Round trip

        # GST applies to Brokerage + Turnover + SEBI
        gst_base = brokerage + turnover_charges + sebi_charges
        gst = round(gst_base * cls.GST_RATE, 2)

        total_fees = round(stt + turnover_charges + sebi_charges + stamp_duty + brokerage + gst, 2)

        return FeeBreakdown(
            stt=stt,
            turnover_charges=turnover_charges,
            sebi_charges=sebi_charges,
            stamp_duty=stamp_duty,
            brokerage=brokerage,
            gst=gst,
            total_fees=total_fees
        )

    @classmethod
    def compute_net_pnl(cls, gross_pnl: float, buy_value: float, sell_value: float) -> Tuple[float, FeeBreakdown]:
        """Deducts all Indian statutory fees from gross P&L."""
        breakdown = cls.calculate_fees(buy_value, sell_value)
        net_pnl = round(gross_pnl - breakdown.total_fees, 2)
        return net_pnl, breakdown


class SlippageModel:
    """Institutional Slippage Model incorporating bid/ask spread and market impact.
    
    Formula:
      Fill Price = MidPrice +/- (Spread/2 + Volatility_Intra * sqrt(OrderQty / BarVolume))
    """

    def __init__(self, half_spread_pts: float = 0.5, impact_coeff: float = 0.1):
        self.half_spread_pts = half_spread_pts
        self.impact_coeff = impact_coeff

    def calculate_fill_price(
        self,
        base_price: float,
        is_buy: bool,
        order_qty: int = 50,  # 1 lot Nifty
        bar_volume: int = 5000,
        bar_high: Optional[float] = None,
        bar_low: Optional[float] = None
    ) -> Tuple[float, float]:
        """Calculates executed fill price and slippage points."""
        safe_volume = max(1, bar_volume)
        volume_impact = self.impact_coeff * np.sqrt(order_qty / safe_volume)

        # Volatility wiggle
        spread_component = self.half_spread_pts
        total_slippage = spread_component + volume_impact

        if is_buy:
            fill_price = base_price + total_slippage
            if bar_high is not None:
                fill_price = min(fill_price, bar_high)
        else:
            fill_price = base_price - total_slippage
            if bar_low is not None:
                fill_price = max(fill_price, bar_low)

        return round(fill_price, 2), round(total_slippage, 2)


# ==============================================================================
# 2. EVENT-DRIVEN DATA STRUCTURES (ZERO LOOK-AHEAD)
# ==============================================================================

class TradeDirection(Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class ExitReason(Enum):
    HARD_STOP = "HARD_STOP"
    TARGET_1 = "TARGET_1"
    TARGET_2 = "TARGET_2"
    SESSION_CLOSE = "SESSION_CLOSE"


@dataclass
class TradeSignal:
    """Actionable trade trigger emitted by Confluence or Harmonic engine."""
    signal_id: str
    signal_time: datetime
    direction: TradeDirection
    reference_price: float
    hard_stop_points: float = 18.0
    target1_points: float = 125.0
    target2_points: float = 252.0
    reason: str = "Triple Confluence Trigger"


@dataclass
class ExecutedTrade:
    """Complete institutional record of an executed trade with MFE/MAE and fee tracking."""
    trade_id: str
    signal_id: str
    direction: TradeDirection
    dispatch_time: datetime
    fill_time: datetime
    entry_price: float
    stop_price: float
    target1_price: float
    target2_price: float
    qty: int
    exit_time: Optional[datetime] = None
    exit_price: float = 0.0
    exit_reason: Optional[ExitReason] = None
    gross_pnl_points: float = 0.0
    gross_pnl_inr: float = 0.0
    net_pnl_inr: float = 0.0
    mfe_points: float = 0.0
    mae_points: float = 0.0
    holding_minutes: int = 0
    fees: Optional[FeeBreakdown] = None
    is_closed: bool = False


# ==============================================================================
# 3. EVENT-DRIVEN STATE MACHINE ENGINE
# ==============================================================================

class EventDrivenBacktester:
    """Non-anticipative bar-by-bar institutional simulation engine.
    
    Guarantees:
    - Zero look-ahead: signals from bar T_t fill at T_{t+1} Open with latency.
    - Continuous MFE and MAE recording across every intra-trade 1-minute bar.
    - Exact Indian exchange fee deduction on trade resolution.
    """

    def __init__(
        self,
        slippage_model: Optional[SlippageModel] = None,
        latency_sim: Optional[NetworkLatencySimulator] = None,
        contract_lot_size: int = 50  # Nifty 50 lot size
    ):
        self.slippage = slippage_model or SlippageModel()
        self.latency = latency_sim or NetworkLatencySimulator()
        self.lot_size = contract_lot_size

    def simulate(
        self,
        df_1m: pd.DataFrame,
        signals: List[TradeSignal],
        eod_square_off_time: time = time(15, 15)
    ) -> List[ExecutedTrade]:
        """Executes a chronological event-driven simulation over 1-minute bars."""
        if df_1m.empty or not signals:
            return []

        # Sort signals and data chronologically
        df = df_1m.sort_index()
        sorted_signals = sorted(signals, key=lambda s: s.signal_time)
        signal_idx = 0
        total_signals = len(sorted_signals)

        active_trades: List[ExecutedTrade] = []
        completed_trades: List[ExecutedTrade] = []
        pending_orders: List[Tuple[datetime, TradeSignal]] = []

        timestamps = df.index.to_pydatetime()
        n_bars = len(timestamps)

        for i in range(n_bars):
            curr_bar_time = timestamps[i]
            bar_row = df.iloc[i]
            b_open = float(bar_row["open"])
            b_high = float(bar_row["high"])
            b_low = float(bar_row["low"])
            b_close = float(bar_row["close"])
            b_vol = int(bar_row["volume"])

            # ------------------------------------------------------------------
            # 1. PROCESS PENDING ORDERS (Dispatched at prior bar with latency)
            # ------------------------------------------------------------------
            if pending_orders:
                orders_to_fill = pending_orders[:]
                pending_orders.clear()
                for dispatch_dt, sig in orders_to_fill:
                    is_buy = (sig.direction == TradeDirection.LONG)
                    fill_p, slip = self.slippage.calculate_fill_price(
                        base_price=b_open,
                        is_buy=is_buy,
                        order_qty=self.lot_size,
                        bar_volume=b_vol,
                        bar_high=b_high,
                        bar_low=b_low
                    )
                    fill_dt = self.latency.apply_latency(dispatch_dt)

                    if sig.direction == TradeDirection.LONG:
                        stop_p = fill_p - sig.hard_stop_points
                        t1_p = fill_p + sig.target1_points
                        t2_p = fill_p + sig.target2_points
                    else:
                        stop_p = fill_p + sig.hard_stop_points
                        t1_p = fill_p - sig.target1_points
                        t2_p = fill_p - sig.target2_points

                    trade = ExecutedTrade(
                        trade_id=f"TRD_{len(active_trades) + len(completed_trades) + 1:04d}",
                        signal_id=sig.signal_id,
                        direction=sig.direction,
                        dispatch_time=dispatch_dt,
                        fill_time=fill_dt,
                        entry_price=fill_p,
                        stop_price=stop_p,
                        target1_price=t1_p,
                        target2_price=t2_p,
                        qty=self.lot_size
                    )
                    active_trades.append(trade)

            # ------------------------------------------------------------------
            # 2. UPDATE ACTIVE TRADES (Check Excursions, Stops, Targets)
            # ------------------------------------------------------------------
            remaining_trades: List[ExecutedTrade] = []
            for trd in active_trades:
                trd.holding_minutes += 1

                # Calculate bar excursions
                if trd.direction == TradeDirection.LONG:
                    fwd_high = b_high - trd.entry_price
                    fwd_low = b_low - trd.entry_price
                    trd.mfe_points = max(trd.mfe_points, fwd_high)
                    trd.mae_points = min(trd.mae_points, fwd_low)  # Negative drawdown

                    # Stop check
                    if b_low <= trd.stop_price:
                        self._close_trade(trd, curr_bar_time, trd.stop_price, ExitReason.HARD_STOP)
                        completed_trades.append(trd)
                        continue
                    # Target 2 check
                    elif b_high >= trd.target2_price:
                        self._close_trade(trd, curr_bar_time, trd.target2_price, ExitReason.TARGET_2)
                        completed_trades.append(trd)
                        continue
                    # Target 1 check
                    elif b_high >= trd.target1_price:
                        self._close_trade(trd, curr_bar_time, trd.target1_price, ExitReason.TARGET_1)
                        completed_trades.append(trd)
                        continue

                else:  # SHORT
                    fwd_high = trd.entry_price - b_low  # Profit when price falls
                    fwd_low = trd.entry_price - b_high  # Loss when price rises
                    trd.mfe_points = max(trd.mfe_points, fwd_high)
                    trd.mae_points = min(trd.mae_points, fwd_low)  # Negative drawdown

                    # Stop check
                    if b_high >= trd.stop_price:
                        self._close_trade(trd, curr_bar_time, trd.stop_price, ExitReason.HARD_STOP)
                        completed_trades.append(trd)
                        continue
                    # Target 2 check
                    elif b_low <= trd.target2_price:
                        self._close_trade(trd, curr_bar_time, trd.target2_price, ExitReason.TARGET_2)
                        completed_trades.append(trd)
                        continue
                    # Target 1 check
                    elif b_low <= trd.target1_price:
                        self._close_trade(trd, curr_bar_time, trd.target1_price, ExitReason.TARGET_1)
                        completed_trades.append(trd)
                        continue

                # EOD Auto Square-off
                if curr_bar_time.time() >= eod_square_off_time:
                    self._close_trade(trd, curr_bar_time, b_close, ExitReason.SESSION_CLOSE)
                    completed_trades.append(trd)
                    continue

                remaining_trades.append(trd)

            active_trades = remaining_trades

            # ------------------------------------------------------------------
            # 3. CHECK FOR NEW SIGNALS ON COMPLETED BAR (Dispatched at bar close)
            # ------------------------------------------------------------------
            while signal_idx < total_signals:
                sig = sorted_signals[signal_idx]
                if sig.signal_time <= curr_bar_time:
                    # Enqueue order dispatch at current bar close; fills on next bar
                    pending_orders.append((curr_bar_time, sig))
                    signal_idx += 1
                else:
                    break

        # Close any lingering active trades at simulation termination
        final_time = timestamps[-1]
        final_close = float(df.iloc[-1]["close"])
        for trd in active_trades:
            self._close_trade(trd, final_time, final_close, ExitReason.SESSION_CLOSE)
            completed_trades.append(trd)

        return completed_trades

    def _close_trade(
        self,
        trade: ExecutedTrade,
        exit_dt: datetime,
        exit_price: float,
        reason: ExitReason
    ) -> None:
        """Closes trade, computes gross P&L, deducts Indian fees, and records net P&L."""
        trade.exit_time = exit_dt
        trade.exit_price = round(exit_price, 2)
        trade.exit_reason = reason
        trade.is_closed = True

        if trade.direction == TradeDirection.LONG:
            pts = trade.exit_price - trade.entry_price
            buy_val = trade.entry_price * trade.qty
            sell_val = trade.exit_price * trade.qty
        else:
            pts = trade.entry_price - trade.exit_price
            buy_val = trade.exit_price * trade.qty
            sell_val = trade.entry_price * trade.qty

        trade.gross_pnl_points = round(pts, 2)
        trade.gross_pnl_inr = round(pts * trade.qty, 2)

        # Deduct fees
        net_inr, fee_breakdown = IndianFeeModel.compute_net_pnl(
            gross_pnl=trade.gross_pnl_inr,
            buy_value=buy_val,
            sell_value=sell_val
        )
        trade.fees = fee_breakdown
        trade.net_pnl_inr = net_inr


# ==============================================================================
# 4. BACKWARD COMPATIBILITY TIER (For Existing Test Suites)
# ==============================================================================

@dataclass(frozen=True)
class PivotBacktestResult:
    node_name: str
    target_time_ist: time
    is_hit: bool
    setup_type: str            # "HIGH_SHORT" or "LOW_LONG" or "NONE"
    extremum_time_ist: Optional[time]
    time_delta_minutes: float  # |t_extrema - t_node|
    entry_price: float
    mfe_points: float          # Maximum Favorable Excursion in points
    mfe_pct: float             # MFE as percentage of entry price
    subsequent_extrema_price: float
    analysis_window_text: str


@dataclass(frozen=True)
class DayBacktestSummary:
    target_date: date
    script_symbol: str
    total_nodes_evaluated: int
    confirmed_hits: int
    hit_rate_pct: float
    avg_mfe_points: float
    results: list[PivotBacktestResult]


class GannBacktestEngine:
    """Executes automated, zero-hallucination backtests on historical 1-minute OHLC market data."""

    @classmethod
    def evaluate_node(
        cls,
        df_1m: pd.DataFrame,
        target_date: date,
        node_time: time,
        node_name: str = "Harmonic Node",
        window_pre_minutes: int = 15,
        window_post_minutes: int = 30,
        tolerance_minutes: int = 3,
        forward_mfe_minutes: int = 30
    ) -> PivotBacktestResult:
        """Evaluates a single celestial timing node against 1-minute OHLC data."""
        if df_1m.empty:
            return cls._make_empty_result(node_name, node_time)

        # Build datetime targets
        dt_target = pd.Timestamp(datetime.combine(target_date, node_time)).tz_localize("Asia/Kolkata")
        dt_win_start = dt_target - pd.Timedelta(minutes=window_pre_minutes)
        dt_win_end = dt_target + pd.Timedelta(minutes=window_post_minutes)

        # Slice observation window
        window_df = df_1m.loc[(df_1m.index >= dt_win_start) & (df_1m.index <= dt_win_end)]
        if window_df.empty or len(window_df) < 5:
            return cls._make_empty_result(node_name, node_time)

        # Identify window absolute High and Low
        high_idx = window_df["high"].idxmax()
        low_idx = window_df["low"].idxmin()
        win_high = float(window_df["high"].max())
        win_low = float(window_df["low"].min())

        delta_high_sec = abs((high_idx - dt_target).total_seconds())
        delta_low_sec = abs((low_idx - dt_target).total_seconds())
        delta_high_min = delta_high_sec / 60.0
        delta_low_min = delta_low_sec / 60.0

        hit_high = delta_high_min <= tolerance_minutes
        hit_low = delta_low_min <= tolerance_minutes

        if not hit_high and not hit_low:
            closest_delta = min(delta_high_min, delta_low_min)
            closest_time = high_idx.time() if delta_high_min <= delta_low_min else low_idx.time()
            return PivotBacktestResult(
                node_name=node_name,
                target_time_ist=node_time,
                is_hit=False,
                setup_type="NONE",
                extremum_time_ist=closest_time,
                time_delta_minutes=round(closest_delta, 1),
                entry_price=0.0,
                mfe_points=0.0,
                mfe_pct=0.0,
                subsequent_extrema_price=0.0,
                analysis_window_text=f"{dt_win_start.strftime('%H:%M')} - {dt_win_end.strftime('%H:%M')}"
            )

        if hit_high and (not hit_low or delta_high_min <= delta_low_min):
            setup = "HIGH_SHORT"
            hit_dt = high_idx
            extrema_p = win_high
            time_delta = delta_high_min
        else:
            setup = "LOW_LONG"
            hit_dt = low_idx
            extrema_p = win_low
            time_delta = delta_low_min

        entry_close = float(df_1m.loc[hit_dt, "close"]) if hit_dt in df_1m.index else extrema_p

        dt_fwd_end = hit_dt + pd.Timedelta(minutes=forward_mfe_minutes)
        fwd_df = df_1m.loc[(df_1m.index > hit_dt) & (df_1m.index <= dt_fwd_end)]

        if fwd_df.empty:
            mfe_pts = 0.0
            subseq_p = entry_close
        elif setup == "HIGH_SHORT":
            subseq_p = float(fwd_df["low"].min())
            mfe_pts = entry_close - subseq_p
        else:
            subseq_p = float(fwd_df["high"].max())
            mfe_pts = subseq_p - entry_close

        mfe_pct = (mfe_pts / entry_close * 100.0) if entry_close else 0.0

        return PivotBacktestResult(
            node_name=node_name,
            target_time_ist=node_time,
            is_hit=True,
            setup_type=setup,
            extremum_time_ist=hit_dt.time(),
            time_delta_minutes=round(time_delta, 1),
            entry_price=round(entry_close, 2),
            mfe_points=round(max(0.0, mfe_pts), 2),
            mfe_pct=round(max(0.0, mfe_pct), 2),
            subsequent_extrema_price=round(subseq_p, 2),
            analysis_window_text=f"{dt_win_start.strftime('%H:%M')} - {dt_win_end.strftime('%H:%M')}"
        )

    @classmethod
    def evaluate_day(
        cls,
        df_1m: pd.DataFrame,
        target_date: date,
        script_symbol: str,
        nodes: list[tuple[str, time]]
    ) -> DayBacktestSummary:
        """Evaluates an entire trading day across a list of celestial timing nodes."""
        results: list[PivotBacktestResult] = []
        hits = 0
        total_mfe = 0.0

        for name, n_time in nodes:
            res = cls.evaluate_node(df_1m, target_date, n_time, node_name=name)
            results.append(res)
            if res.is_hit:
                hits += 1
                total_mfe += res.mfe_points

        hit_rate = (hits / len(nodes) * 100.0) if nodes else 0.0
        avg_mfe = (total_mfe / hits) if hits > 0 else 0.0

        return DayBacktestSummary(
            target_date=target_date,
            script_symbol=script_symbol,
            total_nodes_evaluated=len(nodes),
            confirmed_hits=hits,
            hit_rate_pct=round(hit_rate, 1),
            avg_mfe_points=round(avg_mfe, 2),
            results=results
        )

    @staticmethod
    def _make_empty_result(name: str, n_time: time) -> PivotBacktestResult:
        return PivotBacktestResult(
            node_name=name,
            target_time_ist=n_time,
            is_hit=False,
            setup_type="NONE",
            extremum_time_ist=None,
            time_delta_minutes=999.0,
            entry_price=0.0,
            mfe_points=0.0,
            mfe_pct=0.0,
            subsequent_extrema_price=0.0,
            analysis_window_text="No Data Available"
        )
