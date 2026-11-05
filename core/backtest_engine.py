"""Automated Gann Backtest Engine for Intraday Celestial Pivots & MFE Metrics.

Evaluates celestial timing nodes (e.g., 90° square at 13:56, 120° trine at 14:27, aspect crossings):
- Window: [T_node - 15m, T_node + 30m]
- Hit Criteria: Extrema prints within exactly +/- 3 minutes of T_node
- Reaction Metric: Maximum Favorable Excursion (MFE) over next 30 minutes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd


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

        # Check hit condition
        hit_high = delta_high_min <= tolerance_minutes
        hit_low = delta_low_min <= tolerance_minutes

        if not hit_high and not hit_low:
            # No hit
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

        # Determine dominant setup (closer to node)
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

        # Measure forward MFE
        dt_fwd_end = hit_dt + pd.Timedelta(minutes=forward_mfe_minutes)
        fwd_df = df_1m.loc[(df_1m.index > hit_dt) & (df_1m.index <= dt_fwd_end)]

        if fwd_df.empty:
            mfe_pts = 0.0
            subseq_p = entry_close
        elif setup == "HIGH_SHORT":
            subseq_p = float(fwd_df["low"].min())
            mfe_pts = entry_close - subseq_p
        else:  # LOW_LONG
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
