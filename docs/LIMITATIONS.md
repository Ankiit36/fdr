# System Capabilities and Technical Limitations

This document outlines the operational boundaries, technical constraints, and design choices of the AICTE FDR / Security Deposit Management Portal. All points reflect verified application code.

## 1. Mock Bank Verification
- The bank verification integration (`apps/verification/services.py`) is implemented using `MockBankVerificationService`.
- No live banking API or core banking system (CBS) gateway is connected. Deposits marked `VERIFIED` with tier `BANK_CONFIRMED` are verified via simulated responses.

## 2. Email Delivery in Development
- In development and testing environments, `EMAIL_BACKEND` is configured to `django.core.mail.backends.console.EmailBackend`.
- Outgoing reminder and alert emails are written to the standard console output and are not dispatched over SMTP to external inboxes.

## 3. Absence of OCR
- The agent extraction layer (`apps/agent/extraction.py`) uses `pypdf` to parse digital text layers only.
- Scanned documents, raster images, and PDFs without embedded text layers produce rule `R05 (NO_TEXT_LAYER)` or missing field extractions (`R06`). No OCR engine (e.g., Tesseract, AWS Textract) is installed or permitted.

## 4. No Digital Signature Verification
- Digital certificate validation, PKCS#7 / PAdES digital signature parsing, and cryptographic verification of e-signatures are not implemented.
- Deposit verification tier `E_FDR_SIGNED` was explicitly excluded because no cryptographic signature library is approved for the environment.

## 5. Metadata-Only Forgery Heuristics
- Document anomaly detection (`apps/agent/forgery.py`) relies exclusively on metadata checks (e.g., software editor tags in Producer/Creator fields, modification vs creation timestamp skew, and multiple `%%EOF` markers).
- These heuristics identify metadata inconsistencies and do **not** prove document forgery or tampering.
- Advanced forensic analyses (such as Error Level Analysis, JPEG ghost detection, or font-embedding raster inspection) are not supported because Pillow and computer vision libraries are excluded.

## 6. Mock SMS and WhatsApp Channels
- SMS and WhatsApp dispatchers (`apps/notifications/channels.py`) are implemented via `SmsMockChannel` and `WhatsAppMockChannel`.
- Messages are logged using the application logger (`logger.info`) without integrating with external SMS gateways (e.g., Twilio, Gupshup) or Meta WhatsApp Business APIs.

## 7. Hand-Built Text-Only PDF Generation
- Institutional summary PDF reports (`apps/dashboard/pdf_report.py`) and synthetic test PDFs (`apps/agent/synthetic.py`) are constructed manually using basic PDF-1.4 text stream syntax and standard Helvetica fonts.
- Neither `reportlab` nor headless browser rendering is used. Reports do not support rich tabular cell wrapping, vector styling, charts, or embedded imagery.

## 8. Dashboard Heading-Only Hindi Localization
- Localization (`apps/dashboard/labels.py`) covers only primary dashboard overview headings and metric cards (such as Active, Expiring, Matured, Renewed, and Total Value).
- Dynamic model fields, error messages, form controls, and detailed child tables remain in English. Full Django `gettext` GNU MO/PO localization is not enabled.

## 9. Rule-Based Review Agent (Non-AI / Non-LLM)
- The review agent (`apps/agent/rules.py`) uses deterministic pure Python comparison functions (`R01` through `R11`).
- No generative AI, Large Language Model (LLM), or probabilistic machine learning framework is utilized. Findings are produced strictly by matching structured regex patterns, dates, numbers, and tolerance boundaries.
