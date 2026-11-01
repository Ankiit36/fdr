"""Institution CRUD views (ADMIN only)."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from apps.accounts.permissions import is_admin
from apps.institutions import services
from apps.institutions.forms import InstitutionForm
from apps.institutions.models import Institution


class InstitutionListView(LoginRequiredMixin, ListView):
    """List institutions (ADMIN only), paginated to 20 per page."""

    model = Institution
    context_object_name = "institutions"
    template_name = "institutions/list.html"
    paginate_by = 20

    def get_queryset(self):
        if not is_admin(self.request.user):
            raise PermissionDenied
        return Institution.objects.order_by("name")


class InstitutionCreateView(LoginRequiredMixin, CreateView):
    """Create an institution (ADMIN only)."""

    model = Institution
    form_class = InstitutionForm
    template_name = "institutions/form.html"
    success_url = "/institutions/"

    def dispatch(self, request, *args, **kwargs):
        if not is_admin(self.request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def perform_create(self, form):
        services.create_institution(
            actor=self.request.user,
            name=form.cleaned_data.get("name"),
            code=form.cleaned_data.get("code"),
            address=form.cleaned_data.get("address") or "",
            contact_email=form.cleaned_data.get("contact_email") or "",
            contact_phone=form.cleaned_data.get("contact_phone") or "",
        )


class InstitutionUpdateView(LoginRequiredMixin, UpdateView):
    """Edit an institution (ADMIN only)."""

    model = Institution
    form_class = InstitutionForm
    template_name = "institutions/form.html"

    def dispatch(self, request, *args, **kwargs):
        if not is_admin(self.request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def perform_update(self, form):
        services.update_institution(
            self.get_object(),
            actor=self.request.user,
            name=form.cleaned_data.get("name"),
            code=form.cleaned_data.get("code"),
            address=form.cleaned_data.get("address") or "",
            contact_email=form.cleaned_data.get("contact_email") or "",
            contact_phone=form.cleaned_data.get("contact_phone") or "",
        )


class InstitutionDeactivateView(LoginRequiredMixin, View):
    """Deactivate an institution (ADMIN only)."""

    def dispatch(self, request, *args, **kwargs):
        if not is_admin(self.request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        institution = get_object_or_404(Institution, pk=pk)
        services.deactivate_institution(institution, actor=request.user)
        return redirect("institution_list")
