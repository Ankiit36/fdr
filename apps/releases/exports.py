"""CSV export utilities for releases."""

import csv
from django.http import HttpResponse


def export_releases_csv(queryset):
    """Export releases queryset as a CSV HttpResponse."""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="releases.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "id",
        "deposit_reference",
        "request_type",
        "status",
        "amount",
        "requested_at",
        "reviewed_at",
    ])

    for release in queryset.select_related("deposit"):
        writer.writerow([
            release.id,
            release.deposit.reference_number if release.deposit else "",
            release.request_type,
            release.status,
            release.amount,
            release.requested_at,
            release.reviewed_at or "",
        ])

    return response
