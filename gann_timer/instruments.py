"""Skill 4 – Instrument universe and hard gold/silver exclusion."""
from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# CRITICAL CONSTRAINT: gold and silver are excluded from every feed, tracker,
# alert and export.  The pattern is checked at config load, routing and output.
# ---------------------------------------------------------------------------
EXCLUDED_PATTERN = re.compile(r"GOLD|SILVER|BULLION", re.IGNORECASE)


class ExcludedInstrumentError(ValueError):
    """Raised if a gold/silver instrument ever reaches the tracking layer."""


def is_excluded(symbol: str) -> bool:
    return bool(EXCLUDED_PATTERN.search(symbol or ""))


def assert_allowed(symbols) -> list[str]:
    bad = [s for s in symbols if is_excluded(s)]
    if bad:
        raise ExcludedInstrumentError(f"Gold/silver instruments are prohibited: {bad}")
    return list(symbols)


def filter_allowed(symbols) -> list[str]:
    return [s for s in symbols if not is_excluded(s)]


@dataclass(frozen=True)
class Segment:
    key: str
    label: str
    exchange_session: str          # "NSE" or "MCX" – selects trading hours
    symbols: tuple[str, ...]
    rulers: tuple[str, ...] | None  # None = all bodies relevant
    strike_step: float | None = None


_SEGMENTS = [
    Segment(
        key="INDEX",
        label="Broad Indices (NSE + BSE)",
        exchange_session="NSE",
        symbols=("NIFTY 50", "NIFTY NEXT 50", "NIFTY 100", "NIFTY 200", "NIFTY 500",
                 "NIFTY BANK", "NIFTY MIDCAP 100",
                 "SENSEX", "BSE 100", "BSE 200", "BSE 500", "BANKEX"),
        rulers=None,
    ),
    Segment(
        key="OPTIONS",
        label="NSE Nifty 50 Options",
        exchange_session="NSE",
        symbols=("NIFTY 50 OPT (CE/PE)",),
        rulers=None,
        strike_step=50.0,
    ),
    Segment(
        key="MCX_ENERGY",
        label="MCX Energy Futures",
        exchange_session="MCX",
        symbols=("CRUDEOIL", "CRUDEOILM", "NATURALGAS", "NATGASMINI"),
        # Neptune: oil/gas, Pluto: underground resources, Mars: combustion, Jupiter: expansion
        rulers=("Neptune", "Pluto", "Mars", "Jupiter"),
    ),
    Segment(
        key="MCX_METALS",
        label="MCX Base Metals Futures",
        exchange_session="MCX",
        symbols=("COPPER", "ZINC", "ZINCMINI", "ALUMINIUM", "ALUMINI", "LEAD", "LEADMINI", "NICKEL"),
        # Venus: copper, Saturn: lead, Mars: nickel/iron group, Uranus: aluminium, Jupiter: zinc/tin
        rulers=("Venus", "Saturn", "Mars", "Uranus", "Jupiter"),
    ),
]

# Layer 1: validate at import time – the app refuses to start if config is polluted.
for _seg in _SEGMENTS:
    assert_allowed(_seg.symbols)

SEGMENTS: dict[str, Segment] = {s.key: s for s in _SEGMENTS}

# UI instrument choices -> segment keys
INSTRUMENT_CHOICES: dict[str, tuple[str, ...]] = {
    "Index (NSE/BSE)": ("INDEX",),
    "Nifty 50 Options": ("OPTIONS",),
    "MCX Energy": ("MCX_ENERGY",),
    "MCX Base Metals": ("MCX_METALS",),
    "MCX (Energy + Base Metals)": ("MCX_ENERGY", "MCX_METALS"),
}


def segments_for_choice(choice: str) -> list[Segment]:
    return [SEGMENTS[k] for k in INSTRUMENT_CHOICES[choice]]


def symbols_for(segments, bodies: tuple[str, ...] = ()) -> list[str]:
    """Layer 2: route a trigger to symbols, never returning excluded instruments."""
    out: list[str] = []
    for seg in segments:
        if seg.rulers is None or not bodies or any(b in seg.rulers for b in bodies):
            out.extend(seg.symbols)
    return filter_allowed(dict.fromkeys(out))
