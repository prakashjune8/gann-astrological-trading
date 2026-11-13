"""Institutional Quantitative Backtest & Visualizer View for CustomTkinter.

Provides direct in-app interactive inspection of:
1. Cumulative Equity Curve & Underwater Drawdown (IS vs OOS).
2. 2D MFE vs MAE Excursion Scatter with the 18.0 pt Hard Stop Barrier.
3. Monthly Return Heatmap Matrix.
4. Comprehensive Executed Trade Ledger.
5. Live Backtest Trigger & Direct PDF Tear Sheet Export.
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
from ui.theme import ThemeTokens

logger = logging.getLogger("backtest_view")


class BacktestView(ctk.CTkFrame):
    """Full-featured institutional backtest terminal view embedded inside CustomTkinter."""

    def __init__(self, master, theme: ThemeTokens, **kwargs):
        super().__init__(master, fg_color=theme.bg_primary, **kwargs)
        self.theme = theme

        # Engine & Data
        self.loader = ParquetDataLoader()
        self.runner = HistoricalBacktestRunner(data_loader=self.loader)

        # Active Data State
        self.is_ledger: Optional[TradeLedger] = None
        self.oos_ledger: Optional[TradeLedger] = None
        self.current_summary: Optional[QuantMetricsSummary] = None

        # Chart Cache
        self.fig_dir = Path(__file__).resolve().parent.parent.parent / "reports" / "figures"
        self.fig_dir.mkdir(parents=True, exist_ok=True)
        self._chart_images: Dict[str, ctk.CTkImage] = {}

        # Layout Scaffolding
        self._build_top_controls()
        self._build_kpi_cards()
        self._build_tabbed_visualizer()

        # Load initial cached benchmark charts
        self._load_cached_charts_and_metrics()

    def _build_top_controls(self):
        """Top action bar: Instrument, Partition, Run Backtest, and Export PDF."""
        self.control_bar = ctk.CTkFrame(self, fg_color=self.theme.bg_secondary, height=48, corner_radius=6)
        self.control_bar.pack(fill="x", padx=12, pady=(10, 6))

        # Instrument Selector
        ctk.CTkLabel(
            self.control_bar, text="Instrument:", font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.theme.text_secondary
        ).pack(side="left", padx=(14, 4))

        self.inst_var = ctk.StringVar(value="NIFTY50")
        self.inst_menu = ctk.CTkOptionMenu(
            self.control_bar,
            values=["NIFTY50", "BANKNIFTY", "CRUDEOIL", "NATURALGAS", "COPPER"],
            variable=self.inst_var,
            font=ctk.CTkFont(size=11),
            fg_color=self.theme.bg_accent,
            button_color=self.theme.accent_blue,
            width=115, height=28
        )
        self.inst_menu.pack(side="left", padx=4)

        # Partition Selector
        ctk.CTkLabel(
            self.control_bar, text="Partition:", font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.theme.text_secondary
        ).pack(side="left", padx=(12, 4))

        self.partition_var = ctk.StringVar(value="Full Comparison (IS & OOS)")
        self.partition_menu = ctk.CTkOptionMenu(
            self.control_bar,
            values=["Full Comparison (IS & OOS)", "In-Sample (2020-2023)", "Out-of-Sample (2024-2025)"],
            variable=self.partition_var,
            font=ctk.CTkFont(size=11),
            fg_color=self.theme.bg_accent,
            button_color=self.theme.accent_blue,
            width=185, height=28
        )
        self.partition_menu.pack(side="left", padx=4)

        # Run Backtest Button
        self.btn_run = ctk.CTkButton(
            self.control_bar,
            text="▶ Run Backtest",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=self.theme.accent_blue,
            text_color="#ffffff",
            command=self._handle_run_backtest,
            width=120, height=28
        )
        self.btn_run.pack(side="left", padx=(14, 6))

        # Export PDF Tear Sheet Button
        self.btn_export_pdf = ctk.CTkButton(
            self.control_bar,
            text="📄 Export PDF Tear Sheet",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=self.theme.accent_amber,
            text_color="#0f172a",
            command=self._handle_export_pdf,
            width=160, height=28
        )
        self.btn_export_pdf.pack(side="left", padx=6)

        # Status Label
        self.status_lbl = ctk.CTkLabel(
            self.control_bar,
            text="● Engine Ready",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.theme.accent_green
        )
        self.status_lbl.pack(side="right", padx=16)

    def _build_kpi_cards(self):
        """Executive KPI status cards strip across the top."""
        self.kpi_frame = ctk.CTkFrame(self, fg_color="transparent", height=70)
        self.kpi_frame.pack(fill="x", padx=12, pady=(0, 6))

        card_defs = [
            ("NET P&L / RETURN", "+₹0.00 (+0.0%)", "card_pnl"),
            ("CAGR / MAX DD", "0.0% / -0.0%", "card_cagr"),
            ("SHARPE (Rf=6.5%)", "0.00 / Sortino: 0.00", "card_sharpe"),
            ("WIN RATE / PF", "0.0% / PF: 0.00", "card_win"),
            ("EXPECTANCY / TRADE", "+0.0 pts (0.0 INR)", "card_expectancy"),
            ("18-PT STOP SURVIVAL", "0.0% Noise Survival", "card_survival"),
        ]

        self.kpi_labels: Dict[str, ctk.CTkLabel] = {}
        for title, default_val, key in card_defs:
            card = ctk.CTkFrame(self.kpi_frame, fg_color=self.theme.bg_secondary, corner_radius=6)
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
            self.kpi_labels[key] = val_lbl

    def _build_tabbed_visualizer(self):
        """Tabbed multi-chart visualizer and execution trade ledger."""
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=self.theme.bg_secondary,
            segmented_button_selected_color=self.theme.accent_blue,
            segmented_button_unselected_color=self.theme.bg_accent,
            text_color=self.theme.text_primary
        )
        self.tabview.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        # Tab 1: Equity Curve & Drawdown
        self.tab_equity = self.tabview.add("📊 Equity Curve & Drawdown")
        self.lbl_equity_chart = ctk.CTkLabel(self.tab_equity, text="Generating Equity Curve...", text_color=self.theme.text_secondary)
        self.lbl_equity_chart.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 2: 2D MFE vs MAE Excursion Scatter (Stop Survival)
        self.tab_scatter = self.tabview.add("🎯 2D MFE vs MAE Stop Proof")
        self.lbl_scatter_chart = ctk.CTkLabel(self.tab_scatter, text="Generating Excursion Scatter...", text_color=self.theme.text_secondary)
        self.lbl_scatter_chart.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 3: Monthly Net Return Heatmap
        self.tab_heatmap = self.tabview.add("🗓 Monthly Return Heatmap")
        self.lbl_heatmap_chart = ctk.CTkLabel(self.tab_heatmap, text="Generating Monthly Heatmap...", text_color=self.theme.text_secondary)
        self.lbl_heatmap_chart.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 4: Trade Execution Ledger
        self.tab_ledger = self.tabview.add("📋 Executed Trades Ledger")
        self._build_ledger_table(self.tab_ledger)

    def _build_ledger_table(self, parent):
        """Scrollable institutional trade execution ledger table."""
        self.ledger_box = ctk.CTkTextbox(
            parent,
            font=ctk.CTkFont(family="Consolas", size=10),
            fg_color=self.theme.bg_primary,
            text_color=self.theme.text_primary,
            wrap="none"
        )
        self.ledger_box.pack(fill="both", expand=True, padx=6, pady=6)
        self.ledger_box.insert("end", "Trade ledger will populate upon backtest completion.\n")
        self.ledger_box.configure(state="disabled")

    def _load_cached_charts_and_metrics(self):
        """Loads and displays pre-rendered benchmark charts if available."""
        c1_file = self.fig_dir / "c1_equity.png"
        c3_file = self.fig_dir / "c3_scatter.png"
        c4_file = self.fig_dir / "c4_heatmap.png"

        if c1_file.is_file():
            self._display_chart_image(c1_file, self.lbl_equity_chart, max_w=980, max_h=480)
        if c3_file.is_file():
            self._display_chart_image(c3_file, self.lbl_scatter_chart, max_w=980, max_h=480)
        if c4_file.is_file():
            self._display_chart_image(c4_file, self.lbl_heatmap_chart, max_w=980, max_h=480)

    def _display_chart_image(self, img_path: Path, label: ctk.CTkLabel, max_w: int = 960, max_h: int = 460):
        """Loads a PNG image, scales it with high quality, and sets it on a CTkLabel."""
        try:
            pil_img = Image.open(str(img_path))
            w, h = pil_img.size
            scale = min(max_w / w, max_h / h, 1.0)
            target_w = int(w * scale)
            target_h = int(h * scale)

            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(target_w, target_h))
            label.configure(image=ctk_img, text="")
            # Keep reference
            self._chart_images[str(img_path)] = ctk_img
        except Exception as e:
            logger.error(f"Failed to display chart image {img_path}: {e}")
            label.configure(text=f"Error displaying chart: {e}")

    def _handle_run_backtest(self):
        """Executes the historical backtest in a background thread to prevent UI freezing."""
        self.btn_run.configure(state="disabled", text="Running...")
        self.status_lbl.configure(text="⏳ Simulating...", text_color=self.theme.accent_amber)

        thread = threading.Thread(target=self._execute_backtest_worker, daemon=True)
        thread.start()

    def _execute_backtest_worker(self):
        symbol = self.inst_var.get()
        partition_mode = self.partition_var.get()

        try:
            # Seed monthly Parquet datasets if not already present
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

            # Merge for metrics and charts
            df_is = self.is_ledger.to_dataframe()
            df_oos = self.oos_ledger.to_dataframe()
            import pandas as pd
            df_master = pd.concat([df_is, df_oos], ignore_index=True)
            if not df_master.empty:
                df_master.sort_values("entry_time", inplace=True)

            summary, daily_df, _, monthly_matrix = QuantMetricsCalculator.calculate_metrics(df_master)
            self.current_summary = summary

            # Render High-DPI Charts
            c1_p = QuantChartRenderer.render_equity_curve(daily_df, output_path=self.fig_dir / "c1_equity.png")
            c3_p = QuantChartRenderer.render_mfe_mae_scatter(df_master, output_path=self.fig_dir / "c3_scatter.png")
            c4_p = QuantChartRenderer.render_monthly_heatmap(monthly_matrix, output_path=self.fig_dir / "c4_heatmap.png")

            # Push UI updates to main thread
            self.after(0, lambda: self._on_backtest_complete(df_master, summary, c1_p, c3_p, c4_p))

        except Exception as e:
            logger.error(f"Error during backtest execution: {e}", exc_info=True)
            self.after(0, lambda: self._on_backtest_error(str(e)))

    def _on_backtest_complete(self, df_trades, summary: QuantMetricsSummary, c1_p: Path, c3_p: Path, c4_p: Path):
        """Update KPI cards, refresh charts, and populate the ledger table."""
        # 1. KPI Cards
        pnl_color = self.theme.accent_green if summary.total_net_pnl >= 0 else self.theme.accent_red
        self.kpi_labels["card_pnl"].configure(
            text=f"INR {summary.total_net_pnl:+,.0f} ({summary.total_return_pct:+.1f}%)",
            text_color=pnl_color
        )
        self.kpi_labels["card_cagr"].configure(
            text=f"{summary.cagr_pct:.1f}% / -{summary.max_drawdown_pct:.1f}% MDD"
        )
        self.kpi_labels["card_sharpe"].configure(
            text=f"Sharpe: {summary.sharpe_ratio:.2f} | Sortino: {summary.sortino_ratio:.2f}"
        )
        self.kpi_labels["card_win"].configure(
            text=f"{summary.win_rate_pct:.1f}% | PF: {summary.profit_factor:.2f}"
        )
        self.kpi_labels["card_expectancy"].configure(
            text=f"+{summary.expectancy_points:.1f} pts (INR {summary.expectancy_inr:+,.0f})"
        )
        self.kpi_labels["card_survival"].configure(
            text=f"{summary.stop_survival_rate_pct:.1f}% Survival (<18pt Noise)"
        )

        # 2. Update Charts
        self._display_chart_image(c1_p, self.lbl_equity_chart)
        self._display_chart_image(c3_p, self.lbl_scatter_chart)
        self._display_chart_image(c4_p, self.lbl_heatmap_chart)

        # 3. Populate Ledger Table
        self.ledger_box.configure(state="normal")
        self.ledger_box.delete("1.0", "end")

        header = (
            f"{'TRADE ID':<10} {'DIR':<6} {'ENTRY TIME':<17} {'FILL':<9} {'EXIT TIME':<17} "
            f"{'EXIT':<9} {'REASON':<14} {'MFE':<7} {'MAE':<7} {'NET P&L (INR)':<14} {'FEES':<8}\n"
        )
        sep = "-" * 118 + "\n"
        self.ledger_box.insert("end", header + sep)

        if not df_trades.empty:
            for _, r in df_trades.tail(100).iterrows():
                e_t = r['entry_time'].strftime('%Y-%m-%d %H:%M') if hasattr(r['entry_time'], 'strftime') else str(r['entry_time'])[:16]
                x_t = r['exit_time'].strftime('%Y-%m-%d %H:%M') if hasattr(r['exit_time'], 'strftime') else str(r['exit_time'])[:16]
                line = (
                    f"{r['trade_id']:<10} {r['direction']:<6} {e_t:<17} {r['fill_price']:<9.1f} {x_t:<17} "
                    f"{r['exit_price']:<9.1f} {r['exit_reason']:<14} {r['mfe_points']:<7.1f} {r['mae_points']:<7.1f} "
                    f"{r['net_pnl_inr']:<+14,.2f} {r['total_fees']:<8.2f}\n"
                )
                self.ledger_box.insert("end", line)

        self.ledger_box.configure(state="disabled")

        # Reset Controls
        self.btn_run.configure(state="normal", text="▶ Run Backtest")
        self.status_lbl.configure(text="● Completed Successfully", text_color=self.theme.accent_green)

    def _on_backtest_error(self, err_msg: str):
        self.btn_run.configure(state="normal", text="▶ Run Backtest")
        self.status_lbl.configure(text=f"✖ Error: {err_msg[:24]}", text_color=self.theme.accent_red)

    def _handle_export_pdf(self):
        """Compiles and opens the publication-grade Quant Tear Sheet PDF."""
        try:
            if self.is_ledger is None or self.oos_ledger is None:
                # Seed and compile default comparison
                self.loader.generate_synthetic_benchmark_parquet("NIFTY50", year=2023, month=12, seed_price=21000.0)
                self.loader.generate_synthetic_benchmark_parquet("NIFTY50", year=2024, month=1, seed_price=21500.0)
                comp = self.runner.run_full_comparison(self.inst_var.get())
                self.is_ledger = comp["IS"]
                self.oos_ledger = comp["OOS"]

            out_pdf = Path(__file__).resolve().parent.parent.parent / "reports" / "GANN_TRIPLE_CONFLUENCE_TEARSHEET.pdf"
            BacktestReportGenerator.generate_tear_sheet(
                is_ledger=self.is_ledger,
                oos_ledger=self.oos_ledger,
                symbol=self.inst_var.get(),
                output_pdf_path=out_pdf
            )
            # Open PDF in default Windows viewer
            os.startfile(str(out_pdf))
            self.status_lbl.configure(text="● PDF Exported & Opened", text_color=self.theme.accent_green)
        except Exception as e:
            logger.error(f"Failed to export PDF: {e}")
            self.status_lbl.configure(text=f"✖ Export Failed: {e}", text_color=self.theme.accent_red)

    def apply_theme(self, theme: ThemeTokens):
        """Dynamic theme updates for all containers and widgets."""
        self.theme = theme
        self.configure(fg_color=theme.bg_primary)
        self.control_bar.configure(fg_color=theme.bg_secondary)
        self.inst_menu.configure(fg_color=theme.bg_accent, button_color=theme.accent_blue)
        self.partition_menu.configure(fg_color=theme.bg_accent, button_color=theme.accent_blue)
        self.tabview.configure(
            fg_color=theme.bg_secondary,
            segmented_button_selected_color=theme.accent_blue,
            segmented_button_unselected_color=theme.bg_accent,
            text_color=theme.text_primary
        )
        self.ledger_box.configure(fg_color=theme.bg_primary, text_color=theme.text_primary)
        for card in self.kpi_frame.winfo_children():
            if isinstance(card, ctk.CTkFrame):
                card.configure(fg_color=theme.bg_secondary)
