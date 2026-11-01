"""Notification views."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import ListView

from apps.core.i18n import t
from apps.notifications.models import Notification


class NotificationListView(LoginRequiredMixin, ListView):
    """List the current user's own notifications, paginated by 20."""

    model = Notification
    context_object_name = "notifications"
    template_name = "notifications/list.html"
    paginate_by = 20

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by(
            "-created_at"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["unread_count"] = Notification.objects.filter(
            user=self.request.user, is_read=False
        ).count()
        return context


class NotificationMarkAllReadView(LoginRequiredMixin, ListView):
    """Mark all of the current user's notifications as read (POST only)."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True
        )
        messages.success(request, t("msg.all_notifications_read", request))
        return redirect(request.META.get("HTTP_REFERER", "notification_list"))