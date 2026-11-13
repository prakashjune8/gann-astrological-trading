"""Unit test verification for Continuous Celestial Tracking Engine."""
from datetime import date
import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.geo_temporal import (
    SESSION_NSE, calculate_true_solar_noon, DEFAULT_STATION, generate_continuous_session_timeline
)
from core.continuous_tracker import ContinuousCelestialTracker


def test_engine():
    print("==========================================================")
    print("  VERIFYING CONTINUOUS CELESTIAL TRACKER (INDIA GEOGRAPHY)")
    print("==========================================================")

    target_date = date(2026, 11, 5)

    # 1. Test True Solar Noon
    noon = calculate_true_solar_noon(target_date, DEFAULT_STATION)
    print(f"[1] True Solar Noon in Mumbai ({DEFAULT_STATION.name}): {noon.strftime('%H:%M:%S IST')}")

    # 2. Test Continuous Timeline Generation
    timeline = generate_continuous_session_timeline(target_date, SESSION_NSE, step_minutes=1)
    print(f"[2] NSE Continuous Session: {timeline[0].strftime('%H:%M')} to {timeline[-1].strftime('%H:%M')} IST")
    print(f"    Total Continuous Minutes: {len(timeline)} bars")
    assert len(timeline) == 376  # 09:15 to 15:30 inclusive = 376 discrete 1-minute samples

    # 3. Test Continuous Celestial Tracker (Mars across NSE session)
    tracker = ContinuousCelestialTracker()
    print("\n[3] Tracking Mars across the continuous NSE session (09:15 to 15:30 IST)...")
    trajectory = tracker.track_body("MARS", target_date, session=SESSION_NSE, step_minutes=15)

    print(f"    Total trajectory points evaluated: {len(trajectory)}")
    print("\n    Sample Session Milestones:")
    print("    " + "-" * 75)
    print(f"    {'Time (IST)':<12} {'Prog%':<7} {'Circle°':<8} {'Geo Lon & Sign':<26} {'Helio Lon & Sign':<26}")
    print("    " + "-" * 75)

    milestones_idx = [0, len(trajectory) // 4, len(trajectory) // 2, (3 * len(trajectory)) // 4, -1]
    for idx in milestones_idx:
        p = trajectory[idx]
        geo_str = f"{p.geo_longitude:6.2f}° ({p.geo_zodiac.format_dms()})"
        helio_str = f"{p.helio_longitude:6.2f}° ({p.helio_zodiac.format_dms()})" if p.helio_longitude else "N/A"
        print(f"    {p.timestamp_ist.strftime('%H:%M'):<12} {p.session_elapsed_pct:5.1f}% {p.session_circle_deg:6.1f}° {geo_str:<26} {helio_str:<26}")

    print("    " + "-" * 75)
    print(f"    Motion State: {trajectory[0].geo_motion_state} (Hourly speed: {trajectory[0].geo_velocity_deg_per_hour:+.4f}°/hr)")

    # Verify continuity (no jumps > 0.1 deg between 15-min bars for Mars)
    for i in range(1, len(trajectory)):
        step_diff = abs(trajectory[i].geo_longitude - trajectory[i-1].geo_longitude)
        if step_diff > 180.0:
            step_diff = 360.0 - step_diff
        assert step_diff < 0.1, f"Discontinuity detected at bar {i}: {step_diff}°"

    print("\n[SUCCESS] Continuous mathematical verification passed! Zero discontinuities.")
    print("==========================================================")


if __name__ == "__main__":
    test_engine()
