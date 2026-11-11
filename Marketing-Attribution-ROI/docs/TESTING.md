# AttributionIQ — Test Suite & Verification Guide

This document inventories the automated test suites and verification checks across the AttributionIQ backend (`backend/`) and frontend (`frontend/`).

---

## 1. Included Backend Test Suites (`36` Tests Across `backend/tests/`)

All backend verification suites live in `backend/tests/` and are configured via [`backend/pytest.ini`](../backend/pytest.ini):

| Stage | Test File | Tests | Scope Covered |
| --- | --- | :---: | --- |
| Stage 1 | [`test_stage1_setup.py`](../backend/tests/test_stage1_setup.py) | 8 | Django system check, health & OpenAPI/Swagger endpoints, root redirect, CORS Vite origin, ID formatting, error envelope formatting, and math helpers. |
| Stage 2 | [`test_stage2_setup.py`](../backend/tests/test_stage2_setup.py) | 5 | `check_db` management command, zero pending migrations, all 18 domain apps registered, strict MySQL `utf8mb4` config, and DB health diagnostics. |
| Stage 3 | [`test_stage3_models.py`](../backend/tests/test_stage3_models.py) | 2 | Full relational hierarchy, deterministic ID sequences, seed collision prevention, and database constraints. |
| Stage 4 | [`test_stage4_auth_rbac.py`](../backend/tests/test_stage4_auth_rbac.py) | 3 | User registration, JWT login/claims/refresh rotation/logout blacklisting, profile role-escalation guard, Admin user management, and RBAC. |
| Stage 5 | [`test_stage5_marketing_apis.py`](../backend/tests/test_stage5_marketing_apis.py) | 2 | Channels, Campaigns, Creatives, and Audiences CRUD, M2M validation, archiving, live ROI, FX mismatch alerts, and missing-cost alerts. |
| Stage 6 | [`test_stage6_customer_tracking_apis.py`](../backend/tests/test_stage6_customer_tracking_apis.py) | 3 | Contacts lifecycle & protected deletes, WebSessions identity evidence rules, Touchpoints, and chronological Customer Journey API. |
| Stage 7 | [`test_stage7_funnel_financial_apis.py`](../backend/tests/test_stage7_funnel_financial_apis.py) | 3 | Leads & Opportunities stage history, Orders duplicate-revenue guard & protected delete, and Costs ledger FX filters. |
| Stage 8 | [`test_stage8_attribution_engine.py`](../backend/tests/test_stage8_attribution_engine.py) | 3 | All 5 attribution models (First Touch, Last Touch, Linear, Time Decay, Position Based) + penny-exact conservation, post-conversion/invalid exclusions, offline & unlinked touchpoints, API persistence, and RBAC. |
| Stage 9 | [`test_stage9_analytics_apis.py`](../backend/tests/test_stage9_analytics_apis.py) | 2 | Dashboard/ROI analytics APIs, FX guards, Pandas trend calculations, and zero-spend ROI edge cases. |
| Stage 10 | [`test_stage10_exceptions_validation_audit.py`](../backend/tests/test_stage10_exceptions_validation_audit.py) | 1 | Five anomaly families, exception triage workflow, 11-rule validation framework, and audit log APIs. |
| Stage 11 | [`test_stage11_generator_exports.py`](../backend/tests/test_stage11_generator_exports.py) | 1 | Deterministic data generation, SHA-256 reproducibility, CSV/JSON/SQL export bundle, and `/api/v1/reports/` endpoints. |
| Stage 12 | [`test_stage12_api_contract.py`](../backend/tests/test_stage12_api_contract.py) | 1 | React frontend CORS, SimpleJWT auth lifecycle, and paginated API contracts. |
| Stage 13 | [`test_stage13_deployment_docs.py`](../backend/tests/test_stage13_deployment_docs.py) | 2 | Dockerfiles, `docker-compose.yml`, `.env.example`, docs/SQL deliverables existence, and production settings hardening. |

**Total Backend Tests:** `36`

---

## 2. Frontend Verification Status

* **Linting & Build:** Configured in [`frontend/package.json`](../frontend/package.json):
  * `npm run lint` (`eslint .`) — verifies JSX hooks, imports, and code quality with `0` errors.
  * `npm run build` (`vite build`) — compiles and bundles the production React application (`2605` modules).
* **API Integration Coverage:** Cross-verified end-to-end against Django via [`backend/tests/test_stage12_api_contract.py`](../backend/tests/test_stage12_api_contract.py) covering Vite CORS headers, JWT token rotation, snake/camel endpoint contracts, and pagination.
* **UI Component Unit Tests:** There are no separate Jest or Vitest component unit tests configured in `frontend/` (`package.json` defines `dev`, `build`, `lint`, and `preview`).

---

## 3. Running Verification Commands (Windows PowerShell)

### Backend Checks & Full Pytest Suite
```powershell
cd c:\CandidateWorkspace\Marketing-Attribution-ROI\backend

# Core Django & migration sanity checks
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py spectacular --validate --fail-on-warn --no-color

# Run all 36 tests across Stages 1-13
.\.venv\Scripts\python.exe -m pytest -v

# Example: run a single stage suite
.\.venv\Scripts\python.exe -m pytest tests\test_stage8_attribution_engine.py -v
```

### Frontend Lint & Build
```powershell
cd c:\CandidateWorkspace\Marketing-Attribution-ROI\frontend

npm run lint
npm run build
```

