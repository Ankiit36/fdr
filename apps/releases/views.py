"""Views for release requests and workflow management."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import ListView

from apps.accounts.permissions import is_admin, is_institution_user, is_officer
from apps.audit.models import AuditLog
from apps.deposits.services import DomainError, get_deposit_for_user
from apps.releases import services
from apps.releases.exports import export_releases_csv
from apps.releases.forms import ReleaseDecisionForm, ReleaseRequestForm
from apps.releases.models import Release


class ReleaseListView(LoginRequiredMixin, ListView):
    """List releases visible to the user, with status filter and pagination."""

    model = Release
    context_object_name = "releases"
    template_name = "releases/list.html"
    paginate_by = 20

    def get_queryset(self):
        status = self.request.GET.get("status") or None
        return services.get_release_list_queryset(self.request.user, status=status)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = Release.Status.choices
        context["selected_status"] = self.request.GET.get("status", "")
        return context


class ReleaseExportCSVView(LoginRequiredMixin, View):
    """Export releases visible to the user matching active filter to CSV."""

    def get(self, request, *args, **kwargs):
        status = request.GET.get("status") or None
        queryset = services.get_release_list_queryset(request.user, status=status)
        return export_releases_csv(queryset)


class ReleaseRequestView(LoginRequiredMixin, View):
    """Request a release for a deposit (INSTITUTION own deposit or ADMIN)."""

    def get_deposit(self, request, pk):
        deposit = get_deposit_for_user(request.user, pk)
        if not (
            is_admin(request.user)
            or (is_institution_user(request.user) and request.user.institution_id == deposit.institution_id)
        ):
            raise PermissionDenied
        return deposit

    def get(self, request, pk):
        deposit = self.get_deposit(request, pk)
        form = ReleaseRequestForm()
        return render(
            request,
            "releases/request_form.html",
            {"deposit": deposit, "form": form},
        )

    def post(self, request, pk):
        deposit = self.get_deposit(request, pk)
        form = ReleaseRequestForm(request.POST)
        if form.is_valid():
            try:
                release = services.request_release(
                    deposit=deposit,
                    actor=request.user,
                    request_type=form.cleaned_data["request_type"],
                    note=form.cleaned_data.get("note", ""),
                )
            except DomainError as exc:
                messages.error(request, f"{t('msg.error_prefix', request)}{exc}")
                return render(
                    request,
                    "releases/request_form.html",
                    {"deposit": deposit, "form": form},
                )
            messages.success(request, t("msg.release_created", request))
            return redirect("releases:release_detail", pk=release.pk)

        return render(
            request,
            "releases/request_form.html",
            {"deposit": deposit, "form": form},
        )


class ReleaseDetailView(LoginRequiredMixin, View):
    """Detail view showing release status, details, and audit history."""

    def get(self, request, pk):
        release = services.get_release_for_user(request.user, pk)
        audit_history = AuditLog.objects.filter(
            model_name="Release",
            object_id=release.pk,
        ).order_by("-timestamp")

        user = request.user
        can_review = (is_officer(user) or is_admin(user)) and release.status == Release.Status.REQUESTED
        can_decide = (is_officer(user) or is_admin(user)) and release.status == Release.Status.UNDER_REVIEW
        can_reject_requested = (
            (is_officer(user) or is_admin(user))
            and release.status in (Release.Status.REQUESTED, Release.Status.UNDER_REVIEW)
        )
        can_pay_out = is_admin(user) and release.status == Release.Status.APPROVED

        decision_form = ReleaseDecisionForm()

        return render(
            request,
            "releases/detail.html",
            {
                "release": release,
                "audit_history": audit_history,
                "can_review": can_review,
                "can_decide": can_decide,
                "can_reject_requested": can_reject_requested,
                "can_pay_out": can_pay_out,
                "decision_form": decision_form,
            },
        )


class ReleaseReviewView(LoginRequiredMixin, View):
    """Transition release from REQUESTED to UNDER_REVIEW (OFFICER or ADMIN)."""

    def post(self, request, pk):
        release = services.get_release_for_user(request.user, pk)
        if not (is_officer(request.user) or is_admin(request.user)):
            raise PermissionDenied

        try:
            services.start_review(release, request.user)
        except DomainError as exc:
            messages.error(request, f"{t('msg.error_prefix', request)}{exc}")
        else:
            messages.success(request, t("msg.review_started", request))
        return redirect("releases:release_detail", pk=pk)


class ReleaseApproveView(LoginRequiredMixin, View):
    """Transition release from UNDER_REVIEW to APPROVED (OFFICER or ADMIN)."""

    def post(self, request, pk):
        release = services.get_release_for_user(request.user, pk)
        if not (is_officer(request.user) or is_admin(request.user)):
            raise PermissionDenied

        note = request.POST.get("note", "")
        try:
            services.approve_release(release, request.user, note)
        except DomainError as exc:
            messages.error(request, f"{t('msg.error_prefix', request)}{exc}")
        else:
            messages.success(request, t("msg.release_approved", request))
        return redirect("releases:release_detail", pk=pk)


class ReleaseRejectView(LoginRequiredMixin, View):
    """Transition release to REJECTED (OFFICER or ADMIN)."""

    def post(self, request, pk):
        release = services.get_release_for_user(request.user, pk)
        if not (is_officer(request.user) or is_admin(request.user)):
            raise PermissionDenied

        note = request.POST.get("note", "")
        try:
            services.reject_release(release, request.user, note)
        except DomainError as exc:
            messages.error(request, f"{t('msg.error_prefix', request)}{exc}")
        else:
            messages.success(request, t("msg.release_rejected", request))
        return redirect("releases:release_detail", pk=pk)


class ReleasePaidOutView(LoginRequiredMixin, View):
    """Transition release from APPROVED to PAID_OUT (ADMIN only)."""

    def post(self, request, pk):
        release = services.get_release_for_user(request.user, pk)
        if not is_admin(request.user):
            raise PermissionDenied

        try:
            services.mark_paid_out(release, request.user)
        except DomainError as exc:
            messages.error(request, f"{t('msg.error_prefix', request)}{exc}")
        else:
            messages.success(request, t("msg.release_paid_out", request))
        return redirect("releases:release_detail", pk=pk)
