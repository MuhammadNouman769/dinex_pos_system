from django.db import migrations

PLANS = [
    dict(code="starter", name="Starter", description="One restaurant, getting started", price_monthly="2999.00", max_locations=1, max_users=5, sort_order=1,
         features=["POS & bill printing", "Orders & kitchen board", "Menu, recipes & inventory", "Cash shifts & daily reports"]),
    dict(code="growth", name="Growth", description="Busy restaurants and small chains", price_monthly="4999.00", max_locations=3, max_users=15, sort_order=2,
         features=["Everything in Starter", "Up to 3 branches", "15 staff accounts", "Audit log & manager controls"]),
    dict(code="pro", name="Pro", description="Chains and large restaurants", price_monthly="6999.00", max_locations=10, max_users=50, sort_order=3,
         features=["Everything in Growth", "Up to 10 branches", "50 staff accounts", "Priority support"]),
]


def create_plans(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")
    for p in PLANS:
        Plan.objects.get_or_create(code=p["code"], defaults=p)


class Migration(migrations.Migration):
    dependencies = [("billing", "0001_initial")]
    operations = [migrations.RunPython(create_plans, migrations.RunPython.noop)]
