"""Serializers for the Agent API."""

from rest_framework import serializers

from apps.agent.models import AgentFinding


class AgentFindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentFinding
        fields = [
            "id",
            "review_run",
            "deposit",
            "severity",
            "category",
            "message",
            "rule_code",
            "status",
            "resolved_by",
            "resolved_at",
            "created_at",
            "resolution_note",
        ]
        read_only_fields = ["id", "review_run", "deposit", "severity", "category", "message", "rule_code", "created_at"]