---
name: Skill_2_Temporal_Conversion
description: Convert Universal Time (UT/UTC) astronomical timestamps to Indian Standard Time (IST, UTC+05:30) and align them with Indian exchange sessions. Use whenever displaying or evaluating event times for Indian markets.
---

# Skill 2 – Temporal Conversion (UT → IST)

* IST is a fixed offset, **UTC+05:30, no daylight saving** (unchanged since 1945):
  `ist = ut.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=5, minutes=30)))`
  Do not depend on `zoneinfo` (Windows lacks the tz database unless `tzdata` is installed).
* Horizons "UT" is UTC for modern dates (UT1 before 1962); differences < 1 s are irrelevant for trading.
* Event instants are found between hourly samples by linear interpolation of the angular
  function's zero crossing: `t = t0 + (t1 - t0) * f0 / (f0 - f1)` (minute-level accuracy).
* Julian Date ↔ datetime: `JD = 2440587.5 + unix_seconds / 86400`.

## Session alignment (IST)
| Segment | Session (Mon–Fri) |
|---|---|
| NSE / BSE cash indices, NSE F&O (Nifty options) | 09:15 – 15:30 |
| MCX energy & base metals | 09:00 – 23:30 while US DST is in effect (2nd Sun Mar → 1st Sun Nov); 09:00 – 23:55 otherwise |

* Events outside a session map to the **next session open** as the actionable entry window.
* Exchange holidays are user-maintained (`holidays.json`); never invent holiday dates.
* Nifty 50 weekly options expire on **Tuesday** (from 1 Sep 2025; shifts to previous trading day on a holiday).
