"""Unit test for Triple Confluence Cluster Node & Master Harmonic Engine."""
from __future__ import annotations

import sys
from datetime import datetime, time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.confluence_engine import ConfluenceEngine
from core.geo_temporal import IST

def test_confluence_engine():
    # 1. Test Declination Calculation
    d_sun_equinox = ConfluenceEngine.calculate_declination(0.0)
    assert abs(d_sun_equinox) < 0.01, f"Expected 0° declination at equinox, got {d_sun_equinox}"

    d_sun_solstice = ConfluenceEngine.calculate_declination(90.0)
    assert abs(d_sun_solstice - 23.44) < 0.05, f"Expected ~23.44° at summer solstice, got {d_sun_solstice}"
    print("Declination test passed (Equinox=0.0°, Solstice=23.44°).")

    # 2. Test Declination Parallels
    body_lons = {
        "SUN": 45.0,
        "MARS": 135.0,  # Same declination by symmetry across solstice
        "SATURN": 280.0
    }
    parallels = ConfluenceEngine.find_declination_parallels(body_lons)
    assert len(parallels) >= 1, "Expected at least 1 parallel"
    assert parallels[0].aspect_type == "PARALLEL"
    print(f"Declination Parallels detected: {parallels[0].body_a} <-> {parallels[0].body_b} (Orb: {parallels[0].orb_deg:.2f}°)")

    # 3. Test 8-Octave Musical Grid
    octaves = ConfluenceEngine.calculate_8_octaves(24000.0, 24800.0, 24350.0)
    assert len(octaves) == 9, "Expected 9 octave boundary points (0/8 to 8/8)"
    assert octaves[4].ratio_label == "4/8"
    assert octaves[4].price == 24400.0  # 50% midpoint
    print(f"8-Octave Grid verified: 4/8 Midpoint = {octaves[4].price}")

    # 4. Test 1x1 Velocity Speedometer
    vel = ConfluenceEngine.evaluate_1x1_velocity(cmp=24300.0, origin_price=24100.0, elapsed_hours=2.0, scale_factor=36.0)
    assert "BULLISH_ACCELERATION" in vel["status"]
    print(f"1x1 Velocity Status: {vel['status']} (+{vel['diff_pts']:.1f} pts)")

    # 5. Test Triple Confluence Evaluation (Simulating exact convergence)
    eval_time = datetime(2026, 11, 5, 12, 22, 10, tzinfo=IST)
    solar_noon = datetime(2026, 11, 5, 12, 22, 12, tzinfo=IST)
    key_levels = [24180.0, 24336.0]
    active_aspects = [{"b1": "SUN", "b2": "MOON", "color": "#ef4444", "is_exact": True}]

    is_conf, g_p, g_t, g_a, setup = ConfluenceEngine.evaluate_triple_confluence(
        cmp=24182.0,
        eval_time_ist=eval_time,
        solar_noon_dt=solar_noon,
        key_price_levels=key_levels,
        active_aspects=active_aspects,
        declination_parallels=parallels
    )

    assert is_conf is True, "Triple Confluence should trigger!"
    assert setup is not None, "SniperTradeSetup should be generated"
    assert setup.risk_pts == 18.0
    assert setup.risk_reward_ratio > 10.0
    print(f"Triple Confluence Sniper Setup Triggered!")
    print(f"  Direction : {setup.direction}")
    print(f"  Entry CMP : {setup.entry_price}")
    print(f"  Hard Stop : {setup.hard_stop_loss} (Risk: {setup.risk_pts} pts)")
    print(f"  Target 1  : {setup.target_1} | Target 2: {setup.target_2}")
    print(f"  R:R Ratio : 1 : {setup.risk_reward_ratio}")

    print("\nALL 5 LEVEL 3 QUANT CONFLUENCE TESTS PASSED (100%)!")

if __name__ == "__main__":
    test_confluence_engine()
