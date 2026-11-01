"""Document upload and download services."""

from uuid import uuid4

from django.conf import settings

from apps.accounts.models import User
from apps.audit.services import write_audit_log
from apps.deposits.services import DomainError
from apps.documents.models import DepositDocument


class DocumentValidationError(DomainError):
    """Raised when a document upload fails validation."""


ALLOWED_DOCUMENT_MIME_TYPES = {
    "application/pdf": "PDF",
    "image/jpeg": "JPG",
    "image/png": "PNG",
}

DOC_TYPE_CHOICES = [
    ("FDR_CERTIFICATE", "FDR Certificate"),
    ("DEPOSIT_CONFIRMATION", "Deposit Confirmation"),
    ("RENEWAL_LETTER", "Renewal Letter"),
    ("OTHER", "Other"),
]


def _sniff_mime_type(file):
    """Sniff the real content type from the file magic bytes."""
    header = file.read(8)
    file.seek(0)
    if header.startswith(b"%PDF"):
        return "application/pdf"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG"):
        return "image/png"
    return None


def validate_document(file, max_size_mb=None):
    """Validate document type and size; return the detected content type."""
    if file is None or getattr(file, "size", 0) == 0:
        raise DomainError("Uploaded file cannot be empty (0 bytes).")
    max_size_mb = int(max_size_mb if max_size_mb is not None else settings.MAX_DOCUMENT_SIZE_MB)
    if file.size and file.size > max_size_mb * 1024 * 1024:
        raise DocumentValidationError(f"File size exceeds the maximum of {max_size_mb} MB.")

    mime_type = _sniff_mime_type(file)
    if mime_type not in ALLOWED_DOCUMENT_MIME_TYPES:
        raise DocumentValidationError("Unsupported file type. Allowed types: PDF, JPG, PNG.")
    return mime_type


def _build_filename(deposit_id, original_name):
    """Build a private storage path with a sanitized filename."""
    safe_name = "".join(
        char
        for char in (original_name or "file").replace("\\", "_")
        if char.isalnum() or char in (".", "-", "_")
    ).strip("._")
    if not safe_name:
        safe_name = "file"
    return f"documents/{deposit_id}/{uuid4().hex}_{safe_name}"


def upload_document(deposit, file, doc_type, user, max_size_mb=None):
    """Validate and store an uploaded document, writing an audit entry."""
    mime_type = validate_document(file, max_size_mb=max_size_mb)
    filename = _build_filename(deposit.pk, file.name)
    document = DepositDocument(deposit=deposit, doc_type=doc_type, uploaded_by=user)
    document.file.save(filename, file)
    write_audit_log(
        actor=user,
        action="DOCUMENT_UPLOADED",
        model_name="DepositDocument",
        object_id=document.pk,
        changes={
            "deposit": deposit.pk,
            "doc_type": doc_type,
            "filename": filename,
            "content_type": mime_type,
        },
    )
    return document


def get_visible_documents(user, queryset=None):
    """Return the documents visible to the given user.

    INSTITUTION users only see documents belonging to deposits of their own
    institution; users without an institution get an empty queryset.
    """
    queryset = DepositDocument.objects.all() if queryset is None else queryset
    if not user.is_authenticated:
        return queryset.none()
    if user.role == User.Roles.INSTITUTION:
        if user.institution_id:
            return queryset.filter(deposit__institution=user.institution)
        return queryset.none()
    return queryset
