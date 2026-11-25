from decimal import Decimal
from django.db import migrations

# Plans start at 2,999 / 4,999 / 6,999. Only rows still on the old launch price are changed,
# so a price XverLabs set by hand in DineX Admin is never overwritten.
OLD_TO_NEW = {"starter": ("4999.00", "2999.00"), "growth": ("9999.00", "4999.00"), "pro": ("19999.00", "6999.00")}


def reprice(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")
    for code, (old, new) in OLD_TO_NEW.items():
        Plan.objects.filter(code=code, price_monthly=Decimal(old)).update(price_monthly=Decimal(new))


class Migration(migrations.Migration):
    dependencies = [("billing", "0003_payments_and_terms")]
    operations = [migrations.RunPython(reprice, migrations.RunPython.noop)]
