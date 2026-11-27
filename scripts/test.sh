#!/usr/bin/env bash
# Backend unit tests + frontend type check. Usage: ./scripts/test.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/dinex" && . venv/bin/activate && python manage.py test --parallel 2>&1 | tail -6
cd "$ROOT/dinex-web" && npx tsc --noEmit && echo "TypeScript OK"
