"""Forgot password by email code, and confirming a new email address."""
import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import EmailCode
from tests.base import PASSWORD, TenantTestCase

A = "/api/v1/auth/"


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", DEFAULT_FROM_EMAIL="DineX <no-reply@dinex.test>")
class ForgotPassword(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.anon = APIClient()
        self.user = get_user_model().objects.get(pk=self.org_a.memberships.filter(role="OWNER").first().user_id)

    def ask(self, ident=None):
        return self.anon.post(A + "forgot-password/", {"identifier": ident or self.user.username}, format="json")

    def code(self):
        return re.search(r"\n\s+(\d{6})\n", mail.outbox[-1].body).group(1)

    def reset(self, code, pw="Fresh-Pass-2027!", ident=None):
        return self.anon.post(A + "reset-password/", {"identifier": ident or self.user.username, "code": code, "new_password": pw}, format="json")

    def can_login(self, pw):
        return self.anon.post(A + "token/", {"username": self.user.username, "password": pw}, format="json").status_code == 200

    def test_full_flow_by_username_or_email(self):
        self.assertEqual(self.ask().status_code, 200)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        self.assertEqual(self.reset(self.code()).status_code, 200)
        self.assertTrue(self.can_login("Fresh-Pass-2027!"))
        self.assertFalse(self.can_login(PASSWORD))
        mail.outbox.clear()
        EmailCode.objects.all().update(created_at=timezone.now() - timedelta(minutes=5))
        self.ask(self.user.email.upper())
        self.assertEqual(len(mail.outbox), 1)

    def test_unknown_account_gets_same_answer_and_no_email(self):
        a, b = self.ask("nobody-here"), self.ask()
        self.assertEqual(a.json(), b.json())
        self.assertEqual(len(mail.outbox), 1)

    def test_wrong_code_five_times_locks_the_code(self):
        self.ask()
        good = self.code()
        for _ in range(5):
            self.assertEqual(self.reset("000000").status_code, 400)
        self.assertEqual(self.reset(good).status_code, 400)          # even the right code is dead now
        self.assertFalse(self.can_login("Fresh-Pass-2027!"))

    def test_code_expires_and_is_single_use(self):
        self.ask()
        c = self.code()
        EmailCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.reset(c).status_code, 400)
        EmailCode.objects.all().update(created_at=timezone.now() - timedelta(minutes=5))
        self.ask()
        c = self.code()
        self.assertEqual(self.reset(c).status_code, 200)
        self.assertEqual(self.reset(c, pw="Another-Pass-77!").status_code, 400)

    def test_newer_code_replaces_older_and_resend_is_rate_limited(self):
        self.ask()
        old = self.code()
        self.ask()                                                    # too soon: ignored, no second email
        self.assertEqual(len(mail.outbox), 1)
        EmailCode.objects.all().update(created_at=timezone.now() - timedelta(minutes=2))
        self.ask()
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(self.reset(old).status_code, 400)
        self.assertEqual(self.reset(self.code()).status_code, 200)

    def test_weak_password_is_refused_with_a_reason(self):
        self.ask()
        r = self.reset(self.code(), pw="12345678")
        self.assertEqual(r.status_code, 400)
        self.assertIn("new_password", r.json())

    def test_email_failure_still_answers_generically(self):
        from unittest import mock
        with mock.patch("apps.accounts.email_codes.send_mail", side_effect=RuntimeError("smtp down")):
            self.assertEqual(self.ask().status_code, 200)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", DEFAULT_FROM_EMAIL="DineX <no-reply@dinex.test>")
class ConfirmEmail(TenantTestCase):
    def test_change_email_needs_password_and_code_from_new_address(self):
        c = self.a
        r = c.post(A + "email/request/", {"email": "new@owner.com", "current_password": "bad"}, format="json")
        self.assertEqual(r.status_code, 400)
        r = c.post(A + "email/request/", {"email": "new@owner.com", "current_password": PASSWORD}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(mail.outbox[0].to, ["new@owner.com"])
        self.assertEqual(c.post(A + "email/confirm/", {"code": "111111"}, format="json").status_code, 400)
        code = re.search(r"\n\s+(\d{6})\n", mail.outbox[0].body).group(1)
        r = c.post(A + "email/confirm/", {"code": code}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(c.get(A + "me/").json()["email"], "new@owner.com")

    def test_email_used_by_someone_else_is_refused_and_bad_format(self):
        other = get_user_model().objects.get(pk=self.org_b.memberships.filter(role="OWNER").first().user_id)
        r = self.a.post(A + "email/request/", {"email": other.email, "current_password": PASSWORD}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.a.post(A + "email/request/", {"email": "not-an-email", "current_password": PASSWORD}, format="json").status_code, 400)

    def test_login_required(self):
        self.assertEqual(APIClient().post(A + "email/request/", {}, format="json").status_code, 401)
        self.assertEqual(APIClient().post(A + "email/confirm/", {}, format="json").status_code, 401)
