#!/usr/bin/env bash
# One-time local setup: Python venv + packages, database, demo data, npm packages.
# Usage: ./scripts/dev-setup.sh [--no-demo]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null || { echo "Python 3.12+ is required (set PYTHON=... if it has another name)"; exit 1; }
command -v node >/dev/null || { echo "Node.js 20+ is required (https://nodejs.org)"; exit 1; }

echo "==> Backend"
cd "$ROOT/dinex"
[ -d venv ] || "$PY" -m venv venv
. venv/bin/activate
pip install -q --upgrade pip && pip install -q -r requirements.txt
[ -f .env ] || { cp .env.example .env; echo "created dinex/.env"; }
python manage.py migrate -v0
if [ "${1:-}" != "--no-demo" ]; then echo "==> Demo data (about 2 minutes)"; python manage.py seed_demo --reset | tail -8; fi

echo "==> Frontend"
cd "$ROOT/dinex-web"
[ -f .env.local ] || { cp .env.example .env.local; echo "created dinex-web/.env.local"; }
npm install --no-audit --no-fund

echo; echo "Ready. Start everything with:   ./scripts/dev.sh     (or: make dev)"
echo "  Web app    http://localhost:3000"
echo "  API docs   http://localhost:8000/api/docs/"
if [ "${1:-}" != "--no-demo" ]; then
  echo "  Restaurant login  karachigrill / Demo@12345"
  echo "  DineX Admin login xverlabs / DineX@2026   (same login page)"
else
  echo "  No demo data loaded. Run: make demo     (or create a restaurant at /start)"
fi
