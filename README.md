# DineX by XverLabs

Restaurant POS + orders + recipe-based inventory + cash, payroll, loyalty and reports, sold as a monthly subscription
(Starter PKR 2,999 · Growth PKR 4,999 · Pro PKR 6,999, 14-day free trial, manual payment approval).
Works offline: orders are stored on the device and synced safely when the internet returns.

| Folder | What |
|---|---|
| `dinex/` | Backend: Django 6 + DRF REST API (SQLite in development, PostgreSQL in production) |
| `dinex-web/` | Frontend: Next.js 15 (public landing page, restaurant app, DineX Admin for XverLabs) |
| `deploy/` | Docker Compose, HTTPS (Caddy), backups, `setup.sh`, deployment guide |
| `scripts/` | Developer helpers (`dev-setup`, `dev`, `test`) for Linux/macOS (`.sh`) and Windows (`.bat`) |
| `qa_e2e/` | Playwright end-to-end scripts used for QA (see `qa_e2e/README.md`) |

## Run it on your computer (development)

Needs **Python 3.12+** and **Node.js 20+**.

```bash
make setup      # one time: venv, packages, database, demo data (~2 min), npm install
make dev        # backend http://localhost:8000  +  web http://localhost:3000
```

No `make`? Use `./scripts/dev-setup.sh` then `./scripts/dev.sh`. On Windows: `scripts\dev-setup.bat` then `scripts\dev.bat`.

| What | Address / login |
|---|---|
| Restaurant app | http://localhost:3000/login — `karachigrill` / `Demo@12345` |
| DineX Admin (XverLabs) | same login page — `xverlabs` / `DineX@2026` |
| API docs (Swagger) | http://localhost:8000/api/docs/ (click Authorize, paste the access token) |
| All demo accounts | `dinex/docs/DEMO_DATA.md` |

Other commands: `make test` (backend tests + TypeScript check), `make demo` (wipe and reload demo data), `make build`, `make help`.

### Configuration
* Backend: `dinex/.env` (copied from `dinex/.env.example` by setup). Email codes print in the terminal unless SMTP is set.
* Frontend: `dinex-web/.env.local` (from `.env.example`). `NEXT_PUBLIC_*` values are fixed at build time.

## Put it live
Open **`deploy/README.md`** (server, domain, HTTPS, backups, email, Google Search Console).

## Google / SEO
The public landing page (`/`) is server-rendered with metadata, a share image, `robots.txt`, `sitemap.xml` and structured data.
Login, signup and app pages are `noindex`. Set `NEXT_PUBLIC_SITE_URL` to your real domain before building
(`deploy/setup.sh` does it). Steps to get listed: `deploy/README.md` → "Google Search Console".
