"""View 1: Master Control Deck (Celestial Cards, Session Timeline, Harmonic Price Levels)."""
from __future__ import annotations

import customtkinter as ctk
from datetime import datetime
from typing import Dict, List, Optional

from ui.theme import ThemeTokens


class ControlDeckView(ctk.CTkScrollableFrame):
    """Primary control desk displaying real-time celestial states and price levels."""

    def __init__(self, master, theme: ThemeTokens, **kwargs):
        super().__init__(master, fg_color=theme.bg_primary, **kwargs)
        self.theme = theme

        self._build_header_cards()
        self._build_planets_grid()
        self._build_price_levels_table()

    def _build_header_cards(self):
        """Top summary strip: Active Script, Session Circle, Solar Noon, 50% Equilibrium."""
        self.summary_frame = ctk.CTkFrame(self, fg_color=self.theme.bg_card, corner_radius=8)
        self.summary_frame.pack(fill="x", padx=12, pady=(8, 12))

        # Script Price Card
        self.card_price = ctk.CTkFrame(self.summary_frame, fg_color="transparent")
        self.card_price.pack(side="left", padx=16, pady=10, fill="both", expand=True)

        ctk.CTkLabel(
            self.card_price, text="ACTIVE INSTRUMENT", font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.theme.text_muted
        ).pack(anchor="w")

        self.lbl_script_name = ctk.CTkLabel(
            self.card_price, text="Nifty 50 Index (^NSEI)", font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.theme.text_primary
        )
        self.lbl_script_name.pack(anchor="w")

        self.lbl_cmp = ctk.CTkLabel(
            self.card_price, text="24,200.00 pts", font=ctk.CTkFont(family="Consolas", size=18, weight="bold"),
            text_color=self.theme.accent_blue
        )
        self.lbl_cmp.pack(anchor="w")

        # Session Circle Progress Card
        self.card_session = ctk.CTkFrame(self.summary_frame, fg_color="transparent")
        self.card_session.pack(side="left", padx=16, pady=10, fill="both", expand=True)

        ctk.CTkLabel(
            self.card_session, text="SESSION WHEEL PROGRESS", font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.theme.text_muted
        ).pack(anchor="w")

        self.lbl_session_pct = ctk.CTkLabel(
            self.card_session, text="0.0% Elapsed", font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.theme.text_primary
        )
        self.lbl_session_pct.pack(anchor="w")

        self.lbl_session_deg = ctk.CTkLabel(
            self.card_session, text="0.0° / 360°", font=ctk.CTkFont(family="Consolas", size=18, weight="bold"),
            text_color=self.theme.accent_amber
        )
        self.lbl_session_deg.pack(anchor="w")

        # True Solar Noon Card
        self.card_noon = ctk.CTkFrame(self.summary_frame, fg_color="transparent")
        self.card_noon.pack(side="left", padx=16, pady=10, fill="both", expand=True)

        ctk.CTkLabel(
            self.card_noon, text="TRUE SOLAR NOON (MUMBAI)", font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.theme.text_muted
        ).pack(anchor="w")

        self.lbl_noon_time = ctk.CTkLabel(
            self.card_noon, text="12:22:12 IST", font=ctk.CTkFont(family="Consolas", size=18, weight="bold"),
            text_color=self.theme.accent_purple
        )
        self.lbl_noon_time.pack(anchor="w", pady=(2, 0))

        # 50% Equilibrium Level Card
        self.card_eq = ctk.CTkFrame(self.summary_frame, fg_color="transparent")
        self.card_eq.pack(side="left", padx=16, pady=10, fill="both", expand=True)

        ctk.CTkLabel(
            self.card_eq, text="50% EQUILIBRIUM PIVOT", font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.theme.text_muted
        ).pack(anchor="w")

        self.lbl_eq_price = ctk.CTkLabel(
            self.card_eq, text="24,180.00 pts", font=ctk.CTkFont(family="Consolas", size=18, weight="bold"),
            text_color=self.theme.accent_green
        )
        self.lbl_eq_price.pack(anchor="w", pady=(2, 0))

    def _build_planets_grid(self):
        """Container for planetary telemetry cards."""
        sec_title = ctk.CTkLabel(
            self, text="ACTIVE CELESTIAL TELEMETRY (CONTINUOUS SESSION)",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=self.theme.text_secondary
        )
        sec_title.pack(anchor="w", padx=14, pady=(6, 4))

        self.planets_container = ctk.CTkFrame(self, fg_color="transparent")
        self.planets_container.pack(fill="x", padx=10, pady=2)

        # We will populate up to 10 celestial cards in 2 rows of 5
        self.planet_cards: dict[str, dict] = {}
        bodies = ["SUN", "MOON", "MERCURY", "VENUS", "MARS", "JUPITER", "SATURN", "URANUS", "NEPTUNE", "PLUTO"]

        for i, b in enumerate(bodies):
            r = i // 5
            c = i % 5

            p_card = ctk.CTkFrame(self.planets_container, fg_color=self.theme.bg_card, corner_radius=6)
            p_card.grid(row=r, column=c, padx=4, pady=4, sticky="nsew")
            self.planets_container.grid_columnconfigure(c, weight=1)

            lbl_name = ctk.CTkLabel(
                p_card, text=b, font=ctk.CTkFont(size=11, weight="bold"),
                text_color=self.theme.accent_blue
            )
            lbl_name.pack(anchor="w", padx=8, pady=(4, 0))

            lbl_lon = ctk.CTkLabel(
                p_card, text="--.--°", font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
                text_color=self.theme.text_primary
            )
            lbl_lon.pack(anchor="w", padx=8)

            lbl_zod = ctk.CTkLabel(
                p_card, text="-- --° --'", font=ctk.CTkFont(size=9),
                text_color=self.theme.text_secondary
            )
            lbl_zod.pack(anchor="w", padx=8)

            lbl_speed = ctk.CTkLabel(
                p_card, text="+0.0000°/hr [DIRECT]", font=ctk.CTkFont(size=9),
                text_color=self.theme.accent_green
            )
            lbl_speed.pack(anchor="w", padx=8, pady=(0, 4))

            self.planet_cards[b] = {
                "lon": lbl_lon,
                "zod": lbl_zod,
                "speed": lbl_speed
            }

    def _build_price_levels_table(self):
        """Displays calculated Gann harmonic price levels around CMP."""
        sec_title = ctk.CTkLabel(
            self, text="GANN HARMONIC PRICE LEVELS (SQUARE OF NINE & SCALE OCTAVES)",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=self.theme.text_secondary
        )
        sec_title.pack(anchor="w", padx=14, pady=(12, 4))

        self.table_frame = ctk.CTkFrame(self, fg_color=self.theme.bg_card, corner_radius=6)
        self.table_frame.pack(fill="x", padx=12, pady=(2, 16))

        # Header Row
        cols = ["Harmonic Level Description", "Type", "Harmonic Price", "Distance to CMP", "Actionable Role"]
        hdr = ctk.CTkFrame(self.table_frame, fg_color=self.theme.bg_accent, height=28, corner_radius=4)
        hdr.pack(fill="x", padx=4, pady=4)

        for col in cols:
            ctk.CTkLabel(
                hdr, text=col, font=ctk.CTkFont(size=10, weight="bold"),
                text_color=self.theme.text_secondary
            ).pack(side="left", expand=True)

        self.rows_container = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        self.rows_container.pack(fill="x", padx=4, pady=(0, 4))

    def update_telemetry(self, state_snapshot: dict):
        """Updates summary values, planet cards, and price levels."""
        m_status = state_snapshot.get("market_status", "OPEN")
        status_msg = state_snapshot.get("status_message", "Normal Trading")

        if m_status in ("EXCHANGE_CLOSED", "WEEKEND_CLOSED"):
            self.lbl_cmp.configure(
                text=f"{status_msg}",
                font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
                text_color=self.theme.accent_amber
            )
            if "script_name" in state_snapshot:
                self.lbl_script_name.configure(text=f"{state_snapshot['script_name']} [EXCHANGE CLOSED]")
        else:
            if "cmp" in state_snapshot:
                self.lbl_cmp.configure(
                    text=f"{state_snapshot['cmp']:,.2f} pts",
                    font=ctk.CTkFont(family="Consolas", size=18, weight="bold"),
                    text_color=self.theme.accent_blue
                )
            if "script_name" in state_snapshot:
                self.lbl_script_name.configure(text=state_snapshot["script_name"])

        if "session_pct" in state_snapshot:
            self.lbl_session_pct.configure(text=f"{state_snapshot['session_pct']:.1f}% Elapsed")
        if "session_deg" in state_snapshot:
            self.lbl_session_deg.configure(text=f"{state_snapshot['session_deg']:.1f}° / 360°")
        if "noon_time" in state_snapshot:
            self.lbl_noon_time.configure(text=state_snapshot["noon_time"])
        if "equilibrium_price" in state_snapshot:
            self.lbl_eq_price.configure(text=f"{state_snapshot['equilibrium_price']:,.2f} pts")

        # Update planet cards
        planets = state_snapshot.get("planets", {})
        for name, p_data in planets.items():
            if name in self.planet_cards:
                c = self.planet_cards[name]
                c["lon"].configure(text=f"{p_data.get('lon', 0.0):.2f}°")
                c["zod"].configure(text=p_data.get("zodiac", ""))
                speed_val = p_data.get("speed", 0.0)
                state_str = p_data.get("state", "DIRECT")
                c_color = self.theme.accent_red if state_str == "RETROGRADE" else self.theme.accent_green
                c["speed"].configure(text=f"{speed_val:+.4f}°/hr [{state_str}]", text_color=c_color)

        # Update price table
        for w in self.rows_container.winfo_children():
            w.destroy()

        levels = state_snapshot.get("price_levels", [])
        cmp_val = state_snapshot.get("cmp", 0.0)
        for pl in levels[:10]:
            r_frame = ctk.CTkFrame(self.rows_container, fg_color="transparent", height=24)
            r_frame.pack(fill="x", pady=1)

            p_val = pl.get("price", 0.0)
            diff = pl.get("distance", 0.0)
            is_sup = p_val <= cmp_val
            role_text = "SUPPORT" if is_sup else "RESISTANCE"
            role_color = self.theme.accent_green if is_sup else self.theme.accent_red

            ctk.CTkLabel(r_frame, text=pl.get("label", ""), font=ctk.CTkFont(size=10), text_color=self.theme.text_primary).pack(side="left", expand=True)
            ctk.CTkLabel(r_frame, text=pl.get("type", ""), font=ctk.CTkFont(size=9), text_color=self.theme.text_muted).pack(side="left", expand=True)
            ctk.CTkLabel(r_frame, text=f"{p_val:,.2f}", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color=self.theme.text_primary).pack(side="left", expand=True)
            ctk.CTkLabel(r_frame, text=f"{diff:+,.2f}", font=ctk.CTkFont(family="Consolas", size=10), text_color=self.theme.text_secondary).pack(side="left", expand=True)
            ctk.CTkLabel(r_frame, text=role_text, font=ctk.CTkFont(size=9, weight="bold"), text_color=role_color).pack(side="left", expand=True)
