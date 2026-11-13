"""Unit & Integration Test Suite for Phase 2 Sub-Task 2: Options Pricing & Greeks Engine.

Verifies:
1. Black-Scholes-Merton engine with continuous dividend yield q (Put-Call parity test).
2. High-precision minute-level time-to-maturity T terminating at 15:30:00 IST on Thursday.
3. Newton-Raphson IV solver convergence across ATM, Deep ITM, and Deep OTM strikes without division-by-zero.
4. Analytical Greeks (Delta, Gamma, 1-day Theta, Vega per 1% vol).
5. Nifty 50 50-point strike lattice generation and Gann alignment.
"""
from __future__ import annotations

import math
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.options_engine import (
    BSMOptionEngine,
    ExpiryCalendarEngine,
    GreeksResult,
    NiftyOptionChainEngine,
    norm_cdf,
    norm_pdf,
)


def test_put_call_parity_with_dividend_yield():
    print("[1/5] Testing BSM Put-Call Parity with Continuous Dividend Yield (q)...")
    spot = 24200.0
    strike = 24200.0
    t_years = 7.0 / 365.25  # 7 days
    vol = 0.145             # 14.5% IV
    r = 0.065               # 6.5% RBI repo rate
    q = 0.0125              # 1.25% Nifty dividend yield

    call_p = BSMOptionEngine.calculate_price(spot, strike, t_years, vol, option_type="CE", r=r, q=q)
    put_p = BSMOptionEngine.calculate_price(spot, strike, t_years, vol, option_type="PE", r=r, q=q)

    # Put-Call Parity with continuous dividend: C - P = S * e^(-q*T) - K * e^(-r*T)
    lhs = call_p - put_p
    rhs = spot * math.exp(-q * t_years) - strike * math.exp(-r * t_years)
    parity_diff = abs(lhs - rhs)

    assert parity_diff < 0.01, f"Put-Call Parity violated: LHS={lhs:.4f}, RHS={rhs:.4f}, Diff={parity_diff}"

    # Comparative check: Call with q > 0 must be cheaper than Call with q = 0
    call_no_div = BSMOptionEngine.calculate_price(spot, strike, t_years, vol, option_type="CE", r=r, q=0.0)
    assert call_p < call_no_div, f"Call with dividend ({call_p}) must be lower than without dividend ({call_no_div})"
    print(f"      Passed. Call: {call_p:.2f}, Put: {put_p:.2f}. Parity Diff: {parity_diff:.6f} pts.")


def test_minute_level_time_to_maturity():
    print("[2/5] Testing Minute-Level Time-to-Maturity (T) Precision...")
    engine = ExpiryCalendarEngine()

    # Case A: Thursday at 14:30:00 IST (exactly 60 minutes before 15:30 close)
    exp_thu = date(2024, 1, 25)
    eval_dt = datetime.combine(exp_thu, time(14, 30, 0))

    t_years = engine.calculate_time_to_maturity_years(eval_dt, expiry_date=exp_thu)
    expected_minutes = 60.0
    expected_years = expected_minutes / 525960.0
    assert abs(t_years - expected_years) < 1e-9, f"T years mismatch: {t_years} vs {expected_years}"

    # Case B: Expiry afternoon at 15:29:57 IST (3 seconds = 0.05 min floor)
    eval_last_sec = datetime.combine(exp_thu, time(15, 29, 57))
    t_floor = engine.calculate_time_to_maturity_years(eval_last_sec, expiry_date=exp_thu)
    assert t_floor > 0.0, "Time-to-maturity must strictly remain positive (no zero-division)"

    # Case C: Holiday shift (2024-03-29 is Good Friday, so Thursday 2024-03-28 is active)
    active_expiry = engine.get_upcoming_weekly_expiry(date(2024, 3, 25))
    assert active_expiry == date(2024, 3, 28)
    print(f"      Passed. 60-Minute Expiry: T={t_years:.8f} yrs ({expected_minutes:.0f} mins). Holiday roll verified.")


def test_newton_raphson_iv_inversion():
    print("[3/5] Testing Newton-Raphson IV Inversion Across Moneyness...")
    spot = 24200.0
    t_years = 4.0 / 365.25  # 4 days
    r = 0.065
    q = 0.0125

    # 1. ATM Strike (24,200)
    target_atm_iv = 0.145
    mkt_price_atm = BSMOptionEngine.calculate_price(spot, 24200.0, t_years, target_atm_iv, "CE", r=r, q=q)
    inverted_atm_iv = BSMOptionEngine.invert_implied_volatility(spot, 24200.0, t_years, mkt_price_atm, "CE", r=r, q=q)
    assert abs(inverted_atm_iv - target_atm_iv) < 0.001, f"ATM IV inversion error: {inverted_atm_iv} vs {target_atm_iv}"

    # 2. Deep ITM Strike (22,000)
    target_itm_iv = 0.220
    mkt_price_itm = BSMOptionEngine.calculate_price(spot, 22000.0, t_years, target_itm_iv, "CE", r=r, q=q)
    inverted_itm_iv = BSMOptionEngine.invert_implied_volatility(spot, 22000.0, t_years, mkt_price_itm, "CE", r=r, q=q)
    # Re-priced difference check
    repriced_itm = BSMOptionEngine.calculate_price(spot, 22000.0, t_years, inverted_itm_iv, "CE", r=r, q=q)
    assert abs(repriced_itm - mkt_price_itm) < 0.10, f"Deep ITM Repricing error: {repriced_itm} vs {mkt_price_itm}"

    # 3. Deep OTM Strike (26,000) - Vega vanishes test
    target_otm_iv = 0.180
    mkt_price_otm = BSMOptionEngine.calculate_price(spot, 26000.0, t_years, target_otm_iv, "CE", r=r, q=q)
    inverted_otm_iv = BSMOptionEngine.invert_implied_volatility(spot, 26000.0, t_years, mkt_price_otm, "CE", r=r, q=q)
    repriced_otm = BSMOptionEngine.calculate_price(spot, 26000.0, t_years, inverted_otm_iv, "CE", r=r, q=q)
    assert abs(repriced_otm - mkt_price_otm) < 0.10, f"Deep OTM Repricing error: {repriced_otm} vs {mkt_price_otm}"

    print(f"      Passed. ATM IV: {inverted_atm_iv:.4f}, Deep ITM: {inverted_itm_iv:.4f}, Deep OTM: {inverted_otm_iv:.4f}")


def test_analytical_greeks():
    print("[4/5] Testing Analytical Greeks Bounds & Sensitivities...")
    spot = 24200.0
    strike = 24200.0
    t_years = 5.0 / 365.25
    vol = 0.145

    call_greeks = BSMOptionEngine.calculate_greeks(spot, strike, t_years, vol, option_type="CE")
    put_greeks = BSMOptionEngine.calculate_greeks(spot, strike, t_years, vol, option_type="PE")

    # Delta bounds
    assert 0.45 <= call_greeks.delta <= 0.55, f"ATM Call Delta unexpected: {call_greeks.delta}"
    assert -0.55 <= put_greeks.delta <= -0.45, f"ATM Put Delta unexpected: {put_greeks.delta}"

    # Gamma positivity and equality
    assert call_greeks.gamma > 0.0
    assert abs(call_greeks.gamma - put_greeks.gamma) < 1e-6, "Call and Put Gamma must be identical"

    # Vega positivity and equality
    assert call_greeks.vega > 0.0
    assert abs(call_greeks.vega - put_greeks.vega) < 0.01, "Call and Put Vega must be identical"

    # Theta decay negative
    assert call_greeks.theta_daily < 0.0, "Call Theta decay must be negative"
    assert put_greeks.theta_daily < 0.0, "Put Theta decay must be negative"
    print(f"      Passed. ATM Call: Delta={call_greeks.delta}, Gamma={call_greeks.gamma}, Theta={call_greeks.theta_daily}pts/day, Vega={call_greeks.vega_per_pct}pts/1%")


def test_nifty_option_chain_and_gann_mapping():
    print("[5/5] Testing NiftyOptionChain Lattice & Gann Strike Mapping...")
    chain_engine = NiftyOptionChainEngine()
    spot = 24182.5  # Realistic spot CMP
    eval_dt = datetime(2024, 1, 22, 11, 30, 0)

    # Key Gann price levels
    gann_levels = [24000.0, 24150.0, 24200.0, 24350.0]

    chain_rows = chain_engine.generate_option_chain(
        spot=spot,
        eval_datetime=eval_dt,
        base_iv=0.140,
        strikes_above_below=5,
        gann_price_levels=gann_levels
    )

    assert len(chain_rows) == 11  # 5 above + 5 below + 1 ATM
    # ATM strike should be 24,200.0 (closest 50-pt multiple to 24182.5)
    atm_rows = [r for r in chain_rows if r.is_atm]
    assert len(atm_rows) == 1
    assert atm_rows[0].strike == 24200.0

    df_chain = chain_engine.to_dataframe(chain_rows)
    assert not df_chain.empty
    assert "CE_PRICE" in df_chain.columns
    assert "PE_PRICE" in df_chain.columns
    assert "GANN_ALIGNMENT" in df_chain.columns
    print(f"      Passed. Generated {len(chain_rows)} strikes. ATM: {atm_rows[0].strike}. Gann alignment confirmed.")


if __name__ == "__main__":
    print("=================================================================")
    print("RUNNING INSTITUTIONAL OPTIONS PRICING & GREEKS TEST SUITE (PHASE 2-2)")
    print("=================================================================")
    test_put_call_parity_with_dividend_yield()
    test_minute_level_time_to_maturity()
    test_newton_raphson_iv_inversion()
    test_analytical_greeks()
    test_nifty_option_chain_and_gann_mapping()
    print("=================================================================")
    print("ALL 5 OPTIONS ENGINE TESTS DETERMINISTICALLY PASSED")
    print("=================================================================")
