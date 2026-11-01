"""Deposit CRUD views."""

from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.accounts.permissions import is_admin, is_institution_user, is_officer
from apps.deposits import services
from apps.deposits.exports import export_deposits_csv
from apps.deposits.forms import DepositForm
from apps.deposits.models import Deposit
from apps.deposits.timeline import deposit_timeline
from apps.documents.services import get_visible_documents
from apps.institutions.models import Institution
from apps.verification.services import apply_officer_status


class DepositListView(LoginRequiredMixin, ListView):
    """List deposits with search and filters (paginated to 20 per page)."""

    model = Deposit
    context_object_name = "deposits"
    template_name = "deposits/list.html"
    paginate_by = 20

    def get_queryset(self):
        issue_date_from = None
        issue_date_to = None
        if self.request.GET.get("issue_date_from"):
            issue_date_from = date.fromisoformat(self.request.GET.get("issue_date_from"))
        if self.request.GET.get("issue_date_to"):
            issue_date_to = date.fromisoformat(self.request.GET.get("issue_date_to"))
        return services.get_deposit_list_queryset(
            self.request.user,
            search=self.request.GET.get("q") or None,
            status=self.request.GET.get("status") or None,
            institution_id=self.request.GET.get("institution") or None,
            issue_date_from=issue_date_from,
            issue_date_to=issue_date_to,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if is_admin(self.request.user) or is_officer(self.request.user):
            context["institutions"] = Institution.objects.order_by("name")
        return context


class DepositExportCSVView(LoginRequiredMixin, View):
    """Export deposits matching current filters to CSV."""

    def get(self, request, *args, **kwargs):
        issue_date_from = None
        issue_date_to = None
        if request.GET.get("issue_date_from"):
            try:
                issue_date_from = date.fromisoformat(request.GET.get("issue_date_from"))
            except ValueError:
                pass
        if request.GET.get("issue_date_to"):
            try:
                issue_date_to = date.fromisoformat(request.GET.get("issue_date_to"))
            except ValueError:
                pass
        queryset = services.get_deposit_list_queryset(
            request.user,
            search=request.GET.get("q") or None,
            status=request.GET.get("status") or None,
            institution_id=request.GET.get("institution") or None,
            issue_date_from=issue_date_from,
            issue_date_to=issue_date_to,
        )
        return export_deposits_csv(queryset)


class DepositCreateView(LoginRequiredMixin, CreateView):
    """Create a deposit (INSTITUTION users for their own institution, ADMIN any)."""

    model = Deposit
    form_class = DepositForm
    template_name = "deposits/form.html"
    success_url = "/deposits/"

    def dispatch(self, request, *args, **kwargs):
        if not (is_admin(request.user) or is_institution_user(request.user)):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def perform_create(self, form):
        cleaned_data = form.cleaned_data
        services.create_deposit(
            institution=cleaned_data.get("institution"),
            instrument_type=cleaned_data.get("instrument_type"),
            reference_number=cleaned_data.get("reference_number"),
            bank_name=cleaned_data.get("bank_name"),
            bank_branch=cleaned_data.get("bank_branch") or "",
            amount=cleaned_data.get("amount"),
            issue_date=cleaned_data.get("issue_date"),
            maturity_date=cleaned_data.get("maturity_date"),
            lock_in_end_date=cleaned_data.get("lock_in_end_date"),
            created_by=self.request.user,
        )


class DepositDetailView(LoginRequiredMixin, DetailView):
    """Deposit detail showing fields, documents and scrutiny observations."""

    model = Deposit
    context_object_name = "deposit"
    template_name = "deposits/detail.html"

    def get_queryset(self):
        return services.get_visible_deposits(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["documents"] = get_visible_documents(self.request.user).filter(deposit=self.object)
        context["scrutiny_observations"] = self.object.scrutiny_observations.all()
        context["renewal_form"] = DepositForm()
        return context


class DepositUpdateView(LoginRequiredMixin, UpdateView):
    """Edit a deposit (INSTITUTION only while SUBMITTED, ADMIN any; OFFICER no)."""

    model = Deposit
    form_class = DepositForm
    template_name = "deposits/form.html"

    def get_queryset(self):
        return services.get_visible_deposits(self.request.user)

    def dispatch(self, request, *args, **kwargs):
        if is_officer(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        deposit = super().get_object(queryset)
        user = self.request.user
        if is_institution_user(user):
            if deposit.institution_id != user.institution_id:
                raise PermissionDenied
            if deposit.status != Deposit.Status.SUBMITTED:
                raise PermissionDenied
        return deposit

    def perform_update(self, form):
        cleaned_data = form.cleaned_data
        services.update_deposit(
            form.instance,
            actor=self.request.user,
            institution=cleaned_data.get("institution"),
            instrument_type=cleaned_data.get("instrument_type"),
            reference_number=cleaned_data.get("reference_number"),
            bank_name=cleaned_data.get("bank_name"),
            bank_branch=cleaned_data.get("bank_branch") or "",
            amount=cleaned_data.get("amount"),
            issue_date=cleaned_data.get("issue_date"),
            maturity_date=cleaned_data.get("maturity_date"),
            lock_in_end_date=cleaned_data.get("lock_in_end_date"),
        )


class DepositDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a deposit (ADMIN only, POST with confirmation)."""

    model = Deposit
    template_name = "deposits/confirm_delete.html"
    success_url = "/deposits/"

    def dispatch(self, request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def perform_delete(self, obj):
        services.delete_deposit(obj, self.request.user)


class ScrutinyAddView(LoginRequiredMixin, View):
    """Add a scrutiny observation (OFFICER or ADMIN only)."""

    def post(self, request, pk):
        deposit = services.get_deposit_for_user(request.user, pk)
        if not (is_admin(request.user) or is_officer(request.user)):
            raise PermissionDenied
        note = (request.POST.get("note") or "").strip()
        if not note:
            raise ValidationError("A note is required for scrutiny observations.")
        services.add_scrutiny_observation(deposit, request.user, note)
        return redirect("deposit_detail", deposit.pk)


class DepositStatusUpdateView(LoginRequiredMixin, View):
    """Set a deposit status decision (OFFICER or ADMIN only)."""

    def post(self, request, pk):
        deposit = services.get_deposit_for_user(request.user, pk)
        if not (is_admin(request.user) or is_officer(request.user)):
            raise PermissionDenied
        new_status = request.POST.get("status")
        if new_status not in (
            Deposit.Status.UNDER_SCRUTINY,
            Deposit.Status.VERIFIED,
            Deposit.Status.DISCREPANCY,
        ):
            raise ValidationError("Invalid status.")
        note = (request.POST.get("note") or "").strip()
        apply_officer_status(deposit, request.user, new_status, note=note)
        return redirect("deposit_detail", deposit.pk)


class DepositRenewalView(LoginRequiredMixin, View):
    """Start a renewal for an ACTIVE, EXPIRING or MATURED deposit."""

    def post(self, request, pk):
        deposit = services.get_deposit_for_user(request.user, pk)
        if not (is_admin(request.user) or is_institution_user(request.user)):
            raise PermissionDenied
        if deposit.status not in (
            Deposit.Status.ACTIVE,
            Deposit.Status.EXPIRING,
            Deposit.Status.MATURED,
        ):
            raise PermissionDenied
        form = DepositForm(request.POST)
        if form.is_valid():
            services.renew_deposit(
                previous_deposit=deposit,
                institution=deposit.institution,
                instrument_type=form.cleaned_data.get("instrument_type"),
                reference_number=form.cleaned_data.get("reference_number"),
                bank_name=form.cleaned_data.get("bank_name"),
                bank_branch=form.cleaned_data.get("bank_branch") or "",
                amount=form.cleaned_data.get("amount"),
                issue_date=form.cleaned_data.get("issue_date"),
                maturity_date=form.cleaned_data.get("maturity_date"),
                created_by=request.user,
            )
        return redirect("deposit_detail", deposit.pk)


class DepositTimelineView(LoginRequiredMixin, View):
    """View chronological lifecycle events for a deposit."""

    def get(self, request, pk):
        deposit = services.get_deposit_for_user(request.user, pk)
        events = deposit_timeline(deposit)
        return render(
            request,
            "deposits/timeline.html",
            {
                "deposit": deposit,
                "events": events,
            },
        )
