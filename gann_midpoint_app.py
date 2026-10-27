"""Standalone Desktop Application: Gann Midpoint & 360° Time Calculator."""
from __future__ import annotations

import csv
from datetime import date, datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from gann_timer.midpoint_engine import (
    analyze_midpoints,
    MidpointAnalysisResult,
    calculate_mumbai_solar_noon,
    equation_of_time,
)

COLUMNS = [
    ("degree", "Degree (°)", 80),
    ("left", "Left Time (-θ Past/Ascending)", 210),
    ("right", "Right Time (+θ Future/Descending)", 210),
    ("desc", "Gann Harmonic Significance", 320),
    ("category", "Importance", 110),
]


class GannMidpointApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title("Gann Midpoint & 360° Time Harmonics – Indian Markets")
        self.geometry("1180x760")
        self.minsize(980, 600)
        
        self.current_result: MidpointAnalysisResult | None = None
        
        self._setup_treeview_styles()
        self._build_header()
        self._build_controls()
        self._build_results_view()
        self._calculate()

    def _setup_treeview_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background="#1f2329",
            fieldbackground="#1f2329",
            foreground="#f0f0f0",
            rowheight=26,
            borderwidth=0,
            font=("Segoe UI", 11),
        )
        style.configure(
            "Treeview.Heading",
            background="#2b313a",
            foreground="#ffffff",
            font=("Segoe UI Semibold", 11),
            relief="flat",
        )
        style.map("Treeview", background=[("selected", "#1f6aa5")])

    def _build_header(self) -> None:
        hdr = ctk.CTkFrame(self, corner_radius=0, fg_color="#181b20", height=65)
        hdr.pack(fill="x", side="top")
        
        title_box = ctk.CTkFrame(hdr, fg_color="transparent")
        title_box.pack(side="left", padx=16, pady=10)
        
        ctk.CTkLabel(
            title_box,
            text="☉ Gann Midpoint & 360° Time Harmonics",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ffffff",
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            title_box,
            text="NSE • BSE • MCX • Astronomical True Solar Noon (Mumbai 72.825° E)",
            font=ctk.CTkFont(size=12),
            text_color="gray70",
        ).pack(anchor="w")

    def _build_controls(self) -> None:
        ctrl = ctk.CTkFrame(self, fg_color="#23272e", corner_radius=8)
        ctrl.pack(fill="x", padx=16, pady=(12, 6))

        # Row 1: Session Selector & Date Input
        r1 = ctk.CTkFrame(ctrl, fg_color="transparent")
        r1.pack(fill="x", padx=12, pady=(10, 6))

        ctk.CTkLabel(r1, text="Market Session:", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=(0, 6))
        self.mode_var = ctk.StringVar(value="NSE_BSE")
        self.mode_combo = ctk.CTkOptionMenu(
            r1,
            variable=self.mode_var,
            values=[
                "NSE / BSE Equity (09:15 - 15:30 IST)",
                "MCX Commodity (09:00 - 23:30/23:55 IST)",
                "Natural Astronomical Solar Noon (Mumbai)",
            ],
            command=self._on_mode_change,
            width=320,
        )
        self.mode_combo.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(r1, text="Trading Date (YYYY-MM-DD):", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=(0, 6))
        self.date_entry = ctk.CTkEntry(r1, width=130)
        self.date_entry.insert(0, date.today().isoformat())
        self.date_entry.pack(side="left", padx=(0, 10))

        ctk.CTkButton(r1, text="Today", width=65, command=self._set_today, fg_color="#3a3f47").pack(side="left", padx=(0, 15))

        # Row 2: Custom Degrees & Actions
        r2 = ctk.CTkFrame(ctrl, fg_color="transparent")
        r2.pack(fill="x", padx=12, pady=(4, 10))

        ctk.CTkLabel(r2, text="Custom Degrees (comma separated, e.g. 22.5, 33, 75):", font=ctk.CTkFont(size=13)).pack(side="left", padx=(0, 6))
        self.custom_entry = ctk.CTkEntry(r2, placeholder_text="e.g. 22.5, 33, 67.5, 75", width=220)
        self.custom_entry.pack(side="left", padx=(0, 15))

        calc_btn = ctk.CTkButton(
            r2,
            text="Calculate Harmonics",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._calculate,
            width=160,
        )
        calc_btn.pack(side="left", padx=(0, 10))

        export_btn = ctk.CTkButton(
            r2,
            text="Export to CSV",
            command=self._export_csv,
            width=120,
            fg_color="#3a3f47",
        )
        export_btn.pack(side="left")

    def _build_results_view(self) -> None:
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=16, pady=(4, 14))

        # Summary Info Banner
        self.summary_card = ctk.CTkFrame(container, fg_color="#1e2227", corner_radius=8)
        self.summary_card.pack(fill="x", pady=(0, 8))

        self.summary_title = ctk.CTkLabel(
            self.summary_card,
            text="",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#61afef",
        )
        self.summary_title.pack(anchor="w", padx=14, pady=(8, 2))

        self.summary_metrics = ctk.CTkLabel(
            self.summary_card,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#abb2bf",
            justify="left",
        )
        self.summary_metrics.pack(anchor="w", padx=14, pady=(0, 8))

        # Table Container
        tbl_frame = tk.Frame(container, bg="#1f2329")
        tbl_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(tbl_frame, columns=[c[0] for c in COLUMNS], show="headings")
        for col_id, col_name, width in COLUMNS:
            self.tree.heading(col_id, text=col_name)
            self.tree.column(col_id, width=width, minwidth=60, anchor="w")

        self.tree.tag_configure("major", foreground="#98c379")
        self.tree.tag_configure("minor", foreground="#abb2bf")
        self.tree.tag_configure("custom", foreground="#e5c07b")

        y_scroll = ttk.Scrollbar(tbl_frame, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(tbl_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        tbl_frame.grid_rowconfigure(0, weight=1)
        tbl_frame.grid_columnconfigure(0, weight=1)

    def _set_today(self) -> None:
        self.date_entry.delete(0, "end")
        self.date_entry.insert(0, date.today().isoformat())
        self._calculate()

    def _on_mode_change(self, _choice: str) -> None:
        self._calculate()

    def _get_selected_mode_key(self) -> str:
        sel = self.mode_var.get()
        if "NSE" in sel:
            return "NSE_BSE"
        if "MCX" in sel:
            return "MCX"
        return "SOLAR"

    def _parse_custom_degrees(self) -> list[float]:
        raw = self.custom_entry.get().strip()
        if not raw:
            return []
        out = []
        for part in raw.split(","):
            part = part.strip()
            if part:
                try:
                    val = float(part)
                    if 0 < val <= 360:
                        out.append(val)
                except ValueError:
                    pass
        return out

    def _calculate(self) -> None:
        try:
            d = date.fromisoformat(self.date_entry.get().strip())
        except ValueError:
            messagebox.showerror("Invalid Date", "Please enter a valid date in YYYY-MM-DD format.")
            return

        mode_key = self._get_selected_mode_key()
        custom_degs = self._parse_custom_degrees()

        result = analyze_midpoints(d, mode_key, custom_degs)
        self.current_result = result

        # Update Summary Banner
        mid_str = result.midpoint_time.strftime("%H:%M:%S IST")
        self.summary_title.configure(text=f"📌 {result.description}")

        metrics_text = (
            f"Exact Midpoint (0° Balance Axis): {mid_str}  |  "
            f"Cycle Scale: 1° = {result.minutes_per_degree:.4f} min ({result.seconds_per_degree:.1f} seconds)  |  "
            f"Total Duration: {result.total_minutes:.1f} minutes = 360°"
        )

        if mode_key == "SOLAR":
            doy = d.timetuple().tm_yday
            eot = equation_of_time(doy)
            metrics_text += f"\nEquation of Time (EoT): {eot:+.2f} minutes  |  Longitude Lag: +38.7 minutes (Mumbai 72.825° E vs 82.5° E IST)"

        self.summary_metrics.configure(text=metrics_text)

        # Clear and Populate Treeview
        self.tree.delete(*self.tree.get_children())
        custom_set = set(custom_degs)

        for pt in result.harmonic_points:
            deg_str = f"{pt.degree:g}°"
            left_str = pt.time_left.strftime("%H:%M:%S IST")
            right_str = pt.time_right.strftime("%H:%M:%S IST")
            
            if pt.degree in custom_set:
                importance = "Custom Asked"
                tag = "custom"
            elif pt.is_major:
                importance = "Major Harmonic"
                tag = "major"
            else:
                importance = "Sub-Harmonic"
                tag = "minor"

            self.tree.insert(
                "",
                "end",
                values=(deg_str, left_str, right_str, pt.label, importance),
                tags=(tag,),
            )

    def _export_csv(self) -> None:
        if not self.current_result:
            messagebox.showinfo("Export", "No data to export.")
            return

        filename = f"Gann_Midpoint_{self.current_result.mode_name}_{self.current_result.session_date.isoformat()}.csv"
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            initialfile=filename,
        )
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Gann Midpoint Harmonics Report"])
            w.writerow(["Mode", self.current_result.description])
            w.writerow(["Date", self.current_result.session_date.isoformat()])
            w.writerow(["Midpoint (0 deg)", self.current_result.midpoint_time.strftime("%H:%M:%S IST")])
            w.writerow(["Minutes Per Degree", f"{self.current_result.minutes_per_degree:.4f}"])
            w.writerow(["Seconds Per Degree", f"{self.current_result.seconds_per_degree:.2f}"])
            w.writerow([])
            w.writerow(["Degree", "Left Time (-deg / Morning)", "Right Time (+deg / Afternoon)", "Significance", "Importance"])
            
            for item_id in self.tree.get_children():
                w.writerow(self.tree.item(item_id, "values"))

        messagebox.showinfo("Export Successful", f"Saved to {path}")


def main() -> None:
    app = GannMidpointApp()
    app.mainloop()


if __name__ == "__main__":
    main()
