"""Stage 10 verification tests covering Anomaly Detection, Exception Triage, 11-Rule Validation & Audit APIs."""

from datetime import date, datetime, timezone
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import UserProfile
from apps.accounts.services import build_token_pair_for_user, create_user_with_profile
from apps.attribution.models import AttributionModel, AttributionResult, AttributionRun
from apps.attribution.services import ensure_attribution_models_seeded, execute_attribution_run
from apps.campaigns.models import Campaign
from apps.channels.models import Channel
from apps.contacts.models import Contact
from apps.costs.models import CostRecord
from apps.exceptions.models import DataException
from apps.leads.models import Lead
from apps.opportunities.models import Opportunity
from apps.orders.models import Order
from apps.touchpoints.models import Touchpoint
from apps.validation.models import ValidationRun
from apps.web_sessions.models import WebSession


def _client_for_role(email: str, role: str) -> APIClient:
    user = create_user_with_profile(
        email=email,
        password='StrongPass!2026',
        name=email.split('@')[0],
        role=role,
    )
    tokens = build_token_pair_for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


@pytest.mark.django_db
def test_stage10_five_anomaly_detection_triage_validation_and_audit_apis():
    anon = APIClient()
    assert anon.get('/api/v1/exceptions/').status_code == 401
    assert anon.get('/api/v1/validation/report/').status_code == 401
    assert anon.get('/api/v1/audit/').status_code == 401

    viewer = _client_for_role('viewer10@attributioniq.io', UserProfile.Role.VIEWER)
    analyst = _client_for_role('analyst10@attributioniq.io', UserProfile.Role.MARKETING_ANALYST)

    ch_search = Channel.objects.create(
        name='Search 10',
        channel_type=Channel.ChannelType.PAID_SEARCH,
    )
    ch_display = Channel.objects.create(
        name='Display 10',
        channel_type=Channel.ChannelType.DISPLAY,
    )

    cmp_cost_ok = Campaign.objects.create(
        name='Paid Search With Cost 10',
        channel=ch_search,
        budget=Decimal('15000.00'),
        currency='USD',
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_paid_campaign=True,
    )
    # Problem 4 target: Paid campaign with budget + active touchpoint, 0 CostRecords
    cmp_cost_omitted = Campaign.objects.create(
        name='Display Cost Omitted 10',
        channel=ch_display,
        budget=Decimal('20000.00'),
        currency='USD',
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_paid_campaign=True,
    )

    contact = Contact.objects.create(
        name='Hannah Lin',
        email='hannah.lin@matrixsys.io',
        company='MatrixSys',
        created_date=date(2026, 4, 1),
    )
    lead = Lead.objects.create(
        contact=contact,
        campaign=cmp_cost_ok,
        source='Paid Search',
        score=89,
        created_date=date(2026, 5, 1),
        status=Lead.Status.CONVERTED,
        converted_at=datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc),
    )
    opp = Opportunity.objects.create(
        lead=lead,
        contact=contact,
        name='MatrixSys Enterprise Rollout',
        stage=Opportunity.Stage.CLOSED_WON,
        expected_revenue=Decimal('5000.00'),
        actual_revenue=Decimal('5000.00'),
        closing_date=date(2026, 6, 10),
        status=Opportunity.Status.WON,
    )
    valid_order = Order.objects.create(
        opportunity=opp,
        contact=contact,
        order_date=date(2026, 6, 10),
        revenue=Decimal('5000.00'),
        currency='USD',
        payment_status=Order.PaymentStatus.PAID,
        verification_status=Order.VerificationStatus.VALID,
    )
    # Problem 1: Duplicate Order
    dup_order = Order.objects.create(
        opportunity=opp,
        contact=contact,
        order_date=date(2026, 6, 11),
        revenue=Decimal('5000.00'),
        currency='USD',
        payment_status=Order.PaymentStatus.PAID,
        verification_status=Order.VerificationStatus.DUPLICATE,
    )
    # Problem 3: Spend Currency Mismatch (EUR cost on USD campaign)
    CostRecord.objects.create(
        campaign=cmp_cost_ok,
        channel=ch_search,
        category=CostRecord.Category.MEDIA_SPEND,
        amount=Decimal('1000.00'),
        currency='USD',
        spend_date=date(2026, 5, 15),
    )
    mismatched_cost = CostRecord.objects.create(
        campaign=cmp_cost_ok,
        channel=ch_search,
        category=CostRecord.Category.AGENCY,
        amount=Decimal('750.00'),
        currency='EUR',
        spend_date=date(2026, 5, 20),
    )

    # Problem 5: Unverified anonymous session link without evidence
    unverified_session = WebSession.objects.create(
        anonymous_id='anon-10-unverified',
        contact=contact,
        campaign=cmp_cost_ok,
        landing_page='/demo',
        referrer='google.com',
        timestamp=datetime(2026, 5, 22, 9, 0, tzinfo=timezone.utc),
        identity_status=WebSession.IdentityStatus.UNVERIFIED_LINK,
        has_evidence=False,
    )
    # Eligible touchpoints
    Touchpoint.objects.create(
        contact=contact,
        campaign=cmp_cost_ok,
        channel=ch_search,
        interaction_type='Search Click',
        timestamp=datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc),
    )
    Touchpoint.objects.create(
        contact=contact,
        campaign=cmp_cost_omitted,
        channel=ch_display,
        interaction_type='Retargeting View',
        timestamp=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
    )
    # Problem 2: Post-conversion touchpoint
    post_tp = Touchpoint.objects.create(
        contact=contact,
        campaign=cmp_cost_ok,
        channel=ch_search,
        interaction_type='Post-Sale Upsell Email',
        timestamp=datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc),
        is_post_conversion=True,
    )

    # Run clean attribution before validation so AttributionResult rows exist cleanly
    execute_attribution_run(model_id='position_based', persist=True)

    # Viewer blocked from scanning, resolving, or running validation or viewing audit logs
    assert viewer.post('/api/v1/exceptions/scan/').status_code == 403
    assert viewer.post('/api/v1/validation/run/').status_code == 403
    assert viewer.get('/api/v1/audit/').status_code == 403

    # Scan detects all 5 business anomalies without duplicates
    scan_resp = analyst.post('/api/v1/exceptions/scan/')
    assert scan_resp.status_code == 200
    scan_data = scan_resp.data['data']
    assert scan_data['created_count'] == 5
    by_issue = scan_data['by_issue_type']
    assert by_issue[DataException.IssueType.DUPLICATE_REVENUE] == 1
    assert by_issue[DataException.IssueType.POST_CONVERSION_TOUCH] == 1
    assert by_issue[DataException.IssueType.CURRENCY_MISMATCH] == 1
    assert by_issue[DataException.IssueType.COSTS_OMITTED] == 1
    assert by_issue[DataException.IssueType.UNVERIFIED_SESSION_LINK] == 1

    # Re-scanning is idempotent (0 newly created rows)
    rescan = analyst.post('/api/v1/exceptions/scan/')
    assert rescan.status_code == 200
    assert rescan.data['data']['created_count'] == 0

    # List, filter, and summary endpoints work for Viewer
    list_resp = viewer.get('/api/v1/exceptions/?severity=Critical')
    assert list_resp.status_code == 200
    assert list_resp.data['count'] == 1
    dup_exc = list_resp.data['results'][0]
    assert dup_exc['entity_id'] == dup_order.id

    summary_resp = viewer.get('/api/v1/exceptions/summary/')
    assert summary_resp.status_code == 200
    assert summary_resp.data['data']['total_exceptions'] == 5
    assert summary_resp.data['data']['open_exceptions'] == 5
    assert summary_resp.data['data']['open_critical_high'] == 3

    # Verify detected entity IDs across all 5 anomaly types
    all_excs = viewer.get('/api/v1/exceptions/').data['results']
    entity_pairs = {(e['issue_type'], e['entity_id']) for e in all_excs}
    assert (DataException.IssueType.DUPLICATE_REVENUE, dup_order.id) in entity_pairs
    assert (DataException.IssueType.POST_CONVERSION_TOUCH, post_tp.id) in entity_pairs
    assert (DataException.IssueType.CURRENCY_MISMATCH, mismatched_cost.id) in entity_pairs
    assert (DataException.IssueType.COSTS_OMITTED, cmp_cost_omitted.id) in entity_pairs
    assert (DataException.IssueType.UNVERIFIED_SESSION_LINK, unverified_session.id) in entity_pairs

    # Analyst resolves and reopens an exception with full audit trail
    assert viewer.patch(f"/api/v1/exceptions/{dup_exc['id']}/resolve/", {}, format='json').status_code == 403
    resolve_resp = analyst.patch(
        f"/api/v1/exceptions/{dup_exc['id']}/resolve/",
        {'resolution_status': 'Resolved', 'resolution_notes': 'Verified invoice duplication with finance.'},
        format='json',
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.data['data']['resolution_status'] == 'Resolved'
    assert resolve_resp.data['data']['resolved_at'] is not None
    assert resolve_resp.data['data']['resolved_by_username'] == 'analyst10'

    reopen_resp = analyst.patch(
        f"/api/v1/exceptions/{dup_exc['id']}/reopen/",
        {'resolution_notes': 'Reopened for secondary ERP reconciliation.'},
        format='json',
    )
    assert reopen_resp.status_code == 200
    assert reopen_resp.data['data']['resolution_status'] == 'Open'
    assert reopen_resp.data['data']['resolved_at'] is None

    # Execute 11-rule validation suite via API
    val_resp = analyst.post('/api/v1/validation/run/', {'sync_exceptions': True}, format='json')
    assert val_resp.status_code == 201
    val_data = val_resp.data['data']
    assert val_data['run_id'] == 'VAL-RUN-2026-000001'
    assert val_data['total_checks'] == 11
    assert val_data['errors'] == 0  # Engine prevented duplicate & post-conversion attribution leakage
    assert val_data['warnings'] == 4  # VAL-06, VAL-07, VAL-09, VAL-11 isolated quarantined issues
    assert ValidationRun.objects.count() == 1

    # Report endpoint & run history readable by Viewer
    report_resp = viewer.get('/api/v1/validation/report/')
    assert report_resp.status_code == 200
    assert report_resp.data['data']['run_id'] == 'VAL-RUN-2026-000001'
    assert len(report_resp.data['data']['checks']) == 11
    assert viewer.get('/api/v1/validation/runs/').data['count'] == 1

    # CLI validate_marketing_data command executes cleanly
    out = StringIO()
    call_command('validate_marketing_data', '--strict', stdout=out)
    assert 'Errors=0' in out.getvalue()

    # Audit endpoint records exception actions and validation run
    audit_resp = analyst.get('/api/v1/audit/?entity_type=DataException')
    assert audit_resp.status_code == 200
    assert audit_resp.data['count'] >= 2

    # Explicitly test VAL-10 & VAL-11 failure detection when corrupted AttributionResult is forced
    ensure_attribution_models_seeded()
    bad_run = AttributionRun.objects.create(
        attribution_model=AttributionModel.objects.get(id='first_touch'),
        rule_version='1.0.0',
        period_label='Corrupt Check',
        total_attributed_revenue=Decimal('999.00'),
    )
    AttributionResult.objects.create(
        run=bad_run,
        attribution_model_id='first_touch',
        order=valid_order,
        touchpoint=post_tp,
        campaign=cmp_cost_ok,
        channel=ch_search,
        contact=contact,
        rule_version='1.0.0',
        credit_weight=Decimal('0.500000'),
        attributed_revenue=Decimal('999.00'),
        source_order_revenue=valid_order.revenue,
    )
    with pytest.raises(CommandError):
        call_command('validate_marketing_data', '--strict', stdout=StringIO())

