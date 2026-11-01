"""Serializers for the Notifications API."""

from rest_framework import serializers

from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "deposit", "message", "is_read", "created_at"]
        read_only_fields = ["id", "user", "deposit", "message", "created_at"]