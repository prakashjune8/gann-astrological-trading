---
name: Skill_3_Gann_Market_Harmonics
description: W. D. Gann price-time squaring and planetary aspect methodology - map conjunctions, squares, trines, oppositions, ingresses, stations, and bidirectional Price-to-Longitude and Longitude-to-Price conversions (Square of Nine, Natural Circle, Scale Octaves). Use when generating Gann timing triggers or harmonic price levels.
---

# Skill 3 – Gann Market Harmonics & Celestial Price Conversion

## 1. Bidirectional Price ↔ Longitude Conversion Principles

W. D. Gann established that price and time are interchangeable dimensions of the same vibration. To harmonize price with planetary movements, three core mathematical conversion systems are utilized:

---

### System A: Gann Square of Nine (Spiral Wheel of 360°)

The Square of Nine is an arithmetic spiral where numbers advance outward from the center (1). 
- One full revolution ($360^\circ$ circle) corresponds to an increment of **2.0** on the square root scale ($\sqrt{P}$).
- An angle of $180^\circ$ corresponds to an increment of **1.0** on the square root scale.
- Therefore, each degree $\theta$ represents an increment of $\frac{\theta}{180}$ on the square root scale.

#### 1. Price to Longitude ($\text{Price} \to \text{Longitude}$):
Given a market price $P$:
$$\theta = \left( \sqrt{P} \pmod 2 \right) \times 180^\circ$$
*(Where $\theta \in [0^\circ, 360^\circ)$ represents the exact tropical ecliptic longitude degree on the Gann wheel).*

*Example:* 
- Nifty 50 at $P = 24,350$:
  - $\sqrt{24350} \approx 156.044865$
  - $156.044865 \pmod 2 = 0.044865$
  - $\theta = 0.044865 \times 180^\circ \approx 8.076^\circ$ ($08^\circ\text{Aries }05'$)

#### 2. Longitude to Price ($\text{Longitude} \to \text{Price}$):
Given a planetary ecliptic longitude $\theta \in [0^\circ, 360^\circ)$ and a reference market price level $P_{\text{ref}}$:
1. Compute base root offset: $\text{offset} = \frac{\theta}{180^\circ}$
2. Identify current cycle number $k$:
   $$k = \left\lfloor \frac{\sqrt{P_{\text{ref}}} - \text{offset}}{2} \right\rfloor$$
3. Calculate harmonic price ladder levels (Support, Resistance, and higher octaves):
   $$P_k = \left(2k + \frac{\theta}{180^\circ}\right)^2$$
   - Support level: $P_{\text{support}} = \left(2k + \frac{\theta}{180^\circ}\right)^2$
   - Resistance level: $P_{\text{resist}} = \left(2(k + 1) + \frac{\theta}{180^\circ}\right)^2$
   - Major Gann Aspect Price Projections from $\theta$ ($+90^\circ$ Square, $+180^\circ$ Opposition):
     $$P_{+90^\circ} = \left(\sqrt{P} + 0.5\right)^2, \quad P_{+180^\circ} = \left(\sqrt{P} + 1.0\right)^2$$

---

### System B: Natural Circle / Gann Wheel 360 ($1^\circ = 1 \text{ Point}$ / Scaled Modulo)

Gann’s "Circle of 360" equates 1 degree of planetary longitude directly to points of market movement, adjusted for market scale factor $S = 10^n$ or instrument tick size.

#### 1. Price to Longitude:
$$\theta = \left(\frac{P}{\text{Scale}}\right) \pmod{360^\circ}$$
- For equities/indices ($P > 10,000$, Scale = 1): $\theta = P \pmod{360}$.
- For commodities/forex with decimals (e.g., Crude Oil, Copper), scale by instrument multiplier (e.g., $\times 10$ or $\times 100$).

*Example:*
- Crude Oil at $P = 6,120$:
  - $6120 \pmod{360} = 0^\circ$ (Squares directly at $0^\circ$ Aries / Vernal Equinox).

#### 2. Longitude to Price:
Given planetary position $\theta$:
$$P_n = (\theta + 360 \times n) \times \text{Scale} \quad \text{for } n \in \mathbb{Z}^+$$
Yields natural static harmonic price nodes across successive 360-point cycles.

---

### System C: Planetary Line on Chart (Degree-to-Price Scale Factor)

When plotting live planetary price curves on trading charts:
$$\text{Price Line}(t) = \left(\theta_{\text{planet}}(t) + 360 \times n\right) \times \text{Scale Factor}$$
- Active conversion factor for Nifty 50: $\text{Scale Factor} = 10 \text{ points per degree}$ or $100 \text{ points per degree}$.
- Active conversion factor for MCX Base Metals (Copper/Zinc): $1 \text{ point per degree}$.

When market price touches $\text{Price Line}(t)$, price has **squared with the planetary position** in real time.

---

## 2. Astronomical Time Factors (Geocentric Tropical Longitudes)

- **Major Aspects:**
  - $0^\circ$ Conjunction ($\☌$) - Cycle initiation / major trend reversal
  - $180^\circ$ Opposition ($\☍$) - Peak polarity / counter-trend extreme
  - $90^\circ / 270^\circ$ Square ($\square$) - High volatility / hard price-time clash
  - $120^\circ / 240^\circ$ Trine ($\triangle$) - Harmonic continuation / momentum swing
- **Gann 1/8 Harmonics (Octiles):**
  - $45^\circ / 315^\circ$ Semi-Square ($\angle$)
  - $135^\circ / 225^\circ$ Sesqui-Square ($\⚼$)
- **Ingresses:** Ingress into Cardinal Signs ($0^\circ$ Aries, Cancer, Libra, Capricorn) denotes Gann's 4 natural seasonal pivot divisions.
- **Stations:** Planetary zero-speed inflection points (Retrograde $\to$ Direct, Direct $\to$ Retrograde).

---

## 3. Algorithmic Python Implementation Reference

```python
import math

def price_to_sq9_longitude(price: float) -> float:
    """Convert any market price to its exact degree on the Square of Nine (0° to 360°)."""
    if price <= 0:
        return 0.0
    return ((math.sqrt(price) % 2.0) * 180.0) % 360.0

def sq9_longitude_to_price(degree: float, reference_price: float) -> tuple[float, float]:
    """Given a planetary degree and current market price, returns the bracketing

    Square of Nine harmonic support and resistance price levels.
    """
    if reference_price <= 0:
        return (0.0, 0.0)
    offset = (degree % 360.0) / 180.0
    root = math.sqrt(reference_price)
    k = math.floor((root - offset) / 2.0)
    support = (2.0 * k + offset) ** 2
    resistance = (2.0 * (k + 1) + offset) ** 2
    if support > reference_price:
        support, resistance = (2.0 * (k - 1) + offset) ** 2, support
    return support, resistance

def price_to_natural_degree(price: float, scale: float = 1.0) -> float:
    """Convert price to natural 360° wheel longitude."""
    return (price / scale) % 360.0

def natural_degree_to_price_ladder(degree: float, reference_price: float, scale: float = 1.0) -> tuple[float, float]:
    """Convert planetary longitude to nearest natural 360-degree price levels."""
    deg = degree % 360.0
    scaled_price = reference_price / scale
    n = math.floor(scaled_price / 360.0)
    support = (n * 360.0 + deg) * scale
    if support > reference_price:
        support -= (360.0 * scale)
    resistance = support + (360.0 * scale)
    return support, resistance
```
