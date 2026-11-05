"""Alert Ledger View & Real-time Notification Banner."""
from __future__ import annotations

from datetime import datetime
import customtkinter as ctk
from ui.theme import ThemeTokens


class AlertLedgerView(ctk.CTkFrame):
    """Notification banner and chronological ledger of triggered harmonic events."""

    def __init__(self, master, theme: ThemeTokens, **kwargs):
        super().__init__(master, fg_color=theme.bg_secondary, height=130, **kwargs)
        self.theme = theme

        self._build_ui()

    def _build_ui(self):
        # Top banner strip
        self.banner_frame = ctk.CTkFrame(self, fg_color=self.theme.bg_accent, height=28, corner_radius=4)
        self.banner_frame.pack(fill="x", padx=10, pady=(6, 4))

        self.lbl_banner = ctk.CTkLabel(
            self.banner_frame,
            text="STATUS: Monitoring Continuous Session Timelines • All Alert Channels Armed",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.theme.accent_green
        )
        self.lbl_banner.pack(side="left", padx=10)

        # Scrollable ledger of events
        self.ledger_scroll = ctk.CTkScrollableFrame(self, fg_color=self.theme.bg_card, height=85)
        self.ledger_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        # Initial placeholder
        self.add_event("SYSTEM", "Engine initialized. Persistent SQLite ephemeris vault active.", "12:22:00 IST")

    def add_event(self, category: str, text: str, timestamp_str: str):
        row = ctk.CTkFrame(self.ledger_scroll, fg_color="transparent", height=20)
        row.pack(fill="x", pady=1)

        ctk.CTkLabel(
            row, text=timestamp_str, font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
            text_color=self.theme.text_muted, width=90
        ).pack(side="left")

        cat_color = self.theme.accent_blue
        if category == "ALERT":
            cat_color = self.theme.accent_amber
        elif category == "HIT":
            cat_color = self.theme.accent_green

        ctk.CTkLabel(
            row, text=f"[{category}]", font=ctk.CTkFont(size=9, weight="bold"),
            text_color=cat_color, width=70
        ).pack(side="left")

        ctk.CTkLabel(
            row, text=text, font=ctk.CTkFont(size=10),
            text_color=self.theme.text_primary, anchor="w"
        ).pack(side="left", fill="x", expand=True)

    def set_banner_alert(self, alert_text: str, is_critical: bool = False):
        color = self.theme.accent_red if is_critical else self.theme.accent_amber
        self.lbl_banner.configure(text=f"ACTIVE TRIGGER: {alert_text}", text_color=color)
