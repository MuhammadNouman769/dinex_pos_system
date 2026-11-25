#!/bin/sh
# Copy the nightly backups OFF this server (a backup on the same disk is not a backup).
# Example with rclone to Backblaze B2 / S3 / Google Drive. Set up once with:  rclone config   (remote name below)
# Then run it every night from the host's cron:   30 3 * * * /opt/dinex/deploy/offsite-backup.sh >> /var/log/dinex-offsite.log 2>&1
set -eu
REMOTE="${1:-dinex-offsite:dinex-backups}"          # <rclone remote>:<bucket or folder>
SRC="$(docker volume inspect dinex_backups --format '{{ .Mountpoint }}')"
rclone copy "$SRC" "$REMOTE" --max-age 2d --transfers 2
echo "$(date -u +%FT%TZ) offsite copy ok -> $REMOTE"
