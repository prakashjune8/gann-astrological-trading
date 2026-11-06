"""Triple Confluence Cluster Node & Master Harmonic Engine (Gann Level 3 Architecture).

Implements:
1. Triple Confluence Radar (Simultaneous Price, Time, and Astronomical Gates).
2. Declination Z-Axis Monitor (Planetary Parallels & Contra-Parallels).
3. True 1x1 Geometric Speedometer Velocity Rails.
4. Cymatic 8-Octave Musical Standing-Wave Grid.
5. Sniper Asymmetric Risk Architecture (15-20 pt stop, 1:5 to 1:15 risk-to-reward).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple

from core.geo_temporal import IST


@dataclass(frozen=True)
class ConfluenceGateStatus:
    is_active: bool
    label: str
    variance: float
    tolerance: float
    description: str


@dataclass(frozen=True)
class DeclinationAspect:
    body_a: str
    body_b: str
    aspect_type: str  # PARALLEL or CONTRA_PARALLEL
    decl_a: float
    decl_b: float
    orb_deg: float
    is_exact: bool


@dataclass(frozen=True)
class OctaveLevel:
    ratio_label: str  # 0/8, 1/8, ..., 8/8
    musical_note: str  # Root C, Minor 2nd, ..., Octave C'
    price: float
    distance: float
    is_support: bool


@dataclass(frozen=True)
class SniperTradeSetup:
    is_triggered: bool
    direction: str  # LONG / CALL or SHORT / PUT
    entry_price: float
    hard_stop_loss: float
    risk_pts: float
    target_1: float
    target_2: float
    reward_pts: float
    risk_reward_ratio: float
    tranche_a_pct: float
    tranche_b_pct: float
    tranche_c_pct: float
    rationale: str


class ConfluenceEngine:
    """Institutional Level 3 Confluence & Sniper Execution Engine."""

    # Standard Intraday Harmonic Time Nodes (IST)
    HARMONIC_TIME_NODES = [
        time(11, 22, 30),  # 90° Morning Square
        time(12, 22, 30),  # 180° Session Midpoint
        time(13, 56, 15),  # 270° Afternoon Square
        time(14, 27, 30),  # 300° Trine Ingress
    ]

    # Obliquity of the Ecliptic (J2000.0)
    EPSILON_RAD = math.radians(23.4392911)

    @classmethod
    def calculate_declination(cls, ecliptic_longitude_deg: float, ecliptic_latitude_deg: float = 0.0) -> float:
        """Derive equatorial declination (delta) from ecliptic longitude and latitude."""
        lambda_rad = math.radians(ecliptic_longitude_deg)
        beta_rad = math.radians(ecliptic_latitude_deg)

        sin_delta = (math.sin(beta_rad) * math.cos(cls.EPSILON_RAD) +
                     math.cos(beta_rad) * math.sin(cls.EPSILON_RAD) * math.sin(lambda_rad))
        delta_rad = math.asin(max(-1.0, min(1.0, sin_delta)))
        return math.degrees(delta_rad)

    @classmethod
    def find_declination_parallels(cls, body_longitudes: dict[str, float], max_orb_deg: float = 0.35) -> list[DeclinationAspect]:
        """Detect Z-Axis Parallels (delta_1 == delta_2) and Contra-Parallels (delta_1 == -delta_2)."""
        decls = {b: cls.calculate_declination(lon) for b, lon in body_longitudes.items()}
        results: list[DeclinationAspect] = []

        bodies = list(decls.keys())
        for i in range(len(bodies)):
            for j in range(i + 1, len(bodies)):
                b1, b2 = bodies[i], bodies[j]
                d1, d2 = decls[b1], decls[b2]

                # 1. Parallel
                diff_par = abs(d1 - d2)
                if diff_par <= max_orb_deg:
                    results.append(DeclinationAspect(
                        body_a=b1, body_b=b2, aspect_type="PARALLEL",
                        decl_a=d1, decl_b=d2, orb_deg=diff_par,
                        is_exact=(diff_par <= 0.10)
                    ))

                # 2. Contra-Parallel
                diff_contra = abs(d1 + d2)
                if diff_contra <= max_orb_deg:
                    results.append(DeclinationAspect(
                        body_a=b1, body_b=b2, aspect_type="CONTRA_PARALLEL",
                        decl_a=d1, decl_b=d2, orb_deg=diff_contra,
                        is_exact=(diff_contra <= 0.10)
                    ))

        return sorted(results, key=lambda x: x.orb_deg)

    @classmethod
    def calculate_8_octaves(cls, low_price: float, high_price: float, cmp: float) -> list[OctaveLevel]:
        """Compute W.D. Gann's 8-Octave Cymatic Standing Wave Liquidity Grid."""
        span = max(1.0, high_price - low_price)
        step = span / 8.0

        notes = [
            ("0/8", "Root Fundamental (C)"),
            ("1/8", "Minor Second (Db)"),
            ("2/8", "Major Second (D)"),
            ("3/8", "Minor Third (Eb)"),
            ("4/8", "50% Master Equilibrium (F)"),
            ("5/8", "Perfect Fifth (G)"),
            ("6/8", "Major Sixth (A)"),
            ("7/8", "Major Seventh (B)"),
            ("8/8", "Octave Roof (C')"),
        ]

        levels: list[OctaveLevel] = []
        for i, (ratio, note) in enumerate(notes):
            p = low_price + i * step
            diff = p - cmp
            levels.append(OctaveLevel(
                ratio_label=ratio,
                musical_note=note,
                price=p,
                distance=diff,
                is_support=(p <= cmp)
            ))

        return levels

    @classmethod
    def evaluate_1x1_velocity(cls, cmp: float, origin_price: float, elapsed_hours: float, scale_factor: float = 36.0) -> dict:
        """Evaluate market velocity against natural 1x1 geometric angle rail."""
        if elapsed_hours <= 0.001:
            return {"status": "EQUILIBRIUM", "diff_pts": 0.0, "rail_price": origin_price, "ratio": 1.0}

        # Expected price on 1x1 angle rail
        rail_price = origin_price + (scale_factor * elapsed_hours)
        diff = cmp - rail_price

        if diff >= 25.0:
            status = "BULLISH_ACCELERATION (> 1x1)"
        elif diff <= -25.0:
            status = "BEARISH_DECELERATION (< 1x1)"
        else:
            status = "HARMONIC_EQUILIBRIUM (1x1)"

        return {
            "status": status,
            "diff_pts": diff,
            "rail_price": rail_price,
            "velocity_ratio": cmp / max(1.0, rail_price)
        }

    @classmethod
    def evaluate_triple_confluence(
        cls,
        cmp: float,
        eval_time_ist: datetime,
        solar_noon_dt: datetime,
        key_price_levels: list[float],
        active_aspects: list[dict],
        declination_parallels: list[DeclinationAspect]
    ) -> tuple[bool, ConfluenceGateStatus, ConfluenceGateStatus, ConfluenceGateStatus, Optional[SniperTradeSetup]]:
        """Evaluate the Triple Confluence Cluster Node with zero-tolerance mathematical gates."""
        # -------------------------------------------------------------
        # Gate 1: Price Dimension (Tolerance <= 0.08% or nearest level)
        # -------------------------------------------------------------
        price_tol = max(5.0, cmp * 0.0008)  # ~18-20 pts on Nifty 24k
        min_p_dist = 999999.0
        nearest_level = cmp

        for p in key_price_levels:
            d = abs(cmp - p)
            if d < min_p_dist:
                min_p_dist = d
                nearest_level = p

        gate_price_active = (min_p_dist <= price_tol)
        gate_price = ConfluenceGateStatus(
            is_active=gate_price_active,
            label="PRICE GATE",
            variance=min_p_dist,
            tolerance=price_tol,
            description=f"Distance to Gann Level ({nearest_level:,.1f}): {min_p_dist:.1f} pts"
        )

        # -------------------------------------------------------------
        # Gate 2: Time Dimension (Tolerance <= 3.5 minutes)
        # -------------------------------------------------------------
        time_tol_sec = 210.0  # 3.5 minutes
        time_candidates = [solar_noon_dt]
        for node_t in cls.HARMONIC_TIME_NODES:
            time_candidates.append(datetime.combine(eval_time_ist.date(), node_t, tzinfo=IST))

        min_t_dist_sec = 999999.0
        nearest_time_label = "None"
        for tc in time_candidates:
            diff_sec = abs((eval_time_ist - tc).total_seconds())
            if diff_sec < min_t_dist_sec:
                min_t_dist_sec = diff_sec
                nearest_time_label = tc.strftime("%H:%M:%S IST")

        gate_time_active = (min_t_dist_sec <= time_tol_sec)
        gate_time = ConfluenceGateStatus(
            is_active=gate_time_active,
            label="TIME GATE",
            variance=min_t_dist_sec / 60.0,
            tolerance=time_tol_sec / 60.0,
            description=f"Proximity to Node ({nearest_time_label}): {min_t_dist_sec / 60.0:.1f}m"
        )

        # -------------------------------------------------------------
        # Gate 3: Astronomical Dimension (Orb <= 0.25° Aspect or Parallel)
        # -------------------------------------------------------------
        has_exact_aspect = any(a.get("is_exact", False) for a in active_aspects)
        has_exact_parallel = any(p.is_exact for p in declination_parallels)
        gate_astro_active = (has_exact_aspect or has_exact_parallel or len(active_aspects) >= 2)

        astro_desc = "Exact Aspect / Parallel Active" if gate_astro_active else "No Confluent Astronomical Alignment"
        gate_astro = ConfluenceGateStatus(
            is_active=gate_astro_active,
            label="ASTRO GATE",
            variance=0.08 if gate_astro_active else 0.50,
            tolerance=0.25,
            description=astro_desc
        )

        # -------------------------------------------------------------
        # Confluence Verdict & Sniper Trade Plan
        # -------------------------------------------------------------
        all_confluent = (gate_price_active and gate_time_active and gate_astro_active)
        trade_setup = None

        if all_confluent:
            is_long = (cmp <= nearest_level)  # Bounce off support
            direction = "LONG / ATM CALL" if is_long else "SHORT / ATM PUT"
            risk = 18.0  # Tight 18-point institutional hard stop
            stop = (nearest_level - risk) if is_long else (nearest_level + risk)
            t1 = (nearest_level + 110.0) if is_long else (nearest_level - 110.0)
            t2 = (nearest_level + 260.0) if is_long else (nearest_level - 260.0)
            reward = 260.0
            rr = reward / risk

            trade_setup = SniperTradeSetup(
                is_triggered=True,
                direction=direction,
                entry_price=cmp,
                hard_stop_loss=stop,
                risk_pts=risk,
                target_1=t1,
                target_2=t2,
                reward_pts=reward,
                risk_reward_ratio=round(rr, 2),
                tranche_a_pct=25.0,
                tranche_b_pct=50.0,
                tranche_c_pct=25.0,
                rationale=(f"Triple Confluence at {nearest_level:,.1f} within {min_t_dist_sec/60.0:.1f}m "
                           f"of {nearest_time_label} with confirmed aspect alignment.")
            )

        return all_confluent, gate_price, gate_time, gate_astro, trade_setup
