"""Offline unit tests: python -m unittest discover -s tests"""
import math
import unittest
from datetime import date, datetime, timedelta

from gann_timer.gann_engine import AnalysisSettings, GannEngine, route_triggers, sq9_levels, wrap180
from gann_timer.horizons_client import BodySeries, Ephemeris, parse_result
from gann_timer.instruments import (INSTRUMENT_CHOICES, SEGMENTS, ExcludedInstrumentError, assert_allowed,
                                    is_excluded, segments_for_choice, symbols_for)
from gann_timer.timeconv import align_to_session, is_nifty_expiry, us_dst_active, ut_to_ist


def synthetic(start, hours, rates, offsets):
    times = [start + timedelta(hours=h) for h in range(hours)]
    bodies = {}
    for name, rate in rates.items():
        s = BodySeries(name, times=list(times))
        s.lon = [(offsets[name] + rate * h / 24) % 360 for h in range(hours)]
        s.lat = [0.0] * hours; s.ra = list(s.lon); s.dec = [0.0] * hours
        bodies[name] = s
    return Ephemeris(times[0], times[-1], 1, bodies)


class TimeTests(unittest.TestCase):
    def test_ut_to_ist_offset(self):
        self.assertEqual(ut_to_ist(datetime(2026, 1, 1, 0, 0)).strftime("%Y-%m-%d %H:%M"), "2026-01-01 05:30")
        self.assertEqual(ut_to_ist(datetime(2026, 1, 1, 20, 0)).strftime("%Y-%m-%d %H:%M"), "2026-01-02 01:30")

    def test_sessions(self):
        # Tue 2026-10-27 05:00 UT = 10:30 IST -> live NSE
        self.assertEqual(align_to_session("NSE", datetime(2026, 10, 27, 5, 0))[0], "LIVE")
        # 12:00 UT = 17:30 IST: NSE closed, MCX live
        st, nxt = align_to_session("NSE", datetime(2026, 10, 27, 12, 0))
        self.assertEqual(st, "POST-CLOSE"); self.assertEqual(nxt.strftime("%Y-%m-%d %H:%M"), "2026-10-28 09:15")
        self.assertEqual(align_to_session("MCX", datetime(2026, 10, 27, 12, 0))[0], "LIVE")
        # Saturday -> next Monday open
        st, nxt = align_to_session("NSE", datetime(2026, 10, 31, 6, 0))
        self.assertEqual(st, "NON-TRADING DAY"); self.assertEqual(nxt.date(), date(2026, 11, 2))

    def test_mcx_dst_close(self):
        self.assertTrue(us_dst_active(date(2026, 7, 1)))
        self.assertFalse(us_dst_active(date(2026, 12, 1)))
        # 23:45 IST in December (US standard time) is still live on MCX
        self.assertEqual(align_to_session("MCX", datetime(2026, 12, 1, 18, 15))[0], "LIVE")
        self.assertEqual(align_to_session("MCX", datetime(2026, 7, 1, 18, 15))[0], "POST-CLOSE")

    def test_nifty_expiry_tuesday(self):
        self.assertTrue(is_nifty_expiry(date(2026, 10, 27)))
        self.assertFalse(is_nifty_expiry(date(2026, 10, 29)))


class ExclusionTests(unittest.TestCase):
    def test_no_gold_silver_anywhere(self):
        for seg in SEGMENTS.values():
            self.assertFalse(any(is_excluded(s) for s in seg.symbols))
        for choice in INSTRUMENT_CHOICES:
            self.assertFalse(any(is_excluded(s) for s in symbols_for(segments_for_choice(choice))))

    def test_guard_raises(self):
        for bad in ("GOLD", "GOLDM", "SILVERMIC", "goldpetal"):
            with self.assertRaises(ExcludedInstrumentError):
                assert_allowed(["COPPER", bad])


class GannTests(unittest.TestCase):
    def test_sq9(self):
        lo, hi = sq9_levels(24350, 0.0)
        self.assertLessEqual(lo, 24350); self.assertGreaterEqual(hi, 24350)
        self.assertTrue(math.isclose(math.sqrt(hi) - math.sqrt(lo), 2.0))
        self.assertAlmostEqual(math.sqrt(lo) % 2, 0.0, places=9)

    def test_conjunction_timing(self):
        # Mars at 1°/day starting 0°, Saturn fixed at 10° -> conjunction exactly 10 days later
        eph = synthetic(datetime(2026, 1, 1), 24 * 20, {"Mars": 1.0, "Saturn": 0.0}, {"Mars": 0.0, "Saturn": 10.0})
        ev = [e for e in GannEngine(eph, AnalysisSettings(["Mars", "Saturn"])).run() if e.kind == "Aspect"]
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0].time_ut, datetime(2026, 1, 11))
        self.assertIn("Conjunction", ev[0].title)

    def test_ingress_and_routing(self):
        eph = synthetic(datetime(2026, 3, 1), 24 * 10, {"Venus": 1.2, "Neptune": 0.01},
                        {"Venus": 357.0, "Neptune": 100.0})
        evs = GannEngine(eph, AnalysisSettings(["Venus", "Neptune"])).run()
        ing = [e for e in evs if e.kind == "Ingress"]
        self.assertEqual(len(ing), 1); self.assertIn("Aries", ing[0].title)
        rows = route_triggers(ing, segments_for_choice("MCX (Energy + Base Metals)"), 750.0, None)
        # Venus rules copper -> base metals only; energy rows filtered by rulership
        self.assertTrue(rows and all(r.segment.key == "MCX_METALS" for r in rows))
        self.assertIn("COPPER", rows[0].symbols)

    def test_wrap(self):
        self.assertEqual(wrap180(359), -1); self.assertEqual(wrap180(181), -179)


class ParserTests(unittest.TestCase):
    def test_parse(self):
        txt = ("hdr\n$$SOE\n 2026-Jan-01 00:00, , , 283.879610807, -23.720007274,  282.6881475, -0.8911035,\n"
               "$$EOE\n")
        s = parse_result(txt, "Mars")
        self.assertEqual(s.times[0], datetime(2026, 1, 1)); self.assertAlmostEqual(s.lon[0], 282.6881475)


if __name__ == "__main__":
    unittest.main()
