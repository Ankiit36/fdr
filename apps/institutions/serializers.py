"""Serializers for the Institutions API."""

from rest_framework import serializers

from apps.institutions.models import Institution


class InstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institution
        fields = ["id", "name", "code", "address", "contact_email", "contact_phone", "is_active"]