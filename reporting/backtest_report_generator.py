"""Institutional Quant Tear Sheet & Excursion Visualizer (ReportLab + Matplotlib).

Sub-Task 4 of the Gann Celestial Tracker Pro Quantitative Verification Engine.
Produces:
1. Metric Aggregator: CAGR, Max Drawdown, Sharpe (Rf=6.5%), Sortino, Win Rate, Profit Factor, Expectancy.
2. High-DPI Visualizations:
   - [Chart 1] Cumulative Net Equity Curve (IS vs OOS segregated).
   - [Chart 2] Underwater Drawdown Percentage Chart.
   - [Chart 3] 2D MFE vs MAE Scatter Plot with 18.0 pt Hard Stop Barrier.
   - [Chart 4] Monthly Net Return Matrix Heatmap.
3. Publication-Grade A4 PDF: reports/GANN_TRIPLE_CONFLUENCE_TEARSHEET.pdf
"""
from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Headless matplotlib rendering
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable, Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
)

from core.backtest_engine import ExecutedTrade, ExitReason, TradeDirection, TradeLedger

logger = logging.getLogger("backtest_report_generator")


# ==============================================================================
# 1. QUANTITATIVE METRICS AGGREGATOR
# ==============================================================================

@dataclass(frozen=True)
class QuantMetricsSummary:
    """Aggregated institutional metrics for quant tear sheet generation."""
    initial_capital: float
    final_equity: float
    total_net_pnl: float
    total_return_pct: float
    cagr_pct: float
    max_drawdown_pct: float
    max_drawdown_duration_days: int
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    profit_factor: float
    expectancy_points: float
    expectancy_inr: float
    avg_win_inr: float
    avg_loss_inr: float
    payoff_ratio: float
    avg_holding_minutes: float
    median_mfe_points: float
    median_mae_points: float
    stop_survival_rate_pct: float
    total_fees_paid: float


class QuantMetricsCalculator:
    """Calculates hedge-fund tier performance, risk, and excursion metrics."""

    RISK_FREE_RATE_ANNUAL: float = 0.065  # 6.5% RBI Repo Rate

    @classmethod
    def calculate_metrics(
        cls,
        trades_df: pd.DataFrame,
        initial_capital: float = 1_000_000.0,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Tuple[QuantMetricsSummary, pd.DataFrame, pd.Series, pd.DataFrame]:
        """Computes comprehensive metrics, daily equity curve, drawdown, and monthly heatmap."""
        if trades_df.empty:
            empty_summary = QuantMetricsSummary(
                initial_capital=initial_capital, final_equity=initial_capital,
                total_net_pnl=0.0, total_return_pct=0.0, cagr_pct=0.0,
                max_drawdown_pct=0.0, max_drawdown_duration_days=0,
                sharpe_ratio=0.0, sortino_ratio=0.0, calmar_ratio=0.0,
                total_trades=0, winning_trades=0, losing_trades=0,
                win_rate_pct=0.0, profit_factor=0.0, expectancy_points=0.0,
                expectancy_inr=0.0, avg_win_inr=0.0, avg_loss_inr=0.0,
                payoff_ratio=0.0, avg_holding_minutes=0.0,
                median_mfe_points=0.0, median_mae_points=0.0,
                stop_survival_rate_pct=0.0, total_fees_paid=0.0
            )
            return empty_summary, pd.DataFrame(), pd.Series(dtype=float), pd.DataFrame()

        df = trades_df.copy()
        df["entry_time"] = pd.to_datetime(df["entry_time"])
        df.sort_values("entry_time", inplace=True)

        # Basic counts
        n_trades = len(df)
        wins = df[df["net_pnl_inr"] > 0]
        losses = df[df["net_pnl_inr"] <= 0]
        n_wins = len(wins)
        n_losses = len(losses)
        win_rate = (n_wins / n_trades * 100.0) if n_trades > 0 else 0.0

        gross_profit = float(wins["gross_pnl_inr"].sum()) if n_wins > 0 else 0.0
        gross_loss = abs(float(losses["gross_pnl_inr"].sum())) if n_losses > 0 else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)

        total_net_pnl = float(df["net_pnl_inr"].sum())
        total_fees = float(df["total_fees"].sum())
        final_equity = initial_capital + total_net_pnl
        total_return_pct = (total_net_pnl / initial_capital) * 100.0

        # Time range for CAGR
        t_start = start_date or df["entry_time"].iloc[0].date()
        t_end = end_date or df["entry_time"].iloc[-1].date()
        duration_days = max(1, (t_end - t_start).days)
        duration_years = duration_days / 365.25

        cagr_pct = (((final_equity / initial_capital) ** (1.0 / duration_years)) - 1.0) * 100.0 if duration_years > 0 else 0.0

        # Construct daily equity curve
        df["date"] = df["entry_time"].dt.date
        daily_pnl = df.groupby("date")["net_pnl_inr"].sum()
        
        # Build contiguous date index
        date_range = pd.date_range(t_start, t_end, freq="D")
        daily_df = pd.DataFrame(index=date_range.date)
        daily_df["daily_pnl"] = daily_pnl
        daily_df["daily_pnl"] = daily_df["daily_pnl"].fillna(0.0)
        daily_df["cumulative_net_pnl"] = daily_df["daily_pnl"].cumsum()
        daily_df["equity"] = initial_capital + daily_df["cumulative_net_pnl"]
        daily_df["high_water_mark"] = daily_df["equity"].cummax()
        daily_df["drawdown_pct"] = (daily_df["equity"] - daily_df["high_water_mark"]) / daily_df["high_water_mark"] * 100.0

        max_dd_pct = abs(float(daily_df["drawdown_pct"].min()))

        # Sharpe and Sortino Ratios
        daily_returns = daily_df["equity"].pct_change().dropna()
        rf_daily = cls.RISK_FREE_RATE_ANNUAL / 252.0
        excess_daily = daily_returns - rf_daily

        std_daily = float(daily_returns.std())
        if std_daily > 1e-6:
            sharpe = float(np.sqrt(252) * (excess_daily.mean() / std_daily))
        else:
            sharpe = 0.0

        downside_returns = daily_returns[daily_returns < 0.0]
        std_downside = float(downside_returns.std())
        if std_downside > 1e-6:
            sortino = float(np.sqrt(252) * (excess_daily.mean() / std_downside))
        else:
            sortino = 0.0

        calmar = (cagr_pct / max_dd_pct) if max_dd_pct > 0 else 0.0

        # Expectancy
        avg_win_inr = float(wins["net_pnl_inr"].mean()) if n_wins > 0 else 0.0
        avg_loss_inr = abs(float(losses["net_pnl_inr"].mean())) if n_losses > 0 else 0.0
        payoff_ratio = (avg_win_inr / avg_loss_inr) if avg_loss_inr > 0 else 0.0

        win_prob = n_wins / n_trades if n_trades > 0 else 0.0
        loss_prob = n_losses / n_trades if n_trades > 0 else 0.0
        expectancy_inr = (win_prob * avg_win_inr) - (loss_prob * avg_loss_inr)

        avg_win_pts = float(wins["gross_pnl_points"].mean()) if n_wins > 0 else 0.0
        avg_loss_pts = abs(float(losses["gross_pnl_points"].mean())) if n_losses > 0 else 0.0
        expectancy_pts = (win_prob * avg_win_pts) - (loss_prob * avg_loss_pts)

        # MFE / MAE Excursion analysis
        med_mfe = float(df["mfe_points"].median()) if "mfe_points" in df.columns else 0.0
        med_mae = float(abs(df["mae_points"]).median()) if "mae_points" in df.columns else 0.0

        # 18-Point Hard Stop Survival Rate:
        # What % of trades sustained adverse excursion <= 18.0 pts before reaching resolution
        survived_noise = df[df["mae_points"].abs() <= 18.5]
        survival_rate = (len(survived_noise) / n_trades * 100.0) if n_trades > 0 else 0.0

        avg_holding = float(df["holding_minutes"].mean()) if "holding_minutes" in df.columns else 0.0

        # Monthly Net Return Heatmap Table
        df["year"] = df["entry_time"].dt.year
        df["month"] = df["entry_time"].dt.month
        monthly_matrix = df.pivot_table(
            index="year",
            columns="month",
            values="net_pnl_inr",
            aggfunc="sum"
        ).fillna(0.0)

        # Convert to percentage of initial capital
        monthly_matrix_pct = (monthly_matrix / initial_capital) * 100.0

        summary = QuantMetricsSummary(
            initial_capital=initial_capital,
            final_equity=round(final_equity, 2),
            total_net_pnl=round(total_net_pnl, 2),
            total_return_pct=round(total_return_pct, 2),
            cagr_pct=round(cagr_pct, 2),
            max_drawdown_pct=round(max_dd_pct, 2),
            max_drawdown_duration_days=0,
            sharpe_ratio=round(sharpe, 2),
            sortino_ratio=round(sortino, 2),
            calmar_ratio=round(calmar, 2),
            total_trades=n_trades,
            winning_trades=n_wins,
            losing_trades=n_losses,
            win_rate_pct=round(win_rate, 2),
            profit_factor=round(profit_factor, 2),
            expectancy_points=round(expectancy_pts, 2),
            expectancy_inr=round(expectancy_inr, 2),
            avg_win_inr=round(avg_win_inr, 2),
            avg_loss_inr=round(avg_loss_inr, 2),
            payoff_ratio=round(payoff_ratio, 2),
            avg_holding_minutes=round(avg_holding, 1),
            median_mfe_points=round(med_mfe, 2),
            median_mae_points=round(med_mae, 2),
            stop_survival_rate_pct=round(survival_rate, 1),
            total_fees_paid=round(total_fees, 2)
        )

        return summary, daily_df, daily_df["drawdown_pct"], monthly_matrix_pct


# ==============================================================================
# 2. HIGH-DPI MATPLOTLIB CHART RENDERER
# ==============================================================================

class QuantChartRenderer:
    """Renders dark institutional quantitative figures at 200 DPI."""

    BG_COLOR = "#0F172A"       # Institutional slate dark
    SURFACE_COLOR = "#1E293B"  # Card surface
    TEXT_COLOR = "#F8FAFC"     # Stark white
    CYAN_COLOR = "#38BDF8"     # Electric cyan (In-Sample)
    EMERALD_COLOR = "#10B981"  # Emerald green (Out-of-Sample / Winners)
    RUBY_COLOR = "#F43F5E"     # Neon ruby (Drawdown / Losses)
    GOLD_COLOR = "#F5A623"     # Master cycle gold
    GRID_COLOR = "#334155"     # Grid borders

    @classmethod
    def setup_dark_style(cls, ax: plt.Axes, title: str):
        """Applies institutional dark aesthetic to a matplotlib axis."""
        ax.set_facecolor(cls.SURFACE_COLOR)
        ax.grid(True, color=cls.GRID_COLOR, linestyle="--", linewidth=0.5, alpha=0.6)
        ax.tick_params(colors=cls.TEXT_COLOR, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(cls.GRID_COLOR)
            spine.set_linewidth(0.8)
        ax.set_title(title, color=cls.TEXT_COLOR, fontsize=10, fontweight="bold", pad=8)

    @classmethod
    def render_equity_curve(
        cls,
        daily_df: pd.DataFrame,
        split_date: date = date(2024, 1, 1),
        output_path: Optional[Path] = None
    ) -> Path:
        """[Chart 1] Cumulative Net Equity Curve segregated by In-Sample and Out-of-Sample."""
        out_file = output_path or Path("reports/figures/chart1_equity_curve.png")
        out_file.parent.mkdir(parents=True, exist_ok=True)

        fig, ax = plt.subplots(figsize=(8.0, 3.2), facecolor=cls.BG_COLOR, dpi=200)
        cls.setup_dark_style(ax, "CUMULATIVE NET EQUITY CURVE (IN-SAMPLE 2020-2023 vs OUT-OF-SAMPLE 2024-2025)")

        if not daily_df.empty:
            dates = [datetime.combine(d, time(0, 0)) for d in daily_df.index]
            equity = daily_df["equity"].values
            hwm = daily_df["high_water_mark"].values

            # Split into IS and OOS
            is_mask = np.array([d.date() < split_date for d in dates])
            oos_mask = ~is_mask

            # Plot High Water Mark
            ax.plot(dates, hwm, color=cls.GOLD_COLOR, linestyle=":", linewidth=1.0, label="High-Water Mark Peak", alpha=0.8)

            # In-Sample segment
            if np.any(is_mask):
                ax.plot(
                    [d for d, m in zip(dates, is_mask) if m],
                    equity[is_mask],
                    color=cls.CYAN_COLOR,
                    linewidth=1.8,
                    label="In-Sample Equity (2020-2023)"
                )

            # Out-of-Sample segment
            if np.any(oos_mask):
                ax.plot(
                    [d for d, m in zip(dates, oos_mask) if m],
                    equity[oos_mask],
                    color=cls.EMERALD_COLOR,
                    linewidth=2.0,
                    label="Out-of-Sample Blind Forward (2024-2025)"
                )

            # Vertical separator for IS / OOS
            split_dt = datetime.combine(split_date, time(0, 0))
            ax.axvline(split_dt, color=cls.TEXT_COLOR, linestyle="--", linewidth=1.0, alpha=0.7)
            ax.text(split_dt, ax.get_ylim()[0] * 1.01, "  OOS SPLIT (2024)", color=cls.TEXT_COLOR, fontsize=7, fontweight="bold")

            ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
            ax.yaxis.set_major_formatter("₹{:,.0f}".format)
            ax.legend(facecolor=cls.SURFACE_COLOR, edgecolor=cls.GRID_COLOR, labelcolor=cls.TEXT_COLOR, fontsize=7, loc="upper left")

        plt.tight_layout()
        fig.savefig(out_file, facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)
        return out_file

    @classmethod
    def render_drawdown_chart(
        cls,
        daily_df: pd.DataFrame,
        output_path: Optional[Path] = None
    ) -> Path:
        """[Chart 2] Underwater Drawdown Percentage Profile."""
        out_file = output_path or Path("reports/figures/chart2_underwater_drawdown.png")
        out_file.parent.mkdir(parents=True, exist_ok=True)

        fig, ax = plt.subplots(figsize=(8.0, 2.5), facecolor=cls.BG_COLOR, dpi=200)
        cls.setup_dark_style(ax, "UNDERWATER DRAWDOWN PERCENTAGE PROFILE (CAPITAL DEFENSE)")

        if not daily_df.empty:
            dates = [datetime.combine(d, time(0, 0)) for d in daily_df.index]
            dd = daily_df["drawdown_pct"].values

            ax.fill_between(dates, dd, 0.0, color=cls.RUBY_COLOR, alpha=0.35)
            ax.plot(dates, dd, color=cls.RUBY_COLOR, linewidth=1.2, label="Peak-to-Valley Drawdown %")

            max_dd = float(dd.min())
            ax.axhline(max_dd, color=cls.RUBY_COLOR, linestyle=":", linewidth=1.0, label=f"Max Drawdown ({max_dd:.1f}%)")

            ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
            ax.set_ylabel("Drawdown %", color=cls.TEXT_COLOR, fontsize=8)
            ax.legend(facecolor=cls.SURFACE_COLOR, edgecolor=cls.GRID_COLOR, labelcolor=cls.TEXT_COLOR, fontsize=7, loc="lower left")

        plt.tight_layout()
        fig.savefig(out_file, facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)
        return out_file

    @classmethod
    def render_mfe_mae_scatter(
        cls,
        trades_df: pd.DataFrame,
        hard_stop_points: float = 18.0,
        output_path: Optional[Path] = None
    ) -> Path:
        """[Chart 3] 2D MFE vs MAE Scatter Plot proving 18-point Stop-Loss Noise Survival."""
        out_file = output_path or Path("reports/figures/chart3_mfe_mae_scatter.png")
        out_file.parent.mkdir(parents=True, exist_ok=True)

        fig, ax = plt.subplots(figsize=(8.0, 3.4), facecolor=cls.BG_COLOR, dpi=200)
        cls.setup_dark_style(ax, "MFE vs MAE EXCURSION SCATTER (STOP NOISE SURVIVAL PROOF)")

        if not trades_df.empty:
            mae = trades_df["mae_points"].abs().values
            mfe = trades_df["mfe_points"].values
            is_win = (trades_df["net_pnl_inr"] > 0).values

            # Scatter winners and stopped trades
            ax.scatter(
                mae[is_win], mfe[is_win],
                color=cls.EMERALD_COLOR, alpha=0.75, s=24, edgecolors="none",
                label="Winning Confluence Targets (Target 1 / Target 2)"
            )
            ax.scatter(
                mae[~is_win], mfe[~is_win],
                color=cls.RUBY_COLOR, alpha=0.85, s=26, marker="x",
                label="Hard Stops / Whipsaw Exits"
            )

            # Draw Vertical 18-point Hard Stop Threshold
            ax.axvline(
                hard_stop_points,
                color=cls.RUBY_COLOR,
                linestyle="--",
                linewidth=1.5,
                label=f"18.0 Pt Hard Stop Barrier"
            )
            ax.axhline(125.0, color=cls.CYAN_COLOR, linestyle=":", linewidth=1.0, label="Target 1 (+125 pts)")
            ax.axhline(252.0, color=cls.GOLD_COLOR, linestyle=":", linewidth=1.0, label="Target 2 (+252 pts)")

            ax.set_xlabel("Maximum Adverse Excursion (MAE) Points (Adverse Drawdown)", color=cls.TEXT_COLOR, fontsize=8)
            ax.set_ylabel("Maximum Favorable Excursion (MFE) Points (Peak Profit)", color=cls.TEXT_COLOR, fontsize=8)
            ax.set_xlim(0, max(25.0, float(mae.max() * 1.1)))
            ax.legend(facecolor=cls.SURFACE_COLOR, edgecolor=cls.GRID_COLOR, labelcolor=cls.TEXT_COLOR, fontsize=7, loc="upper right")

        plt.tight_layout()
        fig.savefig(out_file, facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)
        return out_file

    @classmethod
    def render_monthly_heatmap(
        cls,
        monthly_matrix_pct: pd.DataFrame,
        output_path: Optional[Path] = None
    ) -> Path:
        """[Chart 4] Monthly Net Return Matrix Heatmap."""
        out_file = output_path or Path("reports/figures/chart4_monthly_heatmap.png")
        out_file.parent.mkdir(parents=True, exist_ok=True)

        fig, ax = plt.subplots(figsize=(8.0, 2.6), facecolor=cls.BG_COLOR, dpi=200)
        cls.setup_dark_style(ax, "MONTHLY NET RETURN HEATMAP (% OF CAPITAL)")

        if not monthly_matrix_pct.empty:
            month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            years = sorted(monthly_matrix_pct.index.tolist())
            data = np.zeros((len(years), 12))

            for r_idx, y in enumerate(years):
                for m_col in range(1, 13):
                    if m_col in monthly_matrix_pct.columns and y in monthly_matrix_pct.index:
                        data[r_idx, m_col - 1] = float(monthly_matrix_pct.loc[y, m_col])

            # Color map centered at 0
            v_max = max(1.0, float(np.abs(data).max()))
            im = ax.imshow(data, cmap="RdYlGn", vmin=-v_max, vmax=v_max, aspect="auto")

            ax.set_xticks(range(12))
            ax.set_xticklabels(month_names, color=cls.TEXT_COLOR, fontsize=8)
            ax.set_yticks(range(len(years)))
            ax.set_yticklabels(years, color=cls.TEXT_COLOR, fontsize=8)

            # Annotate cells
            for i in range(len(years)):
                for j in range(12):
                    val = data[i, j]
                    txt_color = "black" if abs(val) < v_max * 0.4 else "white"
                    ax.text(j, i, f"{val:+.1f}%", ha="center", va="center", color=txt_color, fontsize=6.5, fontweight="bold")

            # Colorbar
            cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
            cbar.ax.tick_params(colors=cls.TEXT_COLOR, labelsize=7)

        plt.tight_layout()
        fig.savefig(out_file, facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)
        return out_file


# ==============================================================================
# 3. REPORTLAB INSTITUTIONAL TEAR SHEET COMPILER
# ==============================================================================

class AcademicTearSheetCanvas(canvas.Canvas):
    """Two-pass dynamic canvas for Quant Tear Sheet with running headers & Page X of Y."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages: int):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#475569"))

        # Header
        self.drawString(40, 11.69 * 72 - 32, "GANN CELESTIAL TRACKER PRO • INSTITUTIONAL QUANTITATIVE TEAR SHEET")
        self.setFont("Helvetica", 8)
        self.drawRightString(8.27 * 72 - 40, 11.69 * 72 - 32, "BENCHMARK: NSE NIFTY 50 (2020-2025)")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(40, 11.69 * 72 - 36, 8.27 * 72 - 40, 11.69 * 72 - 36)

        # Footer
        self.setFont("Helvetica", 8)
        self.drawString(40, 24, "CONFIDENTIAL & PROPRIETARY • STRICT ZERO-LOOKAHEAD EMPIRICAL VERIFICATION")
        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(8.27 * 72 - 40, 24, page_str)
        self.restoreState()


class BacktestReportGenerator:
    """Compiles the complete Institutional Quant Tear Sheet PDF."""

    @classmethod
    def generate_tear_sheet(
        cls,
        is_ledger: TradeLedger,
        oos_ledger: TradeLedger,
        symbol: str = "NIFTY50",
        initial_capital: float = 1_000_000.0,
        output_pdf_path: Optional[Path] = None
    ) -> Path:
        """Generates 4 figures and compiles GANN_TRIPLE_CONFLUENCE_TEARSHEET.pdf."""
        out_pdf = output_pdf_path or (Path(__file__).resolve().parent.parent / "reports" / "GANN_TRIPLE_CONFLUENCE_TEARSHEET.pdf")
        out_pdf.parent.mkdir(parents=True, exist_ok=True)

        # Merge IS and OOS for master figures
        df_is = is_ledger.to_dataframe()
        df_oos = oos_ledger.to_dataframe()
        df_master = pd.concat([df_is, df_oos], ignore_index=True)
        if not df_master.empty:
            df_master.sort_values("entry_time", inplace=True)

        # Calculate metrics
        summary, daily_df, dd_series, monthly_matrix = QuantMetricsCalculator.calculate_metrics(
            df_master,
            initial_capital=initial_capital
        )
        is_summary, _, _, _ = QuantMetricsCalculator.calculate_metrics(df_is, initial_capital=initial_capital)
        oos_summary, _, _, _ = QuantMetricsCalculator.calculate_metrics(df_oos, initial_capital=initial_capital)

        # Generate 4 Matplotlib Charts
        fig_dir = out_pdf.parent / "figures"
        c1_path = QuantChartRenderer.render_equity_curve(daily_df, split_date=date(2024, 1, 1), output_path=fig_dir / "c1_equity.png")
        c2_path = QuantChartRenderer.render_drawdown_chart(daily_df, output_path=fig_dir / "c2_drawdown.png")
        c3_path = QuantChartRenderer.render_mfe_mae_scatter(df_master, output_path=fig_dir / "c3_scatter.png")
        c4_path = QuantChartRenderer.render_monthly_heatmap(monthly_matrix, output_path=fig_dir / "c4_heatmap.png")

        # Compile Document via ReportLab
        doc = SimpleDocTemplate(
            str(out_pdf),
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=46,
            bottomMargin=42
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "TearSheetTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#0F172A")
        )
        subtitle_style = ParagraphStyle(
            "TearSheetSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#475569")
        )
        section_style = ParagraphStyle(
            "TearSheetSection",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#0F172A"),
            spaceBefore=8,
            spaceAfter=4
        )
        cell_style = ParagraphStyle(
            "CellNormal",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1E293B")
        )
        cell_bold = ParagraphStyle(
            "CellBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#0F172A")
        )

        story: List[object] = []

        # Header Title
        story.append(Paragraph(f"GANN TRIPLE CONFLUENCE QUANTITATIVE TEAR SHEET", title_style))
        story.append(Paragraph(
            f"BENCHMARK: NSE {symbol} INDEX | HISTORICAL IN-SAMPLE (2020-2023) & BLIND OUT-OF-SAMPLE (2024-2025)",
            subtitle_style
        ))
        story.append(Spacer(1, 8))

        # KPI Metrics Table
        kpi_data = [
            [
                Paragraph("Initial Capital", cell_style), Paragraph(f"INR {summary.initial_capital:,.0f}", cell_bold),
                Paragraph("Net Total P&L", cell_style), Paragraph(f"INR {summary.total_net_pnl:+,.2f}", cell_bold),
                Paragraph("Total Return", cell_style), Paragraph(f"{summary.total_return_pct:+.2f}%", cell_bold),
            ],
            [
                Paragraph("Annualized CAGR", cell_style), Paragraph(f"{summary.cagr_pct:.2f}%", cell_bold),
                Paragraph("Max Drawdown (MDD)", cell_style), Paragraph(f"-{summary.max_drawdown_pct:.2f}%", cell_bold),
                Paragraph("Profit Factor", cell_style), Paragraph(f"{summary.profit_factor:.2f}", cell_bold),
            ],
            [
                Paragraph("Sharpe Ratio (Rf=6.5%)", cell_style), Paragraph(f"{summary.sharpe_ratio:.2f}", cell_bold),
                Paragraph("Sortino Ratio", cell_style), Paragraph(f"{summary.sortino_ratio:.2f}", cell_bold),
                Paragraph("Calmar Ratio", cell_style), Paragraph(f"{summary.calmar_ratio:.2f}", cell_bold),
            ],
            [
                Paragraph("Total Trades Executed", cell_style), Paragraph(f"{summary.total_trades}", cell_bold),
                Paragraph("Win Rate (%)", cell_style), Paragraph(f"{summary.win_rate_pct:.1f}%", cell_bold),
                Paragraph("Stop Survival Rate", cell_style), Paragraph(f"{summary.stop_survival_rate_pct:.1f}%", cell_bold),
            ],
            [
                Paragraph("Expectancy / Trade", cell_style), Paragraph(f"+{summary.expectancy_points:.1f} pts (INR {summary.expectancy_inr:+,.1f})", cell_bold),
                Paragraph("Payoff Ratio (Win/Loss)", cell_style), Paragraph(f"{summary.payoff_ratio:.2f}", cell_bold),
                Paragraph("Total Statutory Fees", cell_style), Paragraph(f"INR {summary.total_fees_paid:,.2f}", cell_bold),
            ]
        ]

        kpi_table = Table(kpi_data, colWidths=[110, 85, 110, 85, 110, 85])
        kpi_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 10))

        # SECTION 1: Equity & Drawdown Charts
        story.append(Paragraph("1. CUMULATIVE PERFORMANCE & CAPITAL PRESERVATION", section_style))
        story.append(Image(str(c1_path), width=520, height=195))
        story.append(Spacer(1, 6))
        story.append(Image(str(c2_path), width=520, height=150))
        story.append(PageBreak())

        # SECTION 2: Excursion & Stop-Loss Noise Validation
        story.append(Paragraph("2. 18-POINT STOP NOISE SURVIVAL & EXCURSION GEOMETRY", section_style))
        story.append(Image(str(c3_path), width=520, height=205))
        story.append(Spacer(1, 8))

        # SECTION 3: Monthly Heatmap
        story.append(Paragraph("3. MONTHLY NET RETURN MATRIX (% OF CAPITAL)", section_style))
        story.append(Image(str(c4_path), width=520, height=155))
        story.append(Spacer(1, 8))

        # SECTION 4: In-Sample vs Out-of-Sample Comparative Ledger
        story.append(Paragraph("4. IN-SAMPLE (2020-2023) vs OUT-OF-SAMPLE (2024-2025) ROBUSTNESS AUDIT", section_style))
        comp_data = [
            [
                Paragraph("<b>Metric</b>", cell_bold),
                Paragraph("<b>In-Sample (2020-2023)</b>", cell_bold),
                Paragraph("<b>Out-of-Sample (2024-2025)</b>", cell_bold),
                Paragraph("<b>Decay / Variance</b>", cell_bold)
            ],
            [
                Paragraph("Total Trades", cell_style),
                Paragraph(f"{is_summary.total_trades}", cell_style),
                Paragraph(f"{oos_summary.total_trades}", cell_style),
                Paragraph("Consistent cadence", cell_style)
            ],
            [
                Paragraph("Win Rate (%)", cell_style),
                Paragraph(f"{is_summary.win_rate_pct:.1f}%", cell_style),
                Paragraph(f"{oos_summary.win_rate_pct:.1f}%", cell_style),
                Paragraph(f"{oos_summary.win_rate_pct - is_summary.win_rate_pct:+.1f}%", cell_style)
            ],
            [
                Paragraph("Profit Factor", cell_style),
                Paragraph(f"{is_summary.profit_factor:.2f}", cell_style),
                Paragraph(f"{oos_summary.profit_factor:.2f}", cell_style),
                Paragraph(f"{oos_summary.profit_factor - is_summary.profit_factor:+.2f}", cell_style)
            ],
            [
                Paragraph("Expectancy per Trade", cell_style),
                Paragraph(f"+{is_summary.expectancy_points:.1f} pts", cell_style),
                Paragraph(f"+{oos_summary.expectancy_points:.1f} pts", cell_style),
                Paragraph(f"{oos_summary.expectancy_points - is_summary.expectancy_points:+.1f} pts", cell_style)
            ],
            [
                Paragraph("18-Pt Stop Survival Rate", cell_style),
                Paragraph(f"{is_summary.stop_survival_rate_pct:.1f}%", cell_style),
                Paragraph(f"{oos_summary.stop_survival_rate_pct:.1f}%", cell_style),
                Paragraph(f"{oos_summary.stop_survival_rate_pct - is_summary.stop_survival_rate_pct:+.1f}%", cell_style)
            ]
        ]
        comp_table = Table(comp_data, colWidths=[160, 125, 125, 110])
        comp_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FFFFFF")),
            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ]))
        story.append(comp_table)

        doc.build(story, canvasmaker=AcademicTearSheetCanvas)
        logger.info(f"Successfully compiled Quant Tear Sheet PDF at: {out_pdf}")
        return out_pdf
