"""Admin configuration for the deposits app."""

from django.contrib import admin
from apps.deposits.models import Deposit, ScrutinyObservation


@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "reference_number",
        "institution",
        "bank_name",
        "amount",
        "status",
        "verification_tier",
        "lock_in_end_date",
        "maturity_date",
    )
    list_filter = ("status", "verification_tier", "instrument_type")
    search_fields = ("reference_number", "bank_name", "institution__name", "institution__code")


@admin.register(ScrutinyObservation)
class ScrutinyObservationAdmin(admin.ModelAdmin):
    list_display = ("id", "deposit", "officer", "created_at")

