# AttributionIQ — Domain & Synthetic Dataset Dictionary

## 1. Synthetic Benchmark Presets (`data_generator`)
Generated deterministically via:
```bash
python manage.py generate_marketing_data --mode <starter|full> --seed 20261022
```

| Entity | `starter` Mode | `full` Mode | Primary Key Prefix |
| :--- | ---: | ---: | :--- |
| Channels (`channels_channel`) | 8 | 8 | `CHN-2026-` |
| Campaigns (`campaigns_campaign`) | 15 | 500 | `CMP-2026-` |
| Creatives (`creatives_creative`) | 20 | 150 | `CRT-2026-` |
| Audiences (`audiences_audience`) | 10 | 50 | `AUD-2026-` |
| Contacts (`contacts_contact`) | 60 | 50,000 | `CON-2026-` |
| Web Sessions (`web_sessions_session`) | 120 + unverified | 65,000 + unverified | `SES-2026-` |
| Touchpoints (`touchpoints_touchpoint`) | 220 + anomalies | 200,000 + anomalies | `TOUCH-<CON>-` |
| Leads (`leads_lead`) | 40 | 16,000 | `LEAD-2026-` |
| Opportunities (`opportunities_opportunity`) | 28 | 10,000 | `OPP-2026-` |
| Orders (`orders_order`) | Closed Won + dups | Closed Won + dups | `ORD-2026-` |
| Cost Records (`costs_cost_record`) | 3/paid + FX mismatch | 3/paid + FX mismatch | `COST-2026-` |

> **Leakage Prevention Guarantee:** Ground-truth anomaly manifests are written solely to `source_manifest.json` (`ground_truth_anomaly_manifest`) and never injected onto domain model tables or exported CSV/JSON dataset rows.

---

## 2. Entity Field Reference

### Campaigns & Taxonomy
- **Channel (`channels_channel`):** `id`, `name` (unique), `channel_type` (`Paid Search`, `Paid Social`, `Email`, `Display`, `Events & Webinars`, `Organic`, `Direct`, `Referral`), `status` (`Active`, `Inactive`), `owner`, `description`.
- **Campaign (`campaigns_campaign`):** `id`, `name`, `channel`, `budget` (`Decimal(14,2)`), `currency` (`USD`, `EUR`, `GBP`), `start_date`, `end_date`, `objective`, `status` (`Active`, `Paused`, `Completed`, `Draft`, `Archived`), `is_paid_campaign`, M2M `creatives` & `audiences`.
- **Creative (`creatives_creative`):** `id`, `name`, `primary_campaign`, `creative_type`, `start_date`, `end_date`, `status`.
- **Audience (`audiences_audience`):** `id`, `name` (unique), `audience_type`, `estimated_size`, `criteria`, `status`, `effective_from`, `effective_to`.

### Journey & Funnel
- **Contact (`contacts_contact`):** `id`, `name`, `email` (unique), `phone`, `company`, `source`, `created_date`, `lifecycle_status` (`Subscriber`, `Lead`, `Opportunity`, `Customer`).
- **WebSession (`web_sessions_session`):** `id`, `anonymous_id`, `contact` (nullable), `campaign` (nullable), `landing_page`, `referrer`, `timestamp`, `device_type`, `identity_status` (`Identified`, `Anonymous`, `Unverified Link`), `has_evidence`, `evidence_type`, `linking_issue`.
- **Touchpoint (`touchpoints_touchpoint`):** `id`, `contact`, `campaign` (nullable), `channel`, `creative`, `session`, `interaction_type`, `timestamp`, `device`, `is_online`, `source`, `is_post_conversion`, `is_valid`, `validation_notes`.
- **Lead (`leads_lead`):** `id`, `contact`, `campaign`, `source`, `score` (`0..100`), `created_date`, `status` (`New`, `MQL`, `SQL`, `Converted`, `Disqualified`), `converted_at`.
- **Opportunity (`opportunities_opportunity`):** `id`, `lead`, `contact`, `name`, `stage` (`New`, `Qualification`, `Proposal`, `Negotiation`, `Closed Won`, `Closed Lost`), `expected_revenue`, `actual_revenue`, `closing_date`, `status` (`Open`, `Won`, `Lost`).

### Revenue, Spend, Attribution & Governance
- **Order (`orders_order`):** `id`, `opportunity`, `contact`, `order_date`, `revenue`, `currency`, `payment_status` (`Paid`, `Pending`, `Refunded`, `Failed`), `verification_status` (`Valid`, `Duplicate`, `Invalid`, `Pending Review`), `notes`.
- **CostRecord (`costs_cost_record`):** `id`, `campaign`, `channel`, `category`, `amount`, `currency`, `spend_date`, `description`.
- **AttributionModel (`attribution_model`):** `id` (`first_touch`, `last_touch`, `linear`, `time_decay`, `position_based`), `name`, `rule_version`, `config` (JSON), `is_active`.
- **AttributionRun / AttributionResult:** Stores parameters (`conversion_window_days`, `half_life_days`), exclusion counters, penny-exact `credit_weight` (`Decimal(7,6)`), and `attributed_revenue`.
- **DataException (`exceptions_data_exception`):** `id`, `issue_type` (5 anomaly types), `entity_type`, `entity_id`, `severity`, `description`, `expected_decision`, `actual_decision`, `resolution_status` (`Open`, `Reviewed`, `Resolved`, `Ignored`), `resolved_by`, `resolved_at`, `resolution_notes`.
- **ValidationRun / ValidationCheckResult:** Tracks `VAL-01` through `VAL-11` outcomes, `records_checked`, `failed_records`, `status` (`Passed`, `Warning`, `Failed`).

