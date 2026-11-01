"""Forms for release requests and actions."""

from django import forms
from apps.releases.models import Release


class ReleaseRequestForm(forms.Form):
    """Form to submit a new release request."""

    request_type = forms.ChoiceField(
        choices=Release.RequestType.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    note = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        required=False,
        label="Note (optional)",
    )


class ReleaseDecisionForm(forms.Form):
    """Form for approve/reject actions requiring a decision note."""

    note = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        required=True,
        label="Decision Note",
    )
