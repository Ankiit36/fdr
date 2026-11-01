"""Forms for deposit CRUD."""

from django import forms

from apps.deposits import services
from apps.deposits.models import Deposit


class DepositForm(forms.ModelForm):
    """Form for creating and editing deposits.

    Business rules (maturity after issue date, unique bank + reference) are
    enforced through the service layer, not duplicated here.
    """

    class Meta:
        model = Deposit
        fields = [
            "institution",
            "instrument_type",
            "reference_number",
            "bank_name",
            "bank_branch",
            "amount",
            "issue_date",
            "maturity_date",
            "lock_in_end_date",
        ]

    def clean(self):
        cleaned_data = super().clean()
        try:
            services.validate_deposit(
                institution=cleaned_data.get("institution"),
                reference_number=cleaned_data.get("reference_number"),
                bank_name=cleaned_data.get("bank_name"),
                amount=cleaned_data.get("amount"),
                issue_date=cleaned_data.get("issue_date"),
                maturity_date=cleaned_data.get("maturity_date"),
                exclude_deposit=self.instance if self.instance and self.instance.pk else None,
            )
        except services.DomainError as exc:
            raise forms.ValidationError(str(exc))
        return cleaned_data
