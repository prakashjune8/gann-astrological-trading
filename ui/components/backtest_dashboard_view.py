"""Institutional Backtest Dashboard View (High-DPI Embedded Visualizer).

Implements:
1. Interactive Control Panel (Instrument, IS/OOS Date Range Partition, Asynchronous Execution).
2. Asynchronous Non-Blocking Execution Threading with Responsive Loading Indicators.
3. High-DPI Embedded Image Viewer for Matplotlib Charts (Equity, Drawdown, MFE/MAE Scatter, Heatmap).
4. Direct PDF Tear Sheet Compilation & Launch.
5. Dynamic Theme Adaptation across All Institutional Color Tokens.
"""
from __future__ import annotations

import logging
import os
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

import customtkinter as ctk
from PIL import Image

from core.backtest_data import ParquetDataLoader
from core.backtest_engine import HistoricalBacktestRunner, TradeLedger
from reporting.backtest_report_generator import (
    BacktestReportGenerator,
    QuantChartRenderer,
    QuantMetricsCalculator,
    QuantMetricsSummary,
)
from ui.components.interactive_trade_inspector import InteractiveTradeInspector
from ui.theme import ThemeTokens

logger = logging.getLogger("backtest_dashboard_view")


class BacktestDashboardView(ctk.CTkFrame):
    """Dedicated institutional backtesting dashboard view embedded in CustomTkinter."""

    def __init__(self, master, theme: ThemeTokens, **kwargs):
        super().__init__(master, fg_color=theme.bg_primary, **kwargs)
        self.theme = theme

        # Engine & Data Stores
        self.loader = ParquetDataLoader()
        self.runner = HistoricalBacktestRunner(data_loader=self.loader)

        # Operational State
        self.is_ledger: Optional[TradeLedger] = None
        self.oos_ledger: Optional[TradeLedger] = None
        self.current_summary: Optional[QuantMetricsSummary] = None
        self.is_running: bool = False

        # Chart Path Cache
        self.fig_dir = Path(__file__).resolve().parent.parent.parent / "reports" / "figures"
        self.fig_dir.mkdir(parents=True, exist_ok=True)
        self._ctk_image_refs: Dict[str, ctk.CTkImage] = {}

        # UI Layout
        self._build_header_controls()
        self._build_kpi_summary_cards()
        self._build_chart_viewer_tabs()

        # Load initial pre-rendered benchmark charts if present
        self._load_initial_visuals()

    def _build_header_controls(self):
        """Builds top control strip with instrument, date range, and action buttons."""
        self.control_panel = ctk.CTkFrame(self, fg_color=self.theme.bg_secondary, height=52, corner_radius=6)
        self.control_panel.pack(fill="x", padx=14, pady=(10, 6))

        # Instrument Selector
        ctk.CTkLabel(
            self.control_panel, text="Instrument:", font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.theme.text_secondary
        ).pack(side="left", padx=(14, 4))

        self.symbol_var = ctk.StringVar(value="NIFTY50")
        self.symbol_menu = ctk.CTkOptionMenu(
            self.control_panel,
            values=["NIFTY50", "BANKNIFTY", "CRUDEOIL", "NATURALGAS", "COPPER"],
            variable=self.symbol_var,
            font=ctk.CTkFont(size=11),
            fg_color=self.theme.bg_accent,
            button_color=self.theme.accent_blue,
            width=120, height=28
        )
        self.symbol_menu.pack(side="left", padx=4)

        # Date Range Partition Selector
        ctk.CTkLabel(
            self.control_panel, text="Date Range:", font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.theme.text_secondary
        ).pack(side="left", padx=(12, 4))

        self.partition_var = ctk.StringVar(value="Full Comparison (IS & OOS)")
        self.partition_menu = ctk.CTkOptionMenu(
            self.control_panel,
            values=[
                "Full Comparison (IS & OOS)",
                "In-Sample (2020-2023) [Calibration]",
                "Out-of-Sample (2024-2025) [Blind Forward]"
            ],
            variable=self.partition_var,
            font=ctk.CTkFont(size=11),
            fg_color=self.theme.bg_accent,
            button_color=self.theme.accent_blue,
            width=230, height=28
        )
        self.partition_menu.pack(side="left", padx=4)

        # Run Backtest Button
        self.btn_run = ctk.CTkButton(
            self.control_panel,
            text="▶ Run Backtest",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=self.theme.accent_blue,
            hover_color=self.theme.border_color,
            text_color="#ffffff",
            command=self._on_run_clicked,
            width=125, height=28
        )
        self.btn_run.pack(side="left", padx=(14, 6))

        # Export PDF Tear Sheet Button
        self.btn_pdf = ctk.CTkButton(
            self.control_panel,
            text="📄 Export PDF Tear Sheet",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=self.theme.accent_amber,
            text_color="#0f172a",
            command=self._on_export_pdf_clicked,
            width=165, height=28
        )
        self.btn_pdf.pack(side="left", padx=6)

        # Async Progress / Status Indicator
        self.status_lbl = ctk.CTkLabel(
            self.control_panel,
            text="● Engine Ready",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.theme.accent_green
        )
        self.status_lbl.pack(side="right", padx=(6, 16))

        self.progress_bar = ctk.CTkProgressBar(self.control_panel, width=120, height=8, mode="indeterminate")
        self.progress_bar.pack(side="right", padx=6)
        self.progress_bar.set(0.0)

    def _build_kpi_summary_cards(self):
        """Builds 6 executive KPI metric cards for at-a-glance quant audit."""
        self.kpi_strip = ctk.CTkFrame(self, fg_color="transparent", height=68)
        self.kpi_strip.pack(fill="x", padx=14, pady=(0, 6))

        kpis = [
            ("TOTAL NET P&L", "+₹0.00 (+0.0%)", "pnl"),
            ("CAGR / MAX DRAWDOWN", "0.0% / -0.0%", "cagr"),
            ("SHARPE (Rf=6.5%) / SORTINO", "0.00 / 0.00", "sharpe"),
            ("WIN RATE / PROFIT FACTOR", "0.0% / PF: 0.00", "win"),
            ("EXPECTANCY / TRADE", "+0.0 pts (0.0 INR)", "expectancy"),
            ("18-PT STOP NOISE SURVIVAL", "0.0% Validated", "survival"),
        ]

        self.kpi_widgets: Dict[str, ctk.CTkLabel] = {}
        for title, default_val, key in kpis:
            card = ctk.CTkFrame(self.kpi_strip, fg_color=self.theme.bg_secondary, corner_radius=6)
            card.pack(side="left", fill="both", expand=True, padx=3)

            ctk.CTkLabel(
                card, text=title, font=ctk.CTkFont(size=9, weight="bold"),
                text_color=self.theme.text_secondary
            ).pack(anchor="w", padx=10, pady=(6, 1))

            val_lbl = ctk.CTkLabel(
                card, text=default_val, font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
                text_color=self.theme.text_primary
            )
            val_lbl.pack(anchor="w", padx=10, pady=(0, 6))
            self.kpi_widgets[key] = val_lbl

    def _build_chart_viewer_tabs(self):
        """Tabbed high-DPI image viewer with native DPI scaling."""
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=self.theme.bg_secondary,
            segmented_button_selected_color=self.theme.accent_blue,
            segmented_button_unselected_color=self.theme.bg_accent,
            text_color=self.theme.text_primary
        )
        self.tabview.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        # Tab 1: Interactive Candlestick & Trade Inspector
        self.tab_inspector = self.tabview.add("🕯 Trade & Method Inspector")
        self.inspector_view = InteractiveTradeInspector(self.tab_inspector, theme=self.theme)
        self.inspector_view.pack(fill="both", expand=True, padx=4, pady=4)

        # Tab 2: Equity Curve & Drawdown
        self.tab_equity = self.tabview.add("📊 Equity Curve & Drawdown")
        self.scroll_equity = ctk.CTkScrollableFrame(self.tab_equity, fg_color="transparent")
        self.scroll_equity.pack(fill="both", expand=True, padx=4, pady=4)

        self.lbl_chart1 = ctk.CTkLabel(self.scroll_equity, text="Generating Cumulative Equity Curve...", text_color=self.theme.text_secondary)
        self.lbl_chart1.pack(fill="x", padx=10, pady=6)

        self.lbl_chart2 = ctk.CTkLabel(self.scroll_equity, text="Generating Underwater Drawdown Profile...", text_color=self.theme.text_secondary)
        self.lbl_chart2.pack(fill="x", padx=10, pady=6)

        # Tab 2: 2D MFE vs MAE Scatter (18-pt Stop Survival Proof)
        self.tab_scatter = self.tabview.add("🎯 2D MFE vs MAE Stop Proof")
        self.lbl_chart3 = ctk.CTkLabel(self.tab_scatter, text="Generating Excursion Scatter...", text_color=self.theme.text_secondary)
        self.lbl_chart3.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 3: Monthly Net Return Matrix Heatmap
        self.tab_heatmap = self.tabview.add("🗓 Monthly Return Heatmap")
        self.lbl_chart4 = ctk.CTkLabel(self.tab_heatmap, text="Generating Monthly Heatmap...", text_color=self.theme.text_secondary)
        self.lbl_chart4.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 4: Executed Trade Ledger моноspace view
        self.tab_ledger = self.tabview.add("📋 Executed Trade Ledger")
        self.ledger_box = ctk.CTkTextbox(
            self.tab_ledger,
            font=ctk.CTkFont(family="Consolas", size=10),
            fg_color=self.theme.bg_primary,
            text_color=self.theme.text_primary,
            wrap="none"
        )
        self.ledger_box.pack(fill="both", expand=True, padx=6, pady=6)
        self.ledger_box.insert("end", "Trade ledger will populate automatically upon backtest completion.\n")
        self.ledger_box.configure(state="disabled")

    def _load_initial_visuals(self):
        """Loads and embeds any pre-computed charts from reports/figures/."""
        c1 = self.fig_dir / "c1_equity.png"
        c2 = self.fig_dir / "c2_drawdown.png"
        c3 = self.fig_dir / "c3_scatter.png"
        c4 = self.fig_dir / "c4_heatmap.png"

        if c1.is_file():
            self._render_image_to_label(c1, self.lbl_chart1, target_width=860, target_height=320)
        if c2.is_file():
            self._render_image_to_label(c2, self.lbl_chart2, target_width=860, target_height=260)
        if c3.is_file():
            self._render_image_to_label(c3, self.lbl_chart3, target_width=920, target_height=420)
        if c4.is_file():
            self._render_image_to_label(c4, self.lbl_chart4, target_width=920, target_height=340)

    def _render_image_to_label(self, path: Path, label: ctk.CTkLabel, target_width: int, target_height: int):
        """Safely loads and scales a PIL image into a High-DPI CTkImage without scaling distortion."""
        try:
            pil_img = Image.open(str(path))
            orig_w, orig_h = pil_img.size
            aspect = orig_h / orig_w
            w = target_width
            h = int(w * aspect)
            if h > target_height:
                h = target_height
                w = int(h / aspect)

            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(w, h))
            label.configure(image=ctk_img, text="")
            self._ctk_image_refs[str(path)] = ctk_img
        except Exception as e:
            logger.error(f"Error loading image {path}: {e}")
            label.configure(text=f"Image load error: {e}")

    # ==========================================================================
    # ASYNCHRONOUS NON-BLOCKING EXECUTION PIPELINE
    # ==========================================================================

    def _on_run_clicked(self):
        """Triggered when the user clicks 'Run Backtest'."""
        if self.is_running:
            return

        self.is_running = True
        self.btn_run.configure(state="disabled", text="Simulating...")
        self.status_lbl.configure(text="⏳ Simulation in Progress...", text_color=self.theme.accent_amber)
        self.progress_bar.start()

        # Spawn asynchronous background daemon thread
        worker = threading.Thread(target=self._run_backtest_async_worker, daemon=True)
        worker.start()

    def _run_backtest_async_worker(self):
        """Background thread executing the high-frequency Parquet streaming simulation."""
        symbol = self.symbol_var.get()
        partition_mode = self.partition_var.get()

        try:
            # Guarantee monthly Parquet partitions are seeded
            self.loader.generate_synthetic_benchmark_parquet(symbol, year=2023, month=12, seed_price=21000.0)
            self.loader.generate_synthetic_benchmark_parquet(symbol, year=2024, month=1, seed_price=21500.0)

            if "In-Sample" in partition_mode:
                self.is_ledger = self.runner.run_partition(symbol, partition="IS")
                self.oos_ledger = TradeLedger()
            elif "Out-of-Sample" in partition_mode:
                self.is_ledger = TradeLedger()
                self.oos_ledger = self.runner.run_partition(symbol, partition="OOS")
            else:
                comparison = self.runner.run_full_comparison(symbol)
                self.is_ledger = comparison["IS"]
                self.oos_ledger = comparison["OOS"]

            # Merge for metrics calculation
            import pandas as pd
            df_is = self.is_ledger.to_dataframe()
            df_oos = self.oos_ledger.to_dataframe()
            df_master = pd.concat([df_is, df_oos], ignore_index=True)
            if not df_master.empty:
                df_master.sort_values("entry_time", inplace=True)

            summary, daily_df, _, monthly_matrix = QuantMetricsCalculator.calculate_metrics(df_master)
            self.current_summary = summary

            # Render High-DPI Charts at 200 DPI
            c1_path = QuantChartRenderer.render_equity_curve(daily_df, output_path=self.fig_dir / "c1_equity.png")
            c2_path = QuantChartRenderer.render_drawdown_chart(daily_df, output_path=self.fig_dir / "c2_drawdown.png")
            c3_path = QuantChartRenderer.render_mfe_mae_scatter(df_master, output_path=self.fig_dir / "c3_scatter.png")
            c4_path = QuantChartRenderer.render_monthly_heatmap(monthly_matrix, output_path=self.fig_dir / "c4_heatmap.png")

            # Thread-safe UI update
            self.after(0, lambda: self._on_simulation_success(df_master, summary, c1_path, c2_path, c3_path, c4_path))

        except Exception as e:
            logger.error(f"Asynchronous simulation encountered an error: {e}", exc_info=True)
            self.after(0, lambda: self._on_simulation_error(str(e)))

    def _on_simulation_success(
        self,
        df_master,
        summary: QuantMetricsSummary,
        c1: Path,
        c2: Path,
        c3: Path,
        c4: Path
    ):
        """Invoked on the main UI thread upon background thread completion."""
        self.progress_bar.stop()
        self.btn_run.configure(state="normal", text="▶ Run Backtest")
        self.status_lbl.configure(text="● Simulation Completed", text_color=self.theme.accent_green)
        self.is_running = False

        # 1. Update KPI Card Labels
        pnl_col = self.theme.accent_green if summary.total_net_pnl >= 0 else self.theme.accent_red
        self.kpi_widgets["pnl"].configure(
            text=f"INR {summary.total_net_pnl:+,.0f} ({summary.total_return_pct:+.1f}%)",
            text_color=pnl_col
        )
        self.kpi_widgets["cagr"].configure(
            text=f"{summary.cagr_pct:.1f}% / -{summary.max_drawdown_pct:.1f}% MDD"
        )
        self.kpi_widgets["sharpe"].configure(
            text=f"Sharpe: {summary.sharpe_ratio:.2f} | Sortino: {summary.sortino_ratio:.2f}"
        )
        self.kpi_widgets["win"].configure(
            text=f"{summary.win_rate_pct:.1f}% | PF: {summary.profit_factor:.2f}"
        )
        self.kpi_widgets["expectancy"].configure(
            text=f"+{summary.expectancy_points:.1f} pts (INR {summary.expectancy_inr:+,.0f})"
        )
        self.kpi_widgets["survival"].configure(
            text=f"{summary.stop_survival_rate_pct:.1f}% (<18pt Noise)"
        )

        # 2. Render Scaled Charts into Image Labels
        self._render_image_to_label(c1, self.lbl_chart1, target_width=860, target_height=320)
        self._render_image_to_label(c2, self.lbl_chart2, target_width=860, target_height=260)
        self._render_image_to_label(c3, self.lbl_chart3, target_width=920, target_height=420)
        self._render_image_to_label(c4, self.lbl_chart4, target_width=920, target_height=340)

        # 3. Populate Trade Ledger Box
        self.ledger_box.configure(state="normal")
        self.ledger_box.delete("1.0", "end")

        header = (
            f"{'TRADE ID':<10} {'DIR':<6} {'ENTRY TIME':<17} {'FILL':<9} {'EXIT TIME':<17} "
            f"{'EXIT':<9} {'REASON':<14} {'MFE':<7} {'MAE':<7} {'NET P&L (INR)':<14} {'FEES':<8}\n"
        )
        sep = "-" * 118 + "\n"
        self.ledger_box.insert("end", header + sep)

        if not df_master.empty:
            for _, r in df_master.tail(120).iterrows():
                e_t = r['entry_time'].strftime('%Y-%m-%d %H:%M') if hasattr(r['entry_time'], 'strftime') else str(r['entry_time'])[:16]
                x_t = r['exit_time'].strftime('%Y-%m-%d %H:%M') if hasattr(r['exit_time'], 'strftime') else str(r['exit_time'])[:16]
                line = (
                    f"{r['trade_id']:<10} {r['direction']:<6} {e_t:<17} {r['fill_price']:<9.1f} {x_t:<17} "
                    f"{r['exit_price']:<9.1f} {r['exit_reason']:<14} {r['mfe_points']:<7.1f} {r['mae_points']:<7.1f} "
                    f"{r['net_pnl_inr']:<+14,.2f} {r['total_fees']:<8.2f}\n"
                )
                self.ledger_box.insert("end", line)

        self.ledger_box.configure(state="disabled")

    def _on_simulation_error(self, err_msg: str):
        """Invoked if the background worker encounters an exception."""
        self.progress_bar.stop()
        self.btn_run.configure(state="normal", text="▶ Run Backtest")
        self.status_lbl.configure(text=f"✖ Failed: {err_msg[:25]}", text_color=self.theme.accent_red)
        self.is_running = False

    def _on_export_pdf_clicked(self):
        """Generates and opens the master Quant Tear Sheet PDF."""
        try:
            if self.is_ledger is None or self.oos_ledger is None:
                # Seed and compile default comparison
                self.loader.generate_synthetic_benchmark_parquet("NIFTY50", year=2023, month=12, seed_price=21000.0)
                self.loader.generate_synthetic_benchmark_parquet("NIFTY50", year=2024, month=1, seed_price=21500.0)
                comp = self.runner.run_full_comparison(self.symbol_var.get())
                self.is_ledger = comp["IS"]
                self.oos_ledger = comp["OOS"]

            out_pdf = Path(__file__).resolve().parent.parent.parent / "reports" / "GANN_TRIPLE_CONFLUENCE_TEARSHEET.pdf"
            BacktestReportGenerator.generate_tear_sheet(
                is_ledger=self.is_ledger,
                oos_ledger=self.oos_ledger,
                symbol=self.symbol_var.get(),
                output_pdf_path=out_pdf
            )
            os.startfile(str(out_pdf))
            self.status_lbl.configure(text="● PDF Exported & Opened", text_color=self.theme.accent_green)
        except Exception as e:
            logger.error(f"Failed to export PDF: {e}")
            self.status_lbl.configure(text=f"✖ PDF Export Error", text_color=self.theme.accent_red)

    def apply_theme(self, theme: ThemeTokens):
        """Dynamic theme tokens propagation."""
        self.theme = theme
        self.configure(fg_color=theme.bg_primary)
        self.control_panel.configure(fg_color=theme.bg_secondary)
        self.symbol_menu.configure(fg_color=theme.bg_accent, button_color=theme.accent_blue)
        self.partition_menu.configure(fg_color=theme.bg_accent, button_color=theme.accent_blue)
        self.tabview.configure(
            fg_color=theme.bg_secondary,
            segmented_button_selected_color=theme.accent_blue,
            segmented_button_unselected_color=theme.bg_accent,
            text_color=theme.text_primary
        )
        self.ledger_box.configure(fg_color=theme.bg_primary, text_color=theme.text_primary)
        for card in self.kpi_strip.winfo_children():
            if isinstance(card, ctk.CTkFrame):
                card.configure(fg_color=theme.bg_secondary)
