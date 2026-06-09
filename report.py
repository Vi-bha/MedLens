"""
MedLens — PDF Report Generator
Produces structured clinical reports using ReportLab.
"""

import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image as RLImage, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
)


def generate_pdf_report(
    patient_id: str,
    findings: list[dict],
    pirads: int | str,
    viz_path: str | None,
    output_path: str,
) -> str:
    """
    Build a structured PDF clinical report.

    Args:
        patient_id:   PROSTATEx patient identifier.
        findings:     List of finding dicts with keys: finding, significant, gleason.
        pirads:       PI-RADS score (int or 'N/A').
        viz_path:     Path to MRI visualization PNG (optional).
        output_path:  Where to save the PDF.

    Returns:
        output_path on success.
    """
    sig_count = sum(1 for f in findings if f["significant"])

    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=1 * inch, bottomMargin=1 * inch,
    )
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle(
        "Title", parent=styles["Heading1"],
        fontSize=22, alignment=TA_CENTER, spaceAfter=20,
    )
    story.append(Paragraph("<b>MedLens Clinical Report</b>", title_style))
    story.append(Spacer(1, 0.2 * inch))

    # Patient summary table
    status_text = "YES — Clinically Significant" if sig_count > 0 else "NO — Benign"
    data = [
        ["Patient ID",             patient_id],
        ["Report Date",            datetime.now().strftime("%Y-%m-%d %H:%M")],
        ["PI-RADS Score",          f"{pirads} / 5"],
        ["Total Findings",         str(len(findings))],
        ["Clinically Significant", status_text],
    ]
    table = Table(data, colWidths=[2.2 * inch, 4 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eeeeee")),
        ("FONTNAME",   (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 10),
        ("GRID",       (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.3 * inch))

    # MRI visualization
    if viz_path and os.path.exists(viz_path):
        story.append(RLImage(viz_path, width=5.5 * inch, height=2.5 * inch))
        story.append(Spacer(1, 0.2 * inch))

    # Findings
    story.append(Paragraph("<b>Clinical Findings</b>", styles["Heading2"]))
    if findings:
        for f in findings:
            is_sig = f["significant"]
            color = "#cc0000" if is_sig else "#226622"
            label = "CLINICALLY SIGNIFICANT" if is_sig else "Benign"
            story.append(Paragraph(
                f"<font color='{color}'><b>Finding {f['finding']}: {label}</b></font>"
                f" — Gleason: {f.get('gleason', 'N/A')}",
                styles["Normal"],
            ))
            story.append(Spacer(1, 0.1 * inch))
    else:
        story.append(Paragraph("No lesions detected.", styles["Normal"]))

    story.append(Spacer(1, 0.2 * inch))

    # Recommendation
    story.append(Paragraph("<b>Clinical Recommendation</b>", styles["Heading2"]))
    if sig_count > 0:
        rec = ("Clinically significant findings detected. "
               "Recommend urological consultation and biopsy confirmation.")
    elif isinstance(pirads, int) and pirads >= 3:
        rec = ("Equivocal findings. Consider repeat MRI in 6–12 months "
               "or targeted biopsy if PSA is rising.")
    else:
        rec = "No significant findings. Continue routine surveillance with annual PSA."

    story.append(Paragraph(rec, styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(
        "<i>AI-assisted report. Requires radiologist confirmation. "
        "Not for clinical use without expert review.</i>",
        styles["Normal"],
    ))

    doc.build(story)
    print(f"✅ PDF saved: {output_path}")
    return output_path
