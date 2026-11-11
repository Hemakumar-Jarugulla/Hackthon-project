# AttributionIQ — REST API Documentation (`/api/v1/`)

Interactive OpenAPI / Swagger documentation is served automatically at `/api/docs/` and `/api/schema/`.

## 1. Conventions
- **Authentication:** Bearer SimpleJWT (`Authorization: Bearer <access_token>`)
- **Standard Object Envelope:**
  ```json
  { "success": true, "message": "...", "data": { ... } }
  ```
- **Standard Error Envelope:**
  ```json
  { "success": false, "error": { "code": "...", "message": "...", "details": { ... } } }
  ```
- **Paginated Collection Envelope (`page`, `page_size <= 100`):**
  ```json
  { "count": 60, "total_pages": 1, "current_page": 1, "page_size": 100, "next": null, "previous": null, "results": [ ... ] }
  ```
- **RBAC Tiers:** `Admin` > `Marketing Manager` > `Marketing Analyst` > `Viewer`.

---

## 2. Endpoints by Domain

### Health & Authentication
| Method | Endpoint | Access | Notes |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/health/` | Public | DB status, API prefix, attribution defaults |
| `POST` | `/api/v1/auth/register/` | Public | Self-register (`Viewer` or `Marketing Analyst`) |
| `POST` | `/api/v1/auth/login/` | Public | Returns `{ user, access, refresh }` |
| `POST` | `/api/v1/auth/refresh/` | Public | Rotates SimpleJWT refresh/access tokens |
| `POST` | `/api/v1/auth/logout/` | Authenticated | Blacklists refresh token & records audit log |
| `GET`/`PATCH` | `/api/v1/auth/me/`, `/api/v1/auth/profile/` | Authenticated | Read/update own profile |
| `POST` | `/api/v1/auth/change-password/` | Authenticated | Verified password change |
| `POST` | `/api/v1/auth/forgot-password/` | Public | Non-enumerating password reset token generation |
| `POST` | `/api/v1/auth/reset-password/` | Public | Reset password with `uid` + `token` |
| `GET` | `/api/v1/auth/roles/` | Authenticated | RBAC permission matrix |
| `CRUD` | `/api/v1/users/` | Admin | Manage workspace accounts & roles |

### Marketing Entities
| Prefix | Actions | Notes |
| :--- | :--- | :--- |
| `/api/v1/channels/` | `CRUD` | Channel performance rollups |
| `/api/v1/campaigns/` | `CRUD`, `POST /{id}/assign-creatives/`, `assign-audiences/`, `GET /{id}/history/` | Live attributed revenue & missing-cost flags |
| `/api/v1/creatives/` | `CRUD` | Asset types & primary campaign links |
| `/api/v1/audiences/` | `CRUD` | Target segments & estimated reach |

### Customer Journey, Sales & Financial Ledger
| Prefix | Actions | Notes |
| :--- | :--- | :--- |
| `/api/v1/contacts/` | `CRUD`, `GET /{id}/journey/`, `GET /{id}/lifecycle/` | Accepts `?model_id=` or `?modelId=` |
| `/api/v1/sessions/` | `CRUD` | Tracks `identity_status` & `has_evidence` |
| `/api/v1/touchpoints/` | `CRUD` | Chronological interactions & `is_post_conversion` |
| `/api/v1/leads/` | `CRUD`, `GET /{id}/history/` | Lead scoring & qualification transitions |
| `/api/v1/opportunities/` | `CRUD`, `GET /{id}/history/` | 6-stage pipeline transitions |
| `/api/v1/orders/` | `CRUD`, `POST /{id}/mark-duplicate/` | Non-destructive duplicate quarantine |
| `/api/v1/costs/` | `CRUD` | Spend items & FX currency mismatch detection |

### Attribution Engine, Analytics & Governance
| Method | Endpoint | Notes |
| :--- | :--- | :--- |
| `GET`/`PUT`/`PATCH` | `/api/v1/attribution/models/` | 5 seeded attribution methodologies |
| `GET`/`POST` | `/api/v1/attribution/run/`, `/api/v1/attribution/calculate/` | Execute/preview single model run (`GET` previews, `POST` persists) |
| `GET` | `/api/v1/attribution/compare/` | Side-by-side 5-model campaign & channel comparison |
| `GET` | `/api/v1/attribution/runs/`, `/results/` | Persisted audit run history & per-touchpoint credits |
| `GET` | `/api/v1/analytics/dashboard/` | Unified KPIs, 7 charts & 6 dashboard widgets |
| `GET` | `/api/v1/analytics/roi/`, `/overview/` | Overall KPIs, campaign/channel ROI, FX mismatch alerts |
| `GET` | `/api/v1/analytics/campaigns/`, `/campaign-performance/` | Campaign spend vs attributed revenue ranking |
| `GET` | `/api/v1/analytics/channels/`, `/channel-performance/` | Channel attribution share & unit economics |
| `GET` | `/api/v1/analytics/creatives/`, `/audiences/` | Creative & Audience performance |
| `GET` | `/api/v1/analytics/funnel/`, `/conversion-funnel/` | Lead & 6-stage Opportunity funnel telemetry |
| `GET` | `/api/v1/analytics/trends/`, `/revenue-trends/` | Monthly series & Pandas/NumPy trend statistics |
| `GET` | `/api/v1/exceptions/`, `/summary/` | Filterable exceptions & severity breakdown |
| `POST` | `/api/v1/exceptions/scan/` | Run 5-anomaly detector idempotently |
| `POST`/`PATCH` | `/api/v1/exceptions/{id}/resolve/`, `/reopen/` | Audited triage workflow |
| `GET`/`POST` | `/api/v1/validation/report/`, `/run/`, `/history/` | 11-rule validation telemetry |
| `GET` | `/api/v1/audit/` | Immutable security/action audit stream (`Marketing Analyst`+) |
| `GET` | `/api/v1/reports/datasets/`, `/export/csv/`, `/export/json/` | Downloadable UTF-8 CSV (formula-neutralized) & JSON exports |

