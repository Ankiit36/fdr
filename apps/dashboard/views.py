"""Dashboard and institutional analytics views."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.permissions import is_admin, is_officer
from apps.agent.models import AgentFinding
from apps.dashboard.labels import LABELS
from apps.dashboard.pdf_report import render_summary_pdf
from apps.dashboard.services import analytics_by_institution, dashboard_data


class DashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard view showing counts, upcoming maturities, pending verifications, unread notifications, and top findings."""

    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.core.i18n import get_language
        selected_lang = get_language(self.request)
        context["data"] = dashboard_data(self.request.user, lang=selected_lang)
        context["labels"] = {k: v[selected_lang] for k, v in LABELS.items()}
        context["current_lang"] = selected_lang
        return context


class AnalyticsView(LoginRequiredMixin, View):
    """Institutional analytics view for ADMIN and OFFICER."""

    template_name = "dashboard/analytics.html"

    def dispatch(self, request, *args, **kwargs):
        if not (is_admin(request.user) or is_officer(request.user)):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        analytics = analytics_by_institution(request.user)
        return render(
            request,
            self.template_name,
            {
                "analytics": analytics,
            },
        )


class SummaryPdfView(LoginRequiredMixin, View):
    """Download text-only PDF summary report for ADMIN and OFFICER."""

    def dispatch(self, request, *args, **kwargs):
        if not (is_admin(request.user) or is_officer(request.user)):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        analytics_rows = analytics_by_institution(request.user)
        total_open_findings = AgentFinding.objects.filter(
            status=AgentFinding.Status.OPEN
        ).count()

        lines = [
            f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"Requested by: {request.user.username} ({request.user.role})",
            f"Total open findings across portal: {total_open_findings}",
            "",
            "Institutional Breakdown:",
            "------------------------------------------------------------------",
        ]
        for row in analytics_rows:
            lines.append(f"Institution: {row['name']} ({row['code']})")
            lines.append(f"  Deposits: {row['total_deposits']} | Total Value: INR {row['total_value']}")
            lines.append(
                f"  Expiring: {row['expiring_count']} | Matured: {row['matured_count']} "
                f"| Discrepancy: {row['discrepancy_count']}"
            )
            lines.append(f"  Critical Findings: {row['critical_findings_count']}")
            lines.append("")

        pdf_bytes = render_summary_pdf("AICTE FDR Institutional Summary Report", lines)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="summary.pdf"'
        return response
