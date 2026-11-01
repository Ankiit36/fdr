"""Context processors for the notifications app."""


def unread_notifications(request):
    """Return unread notification count for authenticated users, otherwise 0."""
    if request.user.is_authenticated:
        from apps.notifications.models import Notification

        count = Notification.objects.filter(
            user=request.user, is_read=False
        ).count()
        return {"unread_notifications_count": count}
    return {"unread_notifications_count": 0}