"""Things production relies on: health check, moved Django admin, throttle wiring, settings guards."""
from django.test import SimpleTestCase
from rest_framework.test import APIClient

from tests.base import TenantTestCase


class Health(TenantTestCase):
    def test_health_needs_no_login_and_checks_the_database(self):
        r = APIClient().get("/api/v1/health/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok", "database": "ok"})

    def test_django_admin_lives_at_django_admin_not_admin(self):
        c = APIClient()
        self.assertEqual(c.get("/django-admin/login/").status_code, 200)
        self.assertEqual(c.get("/admin/").status_code, 404)        # /admin belongs to the DineX Admin web page


class Wiring(SimpleTestCase):
    def test_login_endpoint_is_rate_limited(self):
        from apps.accounts.schemas.auth_schema import LoginAPIView
        self.assertEqual(LoginAPIView.throttle_scope, "login")
        from django.conf import settings
        self.assertIn("login", settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"])

    def test_weak_secret_key_is_refused_in_production(self):
        import os, subprocess, sys
        env = {**os.environ, "DEBUG": "False", "SECRET_KEY": "dev-only-key"}
        r = subprocess.run([sys.executable, "manage.py", "check"], env=env, capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("SECRET_KEY", r.stderr)

    def test_docker_files_exist(self):
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        for name in ("Dockerfile", "docker-entrypoint.sh", "requirements.txt"):
            self.assertTrue((root / name).exists(), name)
