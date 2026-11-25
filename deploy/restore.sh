#!/bin/sh
# Restore the database from a backup file.   Usage:  ./restore.sh /path/to/dinex_20261018_030000.dump
# WARNING: replaces ALL current data. Take a fresh backup first if unsure.
set -eu
FILE="${1:?Usage: ./restore.sh <backup.dump>}"
[ -f "$FILE" ] || { echo "File not found: $FILE"; exit 1; }
cd "$(dirname "$0")"
. ./.env
printf "This will REPLACE all data in '%s' with %s. Type YES to continue: " "$POSTGRES_DB" "$FILE"
read -r ANSWER; [ "$ANSWER" = "YES" ] || { echo "Cancelled."; exit 1; }
docker compose stop backend scheduler web
docker compose exec -T db dropdb -U "$POSTGRES_USER" --if-exists "$POSTGRES_DB"
docker compose exec -T db createdb -U "$POSTGRES_USER" "$POSTGRES_DB"
docker compose exec -T db pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner < "$FILE"
docker compose up -d
echo "Restored. Check https://$DOMAIN"
