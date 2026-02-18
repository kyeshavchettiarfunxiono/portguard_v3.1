import re
import logging
from typing import List, Optional
from datetime import date, datetime
from dataclasses import dataclass
import requests
from io import BytesIO
import os

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    from pdf2image import convert_from_bytes
    import pytesseract
    from PIL import Image, ImageEnhance, ImageOps

    if os.name == "nt":
        t_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.path.exists(t_path):
            pytesseract.pytesseract.tesseract_cmd = t_path

    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


@dataclass
class TransnetVesselData:
    vessel_name: str
    voyage_number: Optional[str] = None
    terminal: Optional[str] = None
    berth: Optional[str] = None
    eta: Optional[datetime] = None
    etd: Optional[datetime] = None
    stack_open: Optional[datetime] = None
    stack_close: Optional[datetime] = None
    status: Optional[str] = None
    source_url: Optional[str] = None
    confidence: float = 0.0


class TransnetPDFParser:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    def parse_pdf_from_url(self, url: str) -> List[TransnetVesselData]:
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return self.parse_pdf_from_bytes(BytesIO(response.content))
        except Exception as exc:
            self.logger.error("Failed to parse PDF from URL %s: %s", url, exc)
            return []

    def parse_pdf_from_bytes(self, pdf_bytes: BytesIO, use_ocr: bool = False) -> List[TransnetVesselData]:
        vessels: List[TransnetVesselData] = []
        try:
            if PDFPLUMBER_AVAILABLE or OCR_AVAILABLE:
                self.logger.info("Starting Transnet PDF parse")
                pdf_bytes.seek(0)
                vessels = self._parse_with_ocr(pdf_bytes)
            else:
                self.logger.warning("No PDF parsing backend available (pdfplumber/OCR missing).")
            return vessels
        except Exception as exc:
            self.logger.error("Failed to parse PDF: %s", exc, exc_info=True)
            return []

    def _parse_with_ocr(self, pdf_bytes: BytesIO) -> List[TransnetVesselData]:
        vessels: List[TransnetVesselData] = []
        try:
            self.logger.info("Attempting direct text extraction")
            if PDFPLUMBER_AVAILABLE:
                with pdfplumber.open(pdf_bytes) as pdf:
                    full_text = ""
                    for page in pdf.pages:
                        full_text += page.extract_text() or ""

                    if full_text.strip():
                        self.logger.info("Direct text extracted successfully")
                        vessels = self._extract_vessels_from_text(full_text, 0, datetime.now().date())

            if not vessels and OCR_AVAILABLE:
                self.logger.warning("Direct text failed or empty. OCR fallback not implemented.")

            return vessels
        except Exception as exc:
            self.logger.error("Scraper error: %s", exc)
            return []

    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            clean = (
                date_str.strip()
                .replace("l", "1")
                .replace("O", "0")
                .replace("o", "0")
                .replace(".", "/")
            )
            for fmt in ["%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"]:
                try:
                    return datetime.strptime(clean, fmt)
                except ValueError:
                    continue
            return None
        except Exception:
            return None

    def _extract_vessels_from_text(self, text: str, page_num: int, report_date: date) -> List[TransnetVesselData]:
        results: List[TransnetVesselData] = []
        lines = text.split("\n")
        visit_pattern = re.compile(r"(DCT\d{5})")

        for line in lines:
            match = visit_pattern.search(line)
            if match:
                visit_no = match.group(1)
                parts = line.split(visit_no)
                vessel_name = parts[0].strip()

                if len(vessel_name) < 3 or any(v.voyage_number == visit_no for v in results):
                    continue

                date_match = re.search(r"(\d{2}/\d{2}/\d{4})", line)
                eta = self._parse_date_string(date_match.group(1)) if date_match else None

                vessel = TransnetVesselData(
                    vessel_name=vessel_name,
                    voyage_number=visit_no,
                    terminal="Pier 2",
                    eta=eta if eta else datetime.combine(report_date, datetime.min.time()),
                    status="Working" if "WORKING" in line.upper() else "Scheduled",
                    confidence=1.0,
                )
                results.append(vessel)
                self.logger.info("FOUND: %s (%s)", vessel_name, visit_no)

        return results

    def validate_vessel_data(self, vessel: TransnetVesselData) -> bool:
        return bool(vessel.vessel_name and len(vessel.vessel_name) > 2)

    def enhance_vessel_data(self, vessel: TransnetVesselData) -> TransnetVesselData:
        return vessel


def parse_transnet_pdf_url(url: str):
    parser = TransnetPDFParser()
    results = []
    for vessel in parser.parse_pdf_from_url(url):
        results.append(vars(vessel))
    return results
