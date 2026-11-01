"""Audit trail views."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.views import View
from django.views.generic import ListView

from apps.accounts.permissions import is_admin
from apps.audit.chain import verify_chain
from apps.audit.services import filter_audit_logs


class AuditLogListView(LoginRequiredMixin, ListView):
    """List audit logs with optional filtering. ADMIN only."""

    model = None
    context_object_name = "audit_logs"
    template_name = "audit/list.html"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return filter_audit_logs(self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_user"] = self.request.GET.get("user", "")
        context["filter_model_name"] = self.request.GET.get("model_name", "")
        context["filter_date_from"] = self.request.GET.get("date_from", "")
        context["filter_date_to"] = self.request.GET.get("date_to", "")
        return context


class AuditChainVerifyView(LoginRequiredMixin, View):
    """Verify cryptographic audit log hash chain. ADMIN only."""

    template_name = "audit/verify.html"

    def dispatch(self, request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {"result": None})

    def post(self, request, *args, **kwargs):
        result = verify_chain()
        return render(request, self.template_name, {"result": result})
