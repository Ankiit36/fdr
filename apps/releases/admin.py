"""Admin registration for the releases app."""

from django.contrib import admin
from apps.releases.models import Release


@admin.register(Release)
class ReleaseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "deposit",
        "request_type",
        "status",
        "amount",
        "requested_by",
        "requested_at",
        "reviewed_by",
        "reviewed_at",
    )
    list_filter = ("status", "request_type", "requested_at")
    search_fields = ("deposit__reference_number", "deposit__bank_name", "decision_note")
    readonly_fields = ("amount", "requested_at", "created_at", "updated_at")
