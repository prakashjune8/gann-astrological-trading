---
name: Skill_3_Gann_Market_Harmonics
description: W. D. Gann price-time squaring and planetary aspect methodology - map conjunctions, squares, trines, oppositions, ingresses, stations, bidirectional Price-to-Longitude and Longitude-to-Price conversions (Square of Nine, Natural Circle, Scale Octaves), and intraday midpoint calculations (50% price equilibrium, session time midpoint, and true solar noon). Use when generating Gann timing triggers or harmonic price levels.
---

# Skill 3 – Gann Market Harmonics, Celestial Conversions & Daily Midpoints

## 1. The Gann Midpoint of the Day Methodologies

In W. D. Gann's trading philosophy, the **50% mark (the Midpoint)** is the absolute gravity center and the most critical line of balance. Gann stated: 
> *"The 50% point or half-way point of any movement, range, or cycle is the strongest resistance and support point."*

When analyzing the **Midpoint of the Day**, Gann applied this concept across three distinct dimensions:
1. **Intraday Price Midpoint (50% Price Equilibrium)**
2. **Trading Session Time Midpoint (50% Temporal Division)**
3. **Astronomical True Solar Noon (Celestial Midpoint of the Day)**

---

### A. Intraday Price Midpoint (The 50% Equilibrium Level)

The price midpoint separates bullish territory from bearish territory for the current trading day.

#### 1. Daily Range Midpoint:
$$\text{Midpoint}_{\text{Day}} = \frac{\text{High}_{\text{Day}} + \text{Low}_{\text{Day}}}{2}$$

- **Trend Filter Rule:**
  - $\text{Price} > \text{Midpoint}$: Bullish bias $\to$ favor long entries toward $\frac{\text{High} + \text{Midpoint}}{2}$ (75% quartile) and extension targets.
  - $\text{Price} < \text{Midpoint}$: Bearish bias $\to$ favor short entries toward $\frac{\text{Low} + \text{Midpoint}}{2}$ (25% quartile) and lower extensions.

#### 2. Opening Range / First-Hour Midpoint:
Gann placed significant emphasis on the range established during the initial market balance (first 45–60 minutes):
$$\text{Midpoint}_{\text{Opening}} = \frac{\text{High}_{\text{First Hour}} + \text{Low}_{\text{First Hour}}}{2}$$
A retest of this 50% opening equilibrium between 11:30 AM and 1:30 PM IST often marks the day's trend continuation or reversal trigger.

---

### B. Trading Session Time Midpoint (50% Temporal Division)

Just as price has a 50% equilibrium, the **duration of the trading day** has an exact 50% temporal midpoint where accumulated morning momentum exhausts and afternoon counter-trend or acceleration commences.

#### 1. Indian Equity Session (NSE / BSE):
- **Trading Hours:** 09:15 to 15:30 IST (Total duration: 6 hours 15 minutes = 375 minutes).
- **Exact Session Midpoint:**
  $$T_{\text{NSE Midpoint}} = 09:15 + \frac{375\text{ mins}}{2} = 09:15 + 187.5\text{ mins} = \mathbf{12:22:30\text{ IST}}$$
  *(Practical window: 12:20 PM to 12:25 PM IST).*
- **Gann Rule:** If the market forms an extreme high or low within $\pm 15$ minutes of **12:22 IST**, expect a trend reversal into the close.

#### 2. MCX Commodity Session:
- **During US Daylight Saving Time (US DST):**
  - Session: 09:00 to 23:30 IST (14 hours 30 mins = 870 minutes).
  - Exact Session Midpoint: $09:00 + 435\text{ mins} = \mathbf{16:15\text{ IST}}$ (4:15 PM IST).
- **During US Standard Time (US Winter):**
  - Session: 09:00 to 23:55 IST (14 hours 55 mins = 895 minutes).
  - Exact Session Midpoint: $09:00 + 447.5\text{ mins} = \mathbf{16:27:30\text{ IST}}$ (4:27 PM IST).

---

### C. Astronomical True Solar Noon (Celestial Midpoint of the Day)

Gann distinguished between "clock time" (man-made time zones) and "Natural Time" (solar progression). The true celestial midpoint of the day is **Local Apparent Noon (True Solar Noon)**, the exact second when the Sun transits the local celestial meridian (highest altitude / zero hour-angle).

#### Mathematical Calculation:
For Indian exchanges (Mumbai coordinates: Latitude $18.925^\circ\text{ N}$, Longitude $72.825^\circ\text{ E}$):
$$\text{Solar Noon (IST)} = 12:00 + \frac{82.5^\circ - \text{Longitude}_{\text{local}}}{15^\circ/\text{hour}} - \frac{\text{EoT}}{60}$$
- **IST Reference Meridian:** $82.5^\circ\text{ E}$ ($UTC+05:30$).
- **Mumbai Meridian Offset:** $(82.5^\circ - 72.825^\circ) \times 4\text{ mins/degree} \approx \mathbf{+38.7\text{ minutes}}$ (lag behind IST).
- **Equation of Time ($\text{EoT}$):** Cyclical astronomical deviation (-14 mins to +16 mins) due to Earth’s orbital eccentricity and axial obliquity.
- **True Solar Noon in Mumbai:** Fluctuates between **12:24 PM IST** and **12:54 PM IST** across the calendar year.

---

### D. Gann Price-Time Midpoint Confluence (The Master Setup)

The highest probability trading setup occurs when **Price Midpoint** and **Time Midpoint** coincide:
$$\text{If } \text{Price}(t) \approx \text{Midpoint}_{\text{Price}} \quad \text{at } \quad t \approx \text{Session Midpoint (12:22 IST)},$$
a severe price-time squaring takes place, dictating the entire afternoon trend direction for Nifty / Bank Nifty.

---

## 2. Bidirectional Price ↔ Longitude Conversion Principles

W. D. Gann established that price and time are interchangeable dimensions of the same vibration.

### System A: Gann Square of Nine (Spiral Wheel of 360°)
One full revolution ($360^\circ$ circle) corresponds to an increment of **2.0** on the square root scale ($\sqrt{P}$).

#### 1. Price to Longitude ($\text{Price} \to \text{Longitude}$):
$$\theta = \left( \sqrt{P} \pmod 2 \right) \times 180^\circ$$

#### 2. Longitude to Price ($\text{Longitude} \to \text{Price}$):
$$\text{offset} = \frac{\theta}{180^\circ}, \quad k = \left\lfloor \frac{\sqrt{P_{\text{ref}}} - \text{offset}}{2} \right\rfloor$$
$$P_{\text{support}} = \left(2k + \frac{\theta}{180^\circ}\right)^2, \quad P_{\text{resist}} = \left(2(k + 1) + \frac{\theta}{180^\circ}\right)^2$$

### System B: Natural Circle / Gann Wheel 360 ($1^\circ = 1 \text{ Point}$)
$$\theta = \left(\frac{P}{\text{Scale}}\right) \pmod{360^\circ}$$
$$P_n = (\theta + 360 \times n) \times \text{Scale}$$

---

## 3. Algorithmic Python Implementation Reference

```python
import math
from datetime import date, datetime, time, timedelta

def intraday_price_midpoint(high: float, low: float) -> dict[str, float]:
    """Calculate Gann 50% price equilibrium and quartile harmonic levels."""
    mid = (high + low) / 2.0
    q1 = (low + mid) / 2.0   # 25% level
    q3 = (mid + high) / 2.0  # 75% level
    return {
        "low": low,
        "support_25": q1,
        "midpoint_50": mid,
        "resistance_75": q3,
        "high": high,
        "range": high - low
    }

def session_time_midpoint(session_open: time, session_close: time, session_date: date) -> datetime:
    """Calculate the exact 50% temporal midpoint of any market trading session."""
    dt_open = datetime.combine(session_date, session_open)
    dt_close = datetime.combine(session_date, session_close)
    duration = dt_close - dt_open
    return dt_open + duration / 2

def nse_session_midpoint(session_date: date) -> datetime:
    """NSE trading session midpoint (09:15 to 15:30 IST) -> 12:22:30 IST."""
    return session_time_midpoint(time(9, 15), time(15, 30), session_date)

def equation_of_time(day_of_year: int) -> float:
    """Approximate Equation of Time in minutes given day of the year (1-366)."""
    b = 2.0 * math.pi * (day_of_year - 81) / 365.0
    return 9.87 * math.sin(2.0 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)

def solar_noon_ist(session_date: date, longitude_deg: float = 72.825) -> datetime:
    """Calculate True Solar Noon (Astronomical Midpoint of the Day) in IST.

    Default longitude is Mumbai (72.825° E).
    """
    doy = session_date.timetuple().tm_yday
    eot = equation_of_time(doy)
    meridian_offset_minutes = (82.5 - longitude_deg) * 4.0
    total_offset_minutes = meridian_offset_minutes - eot
    noon_base = datetime.combine(session_date, time(12, 0))
    return noon_base + timedelta(minutes=total_offset_minutes)
```
