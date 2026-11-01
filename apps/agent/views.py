"""Agent views: findings list/detail and human-in-the-loop actions."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, ListView

from apps.accounts.models import User
from apps.accounts.permissions import is_admin, is_officer
from apps.agent.actions import acknowledge_finding, apply_suggestion, resolve_finding
from apps.core.i18n import get_language, t
from apps.agent.messages_hi import render_finding_message
from apps.agent.models import AgentFinding
from apps.agent.services import case_summary
from apps.deposits.models import Deposit
from apps.deposits.services import get_deposit_for_user


def _findings_queryset_for_user(user):
    """Return the AgentFinding queryset visible to the given user."""
    if not user.is_authenticated:
        return AgentFinding.objects.none()
    if user.role in (User.Roles.ADMIN, User.Roles.OFFICER):
        return AgentFinding.objects.all()
    if user.role == User.Roles.INSTITUTION:
        if user.institution_id:
            return AgentFinding.objects.filter(deposit__institution=user.institution)
        return AgentFinding.objects.none()
    return AgentFinding.objects.none()


class FindingListView(LoginRequiredMixin, ListView):
    """List agent findings with optional filters and pagination."""

    model = AgentFinding
    context_object_name = "findings"
    template_name = "agent/findings_list.html"
    paginate_by = 20

    def get_queryset(self):
        queryset = _findings_queryset_for_user(self.request.user)
        severity = self.request.GET.get("severity")
        category = self.request.GET.get("category")
        status = self.request.GET.get("status")
        if severity:
            queryset = queryset.filter(severity=severity)
        if category:
            queryset = queryset.filter(category=category)
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lang = get_language(self.request)
        for finding in context["findings"]:
            finding.display_message = render_finding_message(finding, lang)
        context["severity_choices"] = AgentFinding.Severity.choices
        context["category_choices"] = AgentFinding.Category.choices
        context["status_choices"] = AgentFinding.Status.choices
        context["current_severity"] = self.request.GET.get("severity", "")
        context["current_category"] = self.request.GET.get("category", "")
        context["current_status"] = self.request.GET.get("status", "")
        return context


class FindingDetailView(LoginRequiredMixin, DetailView):
    """Detail of a single finding with its extracted field snippets."""

    model = AgentFinding
    context_object_name = "finding"
    template_name = "agent/finding_detail.html"

    def get_queryset(self):
        return _findings_queryset_for_user(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lang = get_language(self.request)
        finding = self.object
        finding.display_message = render_finding_message(finding, lang)
        review_run = finding.review_run
        extracted_fields = review_run.extracted_fields.all()
        context["extracted_fields"] = extracted_fields
        context["can_act"] = is_admin(self.request.user) or is_officer(
            self.request.user
        )
        return context


class FindingAcknowledgeView(LoginRequiredMixin, View):
    """Acknowledge a finding (OFFICER/ADMIN only)."""

    def dispatch(self, request, *args, **kwargs):
        if not (is_admin(request.user) or is_officer(request.user)):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        finding = get_object_or_404(
            _findings_queryset_for_user(request.user), pk=pk
        )
        try:
            acknowledge_finding(finding, request.user)
        except Exception as exc:
            messages.error(request, f"{t('msg.error_prefix', request)}{exc}")
        else:
            messages.success(request, t("msg.finding_acknowledged", request))
        return redirect("agent:agent_finding_detail", pk=pk)


class FindingResolveView(LoginRequiredMixin, View):
    """Resolve a finding with a note (OFFICER/ADMIN only)."""

    def dispatch(self, request, *args, **kwargs):
        if not (is_admin(request.user) or is_officer(request.user)):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        finding = get_object_or_404(
            _findings_queryset_for_user(request.user), pk=pk
        )
        note = (request.POST.get("note") or "").strip()
        try:
            resolve_finding(finding, request.user, note)
        except Exception as exc:
            messages.error(request, f"{t('msg.error_prefix', request)}{exc}")
        else:
            messages.success(request, t("msg.finding_resolved", request))
        return redirect("agent:agent_finding_detail", pk=pk)


class FindingApplyView(LoginRequiredMixin, View):
    """Apply the agent's suggestion to the deposit status (OFFICER/ADMIN only)."""

    def dispatch(self, request, *args, **kwargs):
        if not (is_admin(request.user) or is_officer(request.user)):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        finding = get_object_or_404(
            _findings_queryset_for_user(request.user), pk=pk
        )
        try:
            apply_suggestion(finding, request.user)
        except Exception as exc:
            messages.error(request, f"{t('msg.error_prefix', request)}{exc}")
        else:
            messages.success(request, t("msg.suggestion_applied", request))
        return redirect("agent:agent_finding_detail", pk=pk)


class DepositReviewView(LoginRequiredMixin, DetailView):
    """Side-by-side review of a deposit vs the agent's latest extraction."""

    model = Deposit
    context_object_name = "deposit"
    template_name = "agent/deposit_review.html"

    def get(self, request, *args, **kwargs):
        deposit = get_deposit_for_user(request.user, kwargs["pk"])
        latest_run = deposit.agent_review_runs.order_by("-run_at").first()
        extracted_fields = []
        if latest_run:
            extracted_fields = list(latest_run.extracted_fields.all())

        summary = case_summary(deposit)
        lang = get_language(request)
        findings = list(deposit.agent_findings.all().order_by("-created_at"))
        for finding in findings:
            finding.display_message = render_finding_message(finding, lang)

        can_act = is_admin(request.user) or is_officer(request.user)

        context = {
            "deposit": deposit,
            "extracted_fields": extracted_fields,
            "summary": summary,
            "findings": findings,
            "can_act": can_act,
        }
        return self.render_to_response(context)