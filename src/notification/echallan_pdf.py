"""
Feature 5: E-Challan PDF Generator
-------------------------------------
Generates a proper RTO-format E-Challan PDF with:
- Violation image
- Owner info + vehicle details
- Fine amount and breakdown
- QR code pointing to online payment portal
CPU-only using reportlab + qrcode. VRAM cost: 0.
"""

import logging
import qrcode
import io
from pathlib import Path
from datetime import datetime
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, Image as RLImage, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

logger = logging.getLogger(__name__)

class EChallanPDFGenerator:
    """
    Generates legally-formatted E-Challan PDFs with QR code for online payment.
    Uses ReportLab. No GPU. CPU only.
    """
    def __init__(self, output_dir: str = 'output/challans', payment_base_url: str = 'https://echallan.parivahan.gov.in/challan/'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.payment_url = payment_base_url
        logger.info(f"EChallanPDFGenerator ready. Output: {output_dir}")

    def _generate_qr(self, violation_id: int) -> io.BytesIO:
        """Generate QR code for online payment."""
        url = f"{self.payment_url}{violation_id}"
        qr = qrcode.QRCode(version=2, box_size=6, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return buf

    def generate(
        self,
        violation_id: int,
        plate_number: str,
        owner_name: str,
        owner_phone: str,
        violation_type: str,
        violation_location: str,
        violation_timestamp: datetime,
        camera_id: str,
        fine_amount: float,
        evidence_image_path: Optional[str] = None
    ) -> str:
        """
        Generate the E-Challan PDF and return the file path.
        """
        challan_no = f"MH-TIS-{violation_id:06d}"
        timestamp_str = violation_timestamp.strftime("%d-%m-%Y %H:%M:%S")
        filename = f"echallan_{challan_no}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = self.output_dir / filename

        doc = SimpleDocTemplate(
            str(filepath), pagesize=A4,
            rightMargin=1.5*cm, leftMargin=1.5*cm,
            topMargin=1.5*cm, bottomMargin=1.5*cm
        )
        styles = getSampleStyleSheet()
        story = []

        # ── Header ──
        header_style = ParagraphStyle('header', fontSize=16, alignment=TA_CENTER, 
                                       textColor=colors.HexColor('#1a237e'), spaceAfter=4)
        sub_style = ParagraphStyle('sub', fontSize=10, alignment=TA_CENTER, 
                                    textColor=colors.grey, spaceAfter=10)
        story.append(Paragraph("🚦 TRAFFIC INTELLIGENCE SYSTEM", header_style))
        story.append(Paragraph("E-CHALLAN / Electronic Notice of Traffic Violation", sub_style))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1a237e')))
        story.append(Spacer(1, 10))

        # ── Challan Info ──
        info_data = [
            ["Challan No:", challan_no,       "Date & Time:", timestamp_str],
            ["Camera ID:", camera_id,         "Status:",      "PENDING PAYMENT"],
            ["Location:", violation_location,  "",             ""],
        ]
        info_table = Table(info_data, colWidths=[3.5*cm, 6*cm, 3.5*cm, 5*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('TEXTCOLOR', (3,1), (3,1), colors.red),
            ('FONTNAME', (3,1), (3,1), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.3, colors.lightgrey),
            ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.HexColor('#f5f5f5'), colors.white]),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 12))

        # ── Vehicle & Owner ──
        story.append(Paragraph("VEHICLE & OWNER INFORMATION", 
                                ParagraphStyle('sec', fontSize=11, textColor=colors.HexColor('#1a237e'),
                                               fontName='Helvetica-Bold', spaceAfter=4)))
        owner_data = [
            ["Number Plate:", plate_number],
            ["Owner Name:", owner_name],
            ["Contact Number:", owner_phone],
        ]
        owner_table = Table(owner_data, colWidths=[5*cm, 13*cm])
        owner_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('GRID', (0,0), (-1,-1), 0.3, colors.lightgrey),
            ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.white, colors.HexColor('#f5f5f5')]),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(owner_table)
        story.append(Spacer(1, 12))

        # ── Violation Details ──
        story.append(Paragraph("VIOLATION DETAILS", 
                                ParagraphStyle('sec2', fontSize=11, textColor=colors.HexColor('#b71c1c'),
                                               fontName='Helvetica-Bold', spaceAfter=4)))
        violation_data = [
            ["Violation Type:", violation_type],
            ["Fine Amount:", f"Rs. {fine_amount:.2f}"],
            ["Due Date:", (violation_timestamp.replace(day=violation_timestamp.day+30)).strftime("%d-%m-%Y") if violation_timestamp.month < 12 else "Next Month"],
        ]
        v_table = Table(violation_data, colWidths=[5*cm, 13*cm])
        v_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTNAME', (1,1), (1,1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (1,1), (1,1), colors.red),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('GRID', (0,0), (-1,-1), 0.3, colors.lightgrey),
            ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.HexColor('#fff3f3'), colors.white]),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(v_table)
        story.append(Spacer(1, 12))

        # ── Evidence Image + QR Code ──
        story.append(Paragraph("EVIDENCE & PAYMENT", 
                                ParagraphStyle('sec3', fontSize=11, textColor=colors.HexColor('#1a237e'),
                                               fontName='Helvetica-Bold', spaceAfter=4)))
        
        ev_elements = []
        # Evidence image (if exists)
        if evidence_image_path and Path(evidence_image_path).exists():
            ev_img = RLImage(evidence_image_path, width=9*cm, height=6*cm)
            ev_elements.append(ev_img)
        else:
            ev_elements.append(Paragraph("[No Image Available]", styles['Normal']))

        # QR code
        qr_buf = self._generate_qr(violation_id)
        qr_img = RLImage(qr_buf, width=4*cm, height=4*cm)
        qr_para = Paragraph(f"Scan to Pay Online\n{self.payment_url}{violation_id}",
                             ParagraphStyle('qr', fontSize=7, alignment=TA_CENTER))
        ev_elements.append(qr_img)
        ev_elements.append(qr_para)

        ev_table = Table([ev_elements], colWidths=[10*cm, 8*cm])
        ev_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (1,0), (1,0), 'CENTER'),
        ]))
        story.append(ev_table)
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))

        # ── Footer ──
        story.append(Paragraph(
            "⚠️ Non-payment within 30 days will result in license suspension and additional penalties under MV Act 2019. "
            "This is a computer-generated notice and does not require a manual signature.",
            ParagraphStyle('foot', fontSize=7, textColor=colors.grey, alignment=TA_CENTER, spaceBefore=6)
        ))

        doc.build(story)
        logger.info(f"E-Challan PDF generated: {filepath}")
        return str(filepath)
