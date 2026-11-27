# DineX API access

Start the backend (development):

```bash
python manage.py migrate
python manage.py seed_demo --reset      # demo restaurants + logins (wipes the dev database first)
python manage.py runserver 8000
```

| Page | URL |
|---|---|
| Interactive API docs (Swagger) | http://127.0.0.1:8000/api/docs/ |
| OpenAPI schema (JSON/YAML) | http://127.0.0.1:8000/api/schema/ |
| Django admin (developers only) | http://127.0.0.1:8000/django-admin/ |
| Health check | http://127.0.0.1:8000/api/v1/health/ |

The API docs are on only when `DEBUG=True` (or `ENABLE_API_DOCS=True`). They are off in production.

## Demo logins (created by `seed_demo`)

| Who | Username | Password |
|---|---|---|
| XverLabs admin (platform) | `xverlabs` | `DineX@2026` |
| Restaurant owners | `karachigrill`, `lahoretikka`, `pizzacorner`, `desidhaba`, `burgerhub`, `chaiwala` | `Demo@12345` |
| Karachi Grill staff | `karachigrill_dha_mgr`, `karachigrill_dha_c1`, `karachigrill_dha_c2` | `Demo@12345` |

These only exist after `seed_demo` has run. If login says "No active account", run `python manage.py seed_demo --reset`.
Full list of demo restaurants: `docs/DEMO_DATA.md`. Never run `seed_demo` on a real server.

## Using the Swagger page

1. Open `/api/docs/`, expand **POST /api/v1/auth/token/**, press *Try it out*, pick an example (XverLabs admin or Restaurant owner), *Execute*.
2. Copy the value of `access` from the response.
3. Press **Authorize** (top right), paste the access token, *Authorize*. All other calls now work.
4. The token lasts a short time; use `POST /api/v1/auth/token/refresh/` with the `refresh` value for a new one.

## Same thing with curl

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "karachigrill", "password": "Demo@12345"}'

curl http://127.0.0.1:8000/api/v1/auth/me/ -H "Authorization: Bearer <access>"
```
