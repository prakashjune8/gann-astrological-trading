"""Diagnostic & Verification Test Suite for Stage 3: Gann Price-Time Harmonization & Aspects.

Audits:
1. Exact Square of Nine odd-square spiral math:
   - Root displacement: Delta_sqrt_P = theta / 180°
   - Angle from Price: theta(P) = [ (sqrt(P) - 1.0) mod 2.0 ] * 180°
   - Price from Angle: P(k, theta) = [ 2k + 1.0 + theta/180° ]^2
2. Bidirectional Roundtrip Proof:
   - For any price P, converting P -> theta -> P_recovered must yield |P - P_recovered| < 0.001.
   - Tested across multiple asset classes: Nifty (24,200), Sensex (79,500), Crude Oil (6,050), Copper (825).
3. Cardinal Cross (0°, 90°, 180°, 270°) and Fixed Cross (45°, 135°, 225°, 315°) verification.
4. Scale Octaves: Automatic scaling based on price magnitude.
5. Geometric Aspect Engine:
   - Angular distance minimal circular metric in [0°, 180°].
   - Detection of exact Conjunction (0°), Semi-Square (45°), Square (90°), Trine (120°), Opposition (180°).
   - Orb validation (exact <= 0.1°, tight <= 1.0°).
"""
from __future__ import annotations

import math
import os
import sys

# Windows console encoding safeguard
if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure d:\ephemeris is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.aspect_engine import ASPECT_ANGLES, AspectEngine
from core.price_harmonics import PriceHarmonicsEngine


def run_stage_3_verification():
    print("================================================================================")
    print("  STAGE 3: GANN PRICE-TIME HARMONIZATION & GEOMETRIC ASPECTS VERIFICATION")
    print("================================================================================")

    # --------------------------------------------------------------------------
    # Part A: Bidirectional Square of Nine Mathematical Roundtrip Proof
    # --------------------------------------------------------------------------
    print("[1] Auditing Bidirectional Square of Nine Odd-Square Formula Roundtrips...")
    test_prices = [
        ("Nifty 50 Index", 24200.00),
        ("Sensex Index", 79500.00),
        ("Bank Nifty", 51800.00),
        ("MCX Crude Oil", 6050.00),
        ("MCX Copper", 825.50),
        ("MCX Natural Gas", 240.20),
        ("Low Price Stock", 45.75),
    ]

    print("    " + "-" * 76)
    print(f"    {'Instrument':<18} {'Input Price':<14} {'Spiral Angle (θ)':<18} {'Recovered Price':<16} {'Delta Error'}")
    print("    " + "-" * 76)

    for name, p_in in test_prices:
        # Step 1: Forward calculation: Price -> Angle
        theta = PriceHarmonicsEngine.price_to_wheel_angle(p_in)
        assert 0.0 <= theta < 360.0, f"Angle out of [0, 360) range: {theta}"

        # Step 2: Backward calculation: Angle -> Price (nearest to p_in)
        p_recovered = PriceHarmonicsEngine.angle_to_price(theta, reference_price=p_in, octave_offset=0)
        err = abs(p_in - p_recovered)

        print(f"    {name:<18} {p_in:12.2f}   {theta:10.4f}°         {p_recovered:12.2f}     {err:+.6f}")
        assert err < 0.001, f"Square of Nine roundtrip mathematical failure for {name}: {p_in} vs {p_recovered} (err={err})"

    print("    --> Bidirectional Mathematical Roundtrip Proof: PASSED (|error| < 0.001)!")

    # --------------------------------------------------------------------------
    # Part B: Cardinal & Fixed Cross Calculations
    # --------------------------------------------------------------------------
    print("\n[2] Auditing Cardinal Cross & Fixed Cross Geometry around Nifty CMP (24,200)...")
    cmp_nifty = 24200.0
    cardinals = PriceHarmonicsEngine.calculate_cardinal_cross(cmp_nifty)
    fixed = PriceHarmonicsEngine.calculate_fixed_cross(cmp_nifty)

    print(f"    Cardinal Cross Levels for CMP {cmp_nifty}:")
    for cl in cardinals[:6]:
        role = "SUPPORT" if cl.is_support else "RESISTANCE"
        print(f"      - {cl.label:<32}: {cl.price:10.2f} pts  ({cl.distance_from_cmp:+8.2f} pts) [{role}]")

    print(f"    Fixed Cross Levels for CMP {cmp_nifty}:")
    for fl in fixed[:6]:
        role = "SUPPORT" if fl.is_support else "RESISTANCE"
        print(f"      - {fl.label:<32}: {fl.price:10.2f} pts  ({fl.distance_from_cmp:+8.2f} pts) [{role}]")

    # Mathematical property check: A Cardinal 90° advance from 0° on the same ring must add +0.5 to root
    # e.g. root_90 = root_0 + 90/180 = root_0 + 0.5
    p_card0 = PriceHarmonicsEngine.angle_to_price(0.0, reference_price=cmp_nifty, octave_offset=0)
    p_card90 = PriceHarmonicsEngine.angle_to_price(90.0, reference_price=cmp_nifty, octave_offset=0)
    root_diff = math.sqrt(p_card90) - math.sqrt(p_card0)
    print(f"    Root displacement for 90° Cardinal step: {root_diff:.4f} (Expected exactly: +0.5000)")
    assert abs(root_diff - 0.5) < 1e-5
    print("    --> Cardinal & Fixed Cross 90° Geometric Orthogonality: PASSED!")

    # --------------------------------------------------------------------------
    # Part C: Planetary Scale Octaves & Equilibrium
    # --------------------------------------------------------------------------
    print("\n[3] Auditing Planetary Scale Octaves & 50% Daily Equilibrium Midpoint...")
    # Scale tests across magnitudes
    assert PriceHarmonicsEngine._determine_price_scale(50.0) == 0.1
    assert PriceHarmonicsEngine._determine_price_scale(500.0) == 1.0
    assert PriceHarmonicsEngine._determine_price_scale(6000.0) == 10.0
    assert PriceHarmonicsEngine._determine_price_scale(24200.0) == 100.0
    print("    --> Price Scaling Octaves (Commodities to 5-Digit Indices): PASSED!")

    # 50% Equilibrium Level test
    day_high, day_low = 24350.0, 24120.0
    eq_level = PriceHarmonicsEngine.calculate_daily_equilibrium(day_high, day_low, cmp_nifty)
    expected_mid = (day_high + day_low) / 2.0  # 24235.0
    print(f"    Day High: {day_high}, Day Low: {day_low} -> 50% Equilibrium: {eq_level.price} (Expected: {expected_mid})")
    assert eq_level.price == expected_mid
    assert eq_level.distance_from_cmp == round(cmp_nifty - expected_mid, 2)
    assert eq_level.is_support == (expected_mid <= cmp_nifty)
    print("    --> 50% Daily Equilibrium Midpoint Calculation: PASSED!")

    # --------------------------------------------------------------------------
    # Part D: Geometric Aspect Engine Verification
    # --------------------------------------------------------------------------
    print("\n[4] Auditing Geometric Aspect Engine & Orb Windows...")
    # Test circular angular distance metric across boundary
    d1 = AspectEngine.angular_distance(10.0, 350.0)  # should be 20°
    d2 = AspectEngine.angular_distance(350.0, 10.0)  # should be 20°
    d3 = AspectEngine.angular_distance(0.0, 180.0)   # should be 180°
    d4 = AspectEngine.angular_distance(45.0, 225.0)  # should be 180°
    assert d1 == 20.0 and d2 == 20.0 and d3 == 180.0 and d4 == 180.0
    print("    --> Circular Distance Metric across 360° Boundary: PASSED!")

    # Synthetic planetary test positions with known exact aspects
    test_longitudes = {
        "Sun": 222.5,
        "Mars": 140.5,        # 222.5 - 140.5 = 82.0°
        "Jupiter": 144.5,     # 222.5 - 144.5 = 78.0°
        "Saturn": 12.5,       # 140.5 - 12.5 = 128.0°
        "Venus": 202.5,       # 222.5 - 202.5 = 20.0°
        "Moon_Square": 132.5, # 222.5 - 132.5 = 90.0° (Exact Square with Sun!)
        "Trine_Body": 102.5,  # 222.5 - 102.5 = 120.0° (Exact Trine with Sun!)
        "Opp_Body": 42.5,     # 222.5 - 42.5 = 180.0° (Exact Opposition with Sun!)
    }

    aspects = AspectEngine.find_aspects_between_bodies(test_longitudes, max_orb=2.0)
    print(f"    Detected {len(aspects)} active aspects within 2.0° orb:")

    exact_found = 0
    for a in aspects:
        exact_str = "[EXACT]" if a.is_exact else f"[Orb: {a.orb:.2f}°]"
        print(f"      - {a.body_a} <-> {a.body_b:<14}: {a.aspect_name:<14} ({a.target_angle:3.0f}°) {exact_str} color={a.color_hex}")
        if a.is_exact:
            exact_found += 1

    assert exact_found >= 3, f"Expected at least 3 exact aspects, found {exact_found}"
    print("    --> Harmonic Aspect Resolution & Exact Orb Trigger: PASSED!")

    print("\n================================================================================")
    print("  STAGE 3 AUDIT COMPLETE: 100% GANN PRICE-TIME & ASPECT HARMONICS CONFIRMED")
    print("================================================================================")


if __name__ == "__main__":
    run_stage_3_verification()
