#!/usr/bin/env bash
# Runs backend (8000) and frontend (3000) together. Ctrl+C stops both.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[ -d "$ROOT/dinex/venv" ] || { echo "Run ./scripts/dev-setup.sh first"; exit 1; }
trap 'kill 0' EXIT INT TERM
( cd "$ROOT/dinex" && . venv/bin/activate && python manage.py runserver 8000 ) &
( cd "$ROOT/dinex-web" && npm run dev ) &
wait
