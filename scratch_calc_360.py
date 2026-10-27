import math
from datetime import date, datetime, time, timedelta

d = date(2026, 10, 27)

# 1. NSE Equity: 09:15 to 15:30 (375 min = 360 deg)
nse_mid = datetime.combine(d, time(9, 15)) + timedelta(minutes=187.5)
nse_scale = 375.0 / 360.0

# 2. MCX Commodity: 09:00 to 23:30 (870 min = 360 deg, US DST active)
mcx_mid = datetime.combine(d, time(9, 0)) + timedelta(minutes=435.0)
mcx_scale = 870.0 / 360.0

# 3. Solar Day: 1440 min = 360 deg (4 min/deg)
doy = d.timetuple().tm_yday
b = 2.0 * math.pi * (doy - 81) / 365.0
eot = 9.87 * math.sin(2.0 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)
solar_offset = (82.5 - 72.825) * 4.0 - eot
solar_mid = datetime.combine(d, time(12, 0)) + timedelta(minutes=solar_offset)
solar_scale = 4.0

options = [
    ("OPTION 1: NSE / BSE Equity Session (375 min = 360 deg)", nse_mid, nse_scale),
    ("OPTION 2: MCX Commodity Session (870 min = 360 deg, US DST)", mcx_mid, mcx_scale),
    ("OPTION 3: Astronomical Solar Cycle (1440 min = 360 deg)", solar_mid, solar_scale)
]

harmonics = [
    (15, "1/24 Circle - Minor Sub-Harmonic"),
    (30, "1/12 Circle - Semi-Sextile / Sign division"),
    (45, "1/8 Circle - Octile / Semi-Square"),
    (60, "1/6 Circle - Sextile (Trine sub-harmonic)"),
    (72, "1/5 Circle - Quintile"),
    (90, "1/4 Circle - Square / Quadrant (Major)"),
    (108, "3/10 Circle - Tridecile"),
    (120, "1/3 Circle - Trine (Major)"),
    (135, "3/8 Circle - Sesqui-Square"),
    (144, "2/5 Circle - Biquintile (Gann 144 number)"),
    (150, "5/12 Circle - Quincunx"),
    (180, "1/2 Circle - Opposition / Session Extremes (Major)")
]

for title, mid, scale in options:
    print("=" * 80)
    print(title)
    print(f"Midpoint (0 deg Balance): {mid.strftime('%H:%M:%S')} IST | 1 deg = {scale:.4f} min ({scale*60:.1f} sec)")
    print("-" * 80)
    print(f"{'Deg':<5} | {'Left (-deg / Morning)':<22} | {'Right (+deg / Afternoon)':<24} | {'Harmonic Significance'}")
    print("-" * 80)
    for deg, desc in harmonics:
        t_left = mid - timedelta(minutes=deg * scale)
        t_right = mid + timedelta(minutes=deg * scale)
        print(f"{deg:>3} deg | {t_left.strftime('%H:%M:%S')} IST           | {t_right.strftime('%H:%M:%S')} IST             | {desc}")
    print()
