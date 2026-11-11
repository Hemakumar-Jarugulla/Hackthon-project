# AttributionIQ — Multi-Touch Attribution Logic, ROI Formulas & Data Quality Rules

## 1. Eligibility & Isolation Rules (Zero Revenue Double-Counting)
Before distributing revenue credit for a customer `Order`, `apps.attribution.services.attribution_validator` enforces:
1. **Valid Order Eligibility (Problem 1 — Duplicate Revenue Protection):**
   Only `Order` rows with `verification_status == 'Valid'` and `payment_status == 'Paid'` are attributed. Duplicate, refunded, pending, or failed orders are excluded and tallied in `excluded_duplicate_orders` / `excluded_other_orders`.
2. **Touchpoint Chronology & Window Eligibility (Problem 2 — Post-Conversion Isolation):**
   A `Touchpoint` is eligible for an order only if:
   - `is_post_conversion == False` and `is_valid == True`
   - `timestamp <= conversion_cutoff` (`23:59:59 UTC` of `order_date`)
   - `timestamp >= conversion_cutoff - timedelta(days=conversion_window_days)` (default `90` days)
3. **Verified Identity Evidence (Problem 5 — Unverified Session Link Protection):**
   Touchpoints attached to a `WebSession` with `identity_status == 'Unverified Link'` or `has_evidence == False` are excluded from credit allocation (`excluded_unverified_session_touches`).
4. **Order Sorting & Tie-Breaking:**
   Eligible touchpoints are sorted deterministically by `(timestamp, id)`.

---

## 2. Five Attribution Weight Methodologies
Every model normalizes weights using `Decimal(7,6)` so $\sum_i w_i = 1.000000$ and allocates revenue via largest-remainder rounding so attributed revenue sums to `Order.revenue` to the exact cent:

| Model Code | Rule Summary | Formula (`N` eligible touchpoints) |
| :--- | :--- | :--- |
| `first_touch` | 100% First Touch | $w_0 = 1.0$, $w_{i>0} = 0$ |
| `last_touch` | 100% Last Touch | $w_{N-1} = 1.0$, $w_{i<N-1} = 0$ |
| `linear` | Uniform Share | $w_i = \frac{1}{N}$ |
| `time_decay` | Exponential Half-Life (`half_life_days = 7`) | $\text{raw}_i = 2^{-\frac{\text{age\_days}_i}{\text{half\_life\_days}}},\quad w_i = \frac{\text{raw}_i}{\sum_j \text{raw}_j}$ |
| `position_based` | U-Shaped (40 / 20 / 40) | $N=1 \Rightarrow 1.0$; $N=2 \Rightarrow (0.5, 0.5)$; $N \ge 3 \Rightarrow w_0=0.4,\ w_{N-1}=0.4,\ w_{1..N-2}=\frac{0.2}{N-2}$ |

---

## 3. Financial ROI, ROAS & Funnel Formulas
Computed inside `apps.analytics.services.metrics` & `roi_analytics.py`:
- **Verified Marketing Spend:** Only `CostRecord` items whose `currency == Campaign.currency` are summed into `marketing_spend`. Cross-currency spend rows (`CostRecord.currency != Campaign.currency`) are surfaced separately via `mismatched_spend_by_currency` and flagged (**Problem 3**).
- **Omitted Cost Flag (Problem 4):** `missing_cost_alert = True` when `is_paid_campaign == True`, `budget > 0`, `marketing_spend == 0`, and touchpoints or leads exist.
- **ROI (%):** $\frac{\text{Attributed Revenue} - \text{Marketing Spend}}{\text{Marketing Spend}} \times 100$ (`null` when `Marketing Spend == 0`)
- **ROAS (x):** $\frac{\text{Attributed Revenue}}{\text{Marketing Spend}}$ (`null` when `Marketing Spend == 0`)
- **CPL:** $\frac{\text{Marketing Spend}}{\text{Total Leads}}$ (`null` when `Total Leads == 0`)
- **Conversion Rate (%):** $\frac{\text{Converted Leads}}{\text{Total Leads}} \times 100$
- **AOV:** $\frac{\text{Actual Closed Valid Revenue}}{\text{Valid Paid Order Count}}$

---

## 4. 11-Rule Validation Framework (`VAL-01` .. `VAL-11`)
Executed via API (`POST /api/v1/validation/run/`) or CLI (`python manage.py validate_marketing_data --strict`):
- `VAL-01`: Deterministic primary-key format validation across domain tables
- `VAL-02`: Contact FK consistency across `Lead -> Opportunity -> Order`
- `VAL-03`: Valid enum choices and Opportunity `Won`/`Closed Won` stage-status alignment
- `VAL-04`: Date-range chronological bounds (`Campaign.end_date >= start_date`, etc.)
- `VAL-05`: Non-negative financial & revenue arithmetic
- `VAL-06`: Paid campaign missing-cost & non-negative cost audit
- `VAL-07`: CostRecord vs Campaign currency consistency check
- `VAL-08`: Lead & Contact lifecycle transition integrity
- `VAL-09`: Duplicate order quarantine check
- `VAL-10`: Stored AttributionResult credit conservation ($100\%$ weights & cent-exact revenue reconciliation)
- `VAL-11`: Post-conversion touchpoint & unverified anonymous session linkage isolation check

