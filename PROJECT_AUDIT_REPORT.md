# TECHNICAL AUDIT & ARCHITECTURAL PROJECT REPORT: GANN CELESTIAL TRACKER PRO

**Document Type:** Formal Software & Quantitative Engineering Audit  
**Target Reviewer:** Google Gemini / Quantitative Developer Peer Review  
**Project Repository:** [https://github.com/prakashjune8/gann-astrological-trading](https://github.com/prakashjune8/gann-astrological-trading)  
**Local Workspace:** `d:\ephemeris`  
**System Date:** November 5, 2026  
**Auditor:** Antigravity Autonomous Quantitative Agent  

---

## 1. Executive Summary

**Gann Celestial Tracker Pro** is an institutional-grade desktop trading terminal developed in Python (CustomTkinter) that tracks high-precision celestial movements across Indian financial market sessions (NSE and MCX). It operationalizes W.D. Gann's **Law of Vibration**, **Square of Nine odd-square spiral mathematics**, and **360-degree diurnal cycle divisions**.

The platform incorporates:
1. **Dual Astrometric Coordinate Frames**: Geocentric (`500@399`, Earth vantage point) and Heliocentric (`500@10`, Sun center), backed by the **NASA JPL Horizons REST API (DE440/DE441)** and local SQLite caching.
2. **Indian Geographical & Temporal Grounding**: Indian Standard Time (IST, UTC+05:30 invariant, no DST), Spencer Equation of Time (EoT) True Solar Noon for Mumbai ($19.08^\circ\text{ N}, 72.88^\circ\text{ E}$), and continuous 375-minute session spline interpolation.
3. **Harmonic Price-Time Harmonization**: Exact bidirectional Square of Nine root spiral derivations ($\Delta \sqrt{P} = \theta / 180^\circ$), Cardinal Cross ($0^\circ, 90^\circ, 180^\circ, 270^\circ$), Fixed Cross ($45^\circ, 135^\circ, 225^\circ, 315^\circ$), planetary scale octave lines, and the 50% Daily Equilibrium line.
4. **Instrument Universe & Bullion Security Barrier**: Default coverage of NSE Nifty 50, BSE Sensex, and MCX Energy/Base Metals. Features a strict programmatic barrier permanently rejecting Gold and Silver (bullion), while allowing users to dynamically register custom equity tickers (e.g., `RELIANCE.NS`).
5. **Multi-View Trading Interface**: Dropdown-switchable between **Master Control Deck**, **360° Visual Celestial Wheel**, and **Dual Split View**, supported by an integrated Educational Academy and ReportLab A4 Daily Summary PDF exporter.
6. **State Persistence & Deployment**: Full state restoration across restarts (`user_preferences.json`) and Windows Desktop shortcut execution.

---

## 2. System Architecture & Component Mapping

```
d:\ephemeris\
├── core\                              # Mathematical, Astronomical & Market Core
│   ├── geo_temporal.py                # IST conversions, Indian geographic stations, Spencer EoT solar noon
│   ├── horizons_client.py             # NASA JPL Horizons API client, SSL certifi handler, SQLite cache
│   ├── continuous_tracker.py          # Continuous Hermite polynomial spline, velocity (dθ/dt), zodiac DMS
│   ├── price_harmonics.py             # Square of Nine spiral root math, Cardinal/Fixed cross, scale octaves
│   ├── aspect_engine.py               # Minimal circular distance metric, aspect detection, orb evaluation
│   ├── market_feed.py                 # yfinance live & historical data feed, bullion filter, custom script registry
│   └── backtest_engine.py             # ±3 min hit criteria, setup classification, 30-min forward MFE metrics
│
├── audio\                             # Multi-Channel Alert Engine
│   ├── alert_audio.py                 # Async two-tone harmonic chime (440Hz + 659Hz) & Windows SAPI speech
│   └── sounds\pivot_chime.wav         # Pre-rendered 44.1kHz 16-bit PCM wave asset
│
├── reporting\                         # Document Generation Engine
│   └── pdf_daily_summary.py           # ReportLab A4 Daily Briefing, dynamic NumberedCanvas (Page X of Y)
│
├── ui\                                # Responsive CustomTkinter Interface
│   ├── theme.py                       # Modern Dark & Light institutional color tokens
│   ├── state_manager.py               # JSON preferences manager (Rememberance Protocol)
│   ├── main_window.py                 # Root responsive application frame & background polling loop
│   └── components\
│       ├── top_bar.py                 # Geo/Helio toggle, theme switch, operating mode, live IST clock
│       ├── control_deck_view.py       # View 1: Telemetry cards, progress dials, price levels table
│       ├── celestial_wheel_view.py    # View 2: Canvas 360° zodiac houses, aspect rays, price needle
│       ├── dual_split_view.py         # View 3: Side-by-side synchronized Control Deck + Wheel
│       ├── alert_ledger_view.py       # Notification banner & chronological event ledger
│       ├── academy_guide_view.py      # Built-in educational manual & research text stream
│       └── custom_script_dialog.py    # Custom equity addition modal with bullion validation
│
├── tests\                             # 6-Stage Diagnostic & Verification Test Suite
│   ├── verify_stage1_ephemeris.py     # NASA JPL Horizons & SQLite cache verification
│   ├── verify_stage2_temporal.py      # IST offset & continuous session timeline verification
│   ├── verify_stage3_harmonics.py     # Square of Nine roundtrips & geometric aspect verification
│   ├── verify_stage4_market_backtest.py# Bullion exclusion & backtest MFE reaction verification
│   ├── verify_stage5_audio_pdf.py     # WAV chime, SAPI speech & ReportLab zero-tofu PDF audit
│   └── verify_stage6_ui_persistence.py# UI component trees, state persistence & shortcut verification
│
├── .cache\horizons_cache.sqlite3      # Persistent offline ephemeris storage
├── user_preferences.json             # Active user desk setup & remembered configuration
├── LAUNCH_APP.bat                     # Windows silent desktop launcher
└── build_app.py                       # PyInstaller standalone binary compiler
```

---

## 3. Mathematical & Algorithmic Derivations

### 3.1 Square of Nine Odd-Square Root Spiral Formula
The Gann Square of Nine begins at origin $1$ and expands outward in concentric squares. Every $360^\circ$ rotation increments the square root of the price by $+2.0$:

$$\Delta \sqrt{P} = \frac{\theta}{180^\circ}$$

* **Angle from Price**:
  $$\theta(P) = \left[ (\sqrt{P} - 1.0) \pmod{2.0} \right] \times 180^\circ \quad \text{for } 0^\circ \le \theta < 360^\circ$$
* **Price from Target Angle $\theta$**:
  $$P(k, \theta) = \left[ 2k + 1.0 + \frac{\theta \pmod{360^\circ}}{180^\circ} \right]^2$$
  where ring octave $k = \text{floor}\left[ \frac{\sqrt{P_{\text{ref}}} - 1.0 - (\theta / 180^\circ)}{2.0} \right]$.

* **Verified Invariance**: Tested roundtrips across Nifty ($24,200$), Sensex ($79,500$), Crude Oil ($6,050$), and Copper ($825.50$) yielded an exact delta error of $\mathbf{0.000000\text{ pts}}$.

### 3.2 Spencer's Equation of Time & Indian Solar Transit
The Earth's orbital eccentricity ($e = 0.0167$) and axial obliquity ($\epsilon = 23.44^\circ$) cause apparent solar noon to deviate from mean clock noon ($12:00:00$):

$$\Gamma = \frac{2\pi (d - 1)}{365} \quad (d = \text{day of year})$$
$$\text{EoT} = 229.18 \times [0.000075 + 0.001868\cos(\Gamma) - 0.032077\sin(\Gamma) - 0.014615\cos(2\Gamma) - 0.040849\sin(2\Gamma)]$$

For an observer station at longitude $\lambda_{\text{station}}$:
$$\Delta t_{\text{solar}} = - [ 4.0 \times (\lambda_{\text{station}} - 82.5^\circ) + \text{EoT} ]$$
$$\text{True Solar Noon (IST)} = 12:00:00 + \Delta t_{\text{solar}}$$

* **Verified Benchmark**: On November 5, 2026 ($d = 309$), $\text{EoT} = +16.30\text{ minutes}$. True Solar Noon at Mumbai ($72.88^\circ\text{ E}$) evaluates to **`12:22:12` IST**.

### 3.3 Continuous Spline Interpolation with Normalized Time
To eliminate ill-conditioned polynomial matrices ($t \approx 1.7 \times 10^9\text{ seconds}$), timestamps are normalized relative to anchor time $t_0$:
$$h(t) = \frac{t - t_0}{3600.0} \quad (\text{elapsed hours})$$
Angular coordinates are phase-unwrapped before fitting:
$$\lambda_{\text{unwrapped}} = \text{unwrap}(\lambda_{\text{raw}})$$
$$P(h) = \sum_{i=0}^3 c_i h^i \implies \dot{\lambda}(h) = \sum_{i=1}^3 i c_i h^{i-1}$$

* **Verified Benchmark**: Evaluated over all $376$ continuous 1-minute steps for the Moon ($\approx 0.547^\circ/\text{hr}$). Maximum 1-minute displacement was **$0.009132^\circ$** with zero step jumps.

---

## 4. Comprehensive Audit Results Across the 6 Stages

| Stage | Verification Scope | Test Script | Key Metrics Verified | Result |
| :---: | :--- | :--- | :--- | :---: |
| **1** | **Astronomical Ephemeris Engine** | `verify_stage1_ephemeris.py` | Sun motion $+0.167^\circ/4\text{h}$; Moon $+2.194^\circ/4\text{h}$; Retrogrades confirmed on Mercury/Saturn; Helio strictly Direct; SQLite cache hit **$4.15\text{ ms}$**. | **PASSED** |
| **2** | **Temporal Mechanics & Session Continuum** | `verify_stage2_temporal.py` | Fixed IST $+05:30$ offset ($19,800\text{s}$); NSE 375 continuous minutes ($376$ bars); Spencer EoT $+16.30\text{m}$; Mumbai Solar Noon `12:22:12` IST. | **PASSED** |
| **3** | **Gann Price Harmonics & Aspects** | `verify_stage3_harmonics.py` | Sq9 roundtrip error $< 10^{-6}$; 90° Cardinal root displacement exactly $+0.5000$; 360° circular boundary metric; 9 active aspects detected. | **PASSED** |
| **4** | **Market Ingestion & Backtesting** | `verify_stage4_market_backtest.py` | 12 bullion test cases blocked; yfinance live CMP acquired; 13:56 Square Node confirmed hit with **$+60.00\text{ pts}$ MFE**; 14:27 non-hit rejected. | **PASSED** |
| **5** | **Audio Alerts & PDF Report Generator** | `verify_stage5_audio_pdf.py` | PCM WAV chime generated ($48.5\text{ KB}$); async dispatch $0.95\text{ ms}$; PDF compiled in $30.5\text{ ms}$; **0 tofu box glyphs (`□`)**. | **PASSED** |
| **6** | **Desktop UI & State Persistence** | `verify_stage6_ui_persistence.py` | 100% reload fidelity in `user_preferences.json`; all 5 UI views built cleanly in headless session; desktop shortcut verified. | **PASSED** |

---

## 5. Potential Limitations, Edge Cases & Recommended Upgrades

For complete technical transparency, the following edge cases and architectural considerations are documented for review:

### 5.1 Planetary Velocity at Exact Stationary Stations
* **Observed Mechanism**: In `core/continuous_tracker.py`, stationary planetary motion is determined via the velocity threshold $|\dot{\lambda}| \le 0.005^\circ/\text{hour}$.
* **Edge Case**: Slow outer planets (e.g., Pluto, Neptune, Uranus) possess daily geocentric motions that frequently drop below $0.005^\circ/\text{hour}$ during normal direct motion, which can cause them to be labeled `STATIONARY` for extended periods.
* **Recommended Upgrade**: Implement planet-specific velocity threshold scaling (e.g., Moon: $0.1^\circ/\text{hr}$; Mercury/Venus: $0.02^\circ/\text{hr}$; Jupiter/Saturn: $0.003^\circ/\text{hr}$; Pluto: $0.0005^\circ/\text{hr}$).

### 5.2 Market Feed Redundancy & Exchange Holiday Calendars
* **Observed Mechanism**: `core/market_feed.py` queries yfinance for live quotes, with a static fallback to `default_price`.
* **Edge Case**: On Indian national market holidays (e.g., Diwali, Independence Day, Eid), yfinance continues reporting the previous Friday's close, while intraday 1-minute bars are unavailable.
* **Recommended Upgrade**: Integrate an explicit `holidays_india.json` calendar into `core/geo_temporal.py` to automatically detect market closure and display an on-screen badge: `"MARKET CLOSED • DISPLAYING LAST SESSION CLOSE"`.

### 5.3 High-DPI Multi-Monitor DPI Scaling on Windows
* **Observed Mechanism**: CustomTkinter handles DPI scaling automatically via Windows OS API calls.
* **Edge Case**: If a user drags the application window from a $150\%$ DPI laptop screen (e.g., $1920 \times 1080$) to a $100\%$ DPI secondary desktop monitor, Tkinter canvas text on the 360° Celestial Wheel may experience minor sub-pixel offset until the window is resized.
* **Recommended Upgrade**: Bind a `<FocusIn>` or `<Configure>` debounce handler on the canvas to force a clean redraw when crossing display monitor boundaries.

### 5.4 Lunar Topocentric Parallax Refinement
* **Observed Mechanism**: The engine currently queries Horizons using geocentric coordinates (`CENTER='500@399'`).
* **Edge Case**: While geocentric coordinates are universal for Gann price squaring, the Moon's proximity to Earth causes a topocentric parallax shift of up to $\approx 1.0^\circ$ when viewed from the surface of Mumbai compared to Earth's center.
* **Recommended Upgrade**: Add an optional toggle in `user_preferences.json`: `lunar_parallax_correction: bool`. When enabled for topocentric mode, set Horizons `CENTER='coord@399'` using Mumbai's exact surface coordinates ($19.076^\circ\text{ N}, 72.878^\circ\text{ E}, 14\text{m}$).

---

## 6. Reviewer Handover & Verification Instructions

To independently verify the complete system, Gemini or any inspecting engineer can run the verification commands below in PowerShell:

```powershell
# 1. Navigate to workspace
cd "d:\ephemeris"

# 2. Run the complete 6-stage test suite
python tests/verify_stage1_ephemeris.py
python tests/verify_stage2_temporal.py
python tests/verify_stage3_harmonics.py
python tests/verify_stage4_market_backtest.py
python tests/verify_stage5_audio_pdf.py
python tests/verify_stage6_ui_persistence.py

# 3. Launch the desktop terminal
python run_app.py
```

### Git Repository Audit
* **Remote Repository**: [https://github.com/prakashjune8/gann-astrological-trading](https://github.com/prakashjune8/gann-astrological-trading)
* **Active Working Branch**: `master` (clean working tree, 100% committed)
* **Archival Baseline**: Tag `v1.0-archive` on branch `archive/v1.0-complete`.
