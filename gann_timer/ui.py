"""Desktop UI (CustomTkinter) – inputs, IST Gann timeline, ephemeris viewer."""
from __future__ import annotations

import csv
import math
import os
import shutil
import threading
import tkinter as tk
from datetime import date, datetime
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from . import config
from .analysis import AnalysisRequest, AnalysisResult, AnalysisService
from .gann_engine import AnalysisSettings, fmt_zodiac, wrap180
from .instruments import INSTRUMENT_CHOICES
from .timeconv import IST, ist_to_ut, ut_to_ist

TIMELINE_COLS = [
    ("ist", "Exact Time (IST)", 150), ("day", "Day", 45), ("event", "Gann Celestial Trigger", 330),
    ("type", "Type", 115), ("strength", "Strength", 70), ("score", "Score", 50),
    ("session", "Session", 120), ("entry", "Actionable Entry (IST)", 150),
    ("sup", "Sq9 Support", 90), ("res", "Sq9 Resistance", 95),
    ("segment", "Segment", 170), ("symbols", "Instruments", 300), ("notes", "Notes", 260),
]
STRENGTH_MIN = {"All": 0.0, "Medium + High": 4.5, "High only": 7.0}
DEFAULT_ON = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto")


class GannApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title(config.APP_TITLE)
        self.geometry("1500x880")
        self.minsize(1150, 700)
        self.service = AnalysisService()
        self.result: AnalysisResult | None = None
        self._rows_by_iid: dict[str, object] = {}
        self._style_tree()
        self._build_sidebar()
        self._build_main()

    # ----------------------------------------------------------------- style --
    def _style_tree(self) -> None:
        st = ttk.Style(self)
        st.theme_use("clam")
        st.configure("Treeview", background="#1f2329", fieldbackground="#1f2329",
                     foreground="#e6e6e6", rowheight=24, borderwidth=0, font=("Segoe UI", 10))
        st.configure("Treeview.Heading", background="#2b313a", foreground="#f0f0f0",
                     font=("Segoe UI Semibold", 10), relief="flat")
        st.map("Treeview", background=[("selected", "#1f6aa5")])

    # --------------------------------------------------------------- sidebar --
    def _build_sidebar(self) -> None:
        sb = ctk.CTkScrollableFrame(self, width=320, corner_radius=0)
        sb.pack(side="left", fill="y")
        self.sidebar = sb

        def header(text):
            ctk.CTkLabel(sb, text=text, font=ctk.CTkFont(size=14, weight="bold"),
                         anchor="w").pack(fill="x", padx=12, pady=(14, 4))

        ctk.CTkLabel(sb, text="☉ Gann Celestial Timer", font=ctk.CTkFont(size=20, weight="bold")).pack(
            padx=12, pady=(14, 0), anchor="w")
        ctk.CTkLabel(sb, text="NASA JPL Horizons • all times IST (UTC+05:30)",
                     text_color="gray70").pack(padx=12, anchor="w")

        header("1. Period (IST)")
        self.range_mode = tk.StringVar(value="year")
        row = ctk.CTkFrame(sb, fg_color="transparent"); row.pack(fill="x", padx=12)
        ctk.CTkRadioButton(row, text="Year", variable=self.range_mode, value="year",
                           command=self._toggle_range).pack(side="left")
        ctk.CTkRadioButton(row, text="Date range", variable=self.range_mode, value="range",
                           command=self._toggle_range).pack(side="left", padx=12)
        self.year_entry = ctk.CTkEntry(sb, placeholder_text="YYYY")
        self.year_entry.insert(0, str(date.today().year))
        self.year_entry.pack(fill="x", padx=12, pady=4)
        rng = ctk.CTkFrame(sb, fg_color="transparent"); rng.pack(fill="x", padx=12)
        self.start_entry = ctk.CTkEntry(rng, placeholder_text="Start YYYY-MM-DD", width=140)
        self.end_entry = ctk.CTkEntry(rng, placeholder_text="End YYYY-MM-DD", width=140)
        self.start_entry.insert(0, date.today().isoformat())
        self.end_entry.insert(0, date(date.today().year, 12, 31).isoformat())
        self.start_entry.pack(side="left"); self.end_entry.pack(side="right")
        self._toggle_range()

        header("2. Target instrument")
        self.instrument = ctk.CTkOptionMenu(sb, values=list(INSTRUMENT_CHOICES))
        self.instrument.set("Index (NSE/BSE)")
        self.instrument.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(sb, text="⛔ Gold & Silver are permanently excluded", text_color="#ff8a80",
                     anchor="w").pack(fill="x", padx=12)

        header("3. Celestial bodies")
        grid = ctk.CTkFrame(sb, fg_color="transparent"); grid.pack(fill="x", padx=12)
        self.body_vars: dict[str, tk.BooleanVar] = {}
        for i, b in enumerate(config.BODIES):
            v = tk.BooleanVar(value=b in DEFAULT_ON)
            self.body_vars[b] = v
            ctk.CTkCheckBox(grid, text=f"{config.GLYPHS[b]} {b}", variable=v, width=140).grid(
                row=i // 2, column=i % 2, sticky="w", pady=2)

        header("4. Gann factors")
        self.opt = {}
        for key, text, default in [
            ("phases", "Lunar phases (New/Full/Quarters)", True),
            ("ingress", "Sign ingresses (cardinal weighted)", True),
            ("stations", "Retrograde / direct stations", True),
            ("octiles", "Gann 1/8 harmonics (45°, 135°)", False),
            ("moon_aspects", "Moon aspects to planets (many)", False),
            ("rulers", "MCX rulership relevance filter", True),
            ("live", "Only triggers inside live session", False),
        ]:
            v = tk.BooleanVar(value=default)
            self.opt[key] = v
            ctk.CTkCheckBox(sb, text=text, variable=v).pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(sb, text="Minimum strength", anchor="w").pack(fill="x", padx=12, pady=(6, 0))
        self.min_strength = ctk.CTkOptionMenu(sb, values=list(STRENGTH_MIN))
        self.min_strength.set("Medium + High")
        self.min_strength.pack(fill="x", padx=12, pady=4)

        header("5. Price-time squaring (optional)")
        self.ref_price = ctk.CTkEntry(sb, placeholder_text="Reference price / LTP (e.g. 24350)")
        self.ref_price.pack(fill="x", padx=12, pady=3)
        self.pivot_dt = ctk.CTkEntry(sb, placeholder_text="Pivot IST  YYYY-MM-DD HH:MM")
        self.pivot_dt.pack(fill="x", padx=12, pady=3)
        self.pivot_price = ctk.CTkEntry(sb, placeholder_text="Pivot price (high/low)")
        self.pivot_price.pack(fill="x", padx=12, pady=3)

        self.run_btn = ctk.CTkButton(sb, text="Generate Gann Timeline", height=40,
                                     font=ctk.CTkFont(size=14, weight="bold"), command=self._on_generate)
        self.run_btn.pack(fill="x", padx=12, pady=(16, 6))
        ctk.CTkButton(sb, text="Export timeline CSV", fg_color="#3a3f47",
                      command=self._export_timeline).pack(fill="x", padx=12, pady=3)
        ctk.CTkButton(sb, text="Export ephemeris CSV", fg_color="#3a3f47",
                      command=self._export_ephemeris).pack(fill="x", padx=12, pady=3)
        ctk.CTkButton(sb, text="Edit exchange holidays", fg_color="#3a3f47",
                      command=self._edit_holidays).pack(fill="x", padx=12, pady=3)
        ctk.CTkButton(sb, text="Clear Horizons cache", fg_color="#3a3f47",
                      command=self._clear_cache).pack(fill="x", padx=12, pady=(3, 16))

    def _toggle_range(self) -> None:
        year = self.range_mode.get() == "year"
        self.year_entry.configure(state="normal" if year else "disabled")
        for e in (self.start_entry, self.end_entry):
            e.configure(state="disabled" if year else "normal")

    # ------------------------------------------------------------------ main --
    def _build_main(self) -> None:
        main = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        main.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        self.tabs = ctk.CTkTabview(main)
        self.tabs.pack(fill="both", expand=True)
        t1 = self.tabs.add("Gann Timeline (IST)")
        t2 = self.tabs.add("Ephemeris (IST)")
        t3 = self.tabs.add("Methodology")

        # timeline
        paned = tk.PanedWindow(t1, orient="vertical", sashwidth=6, bg="#2b2b2b", bd=0)
        paned.pack(fill="both", expand=True)
        top = tk.Frame(paned, bg="#1f2329")
        self.timeline = self._make_tree(top, TIMELINE_COLS)
        self.timeline.tag_configure("High", foreground="#ff6b6b")
        self.timeline.tag_configure("Medium", foreground="#ffd166")
        self.timeline.tag_configure("Low", foreground="#a0a0a0")
        self.timeline.bind("<<TreeviewSelect>>", self._on_select)
        self.detail = ctk.CTkTextbox(paned, height=170, font=("Consolas", 12))
        paned.add(top, stretch="always")
        paned.add(self.detail, height=180)

        # ephemeris
        bar = ctk.CTkFrame(t2, fg_color="transparent"); bar.pack(fill="x")
        ctk.CTkLabel(bar, text="Daily positions at 00:00 UT = 05:30 IST (Astrodienst baseline epoch)").pack(
            side="left", padx=6)
        self.eph_mode = ctk.CTkSegmentedButton(bar, values=["Longitude", "Declination", "Latitude"],
                                               command=lambda _v: self._fill_ephemeris())
        self.eph_mode.set("Longitude")
        self.eph_mode.pack(side="right", padx=6, pady=4)
        eph_frame = tk.Frame(t2, bg="#1f2329"); eph_frame.pack(fill="both", expand=True)
        cols = [("ist", "Date / Time (IST)", 150)] + [(b, f"{config.GLYPHS[b]} {b}", 105) for b in config.BODIES]
        self.eph_tree = self._make_tree(eph_frame, cols)

        # methodology
        txt = ctk.CTkTextbox(t3, wrap="word", font=("Segoe UI", 13))
        txt.pack(fill="both", expand=True)
        txt.insert("end", METHODOLOGY)
        txt.configure(state="disabled")

        # status bar
        sbar = ctk.CTkFrame(main, height=28); sbar.pack(fill="x", pady=(6, 0))
        self.status = ctk.CTkLabel(sbar, text="Ready – select a period and instrument, then Generate.",
                                   anchor="w")
        self.status.pack(side="left", fill="x", expand=True, padx=8)
        self.progress = ctk.CTkProgressBar(sbar, mode="indeterminate", width=180)
        self.progress.pack(side="right", padx=8)
        self.progress.set(0)

    @staticmethod
    def _make_tree(parent, cols) -> ttk.Treeview:
        tree = ttk.Treeview(parent, columns=[c[0] for c in cols], show="headings")
        for key, text, width in cols:
            tree.heading(key, text=text)
            tree.column(key, width=width, minwidth=40, stretch=False, anchor="w")
        ys = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        xs = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        tree.grid(row=0, column=0, sticky="nsew"); ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        parent.grid_rowconfigure(0, weight=1); parent.grid_columnconfigure(0, weight=1)
        return tree

    # ------------------------------------------------------------- actions --
    def _set_status(self, msg: str) -> None:
        self.after(0, lambda: self.status.configure(text=msg))

    @staticmethod
    def _float(entry) -> float | None:
        s = entry.get().strip().replace(",", "")
        return float(s) if s else None

    def _build_request(self) -> AnalysisRequest:
        if self.range_mode.get() == "year":
            y = int(self.year_entry.get().strip())
            if not 1 <= y <= 9998:
                raise ValueError("Year must be between 1 and 9998.")
            start, end = date(y, 1, 1), date(y, 12, 31)
        else:
            start = date.fromisoformat(self.start_entry.get().strip())
            end = date.fromisoformat(self.end_entry.get().strip())
        if end < start:
            raise ValueError("End date is before start date.")
        bodies = [b for b, v in self.body_vars.items() if v.get()]
        if len(bodies) < 1:
            raise ValueError("Select at least one celestial body.")
        pivot_ut = None
        if self.pivot_dt.get().strip():
            p = datetime.strptime(self.pivot_dt.get().strip(), "%Y-%m-%d %H:%M").replace(tzinfo=IST)
            pivot_ut = ist_to_ut(p).replace(tzinfo=None)
        settings = AnalysisSettings(
            bodies=bodies,
            include_octiles=self.opt["octiles"].get(),
            include_moon_aspects=self.opt["moon_aspects"].get(),
            include_lunar_phases=self.opt["phases"].get(),
            include_ingresses=self.opt["ingress"].get(),
            include_stations=self.opt["stations"].get(),
            pivot_ut=pivot_ut,
            pivot_price=self._float(self.pivot_price),
            reference_price=self._float(self.ref_price),
            min_score=STRENGTH_MIN[self.min_strength.get()],
        )
        return AnalysisRequest(start, end, self.instrument.get(), settings,
                               rulership_filter=self.opt["rulers"].get(), live_only=self.opt["live"].get())

    def _on_generate(self) -> None:
        try:
            req = self._build_request()
        except ValueError as exc:
            messagebox.showerror("Invalid input", str(exc))
            return
        self.run_btn.configure(state="disabled")
        self.progress.start()

        def work():
            try:
                res = self.service.run(req, progress=self._set_status)
                self.after(0, lambda: self._show_result(res))
            except Exception as exc:  # surface any network/API error to the user
                msg = str(exc)
                self.after(0, lambda: self._fail(msg))

        threading.Thread(target=work, daemon=True).start()

    def _fail(self, msg: str) -> None:
        self.progress.stop(); self.run_btn.configure(state="normal")
        self.status.configure(text="Error – see dialog.")
        messagebox.showerror("Analysis failed", msg)

    def _show_result(self, res: AnalysisResult) -> None:
        self.progress.stop(); self.progress.set(0); self.run_btn.configure(state="normal")
        self.result = res
        self.timeline.delete(*self.timeline.get_children())
        self._rows_by_iid.clear()
        for r in res.triggers:
            ev = r.event
            vals = (
                r.ist_time.strftime("%Y-%m-%d %H:%M"), r.ist_time.strftime("%a"), ev.title, ev.kind,
                ev.strength, f"{ev.score:.1f}", r.session_status,
                r.actionable_ist.strftime("%Y-%m-%d %H:%M"),
                "" if math.isnan(r.sq9_support) else f"{r.sq9_support:,.2f}",
                "" if math.isnan(r.sq9_resistance) else f"{r.sq9_resistance:,.2f}",
                r.segment.label, ", ".join(r.symbols), r.notes,
            )
            iid = self.timeline.insert("", "end", values=vals, tags=(ev.strength,))
            self._rows_by_iid[iid] = r
        self._fill_ephemeris()
        n_hi = sum(1 for r in res.triggers if r.event.strength == "High")
        self.status.configure(
            text=f"{len(res.triggers)} triggers ({n_hi} high) • {len(res.ephemeris.times)} Horizons samples "
                 f"@ {res.ephemeris.step_hours}h • source: NASA JPL Horizons (DE441)")
        self.tabs.set("Gann Timeline (IST)")

    def _fill_ephemeris(self) -> None:
        self.eph_tree.delete(*self.eph_tree.get_children())
        if not self.result:
            return
        eph, mode = self.result.ephemeris, self.eph_mode.get()
        for i, t in enumerate(eph.times):
            if t.hour or t.minute:
                continue  # daily rows at 00:00 UT
            row = [ut_to_ist(t).strftime("%Y-%m-%d %H:%M")]
            for b in config.BODIES:
                s = eph.bodies.get(b)
                if not s:
                    row.append("–"); continue
                if mode == "Longitude":
                    nxt = s.lon[min(i + 1, len(s.lon) - 1)]
                    rx = " R" if wrap180(nxt - s.lon[i]) < 0 else ""
                    row.append(fmt_zodiac(s.lon[i]) + rx)
                elif mode == "Declination":
                    row.append(f"{s.dec[i]:+.3f}°")
                else:
                    row.append(f"{s.lat[i]:+.3f}°")
            self.eph_tree.insert("", "end", values=row)

    def _on_select(self, _evt=None) -> None:
        sel = self.timeline.selection()
        if not sel:
            return
        r = self._rows_by_iid.get(sel[0])
        if not r:
            return
        ev = r.event
        lines = [
            f"{ev.title}",
            f"Exact: {r.ist_time:%A %d %b %Y %H:%M} IST   (UT {ev.time_ut:%Y-%m-%d %H:%M})",
            f"Gann implication: {ev.implication}   |   Strength {ev.strength} ({ev.score:.1f}/10)",
            f"Session: {r.session_status}  →  actionable from {r.actionable_ist:%a %d %b %H:%M} IST",
            f"Key degree for Square of Nine: {ev.key_degree:.3f}° ({fmt_zodiac(ev.key_degree)})",
        ]
        if not math.isnan(r.sq9_support):
            lines.append(f"Sq9 levels near reference: support {r.sq9_support:,.2f} / resistance {r.sq9_resistance:,.2f}")
        lines.append("Positions at trigger: " + "  ".join(
            f"{config.GLYPHS[b]}{fmt_zodiac(l)}" for b, l in ev.positions.items()))
        lines.append(f"Instruments: {', '.join(r.symbols)}")
        self.detail.delete("1.0", "end")
        self.detail.insert("end", "\n".join(lines))

    def _export_timeline(self) -> None:
        if not self.result:
            return messagebox.showinfo("Nothing to export", "Generate a timeline first.")
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            initialfile="gann_timeline_ist.csv")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow([c[1] for c in TIMELINE_COLS] + ["UT"])
            for iid in self.timeline.get_children():
                w.writerow(list(self.timeline.item(iid, "values")) +
                           [self._rows_by_iid[iid].event.time_ut.strftime("%Y-%m-%d %H:%M")])
        self.status.configure(text=f"Exported {path}")

    def _export_ephemeris(self) -> None:
        if not self.result:
            return messagebox.showinfo("Nothing to export", "Generate a timeline first.")
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            initialfile="horizons_ephemeris_ist.csv")
        if not path:
            return
        eph = self.result.ephemeris
        names = list(eph.bodies)
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["UT", "IST"] + [f"{b}_{q}" for b in names for q in ("lon", "lat", "ra", "dec")])
            for i, t in enumerate(eph.times):
                row = [t.strftime("%Y-%m-%d %H:%M"), ut_to_ist(t).strftime("%Y-%m-%d %H:%M")]
                for b in names:
                    s = eph.bodies[b]
                    row += [f"{s.lon[i]:.6f}", f"{s.lat[i]:.6f}", f"{s.ra[i]:.6f}", f"{s.dec[i]:.6f}"]
                w.writerow(row)
        self.status.configure(text=f"Exported {path}")

    def _edit_holidays(self) -> None:
        path = self.service.calendar.path
        if not path.exists():
            path.write_text('{"NSE": [], "MCX": []}', encoding="utf-8")
        try:
            os.startfile(path)  # type: ignore[attr-defined]
        except AttributeError:
            messagebox.showinfo("Holidays file", str(path))

    def _clear_cache(self) -> None:
        shutil.rmtree(config.cache_dir(), ignore_errors=True)
        config.cache_dir()
        self.status.configure(text="Horizons cache cleared.")


METHODOLOGY = """GANN CELESTIAL TIMER – METHODOLOGY

DATA SOURCE
• NASA JPL Horizons API (ssd.jpl.nasa.gov/api/horizons.api), geocentric (500@399), apparent ecliptic
  longitude/latitude of date (quantity 31) and apparent RA/declination (quantity 2). Any year 1–9998 can be requested;
  results are cached locally. This supersedes the static 2026 Astrodienst tables (00:00 UT), which the Ephemeris tab
  reproduces at 00:00 UT = 05:30 IST for cross-checking.

TIME
• Horizons UT is converted to IST = UTC + 05:30 (no daylight saving). Exact event instants are interpolated between
  hourly samples (minute accuracy).
• NSE/BSE indices & Nifty options: 09:15–15:30 IST. MCX energy/base metals: 09:00–23:30 IST (US DST) or 23:55 IST.
  Out-of-session events are mapped to the next session open. Add exchange holidays via “Edit exchange holidays”.

GANN FACTORS
• Major aspects: conjunction 0°, square 90°/270°, trine 120°/240°, opposition 180° (optional 45°/135° harmonics).
• Ingresses (cardinal 0° Aries/Cancer/Libra/Capricorn weighted), retrograde/direct stations, lunar phases.
• Score = aspect weight × planetary weight (slow planets and the Sun dominate). Windows: ±1 day (fast), ±2 (Mars), ±3 (outer).
• Square of Nine: degree d ↔ price P = (2k + d/180)². Support/resistance are the rungs bracketing your reference price.
• Price-time square: planet transits (price mod 360)°. Time-from-pivot: Sun +90/120/180/240/270/360° from pivot.

INSTRUMENTS
• NSE & BSE broad indices, NSE Nifty 50 options, MCX energy and MCX base metals.
• GOLD AND SILVER ARE EXCLUDED at configuration, routing and output layers.

DISCLAIMER
Gann astro-timing is a speculative, unproven technique. Triggers are research windows, not buy/sell signals.
Always confirm with price action and risk management. This tool is not investment advice.
"""


def main() -> None:
    app = GannApp()
    app.mainloop()
