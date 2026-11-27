import io
import os
import tempfile

from django.core.management import call_command
from django.test import TestCase, override_settings


class ApiDocsClean(TestCase):
    def test_schema_has_no_warnings_or_errors(self):
        """Keeps the terminal quiet when someone opens /api/docs/."""
        err = io.StringIO()
        with tempfile.TemporaryDirectory() as d:
            call_command("spectacular", "--validate", "--fail-on-warn", file=os.path.join(d, "schema.yml"), stderr=err)
        self.assertEqual(err.getvalue().strip(), "")

    @override_settings(ENABLE_API_DOCS=True)
    def test_example_logins_exist_in_demo_seed(self):
        from apps.organizations.management.commands import seed_demo
        self.assertEqual(seed_demo.ADMIN, ("xverlabs", "DineX@2026"))
        self.assertEqual(seed_demo.PASSWORD, "Demo@12345")
