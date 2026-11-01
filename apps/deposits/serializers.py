"""Serializers for the Deposits API."""

from rest_framework import serializers

from apps.deposits.models import Deposit


class DepositSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deposit
        fields = [
            "id",
            "institution",
            "instrument_type",
            "reference_number",
            "bank_name",
            "bank_branch",
            "amount",
            "issue_date",
            "maturity_date",
            "status",
            "verification_source",
            "previous_deposit",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "verification_source", "created_by", "created_at", "updated_at"]