# Digital Product Passport Platform

A student capstone proof of concept that connects a public Digital Product
Passport (DPP) with a manufacturer's product register, lifecycle history, and
after-sales support process. Safe equipment is the primary case study.

## Implemented workflow

- organization administrators create versioned passport templates;
- administrators create product models and configure organization support data;
- administrators add and manage service-technician accounts;
- administrators and technicians register physical product items, including
  products that were installed before the DPP system was introduced;
- product data can be entered manually or suggested from a PDF/image through
  Gemini and reviewed before saving;
- published items expose only public fields and public lifecycle events through
  a public passport URL;
- printable SVG QR codes and supported Web NFC devices can use the same public
  passport URL;
- customers submit Azure DevOps support tickets from the public passport,
  optionally attach one validated image, and receive a private tracking code by
  email;
- customers track the live Azure status and tagged support comments on the DPP
  site and can reply without being sent to Azure DevOps.

## Technology stack

- Frontend: React 19, JavaScript, Vite, and CSS Modules
- Backend: Python, FastAPI, Pydantic, SQLAlchemy, and Alembic
- Database: PostgreSQL 16 with JSONB for configurable passport values
- Local infrastructure: Docker Compose for PostgreSQL
- Integrations: Azure DevOps, SMTP, Cloudinary, and Gemini
- Tests: pytest, FastAPI `TestClient`, and an isolated in-memory SQLite database

## Roles

- `manufacturer_user`: organization administrator who manages templates,
  models, organization settings, technicians, product items, and lifecycle
  events;
- `service_technician`: organization member who can register and publish product
  items and record lifecycle events, but cannot administer the organization or
  retire products;
- `system_admin`: seeded platform role reserved for future platform-level
  administration. No system-administrator UI or category-management API is
  currently implemented.

## Local setup

### 1. Configure the environment

Copy the example configuration and replace every required placeholder with a
local value:

```bash
cp .env.example .env
```

Generate `JWT_SECRET_KEY` with at least 32 characters. Azure DevOps, SMTP,
Cloudinary, and Gemini are optional until their related workflow is used. Keep
all secrets server-side; values prefixed with `VITE_` are visible in the
browser.

### 2. Start PostgreSQL

From the repository root:

```bash
docker compose up -d
```

The database is exposed on `POSTGRES_PORT` (5433 by default).

### 3. Start the backend

Run backend commands from `backend/` and use `backend/.venv`:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
python -m scripts.seed_reference_data
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`, with interactive documentation
at `/docs` and a health check at `/health`.

Create local users through the interactive script so no credentials are stored
in committed files:

```bash
python -m scripts.create_user
```

### 4. Start the frontend

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend is available at `http://localhost:5173` by default. Set
`VITE_API_URL` in `frontend/.env` only when the backend uses another public URL.

## Verification

Backend:

```bash
cd backend
.venv/bin/python -m pytest
```

The tracked suite contains 117 unit and API-level integration tests. External
Azure DevOps, SMTP, Cloudinary, and Gemini calls are replaced with test doubles
where applicable.

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

The frontend currently has lint and production-build checks, but no automated
component or browser test suite.

## Documentation

- [Implemented MVP scope](docs/mvp-scope.md)
- [Database design](docs/database-design.md)
- [UI design and development rules](docs/ui-design-guidelines.md)

## Proof-of-concept limitations

This repository demonstrates an integration model; it is not production-ready.
Notable accepted limitations include a process-local support-ticket rate
limiter, no malware scanner for uploads, no distributed job queue or automatic
retry worker, no dedicated secret manager, and no formal load, penetration,
accessibility, or cross-browser test programme.

Use only fictional or anonymized data. Never commit passwords, PATs, JWT
secrets, SMTP credentials, API keys, or production customer data.
