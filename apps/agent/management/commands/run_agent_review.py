"""Management command to run the agent review for all deposits.

For each deposit, calls run_review_for_deposit and reports how many
deposits were processed and how many new AgentFinding rows were created.
Deposits are never mutated (no status, amount, or date changes).
"""

from django.core.management.base import BaseCommand

from apps.agent.services import run_review_for_deposit
from apps.deposits.models import Deposit


class Command(BaseCommand):
    help = "Run the FDR review agent for all deposits."

    def handle(self, *args, **options):
        deposits = Deposit.objects.all().order_by("pk")
        deposits_processed = 0
        new_findings = 0

        for deposit in deposits:
            existing_count = deposit.agent_findings.count()
            run_review_for_deposit(deposit)
            new_count = deposit.agent_findings.count()
            new_findings += new_count - existing_count
            deposits_processed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {deposits_processed} deposit(s), "
                f"created {new_findings} new finding(s)."
            )
        )