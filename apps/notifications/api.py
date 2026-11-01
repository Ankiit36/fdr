"""API viewsets for the Notifications app."""

from django.http import Http404
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer


class NotificationViewSet(ViewSet):
    """ViewSet for notifications.

    - List: own notifications only, paginated.
    - mark_read: POST to mark one notification as read (own only, 404 otherwise).
    - mark_all_read: POST to mark all own notifications as read.
    """

    pagination_class = PageNumberPagination

    def list(self, request):
        notifications = Notification.objects.filter(user=request.user).order_by("-created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(notifications, request, view=self)
        if page is not None:
            serializer = NotificationSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        """Mark one notification as read (own only, 404 otherwise)."""
        try:
            notification = Notification.objects.get(pk=pk, user=request.user)
        except Notification.DoesNotExist:
            raise Http404("Notification not found.")
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response({"detail": "Notification marked as read."})

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        """Mark all own notifications as read."""
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"detail": "All notifications marked as read."})