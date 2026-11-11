# AttributionIQ: Marketing Attribution & ROI Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![React](https://img.shields.io/badge/React-19-149ECA?logo=react&logoColor=white)](https://react.dev/)
[![MySQL](https://img.shields.io/badge/MySQL-8%2B%20%7C%209.1-4479A1?logo=mysql&logoColor=white)](https://www.mysql.com/)
[![API](https://img.shields.io/badge/API-Django%20REST-0C4B33)](https://www.django-rest-framework.org/)

> **AttributionIQ** is a full-stack marketing analytics platform for multi-touch attribution, campaign ROI reporting, revenue governance, and marketing data-quality validation. It combines a Django REST API and MySQL database with a React dashboard, plus a reproducible synthetic-data generator for local demos and testing.

### Project Documentation

| Resource | Description |
|---|---|
| [Setup Guide](docs/SETUP_GUIDE.md) | Detailed local and Docker setup |
| [API Documentation](docs/API_DOCUMENTATION.md) | REST endpoints and API usage |
| [Attribution Logic](docs/ATTRIBUTION_LOGIC.md) | Attribution models and calculation behavior |
| [Data Dictionary](docs/DATA_DICTIONARY.md) | Entities, fields, and data definitions |
| [Database Design](docs/DATABASE_DESIGN.md) | Database structure and relationships |
| [Testing Guide](docs/TESTING.md) | Validation and test instructions |

---

## 1. Problem Context & Solution Overview

Marketing teams need to understand which campaigns and interactions contribute to conversions, how much revenue they generate, and whether the underlying data is trustworthy. Reports based on inconsistent spend, duplicated orders, or unverified attribution can lead to misleading ROI decisions.

AttributionIQ provides an auditable workflow to:

1. Capture and organize campaign, contact, touchpoint, opportunity, order, and cost data.
2. Attribute conversion revenue across customer touchpoints using selectable models.
3. Compare verified spend with attributed and closed revenue through marketing analytics.
4. Detect common data-quality and attribution anomalies without silently rewriting ledger history.
5. Explore the application using deterministic synthetic data, or connect the UI to the Django API.

The project is designed for local development and demonstration. Configure production-grade secrets, database access, HTTPS, and deployment settings before exposing an instance publicly.

---

## 2. Architecture & Core Workflow

```text
┌─────────────────────────────────────┐
│ Deterministic Marketing Data        │
│ Generator (seeded starter/full data)│
└──────────────────┬──────────────────┘
                   │
        ┌──────────┴───────────┐
        ▼                      ▼
┌───────────────────┐  ┌─────────────────────┐
│ MySQL Database    │  │ CSV / JSON / SQL     │
│ Marketing records │  │ data exports         │
└─────────┬─────────┘  └─────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────┐
│ Django REST API                             │
│ • Authentication and application APIs       │
│ • Attribution and analytics                 │
│ • Validation and anomaly reporting          │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│ React 19 dashboard                          │
│ • Offline mock-data mode                    │
│ • Live API mode with SimpleJWT              │
│ • Marketing performance and ROI views        │
└─────────────────────────────────────────────┘
```

In live mode, the frontend sends requests to the Django REST API. In mock mode, the frontend can run independently for an offline demonstration. The Django backend uses MySQL for persistent application data and provides management commands for data generation and validation.

---

## 3. Key Capabilities & Technical Features

### A. Multi-Touch Attribution

The attribution engine supports:

- **First Touch** — assigns conversion credit to the earliest eligible touchpoint.
- **Last Touch** — assigns credit to the latest eligible touchpoint.
- **Linear** — distributes credit evenly across eligible touchpoints.
- **Time Decay** — weights touchpoints according to age using a configurable half-life.
- **Position Based (40/20/40)** — emphasizes the first and last touchpoints and distributes the remaining credit across intervening touches.

Attribution supports configurable lookback windows (90 days by default) and decimal-safe credit allocation designed to conserve the conversion amount to the cent.

### B. Data Quality & Anomaly Protection

The platform detects and isolates common revenue and attribution hazards:

1. **Duplicate orders** — revenue counted more than once.
2. **Post-conversion touchpoints** — interactions occurring after the conversion.
3. **Foreign spend mismatch** — campaign spend recorded in a different currency.
4. **Paid campaign missing cost** — paid campaigns without corresponding cost data.
5. **Anonymous session links without evidence** — probabilistic links that lack supporting evidence.

An **11-rule validation framework** (`VAL-01` through `VAL-11`) can be run through the REST API or with the `validate_marketing_data` Django management command. Validation findings are surfaced for review rather than silently changing ledger history.

### C. ROI & Marketing Analytics

Analytics include:

- Verified spend, attributed revenue, and actual closed revenue.
- Return on investment (ROI) and return on ad spend (ROAS).
- Cost per lead (CPL), conversion rate, and average order value (AOV).
- Monthly cumulative revenue velocity.
- Opportunity funnel metrics across six stages.
- Trend statistics computed with Pandas and NumPy.

### D. Reproducible Synthetic Data & Exports

The seeded data generator supports `starter` and `full` profiles. The full profile is designed for larger local datasets, including up to 500 campaigns, 50,000 contacts, 200,000 touchpoints, and 10,000 opportunities.

The generator and reporting suite include:

- A repeatable seed (default example: `20261022`).
- SHA-256 dataset reproducibility checksums.
- CSV, JSON, and SQL bundle exports.
- Downloadable report exports under `/api/v1/reports/`.

### E. React Application Modes

- **Mock mode:** `VITE_USE_MOCK_DATA=true`; runs with browser-based demo data without requiring the Django API or MySQL.
- **Live mode:** `VITE_USE_MOCK_DATA=false`; connects to the Django REST API using the configured API base URL and SimpleJWT integration.

---

## 4. Domain Model & Repository Layout

The backend is organized into Django apps for accounts, campaigns, channels, contacts, costs, creatives, leads, opportunities, orders, touchpoints, web sessions, attribution, analytics, audiences, audit, exceptions, and validation.

For detailed entity definitions and relationships, see the [Data Dictionary](docs/DATA_DICTIONARY.md) and [Database Design](docs/DATABASE_DESIGN.md).

```text
Marketing-Attribution-ROI/
├── backend/
│   ├── apps/                 # Django domain apps and API logic
│   ├── common/               # Shared database, permission, and response helpers
│   ├── config/               # Django settings and URL configuration
│   ├── data_generator/       # Seeded synthetic data and export utilities
│   ├── tests/                # Backend integration and feature test suites
│   ├── .env.example          # Backend environment variable template
│   ├── Dockerfile
│   └── requirements.txt
├── database/
│   ├── init_mysql.sql        # Initial MySQL database setup
│   └── schema_documentation.md
├── docs/                     # Setup, API, data, and testing documentation
├── frontend/
│   ├── src/                  # React application
│   ├── .env.example          # Frontend environment variable template
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml        # MySQL, Django API, and frontend services
└── README.md
```

---

## 5. Quick Start & Execution Guide

### Prerequisites

- Python 3.12+
- Node.js 22+ and npm
- MySQL 8+ / 9.1 for local runs, or Docker Desktop with Compose v2

### Option A: Run with Docker Compose

From the project directory, configure strong `DB_PASSWORD` and `DJANGO_SECRET_KEY` environment values for your environment before starting the services. Do not use development defaults for a public or production deployment.

```powershell
# Set these in your PowerShell session; replace the example values first.
$env:DB_PASSWORD = "replace-with-a-strong-password"
$env:DJANGO_SECRET_KEY = "replace-with-a-long-random-secret"

docker compose up --build -d
docker compose exec backend python manage.py generate_marketing_data --mode starter --seed 20261022 --with-attribution
docker compose exec backend python manage.py createsuperuser
```

The application is then available at:

- Frontend: `http://localhost:5173`
- API: `http://localhost:8000/api/v1/`
- API docs: `http://localhost:8000/api/docs/`

Stop the containers with:

```powershell
docker compose down
```

### Option B: Run Locally on Windows

#### 1. Initialize MySQL

Create the `attribution_iq` schema using the provided SQL file:

```powershell
# From the project root
Get-Content -Raw .\database\init_mysql.sql | & 'C:\Program Files\MySQL\MySQL Server 9.1\bin\mysql.exe' -u root -p
```

#### 2. Configure and initialize the backend

```powershell
Set-Location .\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend\.env` and set the database connection values and a strong `DJANGO_SECRET_KEY`. Then run migrations, generate demo data, and create an administrator:

```powershell
.\.venv\Scripts\python.exe manage.py check_db
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py generate_marketing_data --mode starter --seed 20261022 --with-attribution
.\.venv\Scripts\python.exe manage.py validate_marketing_data
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Start the API in a backend terminal:

```powershell
.\.venv\Scripts\python.exe manage.py runserver 8000
```

#### 3. Configure and start the frontend

In a second terminal:

```powershell
Set-Location .\frontend
npm install
Copy-Item .env.example .env.local
```

For live API mode, set these values in `frontend\.env.local`:

```dotenv
VITE_USE_MOCK_DATA=false
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

To run the offline demo, set `VITE_USE_MOCK_DATA=true`. Start the frontend:

```powershell
npm run dev
```

Open `http://localhost:5173` in your browser. In live mode, sign in with the administrator account created in the backend setup.

---

## 6. Useful URLs & Maintenance Commands

| Service | Local URL |
|---|---|
| React frontend | `http://localhost:5173` |
| Django API v1 | `http://localhost:8000/api/v1/` |
| Swagger / OpenAPI docs | `http://localhost:8000/api/docs/` |
| Health check | `http://localhost:8000/api/v1/health/` |

Run these management commands from `backend/`:

```powershell
# Check Django-to-MySQL connectivity
.\.venv\Scripts\python.exe manage.py check_db

# Generate the seeded starter dataset and attribution
.\.venv\Scripts\python.exe manage.py generate_marketing_data --mode starter --seed 20261022 --with-attribution

# Use --mode full for a larger dataset; use --export for an export bundle
.\.venv\Scripts\python.exe manage.py generate_marketing_data --mode full --seed 20261022 --with-attribution

# Run the validation rules in strict mode
.\.venv\Scripts\python.exe manage.py validate_marketing_data --strict
```

---

## 7. Verification & Tests

Run backend checks and tests from `backend/`:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py spectacular --validate --fail-on-warn --no-color
.\.venv\Scripts\python.exe -m pytest -v
```

Run frontend linting and create a production build from `frontend/`:

```powershell
npm run lint
npm run build
```

See the [Testing Guide](docs/TESTING.md) for additional test and validation details.

---

## 8. Publishing to GitHub

Create an empty GitHub repository if you do not already have one. From the local repository root, review the files before committing:

```powershell
git status
# If this project is inside a larger repository, stage only this project folder:
git add -- Marketing-Attribution-ROI
git diff --cached --check
git diff --cached --name-only
```

If this project directory is itself the repository root, use `git add -- .` instead.

Confirm the staged files do not include `.env` files, passwords, API keys, or other local secrets. Then commit and push to the configured remote:

```powershell
git commit -m "feat: add AttributionIQ marketing attribution platform"
git push -u origin main
```

If this is a new local repository, configure its GitHub remote before pushing:

```powershell
git remote add origin https://github.com/<your-username>/<your-repository>.git
git branch -M main
git push -u origin main
```

If `origin` is already configured, do not add it again; verify it with `git remote -v`.

---

## 9. Data & Security Notes

- The synthetic-data generator is intended for demonstration and testing. Do not use generated sample records as real customer or financial data.
- Keep credentials and secret keys out of Git. Use local environment files for development and secure secret management for deployments.
- Restrict `DJANGO_DEBUG`, allowed hosts, CORS origins, database permissions, and network access appropriately before deploying.
- Configure TLS/HTTPS and production security settings before making the application publicly accessible.
