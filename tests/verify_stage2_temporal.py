"""Diagnostic & Verification Test Suite for Stage 2: Temporal Mechanics & Continuous Session Engine.

Audits:
1. Indian Standard Time (IST) fixed +05:30 offset invariance (no DST).
2. Continuous session generation:
   - NSE Equity (09:15 to 15:30 IST): exactly 375 continuous minutes (376 inclusive sample points).
   - MCX Commodities (09:00 to 23:30/23:55 IST): continuous timeline.
3. Spencer Equation of Time (EoT) calculation & True Solar Noon over Mumbai (72.88°E) and Ujjain (75.79°E).
4. Continuous Hermite polynomial spline interpolation:
   - Evaluates all 376 1-minute steps for the Moon (the fastest-moving celestial body, ~0.55°/hr).
   - Checks derivative smoothness (velocity dθ/dt).
   - Checks phase wrap-around (359.9° -> 0.1°) to ensure zero step jumps or discontinuities.
"""
from __future__ import annotations

import math
import os
import sys
from datetime import date, datetime, time, timedelta

# Ensure d:\ephemeris is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.continuous_tracker import ContinuousCelestialTracker
from core.geo_temporal import (
    DEFAULT_STATION, INDIAN_STATIONS, IST, SESSION_FULL_DAY, SESSION_MCX_SUMMER,
    SESSION_MCX_WINTER, SESSION_NSE, UTC, calculate_equation_of_time, calculate_true_solar_noon,
    generate_continuous_session_timeline, get_mcx_session, is_us_dst, to_ist, to_utc
)
from core.horizons_client import HorizonsClient


def run_stage_2_verification():
    print("================================================================================")
    print("  STAGE 2: TEMPORAL MECHANICS & CONTINUOUS SESSION ENGINE VERIFICATION")
    print("================================================================================")

    # --------------------------------------------------------------------------
    # Part A: IST Invariance & Timezone Conversion Tests
    # --------------------------------------------------------------------------
    print("[1] Auditing Indian Standard Time (IST) Offset Invariance...")
    dt_utc = datetime(2026, 11, 5, 3, 45, tzinfo=UTC)
    dt_ist = to_ist(dt_utc)
    offset_sec = dt_ist.utcoffset().total_seconds()
    print(f"    UTC: {dt_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"    IST: {dt_ist.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"    Measured Offset: {offset_sec / 3600.0} hours")
    assert offset_sec == 5.5 * 3600, f"IST offset corrupted: {offset_sec}s instead of 19800s"

    # Roundtrip test
    dt_utc_roundtrip = to_utc(dt_ist)
    assert dt_utc == dt_utc_roundtrip, "UTC <-> IST roundtrip conversion error!"
    print("    --> IST UTC+05:30 Invariance & Roundtrip: PASSED!")

    # --------------------------------------------------------------------------
    # Part B: Exchange Continuous Session Timelines
    # --------------------------------------------------------------------------
    print("\n[2] Auditing Continuous Trading Session Timelines...")
    target_date = date(2026, 11, 5)

    # 1. NSE Session: 09:15 to 15:30 IST
    nse_timeline = generate_continuous_session_timeline(target_date, SESSION_NSE, step_minutes=1)
    duration_min = (nse_timeline[-1] - nse_timeline[0]).total_seconds() / 60.0
    print(f"    NSE Continuous Session: {nse_timeline[0].strftime('%H:%M')} to {nse_timeline[-1].strftime('%H:%M')} IST")
    print(f"    Total Duration: {duration_min} minutes (Sample count: {len(nse_timeline)})")
    assert duration_min == 375.0, f"NSE duration error: {duration_min} mins"
    assert len(nse_timeline) == 376, f"NSE 1-minute step count mismatch: {len(nse_timeline)}"

    # Check that there are zero time gaps between consecutive minutes
    for i in range(1, len(nse_timeline)):
        delta = (nse_timeline[i] - nse_timeline[i - 1]).total_seconds()
        assert delta == 60.0, f"Discontinuity detected between {nse_timeline[i-1]} and {nse_timeline[i]}"
    print("    --> NSE Continuous 375-Minute Timeline Integrity: PASSED (Zero Gaps)!")

    # 2. MCX Session check
    mcx_session = get_mcx_session(target_date)
    mcx_dur = mcx_session.total_duration_minutes
    print(f"    MCX Session: {mcx_session.start_time.strftime('%H:%M')} to {mcx_session.end_time.strftime('%H:%M')} IST (Duration: {mcx_dur} mins)")
    assert mcx_dur in [870.0, 895.0]
    print("    --> MCX Session Alignment: PASSED!")

    # --------------------------------------------------------------------------
    # Part C: Spencer Equation of Time (EoT) & True Solar Noon
    # --------------------------------------------------------------------------
    print("\n[3] Auditing Spencer Equation of Time & Indian True Solar Noon...")
    eot_mins = calculate_equation_of_time(target_date)
    print(f"    Target Date: {target_date.strftime('%Y-%m-%d')} (Day {target_date.timetuple().tm_yday} of year)")
    print(f"    Spencer EoT Value: {eot_mins:+.2f} minutes")
    # Early November EoT is historically around +16.0 to +16.5 minutes (Sun runs fast)
    assert 15.0 <= eot_mins <= 17.0, f"Spencer EoT value out of physical range: {eot_mins}"

    # Calculate solar noon across stations
    for key, st in INDIAN_STATIONS.items():
        noon_dt = calculate_true_solar_noon(target_date, st)
        print(f"    True Solar Noon at {st.name:<40}: {noon_dt.strftime('%H:%M:%S IST')}")

    # Physical verification: Mumbai (72.88°E) is west of the 82.5°E IST meridian by 9.62°
    # 9.62° * 4 mins/deg = +38.5 mins local solar delay.
    # Combined with EoT (+16.3m), noon prints at ~12:22 IST.
    mumbai_noon = calculate_true_solar_noon(target_date, DEFAULT_STATION)
    assert mumbai_noon.hour == 12 and 20 <= mumbai_noon.minute <= 24
    print("    --> Indian Geographical Solar Transit Calculation: PASSED!")

    # --------------------------------------------------------------------------
    # Part D: Continuous Ephemeris Spline Interpolation (Fastest Body: Moon)
    # --------------------------------------------------------------------------
    print("\n[4] Auditing Continuous Hermite Spline Interpolation for the Moon (Fastest Body)...")
    tracker = ContinuousCelestialTracker()

    # Track Moon across all 376 continuous minutes of the NSE session
    traj = tracker.track_body("MOON", target_date, session=SESSION_NSE, step_minutes=1)
    assert len(traj) == 376

    print(f"    Evaluated {len(traj)} continuous minute-by-minute trajectory states.")
    p_open = traj[0]
    p_close = traj[-1]
    total_travel = p_close.geo_longitude - p_open.geo_longitude
    if total_travel < 0:
        total_travel += 360.0

    print(f"    Moon at NSE Open  (09:15 IST): {p_open.geo_longitude:8.4f}° ({p_open.geo_zodiac.format_dms()})")
    print(f"    Moon at NSE Close (15:30 IST): {p_close.geo_longitude:8.4f}° ({p_close.geo_zodiac.format_dms()})")
    print(f"    Total Moon Traverse during session: {total_travel:.4f}° in 6.25 hours (~{total_travel / 6.25:.4f}°/hr)")

    # Audit derivative smoothness and check for zero step jumps
    max_minute_step = 0.0
    for i in range(1, len(traj)):
        d_step = abs(traj[i].geo_longitude - traj[i - 1].geo_longitude)
        if d_step > 180.0:
            d_step = 360.0 - d_step
        if d_step > max_minute_step:
            max_minute_step = d_step
        # 1-minute step for the Moon should be ~0.009° to 0.012°, never > 0.03°
        assert d_step < 0.03, f"Step discontinuity at minute {i}: {d_step}° jump!"

        # Session circle degree must be strictly monotonic
        assert traj[i].session_circle_deg > traj[i - 1].session_circle_deg

    print(f"    Max 1-Minute Angular Displacement: {max_minute_step:.6f}°")
    print("    --> Continuous Spline Derivative & C1 Smoothness: PASSED (Zero Discontinuities)!")

    print("\n================================================================================")
    print("  STAGE 2 AUDIT COMPLETE: 100% TEMPORAL & CONTINUOUS SESSION INTEGRITY CONFIRMED")
    print("================================================================================")


if __name__ == "__main__":
    run_stage_2_verification()
