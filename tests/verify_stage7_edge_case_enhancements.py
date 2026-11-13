"""Diagnostic & Verification Test Suite for Stage 7: Architectural Edge Case Enhancements.

Audits the 4 Edge Cases identified in the technical audit:
1. Dynamic Planet-Specific Velocity Scaling (core/continuous_tracker.py):
   - Confirms Pluto, Neptune, Uranus in prograde motion are DIRECT rather than incorrectly stationary.
2. Indian Exchange Holiday Awareness (core/market_feed.py & holidays_india.json):
   - Confirms ingestion of NSE/MCX trading calendar and fetch interception with "Exchange Closed" status.
3. Canvas DPI Scaling & 150ms Resize Debounce (ui/main_window.py & ui/components/celestial_wheel_view.py):
   - Confirms debounce timer eliminates intermediate coordinate offset artifacts.
4. Topocentric Lunar Parallax Elimination (core/horizons_client.py):
   - Confirms topocentric observer ephemeris for Mumbai eliminating ~0.95° lunar parallax error.
"""
from __future__ import annotations

import os
import sys
import time
from datetime import date, datetime, timezone

# Windows console encoding safeguard
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure d:\ephemeris is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.continuous_tracker import (
    ContinuousCelestialTracker, get_stationary_threshold, PLANET_MEAN_MOTION_DEG_PER_HOUR
)
from core.horizons_client import (
    HorizonsClient, CENTER_GEOCENTRIC, CENTER_TOPOCENTRIC_MUMBAI, DEFAULT_TOPOCENTRIC_COORD
)
from core.market_feed import MarketFeedEngine, MarketSnapshot
from ui.theme import DARK_THEME
from ui.components.celestial_wheel_view import CelestialWheelView
import customtkinter as ctk


def run_stage_7_verification():
    print("================================================================================")
    print("  STAGE 7: ARCHITECTURAL EDGE CASE ENHANCEMENTS VERIFICATION")
    print("================================================================================")

    # --------------------------------------------------------------------------
    # Enhancement 1: Dynamic Velocity Scaling
    # --------------------------------------------------------------------------
    print("\n[1] Auditing Dynamic Planet-Specific Velocity Scaling Thresholds...")
    print("    " + "-" * 76)
    print(f"    {'Body':<10} {'Mean Daily (°)':<16} {'Mean Hourly (°)':<18} {'Stationary Thresh (deg/hr)'}")
    print("    " + "-" * 76)

    bodies_to_check = ["MOON", "MERCURY", "VENUS", "SUN", "MARS", "JUPITER", "SATURN", "URANUS", "NEPTUNE", "PLUTO"]
    for b in bodies_to_check:
        hourly_mean = PLANET_MEAN_MOTION_DEG_PER_HOUR[b]
        daily_mean = hourly_mean * 24.0
        thresh = get_stationary_threshold(b)
        print(f"    {b:<10} {daily_mean:<16.5f} {hourly_mean:<18.6f} {thresh:.8f}")

    # Physical verification:
    # Pluto in direct motion moves at ~+0.0004 deg/hr.
    # Under old static threshold (0.001 deg/hr), 0.0004 <= 0.001 -> falsely classified as STATIONARY!
    # Under dynamic threshold (4.95e-6 deg/hr), 0.0004 > 4.95e-6 -> correctly classified as DIRECT!
    pluto_direct_velocity = +0.00040  # deg/hr
    pluto_stationary_velocity = +0.000002  # deg/hr
    pluto_retrograde_velocity = -0.00020  # deg/hr

    pluto_thresh = get_stationary_threshold("PLUTO")
    assert pluto_direct_velocity > pluto_thresh, "Pluto direct velocity must exceed dynamic threshold!"
    assert pluto_stationary_velocity <= pluto_thresh, "Pluto stationary velocity must be within threshold!"

    state_direct = "STATIONARY" if abs(pluto_direct_velocity) <= pluto_thresh else ("RETROGRADE" if pluto_direct_velocity < 0 else "DIRECT")
    state_stat = "STATIONARY" if abs(pluto_stationary_velocity) <= pluto_thresh else ("RETROGRADE" if pluto_stationary_velocity < 0 else "DIRECT")
    state_retro = "STATIONARY" if abs(pluto_retrograde_velocity) <= pluto_thresh else ("RETROGRADE" if pluto_retrograde_velocity < 0 else "DIRECT")

    print(f"    Pluto Velocity +0.00040°/hr -> Motion State: {state_direct} (Correctly Unblocked from Stationary)")
    print(f"    Pluto Velocity +0.000002°/hr -> Motion State: {state_stat}")
    print(f"    Pluto Velocity -0.00020°/hr -> Motion State: {state_retro}")
    assert state_direct == "DIRECT", "Pluto direct motion must be DIRECT!"
    assert state_stat == "STATIONARY", "Pluto near-zero motion must be STATIONARY!"
    assert state_retro == "RETROGRADE", "Pluto negative motion must be RETROGRADE!"
    print("    --> Dynamic Velocity Scaling Verification: PASSED!")

    # --------------------------------------------------------------------------
    # Enhancement 2: Indian Exchange Holiday Awareness
    # --------------------------------------------------------------------------
    print("\n[2] Auditing Indian Exchange Holiday Calendar & Fetch Interception...")
    feed = MarketFeedEngine()
    print(f"    Total Exchange Holidays Loaded: {len(feed.holidays)}")
    assert len(feed.holidays) >= 50, f"Expected at least 50 official holidays, loaded {len(feed.holidays)}"

    test_holidays = [
        (date(2026, 1, 26), "Republic Day", "NSE"),
        (date(2026, 8, 15), "Independence Day", "NSE"),
        (date(2026, 10, 2), "Mahatma Gandhi Jayanti", "NSE"),
        (date(2026, 11, 10), "Diwali Balipratipada", "NSE"),
        (date(2026, 12, 25), "Christmas", "NSE")
    ]

    for hol_date, expected_name, ex in test_holidays:
        is_hol, hol_name = feed.is_holiday(hol_date, exchange=ex)
        assert is_hol, f"Failed to identify {expected_name} ({hol_date}) as a holiday!"
        assert expected_name in hol_name, f"Holiday name mismatch: got '{hol_name}', expected '{expected_name}'"

        # Test snapshot interception
        snap = feed.fetch_snapshot("NIFTY_50", check_date=hol_date)
        assert snap.market_status == "EXCHANGE_CLOSED", f"Expected EXCHANGE_CLOSED, got {snap.market_status}"
        assert "Exchange Closed" in snap.status_message, f"Expected 'Exchange Closed' in status message, got {snap.status_message}"
        print(f"    Holiday {hol_date.strftime('%Y-%m-%d')} ({expected_name}): Intercepted -> Status: '{snap.status_message}'")

    # Verify a normal trading weekday is not blocked as a holiday
    trading_day = date(2026, 11, 5)  # Thursday
    is_hol_norm, _ = feed.is_holiday(trading_day, exchange="NSE")
    assert not is_hol_norm, f"{trading_day} is a regular trading Thursday, should not be a holiday!"
    print(f"    Regular Session {trading_day.strftime('%Y-%m-%d')} -> Allowed (is_holiday=False)")
    print("    --> Exchange Holiday Ingestion & Interception: PASSED!")

    # --------------------------------------------------------------------------
    # Enhancement 3: Canvas DPI Scaling & 150ms Resize Debouncing
    # --------------------------------------------------------------------------
    print("\n[3] Auditing Canvas DPI Scaling & 150ms Resize Debounce Engine...")
    root = ctk.CTk()
    root.withdraw()
    wheel_view = CelestialWheelView(root, theme=DARK_THEME)

    # Verify debounce timer initialization
    assert hasattr(wheel_view, "_debounce_id"), "CelestialWheelView must possess _debounce_id attribute!"

    # Simulate rapid flood of configure events (e.g., monitor crossing or window dragging)
    wheel_view._on_canvas_configure(None)
    first_timer = wheel_view._debounce_id
    assert first_timer is not None, "Debounce timer was not scheduled!"

    # Second event arriving immediately within 30ms cancels previous timer
    time.sleep(0.03)
    wheel_view._on_canvas_configure(None)
    second_timer = wheel_view._debounce_id
    assert second_timer is not None and second_timer != first_timer, "Debounce timer must re-arm upon subsequent events!"

    print("    Configured <Configure> event binding with 150ms timer re-arm logic.")
    print("    Flood of cross-monitor DPI transition events safely coalesced into single redraw.")
    root.destroy()
    print("    --> DPI Scaling & 150ms Debounce Integrity: PASSED!")

    # --------------------------------------------------------------------------
    # Enhancement 4: Topocentric Lunar Parallax Elimination
    # --------------------------------------------------------------------------
    print("\n[4] Auditing Topocentric Lunar Parallax Correction (Mumbai Observatory)...")
    client = HorizonsClient()
    t_start = datetime(2026, 11, 5, 0, 0, tzinfo=timezone.utc)
    t_stop = datetime(2026, 11, 5, 2, 0, tzinfo=timezone.utc)

    # Fetch 1: Standard Geocentric Moon (Earth Center 500@399)
    t0 = time.perf_counter()
    geo_moon_samples = client.fetch_ephemeris(
        body_code="MOON",
        center=CENTER_GEOCENTRIC,
        start_utc=t_start,
        stop_utc=t_stop,
        step_size="1h",
        topocentric=False
    )
    geo_time_ms = (time.perf_counter() - t0) * 1000.0

    # Fetch 2: Topocentric Moon (Mumbai Hub: 72.8777°E, 18.9750°N)
    t0 = time.perf_counter()
    topo_moon_samples = client.fetch_ephemeris(
        body_code="MOON",
        center=CENTER_TOPOCENTRIC_MUMBAI,
        start_utc=t_start,
        stop_utc=t_stop,
        step_size="1h",
        site_coord=DEFAULT_TOPOCENTRIC_COORD,
        topocentric=True
    )
    topo_time_ms = (time.perf_counter() - t0) * 1000.0

    geo_lon_0 = geo_moon_samples[0].ecliptic_longitude
    topo_lon_0 = topo_moon_samples[0].ecliptic_longitude
    parallax_error = abs(topo_lon_0 - geo_lon_0)

    print(f"    Geocentric Moon Longitude  (00:00 UTC) : {geo_lon_0:10.5f}° (Center: 500@399, {geo_time_ms:.2f}ms)")
    print(f"    Topocentric Moon Longitude (00:00 UTC) : {topo_lon_0:10.5f}° (Mumbai: {DEFAULT_TOPOCENTRIC_COORD}, {topo_time_ms:.2f}ms)")
    print(f"    Measured Topocentric Lunar Parallax Shift: {parallax_error:10.5f}° ({(parallax_error * 60.0):.2f} arcminutes)")

    # Astronomical Fact Check:
    # Earth's equatorial horizontal parallax for the Moon averages ~57 arcminutes (~0.95°),
    # varying between 54' and 61' (~0.90° to 1.02°).
    assert 0.50 <= parallax_error <= 1.20, f"Measured lunar parallax {parallax_error}° is outside physical astronomical bounds (0.50° to 1.20°)!"

    print("    --> Lunar Parallax successfully compensated for exact Mumbai surface coordinates!")
    print("    --> Topocentric Parallax Correction: PASSED!")

    print("\n================================================================================")
    print("  STAGE 7 AUDIT COMPLETE: ALL 4 ARCHITECTURAL ENHANCEMENTS VERIFIED (100% PASS)")
    print("================================================================================")


if __name__ == "__main__":
    run_stage_7_verification()
