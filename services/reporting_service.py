"""
Reporting service for supervisor audit summaries.
"""
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List

from fpdf import FPDF
from sqlalchemy.orm import Session

from models.container import Container
from models.downtime import Downtime
from models.evidence import ContainerImage
from services.evidence_service import EvidenceService


class ContainerSummaryPDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "PORTGUARD CCMS v3 - CONTAINER SUMMARY", 0, 1, "C")
        self.set_font("Arial", "", 10)
        self.cell(0, 6, "Supervisor Audit Report", 0, 1, "C")
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cell(0, 10, f"Generated {timestamp} | Page {self.page_no()}", 0, 0, "C")
def generate_container_summary_pdf(
    container_data: dict,
    images: List,
    commercial_impact: str,
    verified_photos: int,
    required_photos: int
):
    """Generate a basic PDF summary for supervisor audit."""
    try:
        pdf = ContainerSummaryPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=11)

        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, f"Container: {container_data.get('container_no', '-')}", 1, 1, "L", fill=True)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 8, f"Status: {container_data.get('status', '-')}", 1, 1, "L")
        pdf.cell(0, 8, f"Client: {container_data.get('client', '-')}", 1, 1, "L")

        pdf.ln(2)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "Commercial Impact", 0, 1, "L")
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, commercial_impact, 0, 1, "L")

        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 8, f"Verified Photos: {verified_photos}/{required_photos}", 0, 1, "L")
        pdf.ln(2)

        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "Photo Evidence (max 5):", 0, 1)
        pdf.set_font("Arial", "", 8)

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for i, img in enumerate(images[:5]):
            x_pos = 10 if i % 2 == 0 else 110
            if i % 2 == 0 and i > 0:
                pdf.ln(55)

            current_y = pdf.get_y()
            label = getattr(img, "image_type", "UNKNOWN")
            pdf.text(x_pos, current_y, f"Type: {label}")

            rel_path = getattr(img, "file_path", "")
            full_path = os.path.normpath(os.path.join(base_dir, rel_path))
            if os.path.exists(full_path):
                pdf.image(full_path, x=x_pos, y=current_y + 2, w=90)
            else:
                pdf.set_xy(x_pos, current_y + 10)
                pdf.cell(90, 10, "MISSING FILE", 1, 0, "C")

        return pdf.output(dest="S")
    except Exception:
        return None


class ReportingService:
    @staticmethod
    def generate_summary_pdf(container_id: str, db: Session) -> str:
        container_uuid = uuid.UUID(container_id)
        container = db.query(Container).filter(Container.id == container_uuid).first()
        if not container:
            raise ValueError("Container not found")

        images = db.query(ContainerImage).filter(ContainerImage.container_id == container.id).all()
        downtimes = db.query(Downtime).filter(Downtime.container_id == container.id).all()

        total_hours = 0.0
        now = datetime.utcnow()
        for dt in downtimes:
            if dt.end_time is None:
                duration_hours = (now - dt.start_time).total_seconds() / 3600
            else:
                duration_hours = (dt.end_time - dt.start_time).total_seconds() / 3600
            total_hours += duration_hours

        total_cost_impact_zar = total_hours * 250.0
        commercial_impact = f"R {total_cost_impact_zar:,.2f}"

        validation = EvidenceService.validate_evidence(str(container.id), db)
        verified_photos = int(validation.get("uploaded_photos", 0))
        required_photos = int(validation.get("required_photos", 5))

        container_data = {
            "container_no": container.container_no,
            "status": container.status.value if hasattr(container.status, "value") else str(container.status),
            "client": container.client
        }

        pdf_bytes = generate_container_summary_pdf(
            container_data=container_data,
            images=images,
            commercial_impact=commercial_impact,
            verified_photos=verified_photos,
            required_photos=required_photos
        )

        if pdf_bytes is None:
            raise ValueError("Failed to generate PDF")

        if isinstance(pdf_bytes, str):
            pdf_bytes = pdf_bytes.encode("latin-1")

        reports_dir = Path("uploads/reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        file_path = reports_dir / f"container_report_{container.container_no}_{uuid.uuid4()}.pdf"
        file_path.write_bytes(bytes(pdf_bytes))

        return str(file_path)
