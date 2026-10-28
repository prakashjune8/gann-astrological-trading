import os
import sys
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

PDF_PATH = r"d:\ephemeris\Gann_Celestial_and_Midpoint_Trading_Handbook.pdf"

class NumberedCanvas(canvas.Canvas):
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

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#4a5568"))
        
        # Header (Pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "W. D. Gann Astro-Harmonic Market Timing & Midpoint Handbook")
            self.setStrokeColor(colors.HexColor("#cbd5e0"))
            self.setLineWidth(0.5)
            self.line(54, 742, 558, 742)

        # Footer (All Pages)
        self.setStrokeColor(colors.HexColor("#cbd5e0"))
        self.setLineWidth(0.5)
        self.line(54, 45, 558, 45)
        self.drawString(54, 32, "Confidential - For Quantitative & Technical Market Research")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 32, page_text)
        self.restoreState()


def build_pdf():
    doc = SimpleDocTemplate(
        PDF_PATH,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=60,
        bottomMargin=55
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#1a365d"),
        spaceAfter=8
    )

    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#4a5568"),
        spaceAfter=15
    )

    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#1a365d"),
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#2b6cb0"),
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#2d3748"),
        spaceAfter=8
    )

    body_bold = ParagraphStyle(
        'BodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    callout_style = ParagraphStyle(
        'Callout',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#2c5282")
    )

    formula_style = ParagraphStyle(
        'Formula',
        parent=styles['Normal'],
        fontName='Courier-Bold',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#742a2a")
    )

    table_header_style = ParagraphStyle(
        'TH',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.white
    )

    table_cell_style = ParagraphStyle(
        'TC',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#2d3748")
    )

    table_cell_bold = ParagraphStyle(
        'TCB',
        parent=table_cell_style,
        fontName='Helvetica-Bold'
    )

    story = []

    # =========================================================================
    # COVER / HEADER
    # =========================================================================
    story.append(Spacer(1, 10))
    story.append(Paragraph("W. D. GANN ASTRONOMICAL HARMONICS & INTRADAY MIDPOINT MANUAL", title_style))
    story.append(Paragraph("A Master Reference Guide for Quantitative Trading in Indian Equities, Options & Commodities (NSE, BSE, MCX)", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a365d"), spaceAfter=15))

    # Metadata Card
    meta_data = [
        [Paragraph("<b>Target Audience:</b> Quantitative Analysts & Professional Traders", table_cell_style),
         Paragraph("<b>Primary Engine:</b> NASA JPL Horizons + Python", table_cell_style)],
        [Paragraph("<b>Market Coverage:</b> NSE Nifty 50, Bank Nifty, BSE Sensex, MCX", table_cell_style),
         Paragraph("<b>Timezone Standard:</b> Indian Standard Time (IST, UTC+05:30)", table_cell_style)],
        [Paragraph("<b>App 1 (Astro Ephemeris):</b> <code>gann_timer/ui.py</code>", table_cell_style),
         Paragraph("<b>App 2 (Midpoint Calculator):</b> <code>gann_midpoint_app.py</code>", table_cell_style)]
    ]
    meta_table = Table(meta_data, colWidths=[250, 254])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#edf2f7")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e0")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))

    # =========================================================================
    # CHAPTER 1: FOUNDATIONAL CONCEPTS
    # =========================================================================
    story.append(Paragraph("1. Foundational Concept: Why Astro-Harmonics & Midpoints Work", h1_style))
    story.append(Paragraph(
        "Legendary market master W. D. Gann stated that market oscillations are governed by the <b>Law of Vibration</b>. "
        "Price and time are not independent entities—they are two interchangeable manifestations of circular cycles. "
        "Market pivot points occur when circular time geometric divisions align with natural celestial periodicities.",
        body_style
    ))
    story.append(Paragraph(
        "In modern quantitative terms, these tools operate as <b>phase-synchronized volatility oscillators</b>. "
        "Standard clock time is human-constructed and ignores Earth's axial progression, whereas institutional order flows, "
        "algorithmic volume spikes, and seasonal capital allocation consistently align with astronomical milestones (e.g., Solar Equinoxes, "
        "lunar cycle culminations, and intraday half-session boundaries).",
        body_style
    ))

    # Callout Box
    callout_data = [[Paragraph(
        "<b>Gann's Master Axiom:</b> <i>'When time and price square, a change in trend is inevitable. "
        "The 50% point or half-way point of any movement, range, or cycle is the strongest resistance and support point.'</i>",
        callout_style
    )]]
    callout_table = Table(callout_data, colWidths=[504])
    callout_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#ebf8ff")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#63b3ed")),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(callout_table)
    story.append(Spacer(1, 15))

    # =========================================================================
    # CHAPTER 2: APPLICATION 1 - EPHEMERIS & CELESTIAL TIMING
    # =========================================================================
    story.append(Paragraph("2. Application 1: Gann Celestial Tracker (Ephemeris Engine)", h1_style))
    story.append(Paragraph(
        "<b>File:</b> <code>d:\\ephemeris\\main.py</code> (or <code>d:\\ephemeris\\Launch_GannCelestialTracker.lnk</code>)<br/>"
        "<b>Purpose:</b> Tracks planetary orbital mechanics to generate long-term, swing, and intraday market entry windows "
        "synchronized with Indian market operational trading sessions.",
        body_style
    ))

    story.append(Paragraph("2.1 Celestial Phenomena & Market Implications", h2_style))

    aspect_table_data = [
        [Paragraph("Phenomenon", table_header_style), Paragraph("Symbol & Angle", table_header_style), Paragraph("Market Effect & Strategy", table_header_style)],
        [Paragraph("Conjunction", table_cell_bold), Paragraph("☌ (0°)", table_cell_style), Paragraph("<b>Cycle Genesis:</b> Major trend reversal or consolidation breakout. Heavy institutional repositioning.", table_cell_style)],
        [Paragraph("Opposition", table_cell_bold), Paragraph("☍ (180°)", table_cell_style), Paragraph("<b>Cycle Polarity:</b> Market exhaustion, counter-trend pivots, blow-off tops or panic selling troughs.", table_cell_style)],
        [Paragraph("Square", table_cell_bold), Paragraph("□ (90° / 270°)", table_cell_style), Paragraph("<b>Disharmony / Clash:</b> Violent intraday volatility, sudden trend shakes, false breakout traps.", table_cell_style)],
        [Paragraph("Trine", table_cell_bold), Paragraph("△ (120° / 240°)", table_cell_style), Paragraph("<b>Harmonic Flow:</b> Strong trend acceleration, momentum continuations, smooth trending channels.", table_cell_style)],
        [Paragraph("Octiles (1/8)", table_cell_bold), Paragraph("∠ (45°) / ⚼ (135°)", table_cell_style), Paragraph("<b>Minor Turning Points:</b> Short-term counter-swings, weekly option expiry pin targets.", table_cell_style)],
        [Paragraph("Planetary Stations", table_cell_bold), Paragraph("Stat Rx / Stat Dir", table_cell_style), Paragraph("<b>Zero-Velocity Inflections:</b> Strongest macro reversals. Outer planets (Jupiter/Saturn) form multi-week swing pivots.", table_cell_style)],
        [Paragraph("Cardinal Ingress", table_cell_bold), Paragraph("0° Ar, Cn, Li, Cp", table_cell_style), Paragraph("<b>Gann Seasonal Turns:</b> Solstices & Equinoxes dictate seasonal capital rotation across equity sectors.", table_cell_style)]
    ]
    t_aspect = Table(aspect_table_data, colWidths=[95, 80, 329])
    t_aspect.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1a365d")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f7fafc")]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_aspect)
    story.append(Spacer(1, 10))

    story.append(Paragraph("2.2 Bidirectional Price ↔ Longitude Conversion Mathematics", h2_style))
    story.append(Paragraph(
        "The application features Gann's mathematical formulas converting planetary ecliptic degrees into exact market price rungs:",
        body_style
    ))
    story.append(Paragraph("<b>A. Square of Nine Formula:</b> One full 360° circle advances square roots by 2.0. "
                           "Each degree represents <code>offset = degree / 180.0</code>.", body_style))
    story.append(Paragraph("<code>Price = (2 * k + degree / 180.0) ^ 2</code>", formula_style))
    story.append(Paragraph("The software automatically identifies cycle index <code>k</code> based on your active LTP and outputs the exact support and resistance rungs bracketing the spot index.", body_style))
    story.append(Paragraph("<b>B. Natural 360° Wheel:</b> <code>Price Modulo 360</code> equates points directly to circular coordinates (e.g., Nifty at 24,350 = 230° Scorpio).", body_style))

    story.append(Paragraph("2.3 Strict Indian Market Rules & Exclusion Compliance", h2_style))
    story.append(Paragraph(
        "• <b>Session Alignment:</b> Celestial events occurring outside regular market hours (e.g., 03:45 IST) are automatically mapped to the <b>Pre-Open (09:00 or 09:15 IST)</b> of the next trading day.<br/>"
        "• <b>Nifty 50 Options Expiry:</b> Accurately calibrated to weekly <b>Tuesday</b> expiries (effective SEBI mandate).<br/>"
        "• <b>Critical Exclusion Filter:</b> All Gold, Silver, and Bullion contracts are permanently hard-filtered across all data routing and reports.",
        body_style
    ))

    story.append(PageBreak())

    # =========================================================================
    # CHAPTER 3: APPLICATION 2 - GANN MIDPOINT & 360 TIME HARMONICS
    # =========================================================================
    story.append(Paragraph("3. Application 2: Gann Midpoint & 360° Time Harmonics", h1_style))
    story.append(Paragraph(
        "<b>File:</b> <code>d:\\ephemeris\\gann_midpoint_app.py</code><br/>"
        "<b>Purpose:</b> Calculates the exact 50% equilibrium center of any trading day, projecting bidirectional harmonic time angles "
        "(Left = Morning, Right = Afternoon) and corresponding 50% price support/resistance levels.",
        body_style
    ))

    story.append(Paragraph("3.1 The 6 Calculation Methods Explained", h2_style))

    methods_data = [
        [Paragraph("Method", table_header_style), Paragraph("Midpoint Formula", table_header_style), Paragraph("Degree Scale", table_header_style), Paragraph("Trading Application", table_header_style)],
        [
            Paragraph("<b>Method 1:<br/>NSE/BSE Session</b>", table_cell_style),
            Paragraph("09:15 + 187.5m =<br/><b>12:22:30 IST</b>", table_cell_style),
            Paragraph("1° = 1.0417 min<br/>(62.5 sec)", table_cell_style),
            Paragraph("Primary intraday timing tool for Nifty, Bank Nifty, and stock options. Reversals frequently trigger within ±15 min of 12:22 IST.", table_cell_style)
        ],
        [
            Paragraph("<b>Method 2:<br/>MCX Session</b>", table_cell_style),
            Paragraph("09:00 + 435m =<br/><b>16:15:00 IST</b>", table_cell_style),
            Paragraph("1° = 2.4167 min<br/>(145.0 sec)", table_cell_style),
            Paragraph("For Crude Oil, Natural Gas, and Base Metals. Shifts to 16:27 IST during US Standard Time. Marks European/US overlap shift.", table_cell_style)
        ],
        [
            Paragraph("<b>Method 3:<br/>Solar Noon</b>", table_cell_style),
            Paragraph("Mumbai Zenith =<br/><b>12:22 - 12:54 IST</b>", table_cell_style),
            Paragraph("1° = 4.0000 min<br/>(240.0 sec)", table_cell_style),
            Paragraph("Astronomical True Solar Noon corrected for Equation of Time. On Oct 27, aligned within 10s of NSE Midpoint (Double Confluence).", table_cell_style)
        ],
        [
            Paragraph("<b>Method 4:<br/>Opening Range</b>", table_cell_style),
            Paragraph("09:15 + 30m =<br/><b>09:45:00 IST</b>", table_cell_style),
            Paragraph("1° = 10.0 sec<br/>(0.1667 min)", table_cell_style),
            Paragraph("First 60-minute range equilibrium (60m = 360°). Retests of the 09:45 midpoint determine morning trend continuation.", table_cell_style)
        ],
        [
            Paragraph("<b>Method 5:<br/>Custom Pivot Time</b>", table_cell_style),
            Paragraph("User Selected<br/>(e.g., 10:45 IST)", table_cell_style),
            Paragraph("Selectable<br/>(1.04m, 4m, 10s)", table_cell_style),
            Paragraph("Anchors the 0° balance line at the exact minute an extreme intraday High or Low was registered.", table_cell_style)
        ],
        [
            Paragraph("<b>Method 6:<br/>Price Equilibrium</b>", table_cell_style),
            Paragraph("<b>(High + Low) / 2</b><br/>(e.g. 24,350 pts)", table_cell_style),
            Paragraph("1° = Range / 360°<br/>+ Time 1.04m", table_cell_style),
            Paragraph("<b>Dual Price & Time Squaring:</b> Generates exact numerical price support/resistance levels mapped alongside time degrees.", table_cell_style)
        ]
    ]
    t_methods = Table(methods_data, colWidths=[80, 85, 75, 264])
    t_methods.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1a365d")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f7fafc")]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_methods)
    story.append(Spacer(1, 10))

    story.append(Paragraph("3.2 Harmonic Degrees Timetable Reference (NSE Equity Session)", h2_style))

    sample_table_data = [
        [Paragraph("Degree", table_header_style), Paragraph("Left (Morning)", table_header_style), Paragraph("Right (Afternoon)", table_header_style), Paragraph("Significance & Strategy Execution", table_header_style)],
        [Paragraph("<b>0° (MID)</b>", table_cell_bold), Paragraph("★ 12:22:30 IST", table_cell_bold), Paragraph("★ 12:22:30 IST", table_cell_bold), Paragraph("<b>THE MIDPOINT OF THE DAY:</b> Trend gravity axis. Price above = Long, Price below = Short.", table_cell_style)],
        [Paragraph("30°", table_cell_style), Paragraph("11:51:15 IST", table_cell_style), Paragraph("12:53:45 IST", table_cell_style), Paragraph("Semi-Sextile: Pre-midpoint compression and 1:00 PM European market opening reaction.", table_cell_style)],
        [Paragraph("45°", table_cell_style), Paragraph("11:35:37 IST", table_cell_style), Paragraph("13:09:22 IST", table_cell_style), Paragraph("Octile: High-probability swing reversal window. Frequently caps morning rally or slide.", table_cell_style)],
        [Paragraph("90°", table_cell_style), Paragraph("10:48:45 IST", table_cell_style), Paragraph("13:56:15 IST", table_cell_style), Paragraph("<b>Major Square:</b> 10:48 terminates initial morning expansion; 13:56 launches afternoon directional wave.", table_cell_style)],
        [Paragraph("120°", table_cell_style), Paragraph("10:17:30 IST", table_cell_style), Paragraph("14:27:30 IST", table_cell_style), Paragraph("<b>Major Trine:</b> Peak morning liquidity; 14:27 initiates final power-hour momentum surge.", table_cell_style)],
        [Paragraph("144°", table_cell_style), Paragraph("09:52:30 IST", table_cell_style), Paragraph("14:52:30 IST", table_cell_style), Paragraph("Gann Master 144: Opening range completion and pre-closing square-off window.", table_cell_style)],
        [Paragraph("180°", table_cell_style), Paragraph("09:15:00 IST", table_cell_style), Paragraph("15:30:00 IST", table_cell_style), Paragraph("Opposition / Extremes: Official trading bell boundaries of the 375-minute day.", table_cell_style)]
    ]
    t_sample = Table(sample_table_data, colWidths=[55, 95, 95, 259])
    t_sample.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2b6cb0")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f7fafc")]),
        ('TOPPADDING', (0,0), (-1,-1), 4.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_sample)

    story.append(PageBreak())

    # =========================================================================
    # CHAPTER 4: OPERATIONAL WORKFLOW & HOW TO USE
    # =========================================================================
    story.append(Paragraph("4. Step-by-Step Practical Trading Workflow", h1_style))
    story.append(Paragraph(
        "To achieve maximum edge, professional Gann traders execute a structured 4-phase daily workflow:",
        body_style
    ))

    # Phase 1
    story.append(Paragraph("Phase 1: Pre-Market Astro Preparation (08:30 - 09:00 IST)", h2_style))
    story.append(Paragraph(
        "1. Open <b>Gann Celestial Tracker</b> (<code>main.py</code>).<br/>"
        "2. Select your target instrument (e.g., <i>Index (NSE/BSE)</i> or <i>Nifty 50 Options</i>).<br/>"
        "3. Enter today's date and active reference price (yesterday's close, e.g. 24,350).<br/>"
        "4. Click <b>'Generate Gann Timeline'</b>. Review the celestial triggers logged for today.<br/>"
        "5. Note any <b>High Strength</b> aspects or ingresses occurring during market hours. "
        "Take note of the calculated <b>Sq9 Support and Resistance</b> price levels.",
        body_style
    ))

    # Phase 2
    story.append(Paragraph("Phase 2: Midpoint Setup & Degree Projection (09:15 - 10:30 IST)", h2_style))
    story.append(Paragraph(
        "1. Open <b>Gann Midpoint App</b> (<code>gann_midpoint_app.py</code>).<br/>"
        "2. For general index trading, choose <b>Method 1 (NSE/BSE Session)</b>. The app locks the midpoint at <b>12:22:30 IST</b>.<br/>"
        "3. If an extreme high or low forms in the first 45 minutes, switch to <b>Method 6 (Price Equilibrium)</b> and enter the Day High and Day Low.<br/>"
        "4. Click <b>'Recalculate Price Octaves'</b>. The table now displays the exact price rungs and timing nodes side-by-side.<br/>"
        "5. Set alarms at key upcoming angles: <b>90° (10:48 / 13:56 IST)</b> and <b>45° (11:35 / 13:09 IST)</b>.",
        body_style
    ))

    # Phase 3
    story.append(Paragraph("Phase 3: The 12:22 IST Midpoint Execution Rules", h2_style))
    story.append(Paragraph(
        "Between <b>12:15 PM and 12:30 PM IST</b>, monitor the market closely:<br/>"
        "• <b>Bullish Stance:</b> If Nifty is trading <i>above</i> the 50% price equilibrium and prints a higher-low consolidation into 12:22 IST, "
        "initiate long positions targeting the 75% resistance quartile and 90° right time node (13:56 IST).<br/>"
        "• <b>Bearish Stance:</b> If Nifty is trading <i>below</i> the 50% price equilibrium, initiate short positions targeting the 25% support quartile.<br/>"
        "• <b>Reversal Trigger:</b> If price touches an active Square of Nine resistance level <i>at the same time</i> the clock strikes 12:22 IST, "
        "a master price-time squaring has occurred. Look for an immediate trend reversal.",
        body_style
    ))

    # Phase 4
    story.append(Paragraph("Phase 4: Afternoon Momentum Acceleration (13:56 - 15:30 IST)", h2_style))
    story.append(Paragraph(
        "1. At <b>13:56 IST (90° Square)</b>, expect afternoon directional breakout momentum.<br/>"
        "2. At <b>14:27 IST (120° Trine)</b>, trail stop-losses closely as final daily institutional square-off begins.<br/>"
        "3. Export reports to CSV using the built-in <b>'Export CSV'</b> button to maintain an institutional trade audit journal.",
        body_style
    ))

    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e0"), spaceAfter=15))

    # Summary Callout
    summary_box_data = [[Paragraph(
        "<b>Summary Checklist for Active Traders:</b><br/>"
        "✓ Check NASA JPL ephemeris for planetary aspects during session hours.<br/>"
        "✓ Map the 50% price midpoint of the opening range as your bullish/bearish line of control.<br/>"
        "✓ Watch the 12:22:30 IST session midpoint for trend exhaustion or secondary acceleration.<br/>"
        "✓ Trade in the direction of the 50% equilibrium toward the 90° (13:56 IST) and 120° (14:27 IST) time targets.<br/>"
        "✓ Always confirm Gann astro-windows with volume and disciplined stop-loss risk management.",
        callout_style
    )]]
    t_summary_box = Table(summary_box_data, colWidths=[504])
    t_summary_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f0fff4")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#68d391")),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_summary_box)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully generated at: {PDF_PATH}")

if __name__ == "__main__":
    build_pdf()
