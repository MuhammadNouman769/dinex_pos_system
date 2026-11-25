# DineX by XverLabs

Restaurant POS + orders + recipe-based inventory + cash & reports, sold as a monthly subscription.

| Folder | What |
|---|---|
| `dinex/` | Backend: Django REST API (PostgreSQL in production) |
| `dinex-web/` | Frontend: Next.js web app (restaurants + DineX Admin for XverLabs) |
| `deploy/` | Docker Compose, HTTPS (Caddy), backups, setup script, deployment guide |

**Put it live:** open `deploy/README.md`.
**Try it on your laptop with demo data:**
```
cd dinex && python -m venv venv && . venv/bin/activate && pip install -r requirements.txt
printf 'SECRET_KEY=dev-only-key\nDEBUG=True\n' > .env
python manage.py migrate && python manage.py seed_demo --reset && python manage.py runserver 8000
# new terminal
cd dinex-web && cp .env.example .env.local && npm install && npm run dev      # http://localhost:3000
```
Demo logins: `dinex/docs/DEMO_DATA.md` (admin `xverlabs` / `DineX@2026`).
