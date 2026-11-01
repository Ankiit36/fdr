"""API viewsets for the Agent app."""

from django.http import Http404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.accounts.api_permissions import IsOfficerOrAdmin
from apps.accounts.permissions import is_admin, is_officer, is_institution_user
from apps.agent.actions import acknowledge_finding, resolve_finding
from apps.agent.models import AgentFinding
from apps.agent.serializers import AgentFindingSerializer
from apps.deposits.services import get_visible_deposits


class AgentFindingViewSet(ViewSet):
    """ViewSet for agent findings.

    - List/Retrieve: scoped the same way as Phase 6 views.
      OFFICER/ADMIN see all; INSTITUTION sees only its own institution's findings.
    - POST acknowledge: OFFICER/ADMIN only. INSTITUTION gets 403.
    - POST resolve: OFFICER/ADMIN only. INSTITUTION gets 403.
    """

    serializer_class = AgentFindingSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return AgentFinding.objects.none()
        if user.role in ("ADMIN", "OFFICER"):
            return AgentFinding.objects.all().order_by("-created_at")
        if user.role == "INSTITUTION":
            if user.institution_id:
                return (
                    AgentFinding.objects.filter(deposit__institution=user.institution)
                    .order_by("-created_at")
                )
            return AgentFinding.objects.none()
        return AgentFinding.objects.none()

    def get_object(self):
        finding = self.get_queryset().filter(pk=self.kwargs["pk"]).first()
        if finding is None:
            raise Http404("Finding not found.")
        return finding

    def list(self, request):
        queryset = self.get_queryset().order_by("-created_at")
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)

    def paginate_queryset(self, queryset):
        from rest_framework.pagination import PageNumberPagination

        paginator = PageNumberPagination()
        paginator.page_size = 20
        return paginator.paginate_queryset(queryset, self.request, view=self)

    def get_paginated_response(self, data):
        from rest_framework.response import Response

        paginator = PageNumberPagination()
        paginator.page_size = 20
        return Response(
            {
                "count": paginator.count,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
                "results": data,
            }
        )

    def retrieve(self, request, pk=None):
        finding = self.get_object()
        serializer = self.serializer_class(finding)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        """Acknowledge a finding (OFFICER/ADMIN only)."""
        if not (is_officer(request.user) or is_admin(request.user)):
            return Response(
                {"detail": "Only OFFICER or ADMIN can acknowledge findings."},
                status=status.HTTP_403_FORBIDDEN,
            )
        finding = self.get_object()
        try:
            acknowledge_finding(finding, request.user)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.serializer_class(finding)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        """Resolve a finding with a note (OFFICER/ADMIN only)."""
        if not (is_officer(request.user) or is_admin(request.user)):
            return Response(
                {"detail": "Only OFFICER or ADMIN can resolve findings."},
                status=status.HTTP_403_FORBIDDEN,
            )
        finding = self.get_object()
        note = request.data.get("note", "")
        try:
            resolve_finding(finding, request.user, note)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.serializer_class(finding)
        return Response(serializer.data)