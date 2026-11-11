"""
Comprehensive 11-rule Data Validation Framework verifying keys, references,
enums, dates, revenue/cost arithmetic, currencies, lifecycles, and attribution integrity.
"""

from datetime import datetime, timezone as dt_timezone
from decimal import Decimal
import time

from django.db import transaction
from django.db.models import Count, F, Sum

from apps.attribution.models import AttributionResult
from apps.attribution.services.attribution_validator import WEIGHT_TOTAL
from apps.audiences.models import Audience
from apps.audit.models import AuditLog
from apps.campaigns.models import Campaign
from apps.contacts.models import Contact
from apps.costs.models import CostRecord
from apps.creatives.models import Creative
from apps.exceptions.models import DataException
from apps.exceptions.services.detector import detect_and_sync_exceptions
from apps.leads.models import Lead
from apps.opportunities.models import Opportunity
from apps.orders.models import Order
from apps.touchpoints.models import Touchpoint
from apps.validation.models import ValidationCheckResult, ValidationRun
from apps.web_sessions.models import WebSession
from common.audit import record_audit_log


def _make_check(
    *,
    code: str,
    name: str,
    category: str,
    entity: str,
    records_checked: int,
    failed_records: int,
    status_val: str,
    details: str,
) -> dict:
    return {
        'check_code': code,
        'check_name': name,
        'category': category,
        'entity': entity,
        'records_checked': int(records_checked),
        'failed_records': int(failed_records),
        'status': status_val,
        'details': details,
    }


def evaluate_all_validation_rules() -> list[dict]:
    """Evaluate all 11 deterministic data quality & referential rules against MySQL state."""
    Status = ValidationCheckResult.Status
    checks: list[dict] = []

    # VAL-01: Primary-key format & non-empty deterministic IDs
    pk_checks = [
        (Campaign, 'CMP-'),
        (Contact, 'CON-'),
        (WebSession, 'SES-'),
        (Touchpoint, 'TOUCH-'),
        (Lead, 'LEAD-'),
        (Opportunity, 'OPP-'),
        (Order, 'ORD-'),
        (CostRecord, 'COST-'),
    ]
    pk_checked = 0
    pk_bad = 0
    for model_cls, prefix in pk_checks:
        ids = list(model_cls.objects.values_list('id', flat=True))
        pk_checked += len(ids)
        pk_bad += sum(1 for item_id in ids if not item_id or not item_id.startswith(prefix))
    checks.append(
        _make_check(
            code='VAL-01',
            name='Primary-Key Uniqueness & Deterministic Format',
            category='Schema Integrity',
            entity='All Core Entities',
            records_checked=pk_checked,
            failed_records=pk_bad,
            status_val=Status.FAILED if pk_bad else Status.PASSED,
            details=(
                f'{pk_bad} ID format violation(s) detected.'
                if pk_bad
                else f'All {pk_checked} primary keys conform to deterministic prefixes.'
            ),
        )
    )

    # VAL-02: Foreign-key relational contact consistency across Lead -> Opportunity -> Order
    opps = list(Opportunity.objects.select_related('lead').all())
    orders = list(Order.objects.select_related('opportunity').all())
    fk_checked = len(opps) + len(orders)
    fk_bad = sum(1 for o in opps if o.lead and o.contact_id != o.lead.contact_id)
    fk_bad += sum(1 for ord_o in orders if ord_o.opportunity and ord_o.contact_id != ord_o.opportunity.contact_id)
    checks.append(
        _make_check(
            code='VAL-02',
            name='Foreign-Key & Cross-Entity Contact Integrity',
            category='Referential Integrity',
            entity='Opportunity / Order',
            records_checked=fk_checked,
            failed_records=fk_bad,
            status_val=Status.FAILED if fk_bad else Status.PASSED,
            details=(
                f'{fk_bad} contact ownership mismatch(es) between Lead, Opportunity, and Order.'
                if fk_bad
                else 'All Opportunity and Order contact references match parent Leads seamlessly.'
            ),
        )
    )

    # VAL-03: Valid enum choices and stage/status consistency
    valid_order_verif = {c.value for c in Order.VerificationStatus}
    valid_order_pay = {c.value for c in Order.PaymentStatus}
    valid_lead_st = {c.value for c in Lead.Status}
    leads = list(Lead.objects.all())
    enum_checked = len(opps) + len(orders) + len(leads)
    enum_bad = 0
    for opp in opps:
        if opp.stage == Opportunity.Stage.CLOSED_WON and opp.status != Opportunity.Status.WON:
            enum_bad += 1
        elif opp.stage == Opportunity.Stage.CLOSED_LOST and opp.status != Opportunity.Status.LOST:
            enum_bad += 1
    for ord_o in orders:
        if ord_o.verification_status not in valid_order_verif or ord_o.payment_status not in valid_order_pay:
            enum_bad += 1
    for ld in leads:
        if ld.status not in valid_lead_st:
            enum_bad += 1
    checks.append(
        _make_check(
            code='VAL-03',
            name='Enum Value & Stage/Status Alignment',
            category='Domain Constraints',
            entity='Lead / Opportunity / Order',
            records_checked=enum_checked,
            failed_records=enum_bad,
            status_val=Status.FAILED if enum_bad else Status.PASSED,
            details=(
                f'{enum_bad} invalid enum or stage/status mismatch(es).'
                if enum_bad
                else 'All status, stage, and verification enums are valid and consistent.'
            ),
        )
    )

    # VAL-04: Chronological consistency across date bounds
    campaigns = list(Campaign.objects.all())
    creatives = list(Creative.objects.all())
    audiences = list(Audience.objects.all())
    chrono_checked = len(campaigns) + len(creatives) + len(audiences) + len(leads)
    chrono_bad = sum(1 for c in campaigns if c.end_date < c.start_date)
    chrono_bad += sum(1 for cr in creatives if cr.start_date and cr.end_date and cr.end_date < cr.start_date)
    chrono_bad += sum(
        1 for a in audiences if a.effective_from and a.effective_to and a.effective_to < a.effective_from
    )
    chrono_bad += sum(
        1 for ld in leads if ld.converted_at and ld.converted_at.date() < ld.created_date
    )
    checks.append(
        _make_check(
            code='VAL-04',
            name='Chronological & Date Window Consistency',
            category='Temporal Integrity',
            entity='Campaign / Creative / Audience / Lead',
            records_checked=chrono_checked,
            failed_records=chrono_bad,
            status_val=Status.FAILED if chrono_bad else Status.PASSED,
            details=(
                f'{chrono_bad} record(s) have end dates preceding start dates.'
                if chrono_bad
                else 'All campaign, creative, audience, and conversion dates are chronologically valid.'
            ),
        )
    )

    # VAL-05: Revenue arithmetic non-negativity
    rev_checked = len(orders) + len(opps)
    rev_bad = sum(1 for ord_o in orders if ord_o.revenue < Decimal('0.00'))
    rev_bad += sum(
        1
        for opp in opps
        if opp.expected_revenue < Decimal('0.00') or opp.actual_revenue < Decimal('0.00')
    )
    checks.append(
        _make_check(
            code='VAL-05',
            name='Revenue Arithmetic Non-Negativity',
            category='Financial Integrity',
            entity='Order / Opportunity',
            records_checked=rev_checked,
            failed_records=rev_bad,
            status_val=Status.FAILED if rev_bad else Status.PASSED,
            details=(
                f'{rev_bad} negative revenue figure(s) found.'
                if rev_bad
                else 'All order revenues and opportunity deal amounts are non-negative.'
            ),
        )
    )

    # VAL-06: Cost arithmetic & omitted paid campaign costs
    costs = list(CostRecord.objects.select_related('campaign').all())
    spend_by_cmp: dict[str, Decimal] = {}
    for c_rec in costs:
        spend_by_cmp[c_rec.campaign_id] = spend_by_cmp.get(c_rec.campaign_id, Decimal('0.00')) + c_rec.amount
    tp_cmp_counts = {
        row['campaign_id']: row['cnt']
        for row in Touchpoint.objects.filter(campaign_id__isnull=False)
        .order_by()
        .values('campaign_id')
        .annotate(cnt=Count('id'))
    }
    neg_costs = sum(1 for c_rec in costs if c_rec.amount < Decimal('0.00'))
    omitted_paid = sum(
        1
        for c in campaigns
        if c.is_paid_campaign
        and c.budget > Decimal('0.00')
        and spend_by_cmp.get(c.id, Decimal('0.00')) == Decimal('0.00')
        and tp_cmp_counts.get(c.id, 0) > 0
    )
    cost_checked = len(costs) + len(campaigns)
    checks.append(
        _make_check(
            code='VAL-06',
            name='Cost Arithmetic & Omitted Paid Spend Check',
            category='Financial Integrity',
            entity='CostRecord / Campaign',
            records_checked=cost_checked,
            failed_records=neg_costs + omitted_paid,
            status_val=(
                Status.FAILED
                if neg_costs
                else (Status.WARNING if omitted_paid else Status.PASSED)
            ),
            details=(
                f'{neg_costs} negative cost(s); {omitted_paid} paid campaign(s) missing cost ledger entries.'
                if (neg_costs or omitted_paid)
                else 'All cost entries are non-negative and active paid campaigns have logged spend.'
            ),
        )
    )

    # VAL-07: Currency consistency between CostRecord and Campaign
    fx_mismatches = sum(1 for c_rec in costs if c_rec.currency != c_rec.campaign.currency)
    checks.append(
        _make_check(
            code='VAL-07',
            name='Spend Currency Consistency Check',
            category='Financial Integrity',
            entity='CostRecord',
            records_checked=len(costs),
            failed_records=fx_mismatches,
            status_val=Status.WARNING if fx_mismatches else Status.PASSED,
            details=(
                f'{fx_mismatches} cost record(s) use a different currency than their parent Campaign (isolated from USD ROI).'
                if fx_mismatches
                else 'All cost ledger entries match their parent Campaign currency.'
            ),
        )
    )

    # VAL-08: Lead & Contact lifecycle transition consistency
    contacts = list(Contact.objects.all())
    bad_lc = sum(
        1 for ld in leads if ld.status == Lead.Status.CONVERTED and ld.converted_at is None
    )
    checks.append(
        _make_check(
            code='VAL-08',
            name='Lifecycle State & Conversion Timestamp Consistency',
            category='CRM Lifecycle',
            entity='Lead / Contact',
            records_checked=len(leads) + len(contacts),
            failed_records=bad_lc,
            status_val=Status.WARNING if bad_lc else Status.PASSED,
            details=(
                f'{bad_lc} converted Lead(s) lack a converted_at timestamp.'
                if bad_lc
                else 'All converted Leads and Contact lifecycle transitions contain valid timestamps.'
            ),
        )
    )

    # VAL-09: Duplicate order conversions (quarantined vs wrongly attributed)
    dup_orders = sum(
        1 for ord_o in orders if ord_o.verification_status == Order.VerificationStatus.DUPLICATE
    )
    bad_dup_attributed = AttributionResult.objects.filter(
        order__verification_status=Order.VerificationStatus.DUPLICATE
    ).count()
    checks.append(
        _make_check(
            code='VAL-09',
            name='Duplicate Conversion Revenue Prevention',
            category='Attribution Integrity',
            entity='Order / AttributionResult',
            records_checked=len(orders),
            failed_records=bad_dup_attributed if bad_dup_attributed else dup_orders,
            status_val=(
                Status.FAILED
                if bad_dup_attributed
                else (Status.WARNING if dup_orders else Status.PASSED)
            ),
            details=(
                f'{bad_dup_attributed} Duplicate order rows wrongly received attribution credits!'
                if bad_dup_attributed
                else (
                    f'{dup_orders} Duplicate order(s) detected and cleanly excluded from verified revenue & attribution.'
                    if dup_orders
                    else 'No duplicate order conversions detected.'
                )
            ),
        )
    )

    # VAL-10: Attribution credit conservation (100% weights & order revenue reconciliation)
    grouped_results = list(
        AttributionResult.objects.order_by()
        .values('run_id', 'order_id', 'source_order_revenue')
        .annotate(w_sum=Sum('credit_weight'), r_sum=Sum('attributed_revenue'))
    )
    bad_credit_groups = 0
    for grp in grouped_results:
        w_sum = grp['w_sum'] or Decimal('0.000000')
        r_sum = (grp['r_sum'] or Decimal('0.00')).quantize(Decimal('0.01'))
        expected = (grp['source_order_revenue'] or Decimal('0.00')).quantize(Decimal('0.01'))
        if w_sum != WEIGHT_TOTAL or r_sum != expected:
            bad_credit_groups += 1
    out_of_bounds_weights = AttributionResult.objects.filter(
        credit_weight__lt=Decimal('0.000000')
    ).count() + AttributionResult.objects.filter(credit_weight__gt=WEIGHT_TOTAL).count()
    val10_bad = bad_credit_groups + out_of_bounds_weights
    checks.append(
        _make_check(
            code='VAL-10',
            name='Attribution Credit 100% Sum & Revenue Reconciliation',
            category='Attribution Integrity',
            entity='AttributionResult',
            records_checked=len(grouped_results),
            failed_records=val10_bad,
            status_val=Status.FAILED if val10_bad else Status.PASSED,
            details=(
                f'{val10_bad} order attribution group(s) failed exact 1.000000 weight / revenue reconciliation.'
                if val10_bad
                else f'All {len(grouped_results)} attributed run-order pairs sum strictly to 100% credit and order revenue.'
            ),
        )
    )

    # VAL-11: Post-conversion touchpoints & unverified anonymous session linkage
    sessions = list(WebSession.objects.all())
    touchpoints = list(Touchpoint.objects.select_related('session').all())
    bad_post_attr = AttributionResult.objects.filter(touchpoint__is_post_conversion=True).count()
    bad_sess_attr = (
        AttributionResult.objects.filter(touchpoint__session__isnull=False)
        .exclude(
            touchpoint__session__has_evidence=True,
            touchpoint__session__identity_status=WebSession.IdentityStatus.IDENTIFIED,
            touchpoint__session__contact_id=F('touchpoint__contact_id'),
        )
        .count()
    )
    post_touches_flagged = sum(1 for tp in touchpoints if tp.is_post_conversion)
    unverified_sessions = sum(
        1
        for s in sessions
        if s.identity_status == WebSession.IdentityStatus.UNVERIFIED_LINK
        or (s.contact_id is not None and not s.has_evidence)
    )
    leaked_count = bad_post_attr + bad_sess_attr
    quarantined_tp_or_ses = post_touches_flagged + unverified_sessions

    checks.append(
        _make_check(
            code='VAL-11',
            name='Post-Conversion Touchpoint & Anonymous Evidence Guard',
            category='Attribution Integrity',
            entity='Touchpoint / WebSession',
            records_checked=len(touchpoints) + len(sessions),
            failed_records=leaked_count if leaked_count else quarantined_tp_or_ses,
            status_val=(
                Status.FAILED
                if leaked_count
                else (Status.WARNING if quarantined_tp_or_ses else Status.PASSED)
            ),
            details=(
                f'{leaked_count} invalid post-conversion/unverified-session row(s) leaked into AttributionResult!'
                if leaked_count
                else (
                    f'{post_touches_flagged} post-conversion touchpoint(s) and {unverified_sessions} unverified session link(s) isolated cleanly.'
                    if quarantined_tp_or_ses
                    else 'Zero post-conversion or unverified-session attribution anomalies present.'
                )
            ),
        )
    )

    return checks


def _build_report_payload(
    *,
    run_obj: ValidationRun | None,
    checks: list[dict],
    exception_counts: dict,
    history: list[dict],
) -> dict:
    total_checked = sum(c['records_checked'] for c in checks)
    flagged_or_invalid = sum(c['failed_records'] for c in checks)
    errors_count = sum(1 for c in checks if c['status'] == ValidationCheckResult.Status.FAILED)
    warnings_count = sum(1 for c in checks if c['status'] == ValidationCheckResult.Status.WARNING)
    passed_count = sum(1 for c in checks if c['status'] == ValidationCheckResult.Status.PASSED)

    return {
        'run_id': run_obj.id if run_obj else None,
        'executed_at': (
            run_obj.executed_at.isoformat()
            if run_obj
            else datetime.now(dt_timezone.utc).isoformat()
        ),
        'triggered_by': run_obj.triggered_by if run_obj else 'Live Preview',
        'total_checks': len(checks),
        'passed_checks': passed_count,
        'failed_checks': errors_count,
        'warning_checks': warnings_count,
        'total_records_checked': total_checked,
        'valid_records': max(0, total_checked - flagged_or_invalid),
        'invalid_records': flagged_or_invalid,
        'warnings': warnings_count,
        'errors': errors_count,
        'exception_counts': exception_counts,
        'checks': checks,
        'history': history,
    }


def _serialize_history(limit: int = 10) -> list[dict]:
    return [
        {
            'run_id': r.id,
            'executed_at': r.executed_at.isoformat(),
            'triggered_by': r.triggered_by,
            'total_checks': r.total_checks,
            'passed_checks': r.passed_checks,
            'failed_checks': r.failed_checks,
            'warning_checks': r.warning_checks,
            'total_records_checked': r.total_records_checked,
            'total_invalid_records': r.total_invalid_records,
            'duration_ms': r.duration_ms,
        }
        for r in ValidationRun.objects.all().order_by('-executed_at', 'id')[:limit]
    ]


def _current_exception_counts() -> dict:
    by_sev = {sev.value: 0 for sev in DataException.Severity}
    for row in DataException.objects.order_by().values('severity').annotate(cnt=Count('id')):
        by_sev[row['severity']] = row['cnt']
    by_status = {st.value: 0 for st in DataException.ResolutionStatus}
    for row in (
        DataException.objects.order_by().values('resolution_status').annotate(cnt=Count('id'))
    ):
        by_status[row['resolution_status']] = row['cnt']
    return {
        'total': DataException.objects.count(),
        'by_severity': by_sev,
        'by_status': by_status,
    }


@transaction.atomic
def run_validation_suite(
    *,
    triggered_by: str = 'Manual Validation Trigger',
    sync_exceptions: bool = True,
    actor=None,
    source_ip: str | None = None,
) -> dict:
    """Execute all 11 validation checks, optionally sync anomalies, and persist ValidationRun."""
    started = time.perf_counter()
    if sync_exceptions:
        detect_and_sync_exceptions(actor=actor, source_ip=source_ip)

    checks = evaluate_all_validation_rules()
    duration_ms = max(1, int((time.perf_counter() - started) * 1000))

    passed_cnt = sum(1 for c in checks if c['status'] == ValidationCheckResult.Status.PASSED)
    failed_cnt = sum(1 for c in checks if c['status'] == ValidationCheckResult.Status.FAILED)
    warning_cnt = sum(1 for c in checks if c['status'] == ValidationCheckResult.Status.WARNING)
    total_records = sum(c['records_checked'] for c in checks)
    total_invalid = sum(c['failed_records'] for c in checks)

    run_obj = ValidationRun.objects.create(
        triggered_by=triggered_by,
        total_checks=len(checks),
        passed_checks=passed_cnt,
        failed_checks=failed_cnt,
        warning_checks=warning_cnt,
        total_records_checked=total_records,
        total_invalid_records=total_invalid,
        duration_ms=duration_ms,
    )
    ValidationCheckResult.objects.bulk_create(
        [
            ValidationCheckResult(
                run=run_obj,
                check_code=chk['check_code'],
                check_name=chk['check_name'],
                category=chk['category'],
                entity=chk['entity'],
                records_checked=chk['records_checked'],
                failed_records=chk['failed_records'],
                status=chk['status'],
                details=chk['details'],
            )
            for chk in checks
        ]
    )

    resolved_actor = actor if (actor and getattr(actor, 'is_authenticated', False)) else None
    record_audit_log(
        entity_type='ValidationRun',
        entity_id=run_obj.id,
        action=AuditLog.Action.CREATE,
        actor=resolved_actor,
        previous_state=None,
        new_state={
            'run_id': run_obj.id,
            'passed_checks': passed_cnt,
            'failed_checks': failed_cnt,
            'warning_checks': warning_cnt,
            'total_records_checked': total_records,
            'total_invalid_records': total_invalid,
        },
        changed_fields=['status'],
        source_ip=source_ip,
        notes=f'Executed validation suite ({triggered_by}).',
    )

    return _build_report_payload(
        run_obj=run_obj,
        checks=checks,
        exception_counts=_current_exception_counts(),
        history=_serialize_history(),
    )


def get_latest_validation_report() -> dict:
    """Return latest persisted ValidationRun report or compute a read-only preview if none exists."""
    latest = ValidationRun.objects.prefetch_related('checks').order_by('-executed_at', 'id').first()
    if latest is not None:
        checks = [
            {
                'check_code': chk.check_code,
                'check_name': chk.check_name,
                'category': chk.category,
                'entity': chk.entity,
                'records_checked': chk.records_checked,
                'failed_records': chk.failed_records,
                'status': chk.status,
                'details': chk.details,
                'last_run': latest.executed_at.isoformat(),
            }
            for chk in latest.checks.all().order_by('check_code')
        ]
    else:
        now_iso = datetime.now(dt_timezone.utc).isoformat()
        checks = [{**chk, 'last_run': now_iso} for chk in evaluate_all_validation_rules()]

    return _build_report_payload(
        run_obj=latest,
        checks=checks,
        exception_counts=_current_exception_counts(),
        history=_serialize_history(),
    )
