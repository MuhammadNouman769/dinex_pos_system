from django.core.management.base import BaseCommand

from apps.loyalty import services
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Email customers their points balance. Run twice a week, e.g. cron: 0 11 * * 1,4"

    def handle(self, *args, **opts):
        for org in Organization.objects.filter(is_active=True):
            r = services.send_reminders(org)
            if r["sent"] or r["skipped"]:
                self.stdout.write(f"{org.name}: sent {r['sent']}, skipped {r['skipped']}")
