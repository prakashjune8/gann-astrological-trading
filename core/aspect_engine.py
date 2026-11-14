"""Harmonic Aspect Engine for Celestial Angle Crossings, Conjunctions & Orbs.

Detects major Gann geometric angles between moving bodies or between a body and fixed gates:
- Conjunction (0°): Unity, major trend seed.
- Semi-Square (45°): 1/8 cycle harmonic tension.
- Sextile (60°): 1/6 cycle opportunity.
- Square (90°): 1/4 cycle price-time squaring / hard pivot.
- Trine (120°): 1/3 cycle equilibrium.
- Sesquiquadrate (135°): 3/8 cycle friction.
- Opposition (180°): 1/2 cycle extreme polarity / reversal.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

ASPECT_ANGLES = {
    0.0: {"name": "Conjunction", "symbol": "0°", "color": "#f59e0b", "weight": 5},
    45.0: {"name": "Semi-Square", "symbol": "45°", "color": "#8b5cf6", "weight": 3},
    60.0: {"name": "Sextile", "symbol": "60°", "color": "#06b6d4", "weight": 2},
    90.0: {"name": "Square", "symbol": "90°", "color": "#ef4444", "weight": 5},
    120.0: {"name": "Trine", "symbol": "120°", "color": "#10b981", "weight": 4},
    135.0: {"name": "Sesquiquadrate", "symbol": "135°", "color": "#a855f7", "weight": 2},
    180.0: {"name": "Opposition", "symbol": "180°", "color": "#e11d48", "weight": 5},
}


@dataclass(frozen=True)
class CelestialAspect:
    body_a: str
    body_b: str
    aspect_name: str
    target_angle: float
    actual_diff: float
    orb: float                  # absolute difference from exact target angle
    color_hex: str
    weight: int
    is_exact: bool              # orb <= 0.1°
    timestamp_ist: Optional[datetime] = None


class AspectEngine:
    """Calculates geometric angular separation and detects exact harmonic aspects."""

    @staticmethod
    def angular_distance(lon1: float, lon2: float) -> float:
        """Returns minimal angular difference in [0°, 180°] between two longitudes."""
        diff = abs((lon1 % 360.0) - (lon2 % 360.0))
        if diff > 180.0:
            diff = 360.0 - diff
        return diff

    @classmethod
    def find_aspects_between_bodies(
        cls,
        longitudes: dict[str, float],
        max_orb: float = 3.0,
        timestamp_ist: Optional[datetime] = None
    ) -> list[CelestialAspect]:
        """Scans all pairs of celestial bodies and returns active aspects within max_orb."""
        aspects: list[CelestialAspect] = []
        bodies = list(longitudes.keys())

        for i in range(len(bodies)):
            for j in range(i + 1, len(bodies)):
                b1 = bodies[i]
                b2 = bodies[j]
                lon1 = longitudes[b1]
                lon2 = longitudes[b2]
                actual_dist = cls.angular_distance(lon1, lon2)

                for target_ang, meta in ASPECT_ANGLES.items():
                    orb = abs(actual_dist - target_ang)
                    if orb <= max_orb:
                        aspects.append(CelestialAspect(
                            body_a=b1,
                            body_b=b2,
                            aspect_name=meta["name"],
                            target_angle=target_ang,
                            actual_diff=round(actual_dist, 3),
                            orb=round(orb, 3),
                            color_hex=meta["color"],
                            weight=meta["weight"],
                            is_exact=(orb <= 0.1),
                            timestamp_ist=timestamp_ist
                        ))

        # Sort by tightest orb (closest to exact)
        aspects.sort(key=lambda a: a.orb)
        return aspects

    @classmethod
    def find_aspects_to_angle(
        cls,
        longitudes: dict[str, float],
        target_degree: float,
        target_name: str = "Price Needle",
        max_orb: float = 3.0
    ) -> list[CelestialAspect]:
        """Detects aspects formed between moving celestial bodies and a fixed angle (e.g., current price angle)."""
        aspects: list[CelestialAspect] = []
        for body, lon in longitudes.items():
            dist = cls.angular_distance(lon, target_degree)
            for target_ang, meta in ASPECT_ANGLES.items():
                orb = abs(dist - target_ang)
                if orb <= max_orb:
                    aspects.append(CelestialAspect(
                        body_a=body,
                        body_b=target_name,
                        aspect_name=meta["name"],
                        target_angle=target_ang,
                        actual_diff=round(dist, 3),
                        orb=round(orb, 3),
                        color_hex=meta["color"],
                        weight=meta["weight"],
                        is_exact=(orb <= 0.1)
                    ))
        aspects.sort(key=lambda a: a.orb)
        return aspects
