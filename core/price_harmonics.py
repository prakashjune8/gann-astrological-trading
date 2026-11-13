"""W.D. Gann Price Harmonization, Square of Nine Spiral Math & Planetary Degree-to-Price Mapping.

Mathematical Derivations:
1. Square of Nine Odd-Square Mechanics:
   - Root displacement: Delta_sqrt_P = theta / 180°
   - Angle from Price: theta(P) = [ (sqrt(P) - 1.0) mod 2.0 ] * 180° for 0° <= theta < 360°
   - Price from Angle: P(k, theta) = [ 2k + 1.0 + (theta mod 360°) / 180° ]^2
2. Harmonic Overlays:
   - Cardinal Cross: 0° (East/Origin), 90° (North), 180° (West), 270° (South)
   - Fixed Cross: 45° (NE), 135° (NW), 225° (SW), 315° (SE)
3. Planetary Longitude Price Projection:
   - Scale Octaves: Automatic scaling based on price magnitude (P in [100, 1000] vs [1000, 10000] vs [10000, 100000])
   - Direct Degree Lines: P_planet = (lambda + 360 * n) * scale
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class GannPriceLevel:
    label: str                  # e.g., "Mars 140.7°", "Cardinal 90°", "50% Equilibrium"
    price: float                # Exact calculated price
    angle_degrees: float        # Source angle on the 360° circle
    level_type: str             # "PLANETARY", "CARDINAL", "FIXED", "EQUILIBRIUM"
    distance_from_cmp: float    # CMP - Price (signed)
    is_support: bool            # True if price <= CMP else False


class PriceHarmonicsEngine:
    """Rigorous mathematical engine for Gann Square of Nine and planetary price harmonization."""

    @staticmethod
    def price_to_wheel_angle(price: float) -> float:
        """Derives the exact geometric angle theta in [0°, 360°) on the Gann Square of Nine spiral."""
        if price <= 0:
            return 0.0
        r = math.sqrt(price)
        # Modulo 2.0 over odd-square progression (origin 1)
        # Every +2.0 increment in square root corresponds to 360° (one full rotation)
        rot = (r - 1.0) % 2.0
        angle = rot * 180.0
        return angle % 360.0

    @staticmethod
    def angle_to_price(target_angle: float, reference_price: float, octave_offset: int = 0) -> float:
        """Calculates exact price on the Square of Nine spiral for target_angle nearest to reference_price.

        octave_offset allows computing harmonic prices on the inner (-1, -2) or outer (+1, +2) rings.
        """
        if reference_price <= 0:
            reference_price = 100.0

        r_ref = math.sqrt(reference_price)
        norm_angle = target_angle % 360.0

        # Base ring integer k: floor((sqrt(P) - 1 - theta/180) / 2)
        k_base = math.floor((r_ref - 1.0 - (norm_angle / 180.0)) / 2.0)
        k = k_base + octave_offset

        root_target = 2.0 * k + 1.0 + (norm_angle / 180.0)
        if root_target <= 0:
            return 0.0
        return root_target * root_target

    @classmethod
    def calculate_cardinal_cross(cls, current_price: float) -> list[GannPriceLevel]:
        """Calculates Square of Nine Cardinal Cross levels (0°, 90°, 180°, 270°) around CMP."""
        cardinal_angles = [
            ("Cardinal 0° (Equinox/Origin)", 0.0),
            ("Cardinal 90° (Summer Solstice)", 90.0),
            ("Cardinal 180° (Autumn Equinox)", 180.0),
            ("Cardinal 270° (Winter Solstice)", 270.0),
        ]
        levels: list[GannPriceLevel] = []
        for label, ang in cardinal_angles:
            # Generate inner, current, and outer ring levels
            for oct_offset in [-1, 0, 1]:
                p = cls.angle_to_price(ang, current_price, octave_offset=oct_offset)
                if p > 0:
                    diff = current_price - p
                    levels.append(GannPriceLevel(
                        label=f"{label} [R{oct_offset:+d}]" if oct_offset != 0 else label,
                        price=round(p, 2),
                        angle_degrees=ang,
                        level_type="CARDINAL",
                        distance_from_cmp=round(diff, 2),
                        is_support=(p <= current_price)
                    ))
        # Sort by distance
        levels.sort(key=lambda x: abs(x.distance_from_cmp))
        return levels

    @classmethod
    def calculate_fixed_cross(cls, current_price: float) -> list[GannPriceLevel]:
        """Calculates Square of Nine Fixed Cross levels (45°, 135°, 225°, 315°) around CMP."""
        fixed_angles = [
            ("Fixed 45° (Taurus/Mid-Spring)", 45.0),
            ("Fixed 135° (Leo/Mid-Summer)", 135.0),
            ("Fixed 225° (Scorpio/Mid-Autumn)", 225.0),
            ("Fixed 315° (Aquarius/Mid-Winter)", 315.0),
        ]
        levels: list[GannPriceLevel] = []
        for label, ang in fixed_angles:
            for oct_offset in [-1, 0, 1]:
                p = cls.angle_to_price(ang, current_price, octave_offset=oct_offset)
                if p > 0:
                    diff = current_price - p
                    levels.append(GannPriceLevel(
                        label=f"{label} [R{oct_offset:+d}]" if oct_offset != 0 else label,
                        price=round(p, 2),
                        angle_degrees=ang,
                        level_type="FIXED",
                        distance_from_cmp=round(diff, 2),
                        is_support=(p <= current_price)
                    ))
        levels.sort(key=lambda x: abs(x.distance_from_cmp))
        return levels

    @classmethod
    def calculate_planetary_price_levels(
        cls,
        planetary_longitudes: dict[str, float],
        current_price: float
    ) -> list[GannPriceLevel]:
        """Converts planetary longitudes into harmonic support and resistance price levels around CMP."""
        levels: list[GannPriceLevel] = []
        for planet_name, lon in planetary_longitudes.items():
            norm_lon = lon % 360.0
            # 1. Square of Nine Spiral Harmonic Level
            for oct_offset in [-1, 0, 1]:
                p_sq9 = cls.angle_to_price(norm_lon, current_price, octave_offset=oct_offset)
                if p_sq9 > 0:
                    diff = current_price - p_sq9
                    tag = f"{oct_offset:+d}" if oct_offset != 0 else "0"
                    levels.append(GannPriceLevel(
                        label=f"{planet_name.title()} ({norm_lon:05.1f}°) Sq9 [R{tag}]",
                        price=round(p_sq9, 2),
                        angle_degrees=round(norm_lon, 2),
                        level_type="PLANETARY",
                        distance_from_cmp=round(diff, 2),
                        is_support=(p_sq9 <= current_price)
                    ))

            # 2. Natural Scale Octave Price Line (Gann degree-to-price direct projection)
            scale = cls._determine_price_scale(current_price)
            # Find closest multiple of 360
            base_rot = math.floor(current_price / (360.0 * scale))
            for rot_offset in [-1, 0, 1]:
                p_direct = (norm_lon + (base_rot + rot_offset) * 360.0) * scale
                if p_direct > 0:
                    diff = current_price - p_direct
                    tag = f"{rot_offset:+d}" if rot_offset != 0 else "0"
                    levels.append(GannPriceLevel(
                        label=f"{planet_name.title()} Direct Line [C{tag}]",
                        price=round(p_direct, 2),
                        angle_degrees=round(norm_lon, 2),
                        level_type="PLANETARY",
                        distance_from_cmp=round(diff, 2),
                        is_support=(p_direct <= current_price)
                    ))

        levels.sort(key=lambda x: abs(x.distance_from_cmp))
        return levels

    @staticmethod
    def calculate_daily_equilibrium(high: float, low: float, current_price: float) -> GannPriceLevel:
        """Calculates the 50% price equilibrium line of balance for the day's range."""
        mid = (high + low) / 2.0
        diff = current_price - mid
        return GannPriceLevel(
            label="50% Daily Equilibrium Midpoint",
            price=round(mid, 2),
            angle_degrees=180.0,
            level_type="EQUILIBRIUM",
            distance_from_cmp=round(diff, 2),
            is_support=(mid <= current_price)
        )

    @staticmethod
    def _determine_price_scale(price: float) -> float:
        """Automatically calculates the Gann scaling factor according to price magnitude."""
        if price <= 100.0:
            return 0.1
        elif price <= 1000.0:
            return 1.0
        elif price <= 10000.0:
            return 10.0
        else:  # e.g., Nifty 24,000, Sensex 80,000
            return 100.0
