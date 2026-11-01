"""Text extraction and field regex extraction for the FDR review agent.

No OCR is performed: images (JPG/PNG/...) and scanned PDFs without a text
layer yield NO_TEXT_LAYER instead of being OCR'd.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


# Extraction statuses mirror apps.agent.models.ExtractedField.ExtractionStatus.
STATUS_OK = "OK"
STATUS_NOT_FOUND = "NOT_FOUND"
STATUS_NO_TEXT_LAYER = "NO_TEXT_LAYER"

# File types the agent must never OCR.
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif"}
PDF_EXTENSION = ".pdf"


# ---------------------------------------------------------------------------
# Regex patterns (module level so they are easy to change)
# ---------------------------------------------------------------------------

# Dates: DD/MM/YYYY, DD-MM-YYYY, DD Mon YYYY (e.g. 12 Jan 2024). No guessing.
DATE_TOKEN = r"\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4}|\d{2} [A-Z][a-z]{2} \d{4}"

REFERENCE_NUMBER_REGEX = re.compile(
    r"(?:reference\s*(?:no|number|#)?|ref\.?)\s*[:\-]?\s*([A-Z0-9][A-Z0-9/\-]{4,})",
    re.IGNORECASE,
)
AMOUNT_REGEX = re.compile(
    r"(?:amount|total\s*amount|value)\s*[:\-]?\s*(?:Rs\.?\s*)?([\d,]+(?:\.\d{1,2})?)",
    re.IGNORECASE,
)
ISSUE_DATE_REGEX = re.compile(
    rf"(?:issue\s*(?:date)?)\s*[:\-]?\s*({DATE_TOKEN})", re.IGNORECASE
)
MATURITY_DATE_REGEX = re.compile(
    rf"(?:maturity\s*(?:date)?)\s*[:\-]?\s*({DATE_TOKEN})", re.IGNORECASE
)
BANK_NAME_REGEX = re.compile(
    r"(?:bank\s*(?:name)?)\s*[:\-]?\s*([A-Z][A-Z0-9 &\.\'-]{2,})",
    re.IGNORECASE,
)

FIELD_REGEXES = (
    ("reference_number", REFERENCE_NUMBER_REGEX),
    ("amount", AMOUNT_REGEX),
    ("issue_date", ISSUE_DATE_REGEX),
    ("maturity_date", MATURITY_DATE_REGEX),
    ("bank_name", BANK_NAME_REGEX),
)


@dataclass(frozen=True)
class FieldExtraction:
    """Result of extracting one field from document text."""

    field_name: str
    extracted_value: str
    source_snippet: str
    extraction_status: str


def extract_pdf_text(file_path) -> str:
    """Return the embedded text layer of a PDF file.

    Returns an empty string for images, for files pypdf cannot read, and for
    scanned PDFs that have no text layer. No OCR is ever performed.
    """
    path = Path(file_path)

    if path.suffix.lower() in IMAGE_EXTENSIONS:
        return ""

    if path.suffix.lower() != PDF_EXTENSION:
        return ""

    try:
        reader = PdfReader(str(path))
    except Exception:
        return ""

    pages_text = []
    for page in reader.pages:
        try:
            pages_text.append(page.extract_text() or "")
        except Exception:
            pages_text.append("")

    return "\n".join(pages_text)


def extract_fields(text: str) -> list[FieldExtraction]:
    """Run every field regex against ``text``.

    Fields without a match are reported as NOT_FOUND with an empty snippet.
    """
    results: list[FieldExtraction] = []
    for field_name, regex in FIELD_REGEXES:
        match = regex.search(text)
        if not match:
            results.append(
                FieldExtraction(
                    field_name=field_name,
                    extracted_value="",
                    source_snippet="",
                    extraction_status=STATUS_NOT_FOUND,
                )
            )
            continue
        snippet = match.group(0).strip()
        value = match.group(1).strip() if match.lastindex else snippet
        results.append(
            FieldExtraction(
                field_name=field_name,
                extracted_value=value,
                source_snippet=snippet,
                extraction_status=STATUS_OK,
            )
        )
    return results


def extract_from_file(file_path) -> tuple[str, list[FieldExtraction]]:
    """Extract the text layer of ``file_path`` then run the field regexes.

    Images and scanned PDFs (no text layer) return empty text and every field
    is reported NO_TEXT_LAYER without any OCR.
    """
    text = extract_pdf_text(file_path)

    if not text:
        return (
            "",
            [
                FieldExtraction(
                    field_name=name,
                    extracted_value="",
                    source_snippet="",
                    extraction_status=STATUS_NO_TEXT_LAYER,
                )
                for name, _ in FIELD_REGEXES
            ],
        )

    return text, extract_fields(text)