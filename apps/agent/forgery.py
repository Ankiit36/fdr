"""PDF metadata and structural forgery heuristics.

Note: These are heuristics based on metadata and raw byte structure.
They do not prove forgery (metadata check, not proof).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

import pypdf
from django.conf import settings

logger = logging.getLogger(__name__)


class ForgeryCheckResult(dict):
    """Dictionary representing a triggered forgery heuristic.

    Supports equality comparison with string rule codes for convenience.
    """

    def __eq__(self, other):
        if isinstance(other, str):
            return self.get("rule_code") == other
        return super().__eq__(other)


def _parse_pdf_date(val) -> datetime | None:
    """Parse PDF date field into a naive or timezone-aware datetime."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    s = str(val).strip()
    if s.startswith("D:"):
        s = s[2:]
    digits = re.sub(r"[^\d]", "", s)
    if len(digits) >= 8:
        try:
            year = int(digits[:4])
            month = int(digits[4:6])
            day = int(digits[6:8])
            hour = int(digits[8:10]) if len(digits) >= 10 else 0
            minute = int(digits[10:12]) if len(digits) >= 12 else 0
            second = int(digits[12:14]) if len(digits) >= 14 else 0
            return datetime(year, month, day, hour, minute, second)
        except Exception:
            return None
    return None


def check_pdf_structure(file_path: str) -> list[ForgeryCheckResult]:
    """Inspect PDF metadata and structure for common anomaly heuristics.

    Checks:
      - F01 EDITOR_PRODUCER (WARNING): Producer or Creator contains a keyword
        from settings.AGENT_EDITOR_KEYWORDS (case-insensitive).
      - F02 MODDATE_AFTER_CREATION (WARNING): CreationDate and ModDate both exist
        and differ by more than 1 day.
      - F03 INCREMENTAL_UPDATE (WARNING): Raw bytes contain more than one "%%EOF".
      - F04 NO_METADATA (INFO): Neither Producer nor CreationDate exists.
    """
    triggered: list[ForgeryCheckResult] = []

    # Read raw bytes
    try:
        with open(file_path, "rb") as f:
            raw_bytes = f.read()
    except Exception as exc:
        logger.warning("Could not read raw PDF bytes for %s: %s", file_path, exc)
        raw_bytes = b""

    # Parse metadata with pypdf
    producer = ""
    creator = ""
    creation_date = None
    mod_date = None
    has_metadata = False

    try:
        reader = pypdf.PdfReader(file_path)
        meta = reader.metadata
        if meta:
            has_metadata = True
            producer = str(meta.get("/Producer") or meta.get("Producer") or "").strip()
            creator = str(meta.get("/Creator") or meta.get("Creator") or "").strip()
            creation_date = meta.get("/CreationDate") or meta.get("CreationDate")
            mod_date = meta.get("/ModDate") or meta.get("ModDate")
    except Exception as exc:
        logger.warning("pypdf metadata extraction failed on %s: %s", file_path, exc)

    # Check F01: EDITOR_PRODUCER (WARNING)
    default_keywords = ["Photoshop", "GIMP", "Canva", "iLovePDF", "Smallpdf", "PDF-XChange"]
    configured_keywords = getattr(settings, "AGENT_EDITOR_KEYWORDS", default_keywords)
    if isinstance(configured_keywords, str):
        keywords = [k.strip() for k in configured_keywords.split(",") if k.strip()]
    else:
        keywords = list(configured_keywords)

    search_text = f"{producer} {creator}".lower()
    matched_keyword = None
    for kw in keywords:
        kw_clean = kw.strip().lower()
        if kw_clean and kw_clean in search_text:
            matched_keyword = kw.strip()
            break

    if matched_keyword:
        triggered.append(
            ForgeryCheckResult({
                "rule_code": "F01",
                "severity": "WARNING",
                "category": "FORGERY_SUSPECT",
                "message": (
                    f"Producer/Creator metadata contains editor keyword '{matched_keyword}' "
                    f"(metadata check, not proof)"
                ),
                "params": {"snippet": str(matched_keyword)},
            })
        )

    # Check F02: MODDATE_AFTER_CREATION (WARNING)
    if creation_date and mod_date:
        c_dt = _parse_pdf_date(creation_date)
        m_dt = _parse_pdf_date(mod_date)
        if c_dt and m_dt:
            diff_seconds = abs((m_dt - c_dt).total_seconds())
            if diff_seconds > 86400:  # more than 1 day
                triggered.append(
                    ForgeryCheckResult({
                        "rule_code": "F02",
                        "severity": "WARNING",
                        "category": "FORGERY_SUSPECT",
                        "message": (
                            f"Modification date differs from creation date by more than 1 day "
                            f"(metadata check, not proof)"
                        ),
                        "params": {},
                    })
                )

    # Check F03: INCREMENTAL_UPDATE (WARNING)
    if raw_bytes.count(b"%%EOF") > 1:
        triggered.append(
            ForgeryCheckResult({
                "rule_code": "F03",
                "severity": "WARNING",
                "category": "FORGERY_SUSPECT",
                "message": (
                    "Multiple %%EOF markers detected; file contains incremental updates "
                    "(metadata check, not proof)"
                ),
                "params": {},
            })
        )

    # Check F04: NO_METADATA (INFO)
    # Neither Producer nor CreationDate exists
    if not producer and not creation_date:
        triggered.append(
            ForgeryCheckResult({
                "rule_code": "F04",
                "severity": "INFO",
                "category": "FORGERY_SUSPECT",
                "message": (
                    "No Producer or CreationDate metadata present in PDF "
                    "(metadata check, not proof)"
                ),
                "params": {},
            })
        )

    return triggered
