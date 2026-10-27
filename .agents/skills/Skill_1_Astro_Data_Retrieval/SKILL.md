---
name: Skill_1_Astro_Data_Retrieval
description: Query the NASA JPL Horizons REST API for high-precision geocentric planetary coordinates (ecliptic longitude/latitude, RA/declination) for any historical or future date range. Use when fetching or parsing ephemeris data.
---

# Skill 1 – Astro Data Retrieval (NASA JPL Horizons)

## Endpoint
`GET https://ssd.jpl.nasa.gov/api/horizons.api` (official doc: https://ssd-api.jpl.nasa.gov/doc/horizons.html)

## Verified parameter set (geocentric, apparent, of-date – matches Astrodienst tropical tables)
| Param | Value | Notes |
|---|---|---|
| `format` | `json` | payload text is in `result` |
| `COMMAND` | `'10'` Sun, `'301'` Moon, `'199'` Mercury, `'299'` Venus, `'499'` Mars, `'599'` Jupiter, `'699'` Saturn, `'799'` Uranus, `'899'` Neptune, `'999'` Pluto | values must be single-quoted |
| `EPHEM_TYPE` | `OBSERVER` | |
| `CENTER` | `'500@399'` | geocentre |
| `QUANTITIES` | `'2,31'` | 2 = apparent RA/DEC, 31 = ObsEcLon/ObsEcLat (ecliptic of date) |
| `START_TIME` / `STOP_TIME` | `'YYYY-MM-DD HH:MM'` | interpreted as UT |
| `STEP_SIZE` | `'1h'`, `'2h'`, `'1d'` … | |
| `ANG_FORMAT` | `DEG` | decimal degrees |
| `CSV_FORMAT` | `YES` | |
| `EXTRA_PREC` | `YES` | |
| `OBJ_DATA` | `NO` | |

## Parsing
* Data rows lie between `$$SOE` and `$$EOE`.
* CSV columns: `Date__(UT)__HR:MN, solar-presence flag, lunar-presence flag, RA, DEC, ObsEcLon, ObsEcLat`.
* Date format `2026-Jan-01 00:00`; a leading `b` marks BC dates.
* An `error` key in the JSON or the absence of `$$SOE` = failure; surface the message to the user.

## Operational rules
* Output is limited to ~90 000 lines per request → chunk ranges (≤ 1 year per request at 1 h step).
* **Send requests one at a time**: JPL returns HTTP 503 when the same IP sends concurrent requests (seen in testing).
  Retry with linear backoff and cache responses on disk keyed by (body, start, stop, step).
* Speed (deg/day) = wrapped longitude difference between samples; sign < 0 ⇒ retrograde.
