"""API viewsets for the Documents app."""

from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.accounts.api_permissions import IsInstitutionOrStaff
from apps.deposits.services import get_deposit_for_user
from apps.documents.models import DepositDocument
from apps.documents.serializers import DepositDocumentSerializer
from apps.documents.services import get_visible_documents, upload_document


class DepositDocumentViewSet(ModelViewSet):
    """ViewSet for documents with role-based scoping.

    - List/Retrieve: scoped via get_visible_documents.
    - Create (upload): uses upload_document service.
    - Download (custom action): returns FileResponse.
    """

    serializer_class = DepositDocumentSerializer
    permission_classes = [IsInstitutionOrStaff]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return get_visible_documents(self.request.user).order_by("-created_at")

    def get_object(self):
        user = self.request.user
        document = (
            get_visible_documents(user).filter(pk=self.kwargs["pk"]).first()
        )
        if document is None:
            raise Http404("Document not found.")
        return document

    def create(self, request, *args, **kwargs):
        """Upload a document through the upload_document service."""
        file_obj = request.data.get("file")
        doc_type = request.data.get("doc_type")
        deposit_id = request.data.get("deposit")

        if not file_obj or not doc_type or not deposit_id:
            return Response(
                {"detail": "file, doc_type, and deposit are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            deposit = get_deposit_for_user(request.user, int(deposit_id))
        except (ValueError, TypeError):
            return Response({"detail": "Invalid deposit id."}, status=status.HTTP_400_BAD_REQUEST)
        except Http404:
            return Response({"detail": "Deposit not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            document = upload_document(
                deposit=deposit,
                file=file_obj,
                doc_type=doc_type,
                user=request.user,
            )
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(document)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        """Download a document file. Reuses the permission scoping from the web download view."""
        document = self.get_object()
        file_obj = document.file.open("rb")
        file_obj.seek(0)
        return FileResponse(
            file_obj,
            content_type=document.file.content_type or "application/octet-stream",
            as_attachment=True,
            filename=document.file.name,
        )