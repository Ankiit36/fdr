"""Document views: upload and secure download."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.views import View
from django.shortcuts import redirect

from apps.accounts.permissions import is_admin, is_institution_user
from apps.documents import services
from apps.documents.forms import DocumentUploadForm
from apps.documents.models import DepositDocument
from apps.documents.services import get_visible_documents
from apps.deposits.services import get_deposit_for_user


class DocumentUploadView(LoginRequiredMixin, View):
    """Upload a document to a deposit (INSTITUTION own deposit / ADMIN)."""

    def post(self, request, pk):
        deposit = get_deposit_for_user(request.user, pk)
        if not (is_admin(request.user) or is_institution_user(request.user)):
            raise PermissionDenied
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            services.upload_document(
                deposit,
                form.cleaned_data.get("file"),
                form.cleaned_data.get("doc_type"),
                request.user,
            )
            return redirect("deposit_detail", deposit.pk)
        return redirect("deposit_detail", deposit.pk)


class DocumentDownloadView(LoginRequiredMixin, View):
    """Secure document download; returns 404 when the user cannot see it."""

    def get(self, request, pk):
        user = request.user
        document = get_visible_documents(user).filter(pk=pk).first()
        if document is None:
            raise Http404("Document not found.")
        file = document.file.open("rb")
        file.seek(0)
        return FileResponse(
            file,
            content_type=document.file.content_type or "application/octet-stream",
            as_attachment=True,
            filename=document.file.name,
        )
