from django.core.management.base import BaseCommand

from apps.audit.chain import verify_chain


class Command(BaseCommand):
    help = "Verify cryptographic integrity and linkage of the audit log hash chain."

    def handle(self, *args, **options):
        result = verify_chain()
        if result["ok"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"OK: Audit log hash chain valid. Checked {result['checked']} entries "
                    f"({result['legacy_skipped']} legacy skipped)."
                )
            )
        else:
            self.stderr.write(
                self.style.ERROR(
                    f"FAILED: Broken at ID {result['broken_at_id']}: {result['reason']} "
                    f"({result['checked']} checked, {result['legacy_skipped']} legacy skipped)."
                )
            )
