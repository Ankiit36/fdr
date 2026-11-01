"""CSV export utilities for deposits."""

import csv
from django.http import HttpResponse


def export_deposits_csv(queryset):
    """Export deposits queryset as a CSV HttpResponse."""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="deposits.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "id",
        "institution_code",
        "reference_number",
        "instrument_type",
        "bank_name",
        "bank_branch",
        "amount",
        "issue_date",
        "maturity_date",
        "lock_in_end_date",
        "status",
        "verification_source",
        "verification_tier",
    ])

    for deposit in queryset.select_related("institution"):
        writer.writerow([
            deposit.id,
            deposit.institution.code if deposit.institution else "",
            deposit.reference_number,
            deposit.instrument_type,
            deposit.bank_name,
            deposit.bank_branch or "",
            deposit.amount,
            deposit.issue_date,
            deposit.maturity_date,
            deposit.lock_in_end_date or "",
            deposit.status,
            deposit.verification_source,
            deposit.verification_tier,
        ])

    return response
