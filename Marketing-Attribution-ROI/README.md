# AttributionIQ — Marketing Attribution & ROI Intelligence Platform

Full-stack **Django 5.2 REST + MySQL 9.1 + React 19 (Vite 8 + Tailwind CSS v4 + Recharts)** B2B marketing attribution, revenue governance, data-quality detection, and ROI analytics platform.

---

## Core Platform Capabilities
1. **Multi-Touch Attribution Engine (`apps.attribution`)**
   - Supports **First Touch**, **Last Touch**, **Linear**, **Time Decay** ($2^{-\text{age}/\text{half\_life}}$), and **Position Based (40/20/40)** models with configurable lookback windows (default 90 days) and penny-exact decimal conservation.
2. **Data Quality & Anomaly Protection (`apps.exceptions`, `apps.validation`)**
   - Detects & isolates 5 core revenue/attribution hazards without mutating ledger history:
     1. Duplicate Orders (`Revenue counted more than once`)
     2. Post-Conversion Touchpoints (`Touchpoint after conversion attributed`)
     3. Foreign Spend Mismatch (`Spend currency mismatch`)
     4. Paid Campaign Missing Cost (`Campaign costs omitted`)
     5. Probabilistic Anonymous Session Links (`Anonymous session linked without evidence`)
   - Ships with an **11-Rule Validation Framework** (`VAL-01` .. `VAL-11`) runnable via REST API or `python manage.py validate_marketing_data --strict`.
3. **ROI & Marketing Analytics (`apps.analytics`)**
   - Computes verified Spend, Attributed Revenue, Actual Closed Revenue, ROI, ROAS, CPL, Conversion Rate, AOV, monthly cumulative velocity, 6-stage Opportunity funnel metrics, and Pandas/NumPy trend statistics.
4. **Deterministic Synthetic Data Generator & Export Suite (`data_generator`)**
   - Seeded PRNG (`--seed 20261022`) supporting `starter` and `full` (`500` campaigns / `50,000` contacts / `200,000` touchpoints / `10,000` opportunities) presets, SHA-256 dataset reproducibility checksums, CSV/JSON/SQL bundle exporters, and downloadable REST export endpoints under `/api/v1/reports/`.
5. **Dual-Mode React 19 UI (`frontend`)**
   - Seamlessly switches between offline demo mode (`VITE_USE_MOCK_DATA=true`) and live Django SimpleJWT backend integration (`VITE_USE_MOCK_DATA=false`).

---

## Repository Layout
```text
Marketing-Attribution-ROI/
├── backend/                  # Django 5.2 + DRF + SimpleJWT + OpenAPI + Pytest suite
│   ├── apps/                 # accounts, analytics, attribution, audiences, audit,
│   │                         # campaigns, channels, contacts, costs, creatives,
│   │                         # exceptions, leads, opportunities, orders,
│   │                         # touchpoints, validation, web_sessions
│   ├── common/               # DB config, atomic ID sequences, RBAC permissions, envelopes
│   ├── config/               # settings, settings_prod, urls, wsgi, asgi
│   ├── data_generator/       # Deterministic generator, SHA-256 verifier, bundle/API exporters
│   ├── tests/                # Comprehensive integration suites (Stages 1–13)
│   ├── .env.example
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                 # React 19 + Vite + Tailwind v4 + Recharts + Axios JWT client
│   ├── src/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── .env.example
├── database/
│   ├── init_mysql.sql
│   └── schema_documentation.md
├── docs/
│   ├── API_DOCUMENTATION.md
│   ├── ATTRIBUTION_LOGIC.md
│   ├── DATA_DICTIONARY.md
│   ├── DATABASE_DESIGN.md
│   ├── SETUP_GUIDE.md
│   └── TESTING.md
└── docker-compose.yml
```

---

## How to Run the Project

### Prerequisites
* **Python:** `3.12+`
* **Node.js & npm:** `Node 22+`
* **Database:** `MySQL 8+` / `9.1` (for local runs) **or** Docker Desktop with Compose v2

---

### Option 1: Run Locally (Windows PowerShell)

#### 1. Initialize & Seed MySQL Database
Create the `attribution_iq` schema in MySQL using [`database/init_mysql.sql`](database/init_mysql.sql):

```powershell
cd c:\CandidateWorkspace\Marketing-Attribution-ROI
Get-Content -Raw .\database\init_mysql.sql | & 'C:\Program Files\MySQL\MySQL Server 9.1\bin\mysql.exe' -u root -p
```

Configure backend environment variables and run migrations + seed data:

```powershell
cd c:\CandidateWorkspace\Marketing-Attribution-ROI\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit backend\.env and set DB_PASSWORD + DJANGO_SECRET_KEY

.\.venv\Scripts\python.exe manage.py check_db
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py generate_marketing_data --mode starter --seed 20261022 --with-attribution
.\.venv\Scripts\python.exe manage.py validate_marketing_data
.\.venv\Scripts\python.exe manage.py createsuperuser
```

#### 2. Start Backend API Server (`http://localhost:8000`)
In Terminal 1:

```powershell
cd c:\CandidateWorkspace\Marketing-Attribution-ROI\backend
.\.venv\Scripts\python.exe manage.py runserver 8000
```

#### 3. Configure & Start Frontend UI (`http://localhost:5173`)
In Terminal 2:

```powershell
cd c:\CandidateWorkspace\Marketing-Attribution-ROI\frontend
npm install
Copy-Item .env.example .env.local
```

Edit `frontend/.env.local` to choose live API vs mock mode:
* **Live Django + MySQL mode (recommended):** set `VITE_USE_MOCK_DATA=false` and `VITE_API_BASE_URL=http://localhost:8000/api/v1`
* **Offline demo mock mode:** keep `VITE_USE_MOCK_DATA=true` (uses browser `localStorage` without needing Django/MySQL)

Start the Vite dev server:

```powershell
npm run dev
```

Open **`http://localhost:5173`** and sign in with your created admin account.

---

### Option 2: Run Full Stack with Docker Compose
Runs MySQL 9.1, Django + Gunicorn, and Nginx React frontend (`VITE_USE_MOCK_DATA=false` baked in):

```powershell
cd c:\CandidateWorkspace\Marketing-Attribution-ROI
docker compose up --build -d
docker compose exec backend python manage.py generate_marketing_data --mode starter --seed 20261022 --with-attribution
docker compose exec backend python manage.py createsuperuser
```

To stop containers cleanly:

```powershell
docker compose down
```

---

### Useful Endpoints & URLs
* **Frontend UI:** `http://localhost:5173`
* **Backend API v1:** `http://localhost:8000/api/v1/`
* **Swagger / OpenAPI Docs:** `http://localhost:8000/api/docs/`
* **Health Check:** `http://localhost:8000/api/v1/health/`

---

### Database & Maintenance Commands
```powershell
# Check Django <-> MySQL connectivity
.\.venv\Scripts\python.exe manage.py check_db

# Open interactive MySQL shell
& 'C:\Program Files\MySQL\MySQL Server 9.1\bin\mysql.exe' -u root -p attribution_iq

# Regenerate deterministic dataset (use --mode full for full-scale dataset, --export for CSV/JSON/SQL bundle)
.\.venv\Scripts\python.exe manage.py generate_marketing_data --mode starter --seed 20261022 --with-attribution

# Validate data integrity (11 rules)
.\.venv\Scripts\python.exe manage.py validate_marketing_data --strict
```

---

### Verification Commands
```powershell
# Backend checks & full pytest suite (from backend/)
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py spectacular --validate --fail-on-warn --no-color
.\.venv\Scripts\python.exe -m pytest -v

# Frontend lint & production build (from frontend/)
npm run lint
npm run build
```

---

## Documentation
* [Setup Guide](docs/SETUP_GUIDE.md)
* [Testing & Verification Guide](docs/TESTING.md)
* [API Documentation](docs/API_DOCUMENTATION.md)
* [Attribution Logic](docs/ATTRIBUTION_LOGIC.md)
* [Data Dictionary](docs/DATA_DICTIONARY.md)
* [Database Design](docs/DATABASE_DESIGN.md) | [Schema Documentation](database/schema_documentation.md)

