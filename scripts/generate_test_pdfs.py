#!/usr/bin/env python3
"""
Generates 4 visually distinct, realistic multi-language Healthcare Claims PDF documents:
1. English (`english_itemized_medical_bill.pdf`):
   US Hospital Billing Statement & CMS-1500 / UB-04 Style Form with simulated Insurance ID Card
   facsimile, Box 21 Diagnosis Grid, CPT/HCPCS Ledger, and detachable Payment Stub.
2. Spanish (`spanish_factura_medica_hospital.pdf`):
   Mexican CFDI 4.0 Electronic Hospital Invoice (Factura Electrónica) with Emerald Masthead,
   Side-by-Side Emisor/Receptor Fiscal Cards, Bordered Emergency Surgical Callout, and SAT CFDI Stamp.
3. French (`french_dossier_medical_autorisation.pdf`):
   European Clinical Dossier & Prior Authorization Letterhead with Indigo Double-Rule Banner,
   Physician Referral Routing Strip, Framed Prior Authorization Certificate, and Radiology Report Box.
4. Korean (`korean_hospital_claim_receipt.pdf`):
   Korean Tertiary Hospital Official Boxed Form Grid (진료비 계산서·영수증 및 진단서) with
   Key-Value Matrix Cells, Embedded Diagnosis Certificate, and Crimson Official Receipt Stamp.
"""

import os
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "sample_documents"


def register_unicode_fonts() -> tuple[str, str]:
    """
    Registers a Latin Unicode font and a Korean Hangul-capable font.
    Returns (latin_font_name, korean_font_name).
    """
    latin_font = "Helvetica"
    korean_font = "Helvetica"

    latin_candidates = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in latin_candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("UnicodeLatin", path))
                latin_font = "UnicodeLatin"
                break
            except Exception:
                pass

    korean_candidates = [
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    for path in korean_candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("UnicodeKorean", path))
                korean_font = "UnicodeKorean"
                break
            except Exception:
                pass

    if korean_font == "Helvetica":
        try:
            pdfmetrics.registerFont(UnicodeCIDFont("HYGoThic-Medium"))
            korean_font = "HYGoThic-Medium"
        except Exception:
            pass

    return latin_font, korean_font


def P(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(str(text), style)


# =============================================================================
# FORMAT 1: ENGLISH — US CMS-1500 / UB-04 Hospital Statement & Insurance Card
# =============================================================================
def generate_english_pdf(output_path: Path, font_name: str):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=0.45 * inch,
        rightMargin=0.45 * inch,
        topMargin=0.4 * inch,
        bottomMargin=0.4 * inch,
    )
    base = getSampleStyleSheet()["Normal"]

    st_hosp = ParagraphStyle("EnHosp", parent=base, fontName=font_name, fontSize=14, leading=17, textColor=colors.HexColor("#7F1D1D"))
    st_sub = ParagraphStyle("EnSub", parent=base, fontName=font_name, fontSize=8, leading=11, textColor=colors.HexColor("#334155"))
    st_box_hdr = ParagraphStyle("EnBoxHdr", parent=base, fontName=font_name, fontSize=8, leading=10, textColor=colors.white, alignment=TA_CENTER)
    st_box_val = ParagraphStyle("EnBoxVal", parent=base, fontName=font_name, fontSize=9, leading=12, textColor=colors.HexColor("#0F172A"), alignment=TA_CENTER)
    st_sec = ParagraphStyle("EnSec", parent=base, fontName=font_name, fontSize=9, leading=12, textColor=colors.HexColor("#7F1D1D"), spaceBefore=6, spaceAfter=3)
    st_cell = ParagraphStyle("EnCell", parent=base, fontName=font_name, fontSize=8, leading=10.5, textColor=colors.HexColor("#1E293B"))
    st_cell_r = ParagraphStyle("EnCellR", parent=st_cell, alignment=TA_RIGHT)
    st_th = ParagraphStyle("EnTh", parent=base, fontName=font_name, fontSize=7.5, leading=10, textColor=colors.white)
    st_th_r = ParagraphStyle("EnThR", parent=st_th, alignment=TA_RIGHT)
    st_card = ParagraphStyle("EnCard", parent=base, fontName=font_name, fontSize=8, leading=11, textColor=colors.HexColor("#0F172A"))

    story = []

    # Top Split Header: Left = Hospital Identity, Right = Account Summary Box
    left_header = [
        P("<b>PACIFIC NORTHWEST MEDICAL CENTER</b>", st_hosp),
        P("1140 Madison Street, Seattle, WA 98104 | Phone: (206) 555-0192", st_sub),
        P("<b>Facility NPI:</b> 1245319599 &nbsp;|&nbsp; <b>Federal Tax ID (EIN):</b> 91-1948273", st_sub),
        P("<b>FORM TYPE:</b> ITEMIZED HOSPITAL MEDICAL BILL (CMS-1500 / UB-04 CODED) &amp; COPAY RECEIPT", st_sub),
    ]
    right_summary = Table(
        [
            [P("<b>STATEMENT #</b>", st_box_hdr), P("<b>SERVICE DATE</b>", st_box_hdr), P("<b>BALANCE FOR ADJUDICATION</b>", st_box_hdr)],
            [P("<b>PNW-CLM-2026-88412</b><br/>Stmt: Oct 14, 2026", st_box_val), P("<b>2026-10-10</b><br/>Outpatient ER", st_box_val), P("<b>$1,695.00 USD</b><br/>(Copay $150 Paid)", st_box_val)],
        ],
        colWidths=[1.48 * inch, 0.97 * inch, 1.35 * inch],
    )
    right_summary.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#991B1B")),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#FEF2F2")),
                ("GRID", (0, 0), (-1, -1), 0.75, colors.HexColor("#991B1B")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    masthead = Table([[left_header, right_summary]], colWidths=[3.8 * inch, 3.8 * inch])
    masthead.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story.append(masthead)
    story.append(Spacer(1, 6))

    # Side-by-Side Boxed Cards: Simulated Insurance Card Facsimile (Left) + Patient & Provider Box (Right)
    ins_card_content = [
        P("<b>AETNA HEALTH INC. — CHOICE POS II INSURANCE CARD</b> &nbsp;&nbsp;[EDI: 60054]", st_th),
        P(
            "<b>Subscriber / Member Name:</b> Eleanor Marie Vance (Relationship: Self)<br/>"
            "<b>Member ID (Policy #):</b> AET-994827164 &nbsp;|&nbsp; <b>Group #:</b> GRP-77420-WA<br/>"
            "<b>Plan Effective Date:</b> 2026-01-01 &nbsp;|&nbsp; <b>Prior Auth #:</b> AUTH-WA-559102<br/>"
            "<b>Benefits:</b> ER Copay: $150.00 (Paid) &nbsp;|&nbsp; In-Network Coinsurance: 20%",
            st_card,
        ),
    ]
    pat_card_content = [
        P("<b>CMS-1500 BOX 2, 3, 5 &amp; 33 — PATIENT &amp; ATTENDING PHYSICIAN</b>", st_th),
        P(
            "<b>Patient Name:</b> Eleanor Marie Vance &nbsp;|&nbsp; <b>DOB:</b> 1978-04-12 &nbsp;|&nbsp; <b>Sex:</b> Female<br/>"
            "<b>Patient Address:</b> 4512 Greenwood Ave N, Seattle, WA 98103 &nbsp;|&nbsp; <b>Tel:</b> (206) 555-0148<br/>"
            "<b>Attending Physician:</b> Dr. Marcus Vance-Sterling, MD (NPI: 1891740215)<br/>"
            "<b>Department / Specialty:</b> Emergency &amp; Internal Medicine",
            st_card,
        ),
    ]
    cards_tbl = Table(
        [
            [ins_card_content[0], pat_card_content[0]],
            [ins_card_content[1], pat_card_content[1]],
        ],
        colWidths=[3.75 * inch, 3.85 * inch],
    )
    cards_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#1E293B")),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#7F1D1D")),
                ("BACKGROUND", (0, 1), (0, 1), colors.HexColor("#F8FAFC")),
                ("BACKGROUND", (1, 1), (1, 1), colors.HexColor("#FFFBEB")),
                ("BOX", (0, 0), (0, 1), 1.0, colors.HexColor("#1E293B")),
                ("BOX", (1, 0), (1, 1), 1.0, colors.HexColor("#7F1D1B")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(cards_tbl)

    # Box 21 Clinical & ICD-10 Grid
    story.append(P("<b>BOX 21 — CLINICAL SUMMARY &amp; ICD-10-CM DIAGNOSIS POINTERS</b>", st_sec))
    dx_grid = Table(
        [
            [
                P("<b>Ptr A (Primary): J18.9</b> [ICD-10-CM]<br/>Pneumonia, unspecified organism (Community-acquired right lower lobe pneumonia)", st_cell),
                P("<b>Ptr B (Secondary): R06.02</b> [ICD-10-CM]<br/>Shortness of breath / Acute dyspnea on exertion", st_cell),
                P("<b>Ptr C (Comorbidity): E11.9</b> [ICD-10-CM]<br/>Type 2 diabetes mellitus without complications", st_cell),
            ],
            [
                P(
                    "<b>Clinical Encounter Note:</b> Patient presented to ER with acute dyspnea, productive cough, and fever (39.1 °C). "
                    "2-view chest radiograph confirmed right lower lobe consolidation consistent with bacterial pneumonia. "
                    "Administered IV normal saline hydration and IV Ceftriaxone 1000 mg antibiotic therapy.",
                    st_cell,
                ),
                "",
                "",
            ],
        ],
        colWidths=[2.7 * inch, 2.45 * inch, 2.45 * inch],
    )
    dx_grid.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 1), (2, 1)),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FEF2F2")),
                ("BACKGROUND", (0, 1), (-1, 1), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#FCA5A5")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(dx_grid)

    # Box 24 Itemized Ledger
    story.append(P("<b>BOX 24 — ITEMIZED MEDICAL PROCEDURES &amp; HOSPITAL SERVICE LINES (CPT / HCPCS)</b>", st_sec))
    ledger_rows = [
        [
            P("<b>Ln</b>", st_th),
            P("<b>Service Date</b>", st_th),
            P("<b>CPT/HCPCS</b>", st_th),
            P("<b>Sys</b>", st_th),
            P("<b>Ptr</b>", st_th),
            P("<b>Procedure / Service Description</b>", st_th),
            P("<b>Qty</b>", st_th_r),
            P("<b>Unit Price</b>", st_th_r),
            P("<b>Total Charge</b>", st_th_r),
        ],
        [P("1", st_cell), P("2026-10-10", st_cell), P("<b>99284</b>", st_cell), P("CPT", st_cell), P("A, B", st_cell), P("Emergency Dept Visit, High Severity &amp; Urgent Evaluation", st_cell), P("1", st_cell_r), P("$1,450.00", st_cell_r), P("$1,450.00", st_cell_r)],
        [P("2", st_cell), P("2026-10-10", st_cell), P("<b>71046</b>", st_cell), P("CPT", st_cell), P("A, B", st_cell), P("Radiologic Examination, Chest; 2 Views (PA &amp; Lateral)", st_cell), P("1", st_cell_r), P("$320.00", st_cell_r), P("$320.00", st_cell_r)],
        [P("3", st_cell), P("2026-10-10", st_cell), P("<b>87070</b>", st_cell), P("CPT", st_cell), P("A", st_cell), P("Culture, Bacterial; Sputum, Aerobic with Isolation", st_cell), P("1", st_cell_r), P("$185.00", st_cell_r), P("$185.00", st_cell_r)],
        [P("4", st_cell), P("2026-10-10", st_cell), P("<b>80053</b>", st_cell), P("CPT", st_cell), P("A, C", st_cell), P("Comprehensive Metabolic Panel (14 Lab Tests)", st_cell), P("1", st_cell_r), P("$140.00", st_cell_r), P("$140.00", st_cell_r)],
        [P("5", st_cell), P("2026-10-10", st_cell), P("<b>96365</b>", st_cell), P("CPT", st_cell), P("A", st_cell), P("Intravenous Infusion for Therapy/Prophylaxis, Initial 1 hr", st_cell), P("1", st_cell_r), P("$410.00", st_cell_r), P("$410.00", st_cell_r)],
        [P("6", st_cell), P("2026-10-10", st_cell), P("<b>J0696</b>", st_cell), P("HCPCS", st_cell), P("A", st_cell), P("Injection, Ceftriaxone Sodium, per 250 mg (1000 mg total)", st_cell), P("4", st_cell_r), P("$65.00", st_cell_r), P("$260.00", st_cell_r)],
    ]
    ledger_tbl = Table(
        ledger_rows,
        colWidths=[0.32 * inch, 0.78 * inch, 0.75 * inch, 0.55 * inch, 0.42 * inch, 2.93 * inch, 0.38 * inch, 0.72 * inch, 0.75 * inch],
    )
    ledger_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7F1D1D")),
                ("LINEBELOW", (0, 1), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#7F1D1D")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(ledger_tbl)
    story.append(Spacer(1, 6))

    # Perforated Remittance & Copay Proof Stub
    story.append(HRFlowable(width="100%", thickness=1, lineCap="round", color=colors.HexColor("#64748B"), dash=(4, 3)))
    story.append(Spacer(1, 4))
    remit_tbl = Table(
        [
            [
                P(
                    "<b>POINT-OF-SERVICE PAYMENT RECEIPT &amp; ADJUDICATION VOUCHER</b><br/>"
                    "• <b>Receipt ID:</b> #TXN-883920-US &nbsp;|&nbsp; <b>Method:</b> VISA Credit Card *4412 (Paid 2026-10-10)<br/>"
                    "• <b>Payer Routing:</b> Aetna Health Inc. (EDI 60054) — Prior Auth #AUTH-WA-559102<br/>"
                    "• <b>Status:</b> Paid ER Copay ($150.00); Remaining $1,695.00 Ready for Primary Payer Adjudication",
                    st_cell,
                ),
                Table(
                    [
                        [P("Total Gross Hospital Charges:", st_cell), P("<b>$2,765.00</b>", st_cell_r)],
                        [P("Aetna POS II Network Adjustment:", st_cell), P("-$920.00", st_cell_r)],
                        [P("Patient ER Copay Paid (VISA *4412):", st_cell), P("-$150.00", st_cell_r)],
                        [P("<b>Net Claim Balance Due:</b>", st_cell), P("<b>$1,695.00 USD</b>", st_cell_r)],
                    ],
                    colWidths=[1.85 * inch, 0.95 * inch],
                    style=TableStyle(
                        [
                            ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#FEE2E2")),
                            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#94A3B8")),
                            ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E2E8F0")),
                            ("TOPPADDING", (0, 0), (-1, -1), 3),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                        ]
                    ),
                ),
            ]
        ],
        colWidths=[4.7 * inch, 2.9 * inch],
    )
    remit_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story.append(remit_tbl)

    doc.build(story)


# =============================================================================
# FORMAT 2: SPANISH — Mexican CFDI 4.0 Fiscal Hospital Invoice & Surgical Note
# =============================================================================
def generate_spanish_pdf(output_path: Path, font_name: str):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=0.45 * inch,
        rightMargin=0.45 * inch,
        topMargin=0.4 * inch,
        bottomMargin=0.4 * inch,
    )
    base = getSampleStyleSheet()["Normal"]

    st_banner_l = ParagraphStyle("EsBanL", parent=base, fontName=font_name, fontSize=12.5, leading=15, textColor=colors.white)
    st_banner_r = ParagraphStyle("EsBanR", parent=base, fontName=font_name, fontSize=8, leading=11, textColor=colors.HexColor("#ECFDF5"), alignment=TA_RIGHT)
    st_card_hdr = ParagraphStyle("EsCardHdr", parent=base, fontName=font_name, fontSize=8, leading=10, textColor=colors.HexColor("#065F46"))
    st_cell = ParagraphStyle("EsCell", parent=base, fontName=font_name, fontSize=8, leading=10.5, textColor=colors.HexColor("#1E293B"))
    st_cell_r = ParagraphStyle("EsCellR", parent=st_cell, alignment=TA_RIGHT)
    st_th = ParagraphStyle("EsTh", parent=base, fontName=font_name, fontSize=8, leading=10, textColor=colors.white)
    st_th_r = ParagraphStyle("EsThR", parent=st_th, alignment=TA_RIGHT)
    st_sec = ParagraphStyle("EsSec", parent=base, fontName=font_name, fontSize=9.5, leading=12, textColor=colors.HexColor("#065F46"), spaceBefore=6, spaceAfter=3)

    story = []

    # Full-Width Emerald CFDI 4.0 Header Banner
    banner = Table(
        [
            [
                P(
                    "<b>HOSPITAL ÁNGELES PEDREGAL</b><br/>"
                    "<font size=8.5>CENTRO MÉDICO QUIRÚRGICO — FACTURA ELECTRÓNICA CFDI 4.0 Y RESUMEN DE URGENCIAS</font>",
                    st_banner_l,
                ),
                P(
                    "<b>FOLIO DE FACTURA: FAC-MX-2026-09481</b><br/>"
                    "Fecha de Emisión: 12 de Octubre de 2026<br/>"
                    "Fecha de Atención: 11–12 de Octubre de 2026",
                    st_banner_r,
                ),
            ]
        ],
        colWidths=[4.8 * inch, 2.8 * inch],
    )
    banner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#065F46")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(banner)
    story.append(Spacer(1, 5))

    # Side-by-Side Mexican CFDI Emisor (Hospital) vs. Receptor (Patient & Insurance) Boxes
    emisor_receptor = Table(
        [
            [
                P("<b>EMISOR (INSTITUCIÓN HOSPITALARIA)</b>", st_card_hdr),
                P("<b>RECEPTOR (PACIENTE) Y PÓLIZA DE SEGURO INTERNACIONAL</b>", st_card_hdr),
            ],
            [
                P(
                    "<b>Razón Social:</b> Hospital Ángeles Pedregal S.A. de C.V.<br/>"
                    "<b>RFC Emisor:</b> HAP890315M7A &nbsp;|&nbsp; <b>Clave CLUES:</b> DFSSA014892<br/>"
                    "<b>Dirección:</b> Camino a Santa Teresa 1055, Col. Héroes de Padierna, La Magdalena Contreras, 10700 Ciudad de México, CDMX, México<br/>"
                    "<b>Teléfono Urgencias:</b> +52 (55) 5652-1188<br/>"
                    "<b>Médico Tratante / Cirujano:</b> Dr. Alejandro Villaseñor Méndez (Cirugía General y Laparoscopía, Cédula Prof.: 4829103)",
                    st_cell,
                ),
                P(
                    "<b>Nombre del Paciente:</b> Mateo Alejandro Rojas Herrera<br/>"
                    "<b>Fecha de Nacimiento:</b> 1985-11-23 &nbsp;|&nbsp; <b>Sexo:</b> Masculino<br/>"
                    "<b>Domicilio:</b> 742 Evergreen Terrace, Austin, TX 78701, EE.UU.<br/>"
                    "<b>Aseguradora:</b> BlueCross BlueShield Global Solutions<br/>"
                    "<b>Número de Miembro (Póliza):</b> BCBS-44819203 &nbsp;|&nbsp; <b>Grupo:</b> GLB-CORP-902<br/>"
                    "<b>Autorización Telefónica de Urgencia:</b> URG-MX-77104 (Reembolso Internacional)",
                    st_cell,
                ),
            ],
        ],
        colWidths=[3.75 * inch, 3.85 * inch],
    )
    emisor_receptor.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D1FAE5")),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F8FAFC")),
                ("GRID", (0, 0), (-1, -1), 0.7, colors.HexColor("#059669")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(emisor_receptor)

    # Clinical Callout Box with Thick Left Accent Bar
    story.append(P("<b>RESUMEN DE HISTORIA CLÍNICA Y NOTA QUIRÚRGICA DE URGENCIAS (SIN CÓDIGOS CPT)</b>", st_sec))
    clinical_box = Table(
        [
            [
                P("<b>SIGNOS VITALES:</b><br/>Edad: 40 años<br/>Fiebre: 38.6 °C<br/>Leucocitos: 16,400/mm³<br/>Blumberg: Positivo (+)<br/>Apéndice: 11 mm", st_cell),
                P(
                    "<b>Motivo de Consulta y Evolución:</b> Paciente masculino de 40 años que acude al servicio de urgencias por cuadro de 14 horas de "
                    "evolución caracterizado por dolor abdominal agudo localizado en fosa ilíaca derecha, náuseas, signo de Blumberg positivo y fiebre de 38.6 °C. "
                    "La biometría hemática reporta leucocitosis de 16,400/mm³ con neutrofilia. El ultrasonido abdominal focalizado confirma apéndice cecal "
                    "no compresible de 11 mm de diámetro con edema de pared.<br/>"
                    "<b>Diagnóstico Definitivo:</b> Apendicitis aguda no perforada sin peritonitis generalizada.<br/>"
                    "<b>Procedimiento Quirúrgico Realizado:</b> Apendicectomía laparoscópica de urgencia bajo anestesia general balanceada sin complicaciones.",
                    st_cell,
                ),
            ]
        ],
        colWidths=[1.45 * inch, 6.15 * inch],
    )
    clinical_box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#ECFDF5")),
                ("BACKGROUND", (1, 0), (1, 0), colors.white),
                ("LINEBEFORE", (0, 0), (0, 0), 4.0, colors.HexColor("#059669")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#A7F3D0")),
                ("LINEAFTER", (0, 0), (0, 0), 0.6, colors.HexColor("#A7F3D0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(clinical_box)

    # Conceptos Facturados (Uncoded Hospital Charges Table)
    story.append(P("<b>DESGLOSE DE CONCEPTOS HOSPITALARIOS Y HONORARIOS MÉDICOS (SIN CODIFICACIÓN CPT)</b>", st_sec))
    item_rows = [
        [
            P("<b>Partida</b>", st_th),
            P("<b>Fecha</b>", st_th),
            P("<b>Código Interno</b>", st_th),
            P("<b>Descripción del Servicio Médico / Quirúrgico (Sin Código CPT)</b>", st_th),
            P("<b>Cant.</b>", st_th_r),
            P("<b>Precio Unitario</b>", st_th_r),
            P("<b>Importe Total</b>", st_th_r),
        ],
        [P("1", st_cell), P("2026-10-11", st_cell), P("<b>URG-001</b>", st_cell), P("Consulta médica de urgencias y valoración inicial por especialista en cirugía general", st_cell), P("1", st_cell_r), P("$3,500.00 MXN", st_cell_r), P("$3,500.00 MXN", st_cell_r)],
        [P("2", st_cell), P("2026-10-11", st_cell), P("<b>IMG-204</b>", st_cell), P("Ultrasonido abdominal y pélvico focalizado de alta resolución en urgencias", st_cell), P("1", st_cell_r), P("$2,800.00 MXN", st_cell_r), P("$2,800.00 MXN", st_cell_r)],
        [P("3", st_cell), P("2026-10-11", st_cell), P("<b>LAB-112</b>", st_cell), P("Biometría hemática completa, química sanguínea de 6 elementos y proteína C reactiva", st_cell), P("1", st_cell_r), P("$1,450.00 MXN", st_cell_r), P("$1,450.00 MXN", st_cell_r)],
        [P("4", st_cell), P("2026-10-11", st_cell), P("<b>QX-509</b>", st_cell), P("Apendicectomía laparoscópica de urgencia (derechos de quirófano, anestesia y honorarios quirúrgicos)", st_cell), P("1", st_cell_r), P("$42,000.00 MXN", st_cell_r), P("$42,000.00 MXN", st_cell_r)],
        [P("5", st_cell), P("2026-10-12", st_cell), P("<b>FARM-308</b>", st_cell), P("Estancia hospitalaria (1 día en habitación estándar) y medicamentos intravenosos (Cefotaxima, Metronidazol, Ketorolaco)", st_cell), P("1", st_cell_r), P("$6,750.00 MXN", st_cell_r), P("$6,750.00 MXN", st_cell_r)],
    ]
    items_tbl = Table(
        item_rows,
        colWidths=[0.5 * inch, 0.8 * inch, 0.85 * inch, 3.25 * inch, 0.4 * inch, 0.9 * inch, 0.9 * inch],
    )
    items_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#065F46")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0FDF4")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#6EE7B7")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(items_tbl)
    story.append(Spacer(1, 6))

    # Bottom Split: Left = SAT CFDI 4.0 Fiscal Stamp & Mastercard Proof, Right = Stacked Totals Box
    cfdi_stamp = P(
        "<b>TIMBRADO FISCAL DIGITAL SAT (CFDI 4.0) Y COMPROBANTE DE PAGO</b><br/>"
        "• <b>Folio Fiscal UUID:</b> 550E8400-E29B-41D4-A716-446655440000<br/>"
        "• <b>Método de Pago:</b> PUE (Pago en una sola exhibición) — Tarjeta Mastercard *8821<br/>"
        "• <b>Código de Autorización Bancaria:</b> #MX-992814 (PAGADO EN SU TOTALIDAD)<br/>"
        "• <b>Tipo de Cambio Referencial:</b> 20.00 MXN / 1.00 USD",
        st_cell,
    )
    totals_sub = Table(
        [
            [P("Subtotal Hospitalario:", st_cell), P("$48,706.90 MXN", st_cell_r), P("$2,435.35 USD", st_cell_r)],
            [P("IVA Trasladado (16%):", st_cell), P("$7,793.10 MXN", st_cell_r), P("$389.65 USD", st_cell_r)],
            [P("<b>TOTAL FACTURADO Y PAGADO:</b>", st_cell), P("<b>$56,500.00 MXN</b>", st_cell_r), P("<b>$2,825.00 USD</b>", st_cell_r)],
        ],
        colWidths=[1.6 * inch, 1.0 * inch, 0.95 * inch],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#D1FAE5")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#059669")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        ),
    )
    footer_tbl = Table([[cfdi_stamp, totals_sub]], colWidths=[4.05 * inch, 3.55 * inch])
    footer_tbl.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (0, 0), 0.7, colors.HexColor("#94A3B8")),
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#F8FAFC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, 0), 7),
                ("RIGHTPADDING", (0, 0), (0, 0), 7),
                ("TOPPADDING", (0, 0), (0, 0), 5),
                ("BOTTOMPADDING", (0, 0), (0, 0), 5),
                ("LEFTPADDING", (1, 0), (1, 0), 6),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ]
        )
    )
    story.append(footer_tbl)

    doc.build(story)


# =============================================================================
# FORMAT 3: FRENCH — European Clinical Letterhead, Prior Auth Certificate & MRI Report
# =============================================================================
def generate_french_pdf(output_path: Path, font_name: str):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.4 * inch,
        bottomMargin=0.4 * inch,
    )
    base = getSampleStyleSheet()["Normal"]

    st_title = ParagraphStyle("FrTitle", parent=base, fontName=font_name, fontSize=13.5, leading=16, textColor=colors.HexColor("#312E81"), alignment=TA_CENTER)
    st_sub = ParagraphStyle("FrSub", parent=base, fontName=font_name, fontSize=8, leading=11, textColor=colors.HexColor("#475569"), alignment=TA_CENTER)
    st_cert = ParagraphStyle("FrCert", parent=base, fontName=font_name, fontSize=8.5, leading=12, textColor=colors.HexColor("#1E1B4B"))
    st_sec = ParagraphStyle("FrSec", parent=base, fontName=font_name, fontSize=9.5, leading=12, textColor=colors.HexColor("#312E81"), spaceBefore=6, spaceAfter=3)
    st_cell = ParagraphStyle("FrCell", parent=base, fontName=font_name, fontSize=8, leading=10.5, textColor=colors.HexColor("#1E293B"))
    st_cell_r = ParagraphStyle("FrCellR", parent=st_cell, alignment=TA_RIGHT)
    st_th = ParagraphStyle("FrTh", parent=base, fontName=font_name, fontSize=8, leading=10, textColor=colors.white)
    st_th_r = ParagraphStyle("FrThR", parent=st_th, alignment=TA_RIGHT)

    story = []

    # Centered European Medical Letterhead with Double Indigo Rule
    story.append(P("<b>HÔPITAL AMÉRICAIN DE PARIS — AMERICAN HOSPITAL OF PARIS</b>", st_title))
    story.append(
        P(
            "Pôle d'Orthopédie, Traumatologie du Sport &amp; Imagerie Médicale &bull; 63 Boulevard Victor Hugo, 92200 Neuilly-sur-Seine, France<br/>"
            "Tél: +33 1 46 41 25 25 &bull; N° FINESS: 920000547 &bull; SIRET: 77566410500019 &bull; Réf. Dossier: <b>HAP-FR-2026-3319</b> (Soins du 14/10/2026)",
            st_sub,
        )
    )
    story.append(Spacer(1, 3))
    story.append(HRFlowable(width="100%", thickness=2.0, color=colors.HexColor("#312E81")))
    story.append(Spacer(1, 1.5))
    story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#6366F1")))
    story.append(Spacer(1, 5))

    # Framed Prior Authorization Certificate Banner + Referral Routing Strip
    auth_cert_box = Table(
        [
            [
                P(
                    "<b>CERTIFICAT D'AUTORISATION PRÉALABLE &amp; COUVERTURE INTERNATIONALE</b><br/>"
                    "• <b>Assureur:</b> Cigna Global Health Benefits (Plan: Cigna Global Gold — Franchise: 0 EUR)<br/>"
                    "• <b>N° d'Autorisation Préalable:</b> <b>PA-FR-2026-90412</b> (Statut: ACCORDÉ / APPROVED)<br/>"
                    "• <b>Période de Validité:</b> 2026-10-01 au 2026-11-30",
                    st_cert,
                ),
                P(
                    "<b>IDENTIFICATION DE L'ASSURÉE &amp; ORIENTATION MÉDICALE</b><br/>"
                    "• <b>Patiente:</b> Claire Marie Dubois &nbsp;|&nbsp; <b>Née le:</b> 1991-07-08 (Féminin)<br/>"
                    "• <b>N° d'Assuré (Member ID):</b> CIG-77301948 &nbsp;|&nbsp; <b>Groupe:</b> INTL-EXP-302<br/>"
                    "• <b>Adresse:</b> 24 Rue de Passy, 75016 Paris, France (Tél: +33 6 12 48 93 10)<br/>"
                    "• <b>Médecin Référent:</b> Dr. Henri Laurent (RPPS: 10003498122) &rarr; <b>Spécialiste:</b> Dr. Sophie Moreau",
                    st_cert,
                ),
            ]
        ],
        colWidths=[3.65 * inch, 3.85 * inch],
    )
    auth_cert_box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#EEF2FF")),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 1.2, colors.HexColor("#312E81")),
                ("LINEAFTER", (0, 0), (0, 0), 1.0, colors.HexColor("#6366F1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(auth_cert_box)

    # Narrative Radiology & Orthopedic Report Box ("Compte-Rendu d'IRM & Ordonnance")
    story.append(P("<b>COMPTE-RENDU D'EXAMEN CLINIQUE, D'IRM DU GENOU GAUCHE ET CODIFICATION CIM-10</b>", st_sec))
    mri_report = Table(
        [
            [
                P(
                    "<b>1. Indication &amp; Examen Clinique d'Orthopédie (Dr. Sophie Moreau):</b><br/>"
                    "Patiente de 35 ans adressée par le Dr. Henri Laurent suite à un traumatisme en torsion du genou gauche survenu lors d'une activité sportive. "
                    "Présence d'un épanchement articulaire important, douleur aiguë de l'interligne interne et test de Lachman nettement positif avec arrêt mou.<br/><br/>"
                    "<b>2. Résultat de l'IRM Ostéo-Articulaire du Genou Gauche:</b><br/>"
                    "Rupture complète aiguë du ligament croisé antérieur (LCA) associée à une fissure longitudinale de la corne postérieure du ménisque médial "
                    "et contusion osseuse du condyle fémoral externe.<br/><br/>"
                    "<b>3. Plan Thérapeutique Autorisé:</b> Immobilisation par orthèse/attelle articulée (L1832), prescription d'anti-inflammatoires "
                    "(Kétoprofène 100 mg) et programme initial de rééducation fonctionnelle pré-opératoire (3 séances).",
                    st_cell,
                ),
                P(
                    "<b>CODES DIAGNOSTICS (CIM-10 / ICD-10):</b><br/><br/>"
                    "• <b>S83.512A (Primaire):</b><br/>"
                    "Entorse et déchirure (rupture complète aiguë) du ligament croisé antérieur (LCA) du genou gauche.<br/><br/>"
                    "• <b>S83.242A (Secondaire):</b><br/>"
                    "Autre déchirure du ménisque médial (corne postérieure) du genou gauche, traumatisme initial.",
                    st_cell,
                ),
            ]
        ],
        colWidths=[5.15 * inch, 2.35 * inch],
    )
    mri_report.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), colors.white),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#F5F3FF")),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#818CF8")),
                ("LINEAFTER", (0, 0), (0, 0), 0.7, colors.HexColor("#818CF8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(mri_report)

    # European Feuille de Soins / Fee Statement Table
    story.append(P("<b>FEUILLE DE SOINS — RELEVÉ DÉTAILLÉ DES ACTES MÉDICAUX (CCAM / CPT / HCPCS)</b>", st_sec))
    fee_rows = [
        [
            P("<b>N°</b>", st_th),
            P("<b>Date</b>", st_th),
            P("<b>Code CCAM / CPT</b>", st_th),
            P("<b>Système</b>", st_th),
            P("<b>Désignation de l'Acte Médical / Prestation</b>", st_th),
            P("<b>Qté</b>", st_th_r),
            P("<b>Montant (EUR)</b>", st_th_r),
            P("<b>Équiv. (USD)</b>", st_th_r),
        ],
        [P("1", st_cell), P("2026-10-14", st_cell), P("<b>YYYY010 / 99204</b>", st_cell), P("CCAM/CPT", st_cell), P("Consultation spécialisée d'orthopédie et traumatologie (nouveau patient)", st_cell), P("1", st_cell_r), P("120,00 EUR", st_cell_r), P("$132.00 USD", st_cell_r)],
        [P("2", st_cell), P("2026-10-14", st_cell), P("<b>NZQN001 / 73721</b>", st_cell), P("CCAM/CPT", st_cell), P("Imagerie par Résonance Magnétique (IRM) ostéo-articulaire du genou gauche", st_cell), P("1", st_cell_r), P("380,00 EUR", st_cell_r), P("$418.00 USD", st_cell_r)],
        [P("3", st_cell), P("2026-10-14", st_cell), P("<b>L1832</b>", st_cell), P("HCPCS", st_cell), P("Orthèse / Attelle articulée d'immobilisation réglable du genou gauche", st_cell), P("1", st_cell_r), P("110,00 EUR", st_cell_r), P("$121.00 USD", st_cell_r)],
        [P("4", st_cell), P("2026-10-14", st_cell), P("<b>AMK9 / 97110</b>", st_cell), P("NGAP/CPT", st_cell), P("Séances initiales de rééducation fonctionnelle et kinésithérapie (3 séances)", st_cell), P("3", st_cell_r), P("135,00 EUR", st_cell_r), P("$148.50 USD", st_cell_r)],
    ]
    fee_tbl = Table(
        fee_rows,
        colWidths=[0.32 * inch, 0.75 * inch, 1.0 * inch, 0.72 * inch, 2.86 * inch, 0.35 * inch, 0.75 * inch, 0.75 * inch],
    )
    fee_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#312E81")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EEF2FF")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#A5B4FC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(fee_tbl)
    story.append(Spacer(1, 6))

    # Quittance de Paiement & Physician Signature Block
    quittance = Table(
        [
            [
                P(
                    "<b>QUITTANCE D'HONORAIRES &amp; ATTESTATION D'ACQUITTEMENT</b><br/>"
                    "• <b>Total Autorisé &amp; Réglé par l'Assurée:</b> <b>745,00 EUR ($819.50 USD)</b> — Franchise: 0,00 EUR<br/>"
                    "• <b>Mode de Règlement:</b> PAYÉ par Carte Bancaire Visa le 14/10/2026 — Quittance <b>#FR-99201-P</b><br/>"
                    "• <b>Montant à Rembourser au Patient:</b> 745,00 EUR ($819.50 USD) sous Autorisation PA-FR-2026-90412",
                    st_cell,
                ),
                P(
                    "<b>CACHET &amp; SIGNATURE DU PRATICIEN</b><br/>"
                    "Dr. Sophie Moreau, Chirurgien Orthopédiste<br/>"
                    "Hôpital Américain de Paris (FINESS 920000547)<br/>"
                    "<i>Document certifié conforme — 15 Octobre 2026</i>",
                    st_cell,
                ),
            ]
        ],
        colWidths=[4.9 * inch, 2.6 * inch],
    )
    quittance.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#F8FAFC")),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#EEF2FF")),
                ("GRID", (0, 0), (-1, -1), 0.7, colors.HexColor("#312E81")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(quittance)

    doc.build(story)


# =============================================================================
# FORMAT 4: KOREAN — Korean Official Ministry-Style Boxed Hospital Form Grid
# =============================================================================
def generate_korean_pdf(output_path: Path, font_name: str):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=0.45 * inch,
        rightMargin=0.45 * inch,
        topMargin=0.4 * inch,
        bottomMargin=0.4 * inch,
    )
    base = getSampleStyleSheet()["Normal"]

    st_form_title = ParagraphStyle("KoTitle", parent=base, fontName=font_name, fontSize=13, leading=16, textColor=colors.HexColor("#0F172A"), alignment=TA_CENTER)
    st_lbl = ParagraphStyle("KoLbl", parent=base, fontName=font_name, fontSize=8, leading=10.5, textColor=colors.HexColor("#0F172A"), alignment=TA_CENTER)
    st_val = ParagraphStyle("KoVal", parent=base, fontName=font_name, fontSize=8, leading=11, textColor=colors.HexColor("#1E293B"))
    st_val_r = ParagraphStyle("KoValR", parent=st_val, alignment=TA_RIGHT)
    st_th = ParagraphStyle("KoTh", parent=base, fontName=font_name, fontSize=8, leading=10, textColor=colors.white, alignment=TA_CENTER)
    st_stamp = ParagraphStyle("KoStamp", parent=base, fontName=font_name, fontSize=8.5, leading=11.5, textColor=colors.HexColor("#991B1B"), alignment=TA_CENTER)

    story = []

    # Official Korean Hospital Form Header Block (Boxed Grid with Outpatient/Inpatient Checkboxes)
    form_header = Table(
        [
            [
                P("<b>영수증 번호 (Receipt No.)</b><br/>AMC-KR-2026-55821", st_lbl),
                P("<b>서울아산병원 (ASAN MEDICAL CENTER)</b><br/><font size=9.5>외래 진료비 계산서·영수증 및 실손보험 청구용 진단서</font>", st_form_title),
                P("<b>진료구분 (Visit Type)</b><br/>[✓] 외래 (Outpatient)<br/>[ &nbsp; ] 입원 (Inpatient)", st_lbl),
            ],
            [
                P("<b>요양기관번호</b><br/>11100079", st_lbl),
                P("서울특별시 송파구 올림픽로43길 88 (풍납동) &nbsp;|&nbsp; 대표전화: +82-2-3010-3114 &nbsp;|&nbsp; 사업자등록번호: 215-82-00192", st_val),
                P("<b>진료일자 / 발행일</b><br/>2026-10-16", st_lbl),
            ],
        ],
        colWidths=[1.5 * inch, 4.6 * inch, 1.5 * inch],
    )
    form_header.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E2E8F0")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#E2E8F0")),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 1.2, colors.HexColor("#0F172A")),
                ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#334155")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(form_header)
    story.append(Spacer(1, 5))

    # Key-Value Matrix Form Grid (Shaded Label Columns Alternating with White Value Columns + Embedded Diagnosis Certificate)
    kv_matrix = Table(
        [
            [
                P("<b>환자 성명</b><br/>(Patient Name)", st_lbl),
                P("<b>김지훈 (Ji-Hoon Kim)</b>", st_val),
                P("<b>해외 보험사명</b><br/>(Insurance Payer)", st_lbl),
                P("<b>UnitedHealthcare Global</b> (유나이티드헬스케어)", st_val),
            ],
            [
                P("<b>생년월일 / 성별</b><br/>(DOB / Sex)", st_lbl),
                P("1982-02-19 &nbsp;|&nbsp; 남성 (Male)", st_val),
                P("<b>증권번호 / 단체번호</b><br/>(Member / Group ID)", st_lbl),
                P("Member ID: <b>UHC-88291044</b> &nbsp;|&nbsp; Group: <b>KOR-TECH-09</b>", st_val),
            ],
            [
                P("<b>주소 및 연락처</b><br/>(Address / Tel)", st_lbl),
                P("서울특별시 강남구 테헤란로 152 (+82-10-3948-2019)", st_val),
                P("<b>진료과 / 담당교수</b><br/>(Attending MD)", st_lbl),
                P("소화기내과 (Gastroenterology) — <b>박성민 교수</b> (면허 제78412호)", st_val),
            ],
            [
                P("<b>주진단 상병코드</b><br/>(Primary ICD-10)", st_lbl),
                P("<b>K25.3</b> — 출혈이 있는 급성 위궤양 (Acute gastric ulcer with hemorrhage)", st_val),
                P("<b>부진단 상병코드</b><br/>(Secondary ICD-10)", st_lbl),
                P("<b>B96.81</b> (헬리코박터 파일로리균) &nbsp;|&nbsp; <b>R10.13</b> (상복부 통증)", st_val),
            ],
            [
                P("<b>임상 소견 및<br/>내시경 진단 내역</b><br/>(Clinical Summary)", st_lbl),
                P(
                    "환자는 5일 전부터 지속된 심와부(상복부) 통증, 속쓰림 및 흑색변 증상으로 소화기내과 외래에 내원함. "
                    "진정 상부소화관 내시경(위내시경) 검사 결과 위 전정부 소만측에 활동성 미세 출혈을 동반한 1.2 cm 크기의 급성 위궤양이 관찰되어 "
                    "내시경적 지혈술 및 조직생검(3개 부위)을 시행함. 신속요소분해효소검사(CLO test) 결과 헬리코박터 파일로리균 양성으로 확인되어 "
                    "양성자펌프억제제(에소메프라졸) 및 제균 항생제 14일분 처방함.",
                    st_val,
                ),
                "",
                "",
            ],
        ],
        colWidths=[1.25 * inch, 2.55 * inch, 1.25 * inch, 2.55 * inch],
    )
    kv_matrix.setStyle(
        TableStyle(
            [
                ("SPAN", (1, 4), (3, 4)),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E2E8F0")),
                ("BACKGROUND", (2, 0), (2, 3), colors.HexColor("#E2E8F0")),
                ("BOX", (0, 0), (-1, -1), 1.0, colors.HexColor("#0F172A")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#475569")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(kv_matrix)
    story.append(Spacer(1, 5))

    # Korean Itemized Fee Schedule Grid
    fee_rows = [
        [
            P("<b>순번</b>", st_th),
            P("<b>진료일자</b>", st_th),
            P("<b>수가 / CPT 코드</b>", st_th),
            P("<b>항목구분</b>", st_th),
            P("<b>진료항목 및 처치 내역 설명 (Itemized Service Description)</b>", st_th),
            P("<b>수량</b>", st_th),
            P("<b>단가 (KRW)</b>", st_th),
            P("<b>금액 (KRW)</b>", st_th),
        ],
        [P("1", st_lbl), P("2026-10-16", st_lbl), P("<b>AA157 / 99203</b>", st_val), P("진찰료", st_lbl), P("초진 진찰료 (소화기내과 상급종합병원 전문의 외래 진료)", st_val), P("1", st_lbl), P("35,000 원", st_val_r), P("35,000 원", st_val_r)],
        [P("2", st_lbl), P("2026-10-16", st_lbl), P("<b>E7611 / 43239</b>", st_val), P("내시경검사", st_lbl), P("상부소화관 내시경검사 및 점막 조직생검 (수면 진정 관리 포함)", st_val), P("1", st_lbl), P("185,000 원", st_val_r), P("185,000 원", st_val_r)],
        [P("3", st_lbl), P("2026-10-16", st_lbl), P("<b>C4612 / 87077</b>", st_val), P("진단검사", st_lbl), P("헬리코박터 파일로리균 신속요소분해효소검사 (CLO Test)", st_val), P("1", st_lbl), P("28,000 원", st_val_r), P("28,000 원", st_val_r)],
        [P("4", st_lbl), P("2026-10-16", st_lbl), P("<b>C5602 / 88305</b>", st_val), P("병리검사", st_lbl), P("위 점막 생검 병리조직검사 (3개 부위 판독료 포함)", st_val), P("1", st_lbl), P("64,000 원", st_val_r), P("64,000 원", st_val_r)],
        [P("5", st_lbl), P("2026-10-16", st_lbl), P("<b>J-PPI / RX14</b>", st_val), P("투약및조제", st_lbl), P("양성자펌프억제제(에소메프라졸) 및 제균 항생제 14일분 처방", st_val), P("1", st_lbl), P("58,000 원", st_val_r), P("58,000 원", st_val_r)],
    ]
    fee_tbl = Table(
        fee_rows,
        colWidths=[0.38 * inch, 0.88 * inch, 0.96 * inch, 0.72 * inch, 2.68 * inch, 0.38 * inch, 0.80 * inch, 0.80 * inch],
    )
    fee_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                ("BOX", (0, 0), (-1, -1), 1.0, colors.HexColor("#0F172A")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#475569")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(fee_tbl)
    story.append(Spacer(1, 5))

    # Bottom Official Receipt Summary & Crimson Stamp Box
    bottom_stamp = Table(
        [
            [
                P("<b>총 진료비 합계<br/>(Total Billed)</b>", st_lbl),
                P("<b>370,000 KRW</b><br/>(미화 환산: <b>$274.07 USD</b> @ 1,350원/USD)", st_val),
                P("<b>결제 수단 및 승인내역<br/>(Payment Proof)</b>", st_lbl),
                P("신용카드 일시불 결제완료<br/><b>현대카드 *7721 (승인번호: #KR-99402812)</b>", st_val),
                P("<b>[ 수 납 필 / PAID ]</b><br/>서울아산병원 원무팀<br/>2026. 10. 16. 영수인의", st_stamp),
            ]
        ],
        colWidths=[1.05 * inch, 1.8 * inch, 1.15 * inch, 2.0 * inch, 1.6 * inch],
    )
    bottom_stamp.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#E2E8F0")),
                ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#E2E8F0")),
                ("BACKGROUND", (4, 0), (4, 0), colors.HexColor("#FEF2F2")),
                ("BOX", (0, 0), (-1, -1), 1.0, colors.HexColor("#0F172A")),
                ("INNERGRID", (0, 0), (3, 0), 0.5, colors.HexColor("#475569")),
                ("BOX", (4, 0), (4, 0), 1.5, colors.HexColor("#991B1B")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(bottom_stamp)

    doc.build(story)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    latin_font, korean_font = register_unicode_fonts()

    en_path = OUTPUT_DIR / "english_itemized_medical_bill.pdf"
    es_path = OUTPUT_DIR / "spanish_factura_medica_hospital.pdf"
    fr_path = OUTPUT_DIR / "french_dossier_medical_autorisation.pdf"
    ko_path = OUTPUT_DIR / "korean_hospital_claim_receipt.pdf"

    generate_english_pdf(en_path, latin_font)
    generate_spanish_pdf(es_path, latin_font)
    generate_french_pdf(fr_path, latin_font)
    generate_korean_pdf(ko_path, korean_font)

    print(f"Generated 4 visually distinct test PDFs in {OUTPUT_DIR}:")
    for p in (en_path, es_path, fr_path, ko_path):
        print(f"  - {p.name} ({p.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
