"""Forms for institution CRUD."""

from django import forms

from apps.institutions.models import Institution


class InstitutionForm(forms.ModelForm):
    """Form for creating and editing institutions; code must be unique."""

    class Meta:
        model = Institution
        fields = [
            "name",
            "code",
            "address",
            "contact_email",
            "contact_phone",
        ]

    def clean_code(self):
        code = self.cleaned_data.get("code")
        queryset = Institution.objects.filter(code=code)
        if self.instance is not None and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError("Institution code must be unique.")
        return code
