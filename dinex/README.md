# Dinex-pos API
This repository contains the backend API for The DineX, built with Django and Django REST Framework.

It supports restaurant organization setup, menu catalog management, customer handling, order processing, tables, inventory workflows, and reporting for a restaurant POS system.

## Overview

The project is a multi-module Django backend designed for a restaurant management and point-of-sale workflow. It includes:

- Authentication and JWT-based access management
- Organization and location management
- Onboarding flow for restaurant setup
- Catalog management for categories, products, variants, modifiers, deals, and product locations
- Customer management
- Order creation, status updates, and table operations
- Inventory and reporting modules
- OpenAPI schema generation via drf-spectacular

## Tech Stack

- Python 3.12+
- Django 6.1
- Django REST Framework 3.18
- djangorestframework-simplejwt
- drf-spectacular
- PostgreSQL support via psycopg2-binary
- SQLite as default/local database option
- python-decouple for environment variables

## Project Structure

```text
.
├── apps/
│   ├── accounts/
│   ├── catalog/
│   ├── customers/
│   ├── inventory/
│   ├── onboarding/
│   ├── orders/
│   ├── organizations/
│   ├── products/
│   ├── reports/
│   └── utils/
├── core/
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── db.sqlite3
├── manage.py
├── requirements.txt
├── README.md
└── docs/
```

## Main Apps

### accounts
Authentication, user model, login, and refresh token endpoints.

### organizations
Organization, location, and membership management.

### onboarding
Restaurant onboarding flow for initial setup.

### catalog
Menu catalog features such as categories, products, variants, dietary tags, modifier groups, product assignments, and deals.

### customers
Customer management APIs.

### orders
Order lifecycle, order items, tables, and status handling.

### inventory
Inventory management module.

### reports
Reporting and analytics endpoints.

### utils
Shared utilities, middleware, permissions, validators, and helper code.

## Features

- JWT authentication and refresh tokens
- Role-based platform ownership model
- Multi-organization and multi-location support
- Restaurant onboarding and setup flow
- Product catalog management
- Variants and modifiers
- Deals and promotion support
- Product assignment by location
- Customer records and tracking
- Order creation, updates, table occupancy, and status handling
- Inventory integration
- Reporting APIs
- Automatic API schema and Swagger UI generation

## Requirements

- Python 3.12+
- pip
- Git
- Optional: PostgreSQL if you want to use it instead of SQLite

## Clone the Repository

```bash
git clone https://github.com/MuhammadNouman769/Dinex-pos.git
cd Dinex-pos
```

## Setup

Create a virtual environment:

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Environment Configuration

Create a `.env` file in the project root and add your settings. Example:

```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
JWT_ACCESS_TOKEN_MINUTES=30
JWT_REFRESH_TOKEN_DAYS=7
```

If you want PostgreSQL instead of SQLite:

```env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=dinex
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=127.0.0.1
DB_PORT=5432
```

> The project defaults to SQLite when `DB_ENGINE` is not set.

## Database Setup

Run migrations:

```bash
python manage.py migrate
```

Create a superuser if needed:

```bash
python manage.py createsuperuser
```

## Run the Application

Start the development server:

```bash
python manage.py runserver
```

The app is available at:

```text
http://127.0.0.1:8000/
```

## API Endpoints

Authentication:

```text
/api/v1/auth/token/
/api/v1/auth/token/refresh/
```

Organizations and locations:

```text
/api/v1/organizations/
/api/v1/organizations/me/
/api/v1/organizations/locations/
/api/v1/organizations/members/
/api/v1/organizations/location-staff/
```

Onboarding:

```text
/api/v1/onboarding/restaurant/
```

Catalog:

```text
/api/v1/catalog/categories/
/api/v1/catalog/products/
/api/v1/catalog/variants/
/api/v1/catalog/dietary-tags/
/api/v1/catalog/modifier-groups/
/api/v1/catalog/modifier-options/
/api/v1/catalog/deals/
```

Customers:

```text
/api/v1/customers/
```

Orders:

```text
/api/v1/orders/
/api/v1/orders/stats/
/api/v1/orders/tables/
```

Schema and docs:

```text
/api/schema/
/api/docs/
```

## API Documentation

This project uses `drf-spectacular` to generate OpenAPI schema and Swagger UI.

- Schema: `/api/schema/`
- Swagger UI: `/api/docs/`

## Development Notes

The project follows a modular app structure with clear separation between:

- models
- serializers
- validators
- views
- schemas
- selectors
- utilities

This keeps business logic and API concerns organized and easier to extend.

## Testing

Run the Django test suite:

```bash
python manage.py test
```

## License

This project is currently provided for internal or project-based use without a formal public license declaration in the repository.

## Notes

- This repository is the backend only. It does not include a separate frontend application.
- Local development works with SQLite by default, while PostgreSQL is supported for production-style setups.
- Environment variables should not be committed to version control.


---
## Production
See `../deploy/README.md` (Docker, HTTPS, PostgreSQL, backups). Health check: `GET /api/v1/health/`.
Other docs: `docs/PHASE0_CHANGES.md`, `PHASE1_BACKEND.md`, `PHASE3_CASH.md`, `PHASE4_ADMIN.md`, `DEMO_DATA.md`.
