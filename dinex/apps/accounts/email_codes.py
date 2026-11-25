"""Send and check 6-digit email codes. Codes live 10 minutes, allow 5 wrong tries, are stored hashed."""
import hashlib
import hmac
import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from apps.accounts.models import EmailCode

TTL_MIN, MAX_TRIES, RESEND_GAP_SEC, MAX_PER_HOUR = 10, 5, 45, 5


def _hash(user, purpose, code):
    return hmac.new(settings.SECRET_KEY.encode(), f"{user.pk}:{purpose}:{code}".encode(), hashlib.sha256).hexdigest()


def _sender():
    m = re.search(r"<(.+)>", settings.DEFAULT_FROM_EMAIL)
    return f"DineX <{m.group(1) if m else settings.DEFAULT_FROM_EMAIL}>"


def issue(user, purpose, email, subject, intro):
    """Returns True if an email was sent. Quietly does nothing when asked too often."""
    now = timezone.now()
    recent = EmailCode.objects.filter(user=user, purpose=purpose, created_at__gte=now - timedelta(hours=1))
    if recent.count() >= MAX_PER_HOUR or recent.filter(created_at__gte=now - timedelta(seconds=RESEND_GAP_SEC)).exists():
        return False
    EmailCode.objects.filter(user=user, purpose=purpose, used=False).update(used=True)      # only the newest code works
    code = f"{secrets.randbelow(10**6):06d}"
    EmailCode.objects.create(user=user, purpose=purpose, email=email, code_hash=_hash(user, purpose, code), expires_at=now + timedelta(minutes=TTL_MIN))
    body = (f"Hi {user.first_name or user.username},\n\n{intro}\n\n    {code}\n\nThis code works for {TTL_MIN} minutes. "
            f"If you did not ask for it, you can ignore this email. Nobody can use it without your account.\n\nDineX")
    send_mail(subject, body, _sender(), [email], fail_silently=False)
    return True


def check(user, purpose, code):
    """True if the code is right. Wrong tries are counted; the code is single use."""
    row = EmailCode.objects.filter(user=user, purpose=purpose, used=False, expires_at__gt=timezone.now()).order_by("-id").first()
    if not row or row.attempts >= MAX_TRIES:
        return None
    if hmac.compare_digest(row.code_hash, _hash(user, purpose, (code or "").strip())):
        row.used = True
        row.save(update_fields=["used"])
        return row
    EmailCode.objects.filter(pk=row.pk).update(attempts=row.attempts + 1)
    return None
