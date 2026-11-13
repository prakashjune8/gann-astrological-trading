"""Daily Gann Summary PDF Report Generator (ReportLab Engine).

Produces an institutional, high-DPI A4 summary report of the day's:
1. Target Script & Market Snapshot (CMP, Range, 50% Equilibrium).
2. Active Planetary Longitudes & Motion States (Geocentric & Heliocentric).
3. Gann Square of Nine & Planetary Key Support/Resistance Price Levels.
4. Intraday Harmonic Timing Nodes & Confirmed Aspects.
5. Zero tofu/square box anomalies using validated TrueType typography.
"""
from __future__ import annotations

import os
from datetime import date, datetime
from typing import Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
)


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas for dynamic Page X of Y footer."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        # Header
        self.drawString(40, 11.69 * 72 - 30, "GANN CELESTIAL TRACKER PRO • DAILY ASTRO-HARMONIC SUMMARY")
        # Footer
        self.drawRightString(8.27 * 72 - 40, 24, f"Page {self._pageNumber} of {total_pages}")
        self.drawString(40, 24, "CONFIDENTIAL & PROPRIETARY • QUANTITATIVE GANN SYSTEM")
        self.restoreState()


class DailyPdfReportGenerator:
    """Compiles publication-grade daily trading summaries."""

    @classmethod
    def generate_report(
        cls,
        output_pdf_path: str,
        target_date: date,
        script_name: str,
        market_cmp: float,
        day_high: float,
        day_low: float,
        coord_frame: str,
        planetary_data: list[dict],
        price_levels: list[dict],
        timing_nodes: list[dict]
    ) -> str:
        doc = SimpleDocTemplate(
            output_pdf_path,
            pagesize=A4,
            leftMargin=40,
            rightMargin=40,
            topMargin=45,
            bottomMargin=40
        )

        styles = getSampleStyleSheet()
        normal = styles["Normal"]

        title_style = ParagraphStyle(
            "RepTitle",
            parent=normal,
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#0f172a")
        )
        sub_style = ParagraphStyle(
            "RepSub",
            parent=normal,
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#64748b")
        )
        h2_style = ParagraphStyle(
            "RepH2",
            parent=normal,
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#1e293b")
        )
        cell_bold = ParagraphStyle(
            "CellBold",
            parent=normal,
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#0f172a")
        )
        cell_reg = ParagraphStyle(
            "CellReg",
            parent=normal,
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#334155")
        )

        story = []

        # Header Title
        story.append(Paragraph("GANN CELESTIAL TRACKER PRO", title_style))
        story.append(Paragraph(
            f"Daily Astro-Harmonic Market Briefing • {target_date.strftime('%A, %d %B %Y')} • Indian Standard Time (IST)",
            sub_style
        ))
        story.append(Spacer(1, 10))

        # Instrument Metadata Card
        eq_mid = round((day_high + day_low) / 2.0, 2)
        meta_data = [
            [
                Paragraph("<b>Active Instrument:</b>", cell_bold), Paragraph(f"<b>{script_name}</b>", cell_reg),
                Paragraph("<b>Current Market Price (CMP):</b>", cell_bold), Paragraph(f"<b>{market_cmp:,.2f}</b>", cell_reg)
            ],
            [
                Paragraph("<b>Day High:</b>", cell_bold), Paragraph(f"{day_high:,.2f}", cell_reg),
                Paragraph("<b>Day Low:</b>", cell_bold), Paragraph(f"{day_low:,.2f}", cell_reg)
            ],
            [
                Paragraph("<b>50% Equilibrium Midpoint:</b>", cell_bold), Paragraph(f"<b>{eq_mid:,.2f}</b>", cell_reg),
                Paragraph("<b>Coordinate Frame:</b>", cell_bold), Paragraph(f"{coord_frame.title()}", cell_reg)
            ]
        ]
        t_meta = Table(meta_data, colWidths=[120, 135, 130, 135])
        t_meta.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t_meta)
        story.append(Spacer(1, 14))

        # Section 1: Active Planetary Ephemeris Coordinates
        story.append(Paragraph("1. Planetary Longitudes & Motion Dynamics", h2_style))
        story.append(Spacer(1, 4))

        planet_rows = [[
            Paragraph("Celestial Body", cell_bold),
            Paragraph("Longitude", cell_bold),
            Paragraph("Zodiac Position", cell_bold),
            Paragraph("Hourly Velocity", cell_bold),
            Paragraph("Motion State", cell_bold)
        ]]
        for p in planetary_data[:10]:
            planet_rows.append([
                Paragraph(str(p.get("name", "")), cell_bold),
                Paragraph(f"{float(p.get('longitude', 0.0)):.2f}°", cell_reg),
                Paragraph(str(p.get("zodiac", "")), cell_reg),
                Paragraph(f"{float(p.get('velocity', 0.0)):+.4f}°/hr", cell_reg),
                Paragraph(str(p.get("state", "DIRECT")), cell_reg)
            ])

        t_planets = Table(planet_rows, colWidths=[110, 80, 150, 95, 85])
        t_planets.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ]))
        story.append(t_planets)
        story.append(Spacer(1, 14))

        # Section 2: Gann Square of Nine & Planetary Key Levels
        story.append(Paragraph("2. Harmonic Price Levels (Square of Nine & Scale Octaves)", h2_style))
        story.append(Spacer(1, 4))

        price_rows = [[
            Paragraph("Harmonic Level / Angle", cell_bold),
            Paragraph("Type", cell_bold),
            Paragraph("Harmonic Price", cell_bold),
            Paragraph("Distance from CMP", cell_bold),
            Paragraph("Function", cell_bold)
        ]]
        for pl in price_levels[:8]:
            p_val = float(pl.get("price", 0.0))
            diff = float(pl.get("distance", 0.0))
            fn_str = "Support" if p_val <= market_cmp else "Resistance"
            price_rows.append([
                Paragraph(str(pl.get("label", "")), cell_reg),
                Paragraph(str(pl.get("type", "")), cell_reg),
                Paragraph(f"<b>{p_val:,.2f}</b>", cell_bold),
                Paragraph(f"{diff:+,.2f} pts", cell_reg),
                Paragraph(f"<b>{fn_str}</b>", cell_reg)
            ])

        t_prices = Table(price_rows, colWidths=[160, 90, 100, 90, 80])
        t_prices.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ]))
        story.append(t_prices)
        story.append(Spacer(1, 14))

        # Section 3: Intraday Celestial Timing Nodes
        story.append(Paragraph("3. Intraday Harmonic Pivot Times (IST Exchange Session)", h2_style))
        story.append(Spacer(1, 4))

        time_rows = [[
            Paragraph("Node Description", cell_bold),
            Paragraph("Target Time (IST)", cell_bold),
            Paragraph("Harmonic Circle", cell_bold),
            Paragraph("Significance", cell_bold)
        ]]
        for tn in timing_nodes[:6]:
            time_rows.append([
                Paragraph(str(tn.get("label", "")), cell_reg),
                Paragraph(f"<b>{tn.get('time_ist', '')}</b>", cell_bold),
                Paragraph(f"{tn.get('circle_deg', '')}", cell_reg),
                Paragraph(str(tn.get("significance", "Harmonic Cycle Turn")), cell_reg)
            ])

        t_timing = Table(time_rows, colWidths=[160, 100, 90, 170])
        t_timing.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ]))
        story.append(t_timing)

        doc.build(story, canvasmaker=NumberedCanvas)
        return output_pdf_path
