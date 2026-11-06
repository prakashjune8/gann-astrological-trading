"""Institutional Nifty 50 European Index Options Pricing & Analytical Greeks Engine.

Phase 2, Sub-Task 2 of the Gann Celestial Tracker Pro Architecture.
Implements:
1. Black-Scholes-Merton (BSM) Engine with Continuous Dividend Yield (q=0.0125) and RBI Risk-Free Rate (r=0.065).
2. High-Precision Minute-Level Time-to-Maturity (T) terminating at 15:30:00 IST on Thursday (with NSE holiday roll).
3. Robust Implied Volatility (IV) Inversion via Newton-Raphson with Brenner-Subrahmanyam seed and Bisection fail-safe.
4. Complete First- & Second-Order Analytical Greeks (Delta, Gamma, 1-Day Theta Decay, Vega per 1% vol, Rho).
5. Nifty 50 50-Point Strike Lattice & Gann Astro-Harmonic Strike Mapping.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Literal, Optional, Tuple

import pandas as pd

from core.backtest_data import MarketCalendarManager

logger = logging.getLogger("options_engine")

# High-precision mathematical constants
INV_SQRT_2PI: float = 0.3989422804014327  # 1.0 / sqrt(2 * pi)
MINUTES_PER_YEAR: float = 525960.0        # 365.25 * 1440


# ==============================================================================
# 1. NORMAL DISTRIBUTION MATHEMATICAL CORE (ZERO C-DEPENDENCY)
# ==============================================================================

def norm_cdf(x: float) -> float:
    """Cumulative distribution function for standard normal distribution N(x).
    
    Uses math.erf for exact double-precision floating point accuracy (1e-15).
    """
    return 0.5 * (1.0 + math.erf(x / 1.4142135623730951))


def norm_pdf(x: float) -> float:
    """Probability density function for standard normal distribution N'(x)."""
    return INV_SQRT_2PI * math.exp(-0.5 * x * x)


# ==============================================================================
# 2. DATA STRUCTURES: GREEKS & OPTION CONTRACTS
# ==============================================================================

@dataclass(frozen=True)
class GreeksResult:
    """Analytical Greeks and theoretical valuation under BSM with continuous dividend yield."""
    theoretical_price: float
    delta: float
    gamma: float
    theta_daily: float        # 1-day time decay in points (per calendar day)
    vega: float               # Full Vega dP / dSigma
    vega_per_pct: float       # P&L change per 1% IV shift (Vega * 0.01)
    rho: float                # P&L change per 1% interest rate shift
    implied_volatility: float
    d1: float
    d2: float


@dataclass(frozen=True)
class OptionStrikeRow:
    """Complete pricing and Greeks row for a single strike in the Nifty option chain."""
    strike: float
    is_atm: bool
    distance_to_spot: float
    call_price: float
    call_iv: float
    call_delta: float
    call_gamma: float
    call_theta: float
    call_vega: float
    put_price: float
    put_iv: float
    put_delta: float
    put_gamma: float
    put_theta: float
    put_vega: float
    nearest_gann_level: float
    gann_alignment_text: str


# ==============================================================================
# 3. HIGH-PRECISION EXPIRY & MINUTE-LEVEL TIME-TO-MATURITY
# ==============================================================================

class ExpiryCalendarEngine:
    """Calculates weekly Thursday expiry dates and minute-level time-to-maturity terminating at 15:30:00 IST."""

    EXCHANGES_CLOSE_TIME: time = time(15, 30, 0)

    def __init__(self, calendar_manager: Optional[MarketCalendarManager] = None):
        self.calendar = calendar_manager or MarketCalendarManager()

    def get_upcoming_weekly_expiry(self, eval_date: date, eval_time: Optional[time] = None) -> date:
        """Determines the active weekly expiry Thursday, rolling to Wednesday if Thursday is an NSE holiday."""
        # Weekday: Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4, Saturday=5, Sunday=6
        current_weekday = eval_date.weekday()

        if current_weekday == 3:  # Today is Thursday
            # If past 15:30, active expiry rolls to next week
            if eval_time is not None and eval_time >= self.EXCHANGES_CLOSE_TIME:
                days_ahead = 7
            else:
                days_ahead = 0
        elif current_weekday < 3:
            days_ahead = 3 - current_weekday
        else:
            days_ahead = 7 - (current_weekday - 3)

        target_thursday = eval_date + timedelta(days=days_ahead)

        # Preempt NSE trading holidays: if Thursday is closed, roll back to Wednesday, then Tuesday
        expiry_date = target_thursday
        while not self.calendar.is_trading_day(expiry_date, exchange="NSE"):
            expiry_date -= timedelta(days=1)

        return expiry_date

    def calculate_time_to_maturity_years(
        self,
        eval_datetime: datetime,
        expiry_date: Optional[date] = None
    ) -> float:
        """Computes exact time-to-maturity T in years down to the minute.
        
        Terminates precisely at 15:30:00 IST on expiry day.
        Floor epsilon = 0.05 minutes prevents division-by-zero during final seconds.
        """
        exp_d = expiry_date or self.get_upcoming_weekly_expiry(eval_datetime.date(), eval_datetime.time())
        exp_dt = datetime.combine(exp_d, self.EXCHANGES_CLOSE_TIME)

        # Localize or match tzinfo if present
        if eval_datetime.tzinfo is not None:
            exp_dt = exp_dt.replace(tzinfo=eval_datetime.tzinfo)

        delta_sec = (exp_dt - eval_datetime).total_seconds()
        delta_mins = max(0.05, delta_sec / 60.0)

        # Annualize: total minutes in 365.25 day year = 525,960.0
        t_years = delta_mins / MINUTES_PER_YEAR
        return t_years


# ==============================================================================
# 4. BLACK-SCHOLES-MERTON ENGINE WITH CONTINUOUS DIVIDEND YIELD
# ==============================================================================

class BSMOptionEngine:
    """European Index Option pricing and analytical Greeks engine with continuous dividend yield (q).
    
    Standard Baseline Parameters for NSE Nifty 50:
    - r (Risk-Free Rate): 0.065 (6.5% RBI Repo Rate)
    - q (Continuous Dividend Yield): 0.0125 (1.25% Nifty 50 Dividend Yield)
    """

    DEFAULT_R: float = 0.065    # 6.5% RBI Repo Rate
    DEFAULT_Q: float = 0.0125   # 1.25% Nifty 50 Continuous Dividend Yield

    @classmethod
    def calculate_d1_d2(
        cls,
        spot: float,
        strike: float,
        t_years: float,
        volatility: float,
        r: float = DEFAULT_R,
        q: float = DEFAULT_Q
    ) -> Tuple[float, float]:
        """Calculates BSM d1 and d2 incorporating continuous dividend yield q."""
        safe_t = max(1e-7, t_years)
        safe_vol = max(1e-4, volatility)
        vol_sqrt_t = safe_vol * math.sqrt(safe_t)

        d1 = (math.log(spot / strike) + (r - q + 0.5 * safe_vol * safe_vol) * safe_t) / vol_sqrt_t
        d2 = d1 - vol_sqrt_t
        return d1, d2

    @classmethod
    def calculate_price(
        cls,
        spot: float,
        strike: float,
        t_years: float,
        volatility: float,
        option_type: Literal["CE", "PE"] = "CE",
        r: float = DEFAULT_R,
        q: float = DEFAULT_Q
    ) -> float:
        """Calculates theoretical option price under BSM with continuous dividend yield."""
        if t_years <= 1e-7:
            # Immediate intrinsic value at expiry
            return max(0.0, spot - strike) if option_type == "CE" else max(0.0, strike - spot)

        d1, d2 = cls.calculate_d1_d2(spot, strike, t_years, volatility, r=r, q=q)
        exp_qt = math.exp(-q * t_years)
        exp_rt = math.exp(-r * t_years)

        if option_type == "CE":
            price = spot * exp_qt * norm_cdf(d1) - strike * exp_rt * norm_cdf(d2)
        else:
            price = strike * exp_rt * norm_cdf(-d2) - spot * exp_qt * norm_cdf(-d1)

        return max(0.0, price)

    @classmethod
    def calculate_greeks(
        cls,
        spot: float,
        strike: float,
        t_years: float,
        volatility: float,
        option_type: Literal["CE", "PE"] = "CE",
        r: float = DEFAULT_R,
        q: float = DEFAULT_Q
    ) -> GreeksResult:
        """Computes complete first- and second-order Greeks with continuous dividend yield."""
        safe_t = max(1e-7, t_years)
        safe_vol = max(1e-4, volatility)
        sqrt_t = math.sqrt(safe_t)

        d1, d2 = cls.calculate_d1_d2(spot, strike, safe_t, safe_vol, r=r, q=q)
        exp_qt = math.exp(-q * safe_t)
        exp_rt = math.exp(-r * safe_t)
        n_prime_d1 = norm_pdf(d1)

        # Theoretical Price
        if option_type == "CE":
            price = spot * exp_qt * norm_cdf(d1) - strike * exp_rt * norm_cdf(d2)
            delta = exp_qt * norm_cdf(d1)
            # Theta Call (Expressed per calendar day / 365)
            theta_term1 = -(spot * exp_qt * safe_vol * n_prime_d1) / (2.0 * sqrt_t)
            theta_term2 = q * spot * exp_qt * norm_cdf(d1)
            theta_term3 = -r * strike * exp_rt * norm_cdf(d2)
            theta_daily = (theta_term1 + theta_term2 + theta_term3) / 365.0
            rho = (strike * safe_t * exp_rt * norm_cdf(d2)) / 100.0
        else:
            price = strike * exp_rt * norm_cdf(-d2) - spot * exp_qt * norm_cdf(-d1)
            delta = -exp_qt * norm_cdf(-d1)
            # Theta Put (Expressed per calendar day / 365)
            theta_term1 = -(spot * exp_qt * safe_vol * n_prime_d1) / (2.0 * sqrt_t)
            theta_term2 = -q * spot * exp_qt * norm_cdf(-d1)
            theta_term3 = r * strike * exp_rt * norm_cdf(-d2)
            theta_daily = (theta_term1 + theta_term2 + theta_term3) / 365.0
            rho = (-strike * safe_t * exp_rt * norm_cdf(-d2)) / 100.0

        # Gamma (identical for Call and Put)
        gamma = (exp_qt * n_prime_d1) / (spot * safe_vol * sqrt_t)

        # Vega (identical for Call and Put)
        vega = spot * exp_qt * sqrt_t * n_prime_d1
        vega_per_pct = vega * 0.01

        return GreeksResult(
            theoretical_price=round(max(0.0, price), 2),
            delta=round(delta, 4),
            gamma=round(gamma, 6),
            theta_daily=round(theta_daily, 2),
            vega=round(vega, 2),
            vega_per_pct=round(vega_per_pct, 2),
            rho=round(rho, 4),
            implied_volatility=round(safe_vol, 4),
            d1=round(d1, 4),
            d2=round(d2, 4)
        )

    @classmethod
    def invert_implied_volatility(
        cls,
        spot: float,
        strike: float,
        t_years: float,
        market_price: float,
        option_type: Literal["CE", "PE"] = "CE",
        r: float = DEFAULT_R,
        q: float = DEFAULT_Q,
        max_iterations: int = 100,
        tolerance: float = 1e-4
    ) -> float:
        """Inverts implied volatility (IV) using Newton-Raphson with fail-safe bisection fallback.
        
        Guarantees zero division-by-zero errors for deep ITM and deep OTM strikes.
        """
        if t_years <= 1e-7 or market_price <= 0.05:
            return 0.15  # Baseline fallback

        # 1. Theoretical Intrinsic Value Check
        exp_qt = math.exp(-q * t_years)
        exp_rt = math.exp(-r * t_years)
        intrinsic = max(0.0, spot * exp_qt - strike * exp_rt) if option_type == "CE" else max(0.0, strike * exp_rt - spot * exp_qt)

        if market_price <= intrinsic + 0.01:
            # Trading at intrinsic floor
            return 0.01

        # 2. Seed Initialization via Brenner-Subrahmanyam (1988)
        sqrt_t = math.sqrt(t_years)
        seed_vol = math.sqrt(2.0 * math.pi / max(1e-7, t_years)) * (market_price / spot)
        sigma = max(0.05, min(2.50, seed_vol))

        # 3. Newton-Raphson Iteration
        for _ in range(max_iterations):
            theo = cls.calculate_price(spot, strike, t_years, sigma, option_type=option_type, r=r, q=q)
            diff = theo - market_price

            if abs(diff) < tolerance:
                return round(sigma, 4)

            # Compute Vega derivative dP / dSigma
            d1, _ = cls.calculate_d1_d2(spot, strike, t_years, sigma, r=r, q=q)
            vega = spot * exp_qt * sqrt_t * norm_pdf(d1)

            if vega < 1e-6:
                # Vega vanishes on deep OTM or deep ITM: break to bisection
                break

            step = diff / vega
            sigma_next = sigma - step

            if sigma_next <= 0.005 or sigma_next >= 4.0:
                # Stepped out of bounds: break to bisection
                break

            sigma = sigma_next

        # 4. Fail-Safe Bisection Solver (Guaranteed Convergence)
        low_vol = 0.005
        high_vol = 4.0

        for _ in range(50):
            mid_vol = 0.5 * (low_vol + high_vol)
            mid_price = cls.calculate_price(spot, strike, t_years, mid_vol, option_type=option_type, r=r, q=q)
            diff = mid_price - market_price

            if abs(diff) < tolerance:
                return round(mid_vol, 4)

            if diff > 0:
                high_vol = mid_vol
            else:
                low_vol = mid_vol

        return round(0.5 * (low_vol + high_vol), 4)


# ==============================================================================
# 5. NIFTY 50 OPTION CHAIN LATTICE & GANN STRIKE MAPPER
# ==============================================================================

class NiftyOptionChainEngine:
    """Constructs dynamic 50-point strike lattices and maps Gann harmonic levels to active strikes."""

    STRIKE_INTERVAL: float = 50.0

    def __init__(
        self,
        bsm_engine: Optional[BSMOptionEngine] = None,
        expiry_engine: Optional[ExpiryCalendarEngine] = None
    ):
        self.bsm = bsm_engine or BSMOptionEngine()
        self.expiry = expiry_engine or ExpiryCalendarEngine()

    def generate_option_chain(
        self,
        spot: float,
        eval_datetime: datetime,
        base_iv: float = 0.145,  # 14.5% baseline Nifty IV
        strikes_above_below: int = 10,
        gann_price_levels: Optional[List[float]] = None,
        r: float = BSMOptionEngine.DEFAULT_R,
        q: float = BSMOptionEngine.DEFAULT_Q
    ) -> List[OptionStrikeRow]:
        """Generates a complete European option chain lattice centered around spot index CMP."""
        # 1. Determine ATM strike rounded to nearest 50 points
        atm_strike = round(spot / self.STRIKE_INTERVAL) * self.STRIKE_INTERVAL

        # 2. Time-to-maturity
        t_years = self.expiry.calculate_time_to_maturity_years(eval_datetime)

        # 3. Generate strike range
        strikes = [
            atm_strike + i * self.STRIKE_INTERVAL
            for i in range(-strikes_above_below, strikes_above_below + 1)
        ]

        chain_rows: List[OptionStrikeRow] = []

        for k in strikes:
            dist = k - spot
            is_atm = (k == atm_strike)

            # Volatility smile curve: slight skew higher on OTM Puts (downside crash protection)
            moneyness = math.log(k / spot)
            skew_vol = base_iv + (-0.08 * moneyness) + (0.12 * moneyness * moneyness)
            strike_iv = max(0.08, min(0.60, skew_vol))

            # Call Greeks
            cg = self.bsm.calculate_greeks(spot, k, t_years, strike_iv, option_type="CE", r=r, q=q)
            # Put Greeks
            pg = self.bsm.calculate_greeks(spot, k, t_years, strike_iv, option_type="PE", r=r, q=q)

            # Nearest Gann Harmonic Level
            nearest_gann = k
            gann_text = "Standard Strike"
            if gann_price_levels:
                best_dist = float("inf")
                for gl in gann_price_levels:
                    d = abs(k - gl)
                    if d < best_dist:
                        best_dist = d
                        nearest_gann = gl
                if best_dist <= 15.0:
                    gann_text = f"Sq9 Harmonic Alignment (Δ={best_dist:.1f}pts)"

            chain_rows.append(OptionStrikeRow(
                strike=k,
                is_atm=is_atm,
                distance_to_spot=round(dist, 1),
                call_price=cg.theoretical_price,
                call_iv=cg.implied_volatility,
                call_delta=cg.delta,
                call_gamma=cg.gamma,
                call_theta=cg.theta_daily,
                call_vega=cg.vega_per_pct,
                put_price=pg.theoretical_price,
                put_iv=pg.implied_volatility,
                put_delta=pg.delta,
                put_gamma=pg.gamma,
                put_theta=pg.theta_daily,
                put_vega=pg.vega_per_pct,
                nearest_gann_level=nearest_gann,
                gann_alignment_text=gann_text
            ))

        return chain_rows

    def to_dataframe(self, chain_rows: List[OptionStrikeRow]) -> pd.DataFrame:
        """Serializes option chain rows into an institutional DataFrame view."""
        data = []
        for r in chain_rows:
            data.append({
                "STRIKE": r.strike,
                "IS_ATM": r.is_atm,
                "DIFF_SPOT": r.distance_to_spot,
                "CE_PRICE": r.call_price,
                "CE_DELTA": r.call_delta,
                "CE_GAMMA": r.call_gamma,
                "CE_THETA": r.call_theta,
                "CE_VEGA": r.call_vega,
                "PE_PRICE": r.put_price,
                "PE_DELTA": r.put_delta,
                "PE_GAMMA": r.put_gamma,
                "PE_THETA": r.put_theta,
                "PE_VEGA": r.put_vega,
                "GANN_ALIGNMENT": r.gann_alignment_text
            })
        return pd.DataFrame(data)
