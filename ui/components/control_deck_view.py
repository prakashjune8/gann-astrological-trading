"""View 1: Master Control Deck (Celestial Cards, Session Timeline, Confluence Radar & Harmonic Price Levels)."""
from __future__ import annotations

import customtkinter as ctk
from datetime import datetime
from typing import Dict, List, Optional

from ui.theme import ThemeTokens


class ControlDeckView(ctk.CTkScrollableFrame):
    """Primary control desk displaying real-time celestial states, confluence radar, and harmonic levels."""

    def __init__(self, master, theme: ThemeTokens, **kwargs):
        super().__init__(master, fg_color=theme.bg_primary, **kwargs)
        self.theme = theme

        self._build_confluence_radar()
        self._build_header_cards()
        self._build_macro_velocity_cards()
        self._build_planets_grid()
        self._build_price_levels_table()

    def apply_theme(self, theme: ThemeTokens):
        """Update colors dynamically when theme toggles."""
        self.theme = theme
        self.configure(fg_color=theme.bg_primary)
        if hasattr(self, "radar_frame"):
            self.radar_frame.configure(fg_color=theme.bg_card)
        if hasattr(self, "summary_frame"):
            self.summary_frame.configure(fg_color=theme.bg_card)
        if hasattr(self, "macro_frame"):
            self.macro_frame.configure(fg_color=theme.bg_card)
        if hasattr(self, "table_frame"):
            self.table_frame.configure(fg_color=theme.bg_card)

    def _build_confluence_radar(self):
        """Top Triple Confluence Cluster Node Sniper Radar (Level 3 Pinnacle)."""
        self.radar_frame = ctk.CTkFrame(self, fg_color=self.theme.bg_card, corner_radius=8)
        self.radar_frame.pack(fill="x", padx=12, pady=(6, 6))

        top_radar = ctk.CTkFrame(self.radar_frame, fg_color="transparent")
        top_radar.pack(fill="x", padx=14, pady=(8, 4))

        lbl_r_title = ctk.CTkLabel(
            top_radar,
            text="⚡ TRIPLE CONFLUENCE CLUSTER RADAR (PRICE • TIME • ASTRO GATES)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=self.theme.accent_amber
        )
        lbl_r_title.pack(side="left")

        # Three Gate Status Badges
        gates_box = ctk.CTkFrame(top_radar, fg_color="transparent")
        gates_box.pack(side="right")

        self.badge_price = ctk.CTkLabel(
            gates_box, text="[PRICE GATE: AWAITING]",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=self.theme.text_muted
        )
        self.badge_price.pack(side="left", padx=4)

        self.badge_time = ctk.CTkLabel(
            gates_box, text="[TIME GATE: AWAITING]",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=self.theme.text_muted
        )
        self.badge_time.pack(side="left", padx=4)

        self.badge_astro = ctk.CTkLabel(
            gates_box, text="[ASTRO GATE: AWAITING]",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=self.theme.text_muted
        )
        self.badge_astro.pack(side="left", padx=4)

        # Sniper Trade Execution Card (Appears on Triple Confluence)
        self.sniper_box = ctk.CTkFrame(self.radar_frame, fg_color=self.theme.bg_accent, corner_radius=6)
        self.sniper_box.pack(fill="x", padx=12, pady=(2, 8))

        self.lbl_sniper_details = ctk.CTkLabel(
            self.sniper_box,
            text="MONITORING THREE INDEPENDENT DIMENSIONS • Awaiting simultaneous mathematical lock...",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=self.theme.text_secondary,
            anchor="w"
        )
        self.lbl_sniper_details.pack(fill="x", padx=10, pady=6)

    def _build_header_cards(self):
        """Summary strip: Active Script, Session Circle, Solar Noon, 50% Equilibrium."""
        self.summary_frame = ctk.CTkFrame(self, fg_color=self.theme.bg_card, corner_radius=8)
        self.summary_frame.pack(fill="x", padx=12, pady=(0, 6))

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
            self.card_noon, text="TRUE SOLAR NOON", font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.theme.text_muted
        ).pack(anchor="w")

        self.lbl_noon_time = ctk.CTkLabel(
            self.card_noon, text="12:22:12 IST (Mumbai)", font=ctk.CTkFont(family="Consolas", size=16, weight="bold"),
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

    def _build_macro_velocity_cards(self):
        """Level 3 Strip: 1x1 Velocity Speedometer, Z-Axis Parallels, Macro Planetary Gears."""
        self.macro_frame = ctk.CTkFrame(self, fg_color=self.theme.bg_card, corner_radius=8)
        self.macro_frame.pack(fill="x", padx=12, pady=(0, 6))

        # 1x1 Velocity Speedometer Card
        card_v = ctk.CTkFrame(self.macro_frame, fg_color="transparent")
        card_v.pack(side="left", padx=16, pady=8, fill="both", expand=True)

        ctk.CTkLabel(card_v, text="1x1 SPEEDOMETER VELOCITY", font=ctk.CTkFont(size=10, weight="bold"), text_color=self.theme.text_muted).pack(anchor="w")
        self.lbl_velocity_status = ctk.CTkLabel(card_v, text="HARMONIC EQUILIBRIUM", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.theme.accent_green)
        self.lbl_velocity_status.pack(anchor="w")
        self.lbl_velocity_details = ctk.CTkLabel(card_v, text="Rail: 24,180.0 | Dev: +0.0 pts", font=ctk.CTkFont(family="Consolas", size=10), text_color=self.theme.text_secondary)
        self.lbl_velocity_details.pack(anchor="w")

        # Z-Axis Declination Parallels Card
        card_z = ctk.CTkFrame(self.macro_frame, fg_color="transparent")
        card_z.pack(side="left", padx=16, pady=8, fill="both", expand=True)

        ctk.CTkLabel(card_z, text="DECLINATION (Z-AXIS) MONITOR", font=ctk.CTkFont(size=10, weight="bold"), text_color=self.theme.text_muted).pack(anchor="w")
        self.lbl_decl_status = ctk.CTkLabel(card_z, text="NO ACTIVE PARALLELS", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.theme.text_secondary)
        self.lbl_decl_status.pack(anchor="w")
        self.lbl_decl_details = ctk.CTkLabel(card_z, text="Solstice Max: ±23.44° | Orb: 0.35°", font=ctk.CTkFont(family="Consolas", size=10), text_color=self.theme.text_muted)
        self.lbl_decl_details.pack(anchor="w")

        # Nested Macro Gears Card
        card_g = ctk.CTkFrame(self.macro_frame, fg_color="transparent")
        card_g.pack(side="left", padx=16, pady=8, fill="both", expand=True)

        ctk.CTkLabel(card_g, text="NESTED MACRO TIME GEARS", font=ctk.CTkFont(size=10, weight="bold"), text_color=self.theme.text_muted).pack(anchor="w")
        self.lbl_macro_gears = ctk.CTkLabel(card_g, text="Jupiter-Saturn: 20-Yr Synod", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.theme.accent_blue)
        self.lbl_macro_gears.pack(anchor="w")
        self.lbl_macro_details = ctk.CTkLabel(card_g, text="Mars-Jupiter: 2.21-Yr | Saros Series 145", font=ctk.CTkFont(family="Consolas", size=10), text_color=self.theme.text_secondary)
        self.lbl_macro_details.pack(anchor="w")

    def _build_planets_grid(self):
        """Container for planetary telemetry cards."""
        sec_title = ctk.CTkLabel(
            self, text="ACTIVE CELESTIAL TELEMETRY (CONTINUOUS SESSION)",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=self.theme.text_secondary
        )
        sec_title.pack(anchor="w", padx=14, pady=(4, 2))

        self.planets_container = ctk.CTkFrame(self, fg_color="transparent")
        self.planets_container.pack(fill="x", padx=10, pady=2)

        self.planet_cards: dict[str, dict] = {}
        bodies = ["SUN", "MOON", "MERCURY", "VENUS", "MARS", "JUPITER", "SATURN", "URANUS", "NEPTUNE", "PLUTO"]

        for i, b in enumerate(bodies):
            r = i // 5
            c = i % 5

            p_card = ctk.CTkFrame(self.planets_container, fg_color=self.theme.bg_card, corner_radius=6)
            p_card.grid(row=r, column=c, padx=4, pady=3, sticky="nsew")
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
            self, text="GANN HARMONIC PRICE LEVELS (SQUARE OF NINE, OCTAVES & CARDINAL CROSSES)",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=self.theme.text_secondary
        )
        sec_title.pack(anchor="w", padx=14, pady=(8, 4))

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
        """Updates summary values, planet cards, confluence radar, and price levels."""
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

        # Update Confluence Radar
        conf_data = state_snapshot.get("confluence", {})
        gate_p = conf_data.get("gate_price", False)
        gate_t = conf_data.get("gate_time", False)
        gate_a = conf_data.get("gate_astro", False)
        is_all = conf_data.get("is_all_confluent", False)
        setup = conf_data.get("trade_setup", None)

        self.badge_price.configure(
            text="[PRICE GATE: LOCKED]" if gate_p else "[PRICE GATE: AWAITING]",
            text_color=self.theme.accent_green if gate_p else self.theme.text_muted
        )
        self.badge_time.configure(
            text="[TIME GATE: LOCKED]" if gate_t else "[TIME GATE: AWAITING]",
            text_color=self.theme.accent_green if gate_t else self.theme.text_muted
        )
        self.badge_astro.configure(
            text="[ASTRO GATE: LOCKED]" if gate_a else "[ASTRO GATE: AWAITING]",
            text_color=self.theme.accent_green if gate_a else self.theme.text_muted
        )

        if is_all and setup:
            self.sniper_box.configure(fg_color="#064e3b")  # Emerald dark
            self.lbl_sniper_details.configure(
                text=(f"🎯 TRIPLE CONFLUENCE SNIPER TRIGGER: {setup.direction} @ {setup.entry_price:,.1f} | "
                      f"Hard Stop: {setup.hard_stop_loss:,.1f} (-{setup.risk_pts:.0f} pts) | "
                      f"T1: {setup.target_1:,.1f} | T2: {setup.target_2:,.1f} | R:R 1:{setup.risk_reward_ratio:.1f}"),
                text_color="#a7f3d0",
                font=ctk.CTkFont(family="Consolas", size=10, weight="bold")
            )
        else:
            self.sniper_box.configure(fg_color=self.theme.bg_accent)
            p_desc = conf_data.get("price_desc", "Monitoring Level Distance")
            t_desc = conf_data.get("time_desc", "Monitoring Node Proximity")
            self.lbl_sniper_details.configure(
                text=f"STATUS: {p_desc}  •  {t_desc}",
                text_color=self.theme.text_secondary,
                font=ctk.CTkFont(family="Segoe UI", size=10)
            )

        # Update Velocity & Declination Cards
        vel_info = state_snapshot.get("velocity_1x1", {})
        if vel_info:
            v_status = vel_info.get("status", "EQUILIBRIUM")
            v_color = self.theme.accent_green if "BULLISH" in v_status else (self.theme.accent_red if "BEARISH" in v_status else self.theme.text_primary)
            self.lbl_velocity_status.configure(text=v_status, text_color=v_color)
            self.lbl_velocity_details.configure(text=f"Rail: {vel_info.get('rail_price', 0.0):,.1f} | Dev: {vel_info.get('diff_pts', 0.0):+,.1f} pts")

        parallels = state_snapshot.get("declination_parallels", [])
        if parallels:
            p0 = parallels[0]
            p_type = p0.aspect_type
            p_color = self.theme.accent_amber if p0.is_exact else self.theme.accent_blue
            self.lbl_decl_status.configure(text=f"{p0.body_a} ∥ {p0.body_b} ({p_type[:4]})", text_color=p_color)
            self.lbl_decl_details.configure(text=f"Orb: {p0.orb_deg:.2f}° {'[EXACT PARALLEL]' if p0.is_exact else ''}")
        else:
            self.lbl_decl_status.configure(text="NO ACTIVE PARALLELS", text_color=self.theme.text_muted)
            self.lbl_decl_details.configure(text="Z-Axis Equilibrium Maintained")

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
        for pl in levels[:12]:
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
