"""Standalone Desktop Application: Gann Midpoint Harmonics Calculator with Method Selection."""
from __future__ import annotations

import csv
from datetime import date, datetime, time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from gann_timer.midpoint_engine import (
    analyze_midpoints_v2,
    MIDPOINT_METHODS,
    MidpointAnalysisResult,
    calculate_mumbai_solar_noon,
    equation_of_time,
)

COLUMNS = [
    ("degree", "Degree (°)", 90),
    ("left", "Left Time (-θ Past/Ascending)", 210),
    ("right", "Right Time (+θ Future/Descending)", 210),
    ("desc", "Gann Harmonic Significance", 330),
    ("category", "Importance", 120),
]


class GannMidpointApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title("Gann Midpoint & 360° Time Harmonics – Indian Markets")
        self.geometry("1220x820")
        self.minsize(1050, 680)

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
            text="Selectable Midpoint Calculation Methods • NSE • BSE • MCX • Astronomical Solar Noon",
            font=ctk.CTkFont(size=12),
            text_color="gray70",
        ).pack(anchor="w")

    def _build_controls(self) -> None:
        ctrl = ctk.CTkFrame(self, fg_color="#23272e", corner_radius=8)
        ctrl.pack(fill="x", padx=16, pady=(12, 6))

        # Row 1: Method Selector Menu
        r1 = ctk.CTkFrame(ctrl, fg_color="transparent")
        r1.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(r1, text="Calculation Method:", font=ctk.CTkFont(size=13, weight="bold"), text_color="#e5c07b").pack(side="left", padx=(0, 8))
        
        self.method_labels = [m["name"] for m in MIDPOINT_METHODS.values()]
        self.method_keys = list(MIDPOINT_METHODS.keys())
        
        self.method_var = ctk.StringVar(value=self.method_labels[0])
        self.method_menu = ctk.CTkOptionMenu(
            r1,
            variable=self.method_var,
            values=self.method_labels,
            command=self._on_method_change,
            width=540,
        )
        self.method_menu.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(r1, text="Date:", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=(0, 6))
        self.date_entry = ctk.CTkEntry(r1, width=120)
        self.date_entry.insert(0, date.today().isoformat())
        self.date_entry.pack(side="left", padx=(0, 8))

        ctk.CTkButton(r1, text="Today", width=60, command=self._set_today, fg_color="#3a3f47").pack(side="left")

        # Row 2: Dynamic Contextual Parameters (Custom Time or Price)
        self.r2 = ctk.CTkFrame(ctrl, fg_color="transparent")
        self.r2.pack(fill="x", padx=12, pady=(4, 6))

        self.custom_time_label = ctk.CTkLabel(self.r2, text="Custom Anchor Time (HH:MM):")
        self.custom_time_entry = ctk.CTkEntry(self.r2, width=90, placeholder_text="12:00")
        self.custom_time_entry.insert(0, "12:00")

        self.scale_label = ctk.CTkLabel(self.r2, text="Time Scale:")
        self.scale_combo = ctk.CTkOptionMenu(
            self.r2,
            values=["NSE Session (1.04 min/deg)", "Solar Day (4.00 min/deg)", "Opening 1st Hr (10 sec/deg)"],
            width=210,
        )

        self.price_high_label = ctk.CTkLabel(self.r2, text="Day High:")
        self.price_high_entry = ctk.CTkEntry(self.r2, width=95, placeholder_text="24400")
        self.price_high_entry.insert(0, "24400")

        self.price_low_label = ctk.CTkLabel(self.r2, text="Day Low:")
        self.price_low_entry = ctk.CTkEntry(self.r2, width=95, placeholder_text="24200")
        self.price_low_entry.insert(0, "24200")

        self._update_contextual_inputs()

        # Row 3: Custom Degrees & Actions
        r3 = ctk.CTkFrame(ctrl, fg_color="transparent")
        r3.pack(fill="x", padx=12, pady=(4, 10))

        ctk.CTkLabel(r3, text="Custom Angles (° comma separated):", font=ctk.CTkFont(size=13)).pack(side="left", padx=(0, 6))
        self.custom_degrees_entry = ctk.CTkEntry(r3, placeholder_text="e.g. 22.5, 33, 67.5, 75", width=200)
        self.custom_degrees_entry.pack(side="left", padx=(0, 16))

        calc_btn = ctk.CTkButton(
            r3,
            text="Calculate Harmonics",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._calculate,
            width=165,
        )
        calc_btn.pack(side="left", padx=(0, 10))

        export_btn = ctk.CTkButton(
            r3,
            text="Export CSV",
            command=self._export_csv,
            width=110,
            fg_color="#3a3f47",
        )
        export_btn.pack(side="left")

    def _update_contextual_inputs(self) -> None:
        # Hide all conditional inputs first
        for widget in [
            self.custom_time_label, self.custom_time_entry, self.scale_label, self.scale_combo,
            self.price_high_label, self.price_high_entry, self.price_low_label, self.price_low_entry
        ]:
            widget.pack_forget()

        key = self._get_selected_method_key()
        if key == "CUSTOM_TIME":
            self.custom_time_label.pack(side="left", padx=(0, 6))
            self.custom_time_entry.pack(side="left", padx=(0, 16))
            self.scale_label.pack(side="left", padx=(0, 6))
            self.scale_combo.pack(side="left", padx=(0, 16))
        elif key == "PRICE_50":
            self.price_high_label.pack(side="left", padx=(0, 6))
            self.price_high_entry.pack(side="left", padx=(0, 14))
            self.price_low_label.pack(side="left", padx=(0, 6))
            self.price_low_entry.pack(side="left", padx=(0, 16))

    def _build_results_view(self) -> None:
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=16, pady=(4, 14))

        # Summary Banner
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

        # Table
        tbl_frame = tk.Frame(container, bg="#1f2329")
        tbl_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(tbl_frame, columns=[c[0] for c in COLUMNS], show="headings")
        for col_id, col_name, width in COLUMNS:
            self.tree.heading(col_id, text=col_name)
            self.tree.column(col_id, width=width, minwidth=60, anchor="w")

        self.tree.tag_configure("midpoint", foreground="#e06c75", font=("Segoe UI Semibold", 11))
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

    def _on_method_change(self, _choice: str) -> None:
        self._update_contextual_inputs()
        self._calculate()

    def _get_selected_method_key(self) -> str:
        idx = self.method_labels.index(self.method_var.get())
        return self.method_keys[idx]

    def _parse_custom_degrees(self) -> list[float]:
        raw = self.custom_degrees_entry.get().strip()
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

        method_key = self._get_selected_method_key()
        custom_degs = self._parse_custom_degrees()

        # Parse contextual values
        custom_t = None
        scale_mode = "SESSION_SCALE"
        hi_val = None
        lo_val = None

        if method_key == "CUSTOM_TIME":
            try:
                t_str = self.custom_time_entry.get().strip()
                h, m = t_str.split(":")
                custom_t = time(int(h), int(m))
            except Exception:
                custom_t = time(12, 0)

            scale_choice = self.scale_combo.get()
            if "Solar" in scale_choice:
                scale_mode = "SOLAR_4MIN"
            elif "Opening" in scale_choice:
                scale_mode = "OPENING_10SEC"
            else:
                scale_mode = "SESSION_SCALE"

        elif method_key == "PRICE_50":
            try:
                hi_val = float(self.price_high_entry.get().strip())
                lo_val = float(self.price_low_entry.get().strip())
            except Exception:
                hi_val, lo_val = 24400.0, 24200.0

        result = analyze_midpoints_v2(
            d=d,
            method_key=method_key,
            custom_time_val=custom_t,
            time_scale_mode=scale_mode,
            price_high=hi_val,
            price_low=lo_val,
            custom_degrees=custom_degs,
        )
        self.current_result = result

        # Update Banner
        mid_str = result.midpoint_time.strftime("%H:%M:%S IST")
        self.summary_title.configure(text=f"📌 {result.description}")

        metrics_text = (
            f"Exact Midpoint (0° Balance Axis): {mid_str}  |  "
            f"Cycle Scale: 1° = {result.minutes_per_degree:.4f} min ({result.seconds_per_degree:.1f} sec)  |  "
            f"Full Cycle (360°): {result.total_minutes:.1f} minutes"
        )

        if result.price_equilibrium is not None:
            metrics_text += f"\n50% Price Equilibrium: {result.price_equilibrium:.2f} pts  |  Day Range: {(result.price_high or 0) - (result.price_low or 0):.2f} pts"

        if method_key == "SOLAR_NOON":
            doy = d.timetuple().tm_yday
            eot = equation_of_time(doy)
            metrics_text += f"\nEquation of Time (EoT): {eot:+.2f} min  |  Meridian Offset: +38.7 min (Mumbai 72.825° E vs 82.5° E IST)"

        self.summary_metrics.configure(text=metrics_text)

        # Clear and Populate Table
        self.tree.delete(*self.tree.get_children())
        custom_set = set(custom_degs)

        for pt in result.harmonic_points:
            deg_str = f"{pt.degree:g}°"
            left_str = pt.time_left.strftime("%H:%M:%S IST")
            right_str = pt.time_right.strftime("%H:%M:%S IST")

            if pt.degree == 0.0:
                deg_str = "0° (MID)"
                left_str = f"★ {mid_str}"
                right_str = f"★ {mid_str}"
                importance = "MIDPOINT OF DAY"
                tag = "midpoint"
            elif pt.degree in custom_set:
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

        filename = f"Gann_Midpoint_{self.current_result.method_key}_{self.current_result.session_date.isoformat()}.csv"
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
            w.writerow(["Method", self.current_result.method_name])
            w.writerow(["Description", self.current_result.description])
            w.writerow(["Date", self.current_result.session_date.isoformat()])
            w.writerow(["Midpoint (0 deg)", self.current_result.midpoint_time.strftime("%H:%M:%S IST")])
            w.writerow(["Minutes Per Degree", f"{self.current_result.minutes_per_degree:.4f}"])
            w.writerow(["Seconds Per Degree", f"{self.current_result.seconds_per_degree:.2f}"])
            if self.current_result.price_equilibrium is not None:
                w.writerow(["Price Equilibrium (50%)", f"{self.current_result.price_equilibrium:.2f}"])
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
