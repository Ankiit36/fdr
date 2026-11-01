"""Serializers for the Documents API."""

from rest_framework import serializers

from apps.documents.models import DepositDocument


class DepositDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepositDocument
        fields = ["id", "deposit", "doc_type", "file", "uploaded_by", "uploaded_at"]
        read_only_fields = ["id", "file", "uploaded_by", "uploaded_at"]