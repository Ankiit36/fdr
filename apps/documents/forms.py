"""Forms for document upload."""

from django import forms

from apps.deposits.services import DomainError
from apps.documents import services
from apps.documents.services import DOC_TYPE_CHOICES


class DocumentUploadForm(forms.Form):
    """Upload form for deposit documents."""

    file = forms.FileField(required=True)
    doc_type = forms.ChoiceField(choices=DOC_TYPE_CHOICES)

    def clean(self):
        cleaned_data = super().clean()
        file = cleaned_data.get("file")
        doc_type = cleaned_data.get("doc_type")
        if file:
            try:
                services.validate_document(file)
            except DomainError as exc:
                raise forms.ValidationError(str(exc))
        cleaned_data["doc_type"] = doc_type
        return cleaned_data
