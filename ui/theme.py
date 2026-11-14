"""Modern Institutional Theme Tokens for Dark & Light Trading Terminal Modes."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemeTokens:
    name: str
    bg_primary: str
    bg_secondary: str
    bg_card: str
    bg_accent: str
    border_color: str
    text_primary: str
    text_secondary: str
    text_muted: str
    accent_blue: str
    accent_green: str
    accent_red: str
    accent_amber: str
    accent_purple: str
    wheel_bg: str
    wheel_ring: str
    wheel_line: str


DARK_THEME = ThemeTokens(
    name="DARK",
    bg_primary="#0b0f19",       # Deepest obsidian canvas
    bg_secondary="#111827",     # Slate dark header & sidebar
    bg_card="#1a2234",          # Elevated card surfaces
    bg_accent="#1e293b",        # Active button & tab backgrounds
    border_color="#2d3748",     # Clean vector borders
    text_primary="#f8fafc",     # Crisp high-contrast white
    text_secondary="#cbd5e1",   # Light silver
    text_muted="#64748b",       # Cool slate grey
    accent_blue="#3b82f6",      # Primary institutional blue
    accent_green="#10b981",     # Bullish / Trine green
    accent_red="#ef4444",       # Bearish / Square red
    accent_amber="#f59e0b",     # Conjunction / Warning amber
    accent_purple="#8b5cf6",    # Semi-square violet
    wheel_bg="#0e1422",         # Rich celestial wheel disc
    wheel_ring="#253047",       # Ring boundaries
    wheel_line="#374151"        # Coordinate axes
)

LIGHT_THEME = ThemeTokens(
    name="LIGHT",
    bg_primary="#f8fafc",       # Clean crisp daylight canvas
    bg_secondary="#ffffff",     # White cards & panels
    bg_card="#ffffff",          # Card backgrounds
    bg_accent="#f1f5f9",        # Active buttons
    border_color="#cbd5e1",     # Subdued border
    text_primary="#0f172a",     # High-contrast charcoal slate
    text_secondary="#334155",   # Medium slate
    text_muted="#64748b",       # Muted annotations
    accent_blue="#2563eb",      # Vibrant blue
    accent_green="#059669",     # Emerald green
    accent_red="#dc2626",       # Crimson red
    accent_amber="#d97706",     # Rich amber
    accent_purple="#7c3aed",    # Royal purple
    wheel_bg="#f1f5f9",         # Light wheel background
    wheel_ring="#cbd5e1",       # Clean slate rings
    wheel_line="#e2e8f0"        # Subdued axes
)
