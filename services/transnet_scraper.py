import hashlib
import logging
from io import BytesIO
from typing import Any, List, cast

import requests
import urllib3
from bs4 import BeautifulSoup

from services.transnet_parser import TransnetPDFParser

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def scrape_transnet_schedule(landing_page_url: str) -> List[dict]:
    log.info("Visiting landing page: %s", landing_page_url)

    try:
        res = requests.get(landing_page_url, headers=HEADERS, verify=False, timeout=20)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        target_link = None
        for anchor in soup.find_all("a", href=True):
            if "DURBAN CONTAINER TERMINAL PIER 2" in anchor.get_text(strip=True).upper():
                target_link = anchor["href"]
                break

        if not target_link:
            log.warning("Could not find Pier 2 link on the page.")
            return []

        if not target_link.startswith("http"):
            base_url = "https://www.transnetportterminals.net"
            if target_link.startswith("/"):
                target_link = base_url + target_link
            else:
                target_link = base_url + "/" + target_link

        log.info("Found PDF link: %s", target_link)

        pdf_res = requests.get(target_link, headers=HEADERS, verify=False, timeout=30)
        pdf_res.raise_for_status()
        pdf_bytes = BytesIO(pdf_res.content)

        log.info("PDF downloaded (%s bytes). Parsing...", len(pdf_res.content))

        parser = TransnetPDFParser()
        vessels = parser.parse_pdf_from_bytes(pdf_bytes)

        log.info("Parser returned %s raw items.", len(vessels))

        final_results = []

        for vessel in vessels:
            vessel_any = cast(Any, vessel)
            if hasattr(vessel_any, "model_dump"):
                vessel_dict = vessel_any.model_dump()
            elif hasattr(vessel_any, "dict"):
                vessel_dict = vessel_any.dict()
            else:
                vessel_dict = vars(vessel_any).copy()

            if "source_url" in vessel_dict:
                vessel_dict["pdf_source_url"] = vessel_dict.pop("source_url")
            else:
                vessel_dict["pdf_source_url"] = target_link

            if "confidence" in vessel_dict:
                del vessel_dict["confidence"]

            v_name = str(vessel_dict.get("vessel_name") or "").strip().upper()
            v_voy = str(vessel_dict.get("voyage_number") or "").strip().upper()
            v_eta = str(vessel_dict.get("eta") or "NO_ETA")

            raw = f"{v_name}-{v_voy}-{v_eta}"
            vessel_dict["row_hash"] = hashlib.sha1(raw.encode()).hexdigest()

            final_results.append(vessel_dict)

        log.info("Parsed %s vessels from PDF.", len(final_results))
        return final_results

    except Exception as exc:
        log.error("Scraper error: %s", exc, exc_info=True)
        return []
