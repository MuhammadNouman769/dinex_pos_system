#!/bin/sh
# First-time setup: writes deploy/.env with fresh random secrets.   Usage:  ./setup.sh app.yourdomain.com you@email.com
set -eu
DOMAIN="${1:?Usage: ./setup.sh <domain> <email>}"
EMAIL="${2:?Usage: ./setup.sh <domain> <email>}"
cd "$(dirname "$0")"
[ -f .env ] && { echo ".env already exists. Delete it first if you really want new secrets (that would lock you out of the existing database)."; exit 1; }
rand() { head -c 64 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c "$1"; }
cat > .env <<ENV
# Generated $(date -u +%Y-%m-%dT%H:%MZ). Keep this file private and back it up somewhere safe.
DOMAIN=$DOMAIN
ACME_EMAIL=$EMAIL

# Django
DEBUG=False
SECRET_KEY=$(rand 80)
ALLOWED_HOSTS=$DOMAIN
CSRF_TRUSTED_ORIGINS=https://$DOMAIN
CORS_ALLOWED_ORIGINS=
LOG_LEVEL=INFO
LOGIN_RATE=30/min
NUM_PROXIES=1
ENABLE_API_DOCS=False
DJANGO_ADMIN_URL=django-admin/

# Email (password-reset codes, customer points). Without a real SMTP account the codes are only printed in the server log,
# so fill these in before going live (Gmail/Zoho/Brevo/SendGrid SMTP all work).
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=DineX <no-reply@$DOMAIN>

# Subscriptions
BILLING_TRIAL_DAYS=14
BILLING_INVOICE_DUE_DAYS=7
BILLING_GRACE_DAYS=7

# PostgreSQL (inside the stack only)
POSTGRES_DB=dinex
POSTGRES_USER=dinex
POSTGRES_PASSWORD=$(rand 32)
BACKUP_KEEP_DAYS=14
ENV
chmod 600 .env
echo "Created deploy/.env for https://$DOMAIN"
echo "Next:  docker compose up -d --build   then   docker compose exec backend python manage.py createsuperuser"
