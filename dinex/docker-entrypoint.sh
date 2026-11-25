#!/bin/sh
# Runs before the main command. Only the "backend" service sets RUN_MIGRATIONS=1,
# so migrations never run twice at once.
set -e
if [ "$RUN_MIGRATIONS" = "1" ]; then
  echo "Applying database migrations…"
  python manage.py migrate --noinput
  echo "Collecting static files…"
  python manage.py collectstatic --noinput
fi
exec "$@"
