"""Management command to send maturity alerts for all deposits."""

from django.core.management.base import BaseCommand

from apps.notifications.services import run_maturity_alerts


class Command(BaseCommand):
    help = "Send maturity alerts for all deposits."

    def handle(self, *args, **options):
        result = run_maturity_alerts()
        self.stdout.write(
            self.style.SUCCESS(
                f"Maturity alerts: "
                f"{result['status_updated']} status updated, "
                f"{result['reminders_sent']} reminders sent, "
                f"{result['skipped']} skipped, "
                f"{result.get('escalated', 0)} escalated."
            )
        )
