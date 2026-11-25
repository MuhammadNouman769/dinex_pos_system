#!/bin/bash
# Fresh QA database + backend (port 8000). Usage: reset.sh
S=/tmp/claude-0/-home-claude/94f64667-3268-56e5-8b32-f373d0460a86/scratchpad/qa
pkill -f "manage.py runserver" ; sleep 1
cd /home/claude/src_zip/dinex
export DB_NAME=$S/qa.sqlite3 CORS_ALLOWED_ORIGINS=http://localhost:3101 SIGNUP_RATE=1000/hour
rm -f $DB_NAME && python manage.py migrate -v0 && python manage.py shell -c "
from django.contrib.auth import get_user_model as g
g().objects.create_superuser('root','root@x.com','Str0ng-Pass!word')
from apps.billing.models import PaymentAccount as P
P.objects.create(method='JAZZCASH',account_title='XverLabs',account_number='0300 1112223',instructions='Send, then enter the TID')
P.objects.create(method='BANK',bank_name='Meezan Bank',account_title='XverLabs (Pvt) Ltd',account_number='PK36MEZN0000001234567890')" >/dev/null
(nohup python manage.py runserver 8000 --noreload > $S/backend.log 2>&1 &)
sleep 3; curl -s localhost:8000/api/v1/public/plans/ | head -c 80; echo
