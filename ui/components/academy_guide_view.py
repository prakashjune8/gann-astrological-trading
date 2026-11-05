"""Educational Academy & Research Guide View (In-Depth Foundations & Plain-Language Manual)."""
from __future__ import annotations

import customtkinter as ctk
from ui.theme import ThemeTokens

ACADEMY_TEXT = """
# W.D. GANN CELESTIAL & HARMONIC TRADING ACADEMY
## Plain-Language Research & Practical Application Manual for Indian Markets

Welcome to the internal research guide for Gann Celestial Tracker Pro. This guide breaks down the core concepts, mathematical derivations, and historical rules without confusing jargon.

---

### 1. The Law of Vibration & Planetary Market Connections

In December 1909, W.D. Gann declared in The Ticker and Investment Digest that stocks and commodities are not random, but act like vibrating atoms governed by exact mathematical harmonics.

How Planets Rule Specific Instruments:
1. Mars (The Red Planet):
   - Fundamental Archetype: Energy, heat, transformation, industrial metals.
   - Assigned Markets: MCX Energy (Crude Oil, Natural Gas) and MCX Base Metals (Copper, Zinc, Aluminium, Lead).
   - Practical Rule: Major trend changes in Crude Oil and Copper frequently coincide with Mars entering a new zodiac sign (Ingress), reversing direction (Retrograde Station), or squaring (90°) the Sun or Jupiter.

2. Moon & Mercury (The Fast Movers):
   - Fundamental Archetype: High-frequency oscillation, news, sentiment, communication.
   - Assigned Markets: Intraday Index Volatility (Nifty 50, Bank Nifty, Sensex).
   - Practical Rule: The Moon travels approximately 13.2° per day (about 0.55° per hour). As it crosses the 45°, 90°, and 180° harmonic aspects during the NSE 09:15 to 15:30 session, it creates rapid intraday pivot windows (often lasting ±15 minutes).

3. Sun & Jupiter (The Macro Anchors):
   - Fundamental Archetype: Vitality, expansion, banking credit, secular cycles.
   - Assigned Markets: Broad Indices & Long-term Support/Resistance.

---

### 2. Geocentric vs. Heliocentric Coordinates

Why does the app have a Global Toggle between Geocentric and Heliocentric?
- Geocentric (Earth-Centered):
  This is the sky as seen by an observer on Earth (or at the NSE servers in Mumbai). Because Earth moves while the other planets move, planets appear to slow down, stop (Station), and move backwards (Retrograde). Geocentric coordinates dictate earthly psychological sentiment and intraday turning points.
  
- Heliocentric (Sun-Centered):
  This is the true orbital physics of the solar system as viewed from the Sun. Planets NEVER move retrograde from the Sun; their motion is pure continuous forward cycles. Gann used Heliocentric cycles (especially the Jupiter-Saturn and Mars-Jupiter heliocentric conjunctions) as his "Master Time Factor" for major multi-year bull and bear cycles.

---

### 3. Price-to-Degree Harmonization (The Square of Nine)

How does a planetary degree (say, Mars at 140.7°) convert into a price like Nifty 24,200?

The Square of Nine Formula:
Gann laid out numbers in a concentric expanding spiral starting at 1. Every complete 360° rotation adds exactly +2.0 to the square root of the price:
  Δ√P = θ / 180°

To find the price matching a target planetary angle θ:
  P(k, θ) = [ 2k + 1.0 + (θ / 180°) ]²
where k is the ring octave matching the current market price magnitude.

Example for Nifty (around 24,200):
- √24200 ≈ 155.56
- Subtract odd origin: 155.56 - 1.0 = 154.56
- Modulo 2.0 = 0.563
- Angle θ = 0.563 × 180° = 101.4° (Cancer)
When a celestial body approaches 101.4° (or its square at 191.4° or opposition at 281.4°), the market reaches exact Price-Time Squaring!

---

### 4. Continuous Session Time & The 50% Equilibrium

Gann emphasized that the 50% point (the Midpoint) is the highest-gravity balance level of any cycle.
1. The 50% Price Equilibrium: (Day High + Day Low) / 2. Above this line is bullish; below is bearish.
2. The Session Midpoint: The NSE 09:15 to 15:30 session has 375 minutes. The 50% temporal midpoint occurs at 12:22:30 IST.
3. Spencer Equation of Time Solar Noon: Because the Earth's orbit is elliptical, True Solar Noon at Mumbai (72.88°E) prints between 12:22 and 12:44 IST depending on the seasonal day of the year. When session time and solar noon align, high-probability reversals occur.
"""


class AcademyGuideView(ctk.CTkScrollableFrame):
    """Integrated research guide and educational manual."""

    def __init__(self, master, theme: ThemeTokens, **kwargs):
        super().__init__(master, fg_color=theme.bg_primary, **kwargs)
        self.theme = theme

        self._build_content()

    def _build_content(self):
        container = ctk.CTkFrame(self, fg_color=self.theme.bg_card, corner_radius=8)
        container.pack(fill="both", expand=True, padx=16, pady=16)

        lbl = ctk.CTkLabel(
            container,
            text=ACADEMY_TEXT.strip(),
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=self.theme.text_primary,
            justify="left",
            wraplength=950
        )
        lbl.pack(padx=24, pady=24, fill="both", expand=True)
