#!/bin/sh
# Runs inside the "backup" container: every 24h dump the database and archive the uploaded images.
# Keeps the last BACKUP_KEEP_DAYS days. THESE ARE ON THE SAME SERVER: also copy them off-site (see README).
set -eu
KEEP="${BACKUP_KEEP_DAYS:-14}"
while true; do
  STAMP="$(date +%Y%m%d_%H%M%S)"
  echo "[backup] $STAMP database…"
  pg_dump -Fc -f "/backups/dinex_${STAMP}.dump" && echo "[backup] ok /backups/dinex_${STAMP}.dump"
  tar -czf "/backups/media_${STAMP}.tar.gz" -C /media . 2>/dev/null || true
  find /backups -type f \( -name 'dinex_*.dump' -o -name 'media_*.tar.gz' \) -mtime "+${KEEP}" -delete
  sleep 86400
done
