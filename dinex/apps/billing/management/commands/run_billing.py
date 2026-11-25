from django.core.management.base import BaseCommand

from apps.billing.services import run_billing


class Command(BaseCommand):
    help = "Issue next invoices, mark overdue ones, suspend after the grace period. Run once a day (cron)."

    def handle(self, *args, **options):
        r = run_billing()
        self.stdout.write(self.style.SUCCESS(f"invoiced={r['invoiced']} past_due={r['past_due']} suspended={r['suspended']}"))
