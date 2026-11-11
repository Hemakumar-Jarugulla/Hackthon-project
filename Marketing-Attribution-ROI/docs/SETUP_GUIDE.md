# AttributionIQ — Local & Docker Setup Guide

## 1. Prerequisites
- **Python:** 3.12+
- **Node.js & npm:** Node 22+
- **Database:** MySQL 8+ / 9.1 (or Docker Desktop with Compose v2)

---

## 2. Quick Start with Docker Compose
Run the full stack (MySQL 9.1 + Django + Gunicorn + Nginx React UI) cleanly from the repository root:

```bash
docker compose up --build -d
```

- **Frontend UI:** `http://localhost:5173`
- **Backend REST API:** `http://localhost:8000/api/v1/`
- **Swagger / OpenAPI Docs:** `http://localhost:8000/api/docs/`
- **Health Check:** `http://localhost:8000/api/v1/health/`

Seed deterministic demo data inside the running backend container:

```bash
docker compose exec backend python manage.py generate_marketing_data --mode starter --seed 20261022 --with-attribution
```

---

## 3. Manual Local Development Setup

### A. Initialize MySQL Database
Run `database/init_mysql.sql` against MySQL (`utf8mb4` + `utf8mb4_unicode_ci`):

```powershell
Get-Content -Raw .\database\init_mysql.sql | mysql -u root -p
```

### B. Configure and Start the Django Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit backend\.env with your local MySQL password and secret key

python manage.py migrate
python manage.py generate_marketing_data --mode starter --seed 20261022 --with-attribution --verify-reproducibility
python manage.py validate_marketing_data --strict
python manage.py runserver 8000
```

Create an admin workspace user:
```powershell
python manage.py createsuperuser
```

### C. Configure and Start the React Frontend
```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
```

Set `VITE_USE_MOCK_DATA` inside `frontend/.env.local`:
- **`VITE_USE_MOCK_DATA=true`** (default): Offline interactive mode backed by JSON seed stores & `localStorage`.
- **`VITE_USE_MOCK_DATA=false`**: Live mode connected to `VITE_API_BASE_URL=http://localhost:8000/api/v1` with SimpleJWT login/refresh/logout and snake_case <-> camelCase response adapters.

Start Vite dev server (`http://localhost:5173`):
```powershell
npm run dev
```

---

## 4. Verification Commands
```powershell
# Backend Django checks & OpenAPI schema validation
cd backend
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py spectacular --validate --fail-on-warn --no-color --file schema_check.yaml

# Full Pytest suite across Stages 1-13
.\.venv\Scripts\python.exe -m pytest -v

# Frontend ESLint & production bundle verification
cd ..\frontend
npm run lint
npm run build
```

