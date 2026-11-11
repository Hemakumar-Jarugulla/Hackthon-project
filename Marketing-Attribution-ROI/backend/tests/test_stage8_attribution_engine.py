"""Stage 8 verification tests covering Multi-Touch Attribution Engine, Models, Comparison, and APIs."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import UserProfile
from apps.accounts.services import build_token_pair_for_user, create_user_with_profile
from apps.attribution.models import AttributionModel, AttributionResult, AttributionRun
from apps.attribution.services import (
    compare_attribution_models,
    execute_attribution_run,
    first_touch,
    last_touch,
    linear,
    position_based,
    time_decay,
)
from apps.attribution.services.attribution_validator import allocate_order_revenue
from apps.audit.models import AuditLog
from apps.campaigns.models import Campaign
from apps.channels.models import Channel
from apps.contacts.models import Contact
from apps.leads.models import Lead
from apps.opportunities.models import Opportunity
from apps.orders.models import Order
from apps.touchpoints.models import Touchpoint
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


def _build_touchpoint_stub(contact: Contact, channel: Channel, ts: datetime, campaign: Campaign | None = None):
    return Touchpoint(
        contact=contact,
        campaign=campaign,
        channel=channel,
        interaction_type='Ad Click',
        timestamp=ts,
    )


@pytest.mark.django_db
def test_five_attribution_model_calculators_and_penny_reconciliation():
    channel = Channel.objects.create(
        name='Search Unit',
        channel_type=Channel.ChannelType.PAID_SEARCH,
    )
    contact = Contact.objects.create(
        name='Unit Buyer',
        email='unit.buyer@attributioniq.io',
        company='Unit Co',
        created_date=date(2026, 1, 1),
    )
    t1 = _build_touchpoint_stub(contact, channel, datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc))
    t2 = _build_touchpoint_stub(contact, channel, datetime(2026, 6, 5, 10, 0, tzinfo=timezone.utc))
    t3 = _build_touchpoint_stub(contact, channel, datetime(2026, 6, 9, 10, 0, tzinfo=timezone.utc))
    t4 = _build_touchpoint_stub(contact, channel, datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc))
    cutoff = datetime(2026, 6, 10, 23, 59, 59, tzinfo=timezone.utc)

    # First Touch
    ft_weights = first_touch.calculate_weights([t1, t2, t3])
    assert ft_weights == [Decimal('1.000000'), Decimal('0.000000'), Decimal('0.000000')]

    # Last Touch
    lt_weights = last_touch.calculate_weights([t1, t2, t3])
    assert lt_weights == [Decimal('0.000000'), Decimal('0.000000'), Decimal('1.000000')]

    # Linear + exact penny conservation on non-divisible revenue ($100.00 / 3)
    lin_weights = linear.calculate_weights([t1, t2, t3])
    assert sum(lin_weights) == Decimal('1.000000')
    assert lin_weights == [Decimal('0.333333'), Decimal('0.333333'), Decimal('0.333334')]
    lin_revenues = allocate_order_revenue(Decimal('100.00'), lin_weights)
    assert sum(lin_revenues) == Decimal('100.00')
    assert lin_revenues == [Decimal('33.33'), Decimal('33.33'), Decimal('33.34')]

    # Time Decay: closer touchpoints strictly get more credit; shorter half-life concentrates weight
    td_default = time_decay.calculate_weights([t1, t2, t3], conversion_cutoff=cutoff, half_life_days=7)
    td_fast = time_decay.calculate_weights([t1, t2, t3], conversion_cutoff=cutoff, half_life_days=2)
    assert sum(td_default) == Decimal('1.000000')
    assert td_default[0] < td_default[1] < td_default[2]
    assert td_fast[2] > td_default[2]

    # Position Based (1, 2, 3, 4 touches)
    assert position_based.calculate_weights([t1]) == [Decimal('1.000000')]
    assert position_based.calculate_weights([t1, t2]) == [Decimal('0.500000'), Decimal('0.500000')]
    assert position_based.calculate_weights([t1, t2, t3]) == [
        Decimal('0.400000'),
        Decimal('0.200000'),
        Decimal('0.400000'),
    ]
    pb4 = position_based.calculate_weights([t1, t2, t3, t4])
    assert pb4 == [
        Decimal('0.400000'),
        Decimal('0.100000'),
        Decimal('0.100000'),
        Decimal('0.400000'),
    ]
    assert sum(pb4) == Decimal('1.000000')


@pytest.mark.django_db
def test_attribution_engine_eligibility_exclusions_offline_and_missing_campaign():
    search_ch = Channel.objects.create(
        name='Search Engine 8',
        channel_type=Channel.ChannelType.PAID_SEARCH,
    )
    events_ch = Channel.objects.create(
        name='Field Events 8',
        channel_type=Channel.ChannelType.EVENTS,
    )
    direct_ch = Channel.objects.create(
        name='Direct Channel 8',
        channel_type=Channel.ChannelType.DIRECT,
    )

    cmp_search = Campaign.objects.create(
        name='Search Intent Q2',
        channel=search_ch,
        budget=Decimal('25000.00'),
        currency='USD',
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    contact = Contact.objects.create(
        name='Elena Rostova',
        email='elena@orbitcloud.io',
        company='OrbitCloud',
        created_date=date(2026, 1, 10),
    )
    other_contact = Contact.objects.create(
        name='Marcus Vance',
        email='mvance@othercorp.io',
        company='OtherCorp',
        created_date=date(2026, 2, 1),
    )
    lead = Lead.objects.create(
        contact=contact,
        campaign=cmp_search,
        source='Paid Search',
        score=88,
        created_date=date(2026, 6, 1),
        status=Lead.Status.CONVERTED,
    )
    opp = Opportunity.objects.create(
        lead=lead,
        contact=contact,
        name='OrbitCloud Annual Platform',
        stage=Opportunity.Stage.CLOSED_WON,
        expected_revenue=Decimal('1000.00'),
        actual_revenue=Decimal('1000.00'),
        closing_date=date(2026, 7, 15),
        status=Opportunity.Status.WON,
    )
    valid_order = Order.objects.create(
        opportunity=opp,
        contact=contact,
        order_date=date(2026, 7, 15),
        revenue=Decimal('1000.00'),
        currency='USD',
        payment_status=Order.PaymentStatus.PAID,
        verification_status=Order.VerificationStatus.VALID,
    )
    # Duplicate and unpaid orders must be excluded
    Order.objects.create(
        opportunity=opp,
        contact=contact,
        order_date=date(2026, 7, 15),
        revenue=Decimal('1000.00'),
        currency='USD',
        payment_status=Order.PaymentStatus.PAID,
        verification_status=Order.VerificationStatus.DUPLICATE,
    )
    Order.objects.create(
        opportunity=opp,
        contact=contact,
        order_date=date(2026, 7, 16),
        revenue=Decimal('500.00'),
        currency='USD',
        payment_status=Order.PaymentStatus.PENDING,
        verification_status=Order.VerificationStatus.VALID,
    )

    verified_session = WebSession.objects.create(
        anonymous_id='anon-ok-8',
        contact=contact,
        campaign=cmp_search,
        landing_page='/pricing',
        referrer='google.com',
        timestamp=datetime(2026, 6, 20, 9, 0, tzinfo=timezone.utc),
        identity_status=WebSession.IdentityStatus.IDENTIFIED,
        has_evidence=True,
        evidence_type='Form Submission',
    )
    unverified_session = WebSession.objects.create(
        anonymous_id='anon-no-evidence-8',
        contact=contact,
        campaign=cmp_search,
        landing_page='/blog',
        referrer='google.com',
        timestamp=datetime(2026, 6, 25, 9, 0, tzinfo=timezone.utc),
        identity_status=WebSession.IdentityStatus.UNVERIFIED_LINK,
        has_evidence=False,
        linking_issue='Heuristic IP match without deterministic token',
    )

    # 1. Eligible online touch linked to verified session (25 days before order)
    tp_online = Touchpoint.objects.create(
        contact=contact,
        campaign=cmp_search,
        channel=search_ch,
        session=verified_session,
        interaction_type='Paid Click',
        timestamp=datetime(2026, 6, 20, 9, 5, tzinfo=timezone.utc),
        is_online=True,
        device=Touchpoint.DeviceType.DESKTOP,
    )
    # 2. Eligible offline touchpoint (10 days before order)
    tp_offline = Touchpoint.objects.create(
        contact=contact,
        campaign=cmp_search,
        channel=events_ch,
        interaction_type='Executive Roundtable',
        timestamp=datetime(2026, 7, 5, 14, 0, tzinfo=timezone.utc),
        is_online=False,
        device=Touchpoint.DeviceType.OFFLINE,
    )
    # 3. Eligible touchpoint with missing campaign_id (2 days before order)
    tp_no_campaign = Touchpoint.objects.create(
        contact=contact,
        campaign=None,
        channel=direct_ch,
        interaction_type='Direct Site Visit',
        timestamp=datetime(2026, 7, 13, 11, 0, tzinfo=timezone.utc),
        is_online=True,
        device=Touchpoint.DeviceType.DESKTOP,
    )

    # Exclusions that MUST NOT receive attribution credit:
    # A. Post-conversion by flag + post-cutoff timestamp
    Touchpoint.objects.create(
        contact=contact,
        campaign=cmp_search,
        channel=search_ch,
        interaction_type='Post Purchase Upsell Email',
        timestamp=datetime(2026, 7, 20, 10, 0, tzinfo=timezone.utc),
        is_post_conversion=True,
    )
    # B. Invalid touchpoint
    Touchpoint.objects.create(
        contact=contact,
        campaign=cmp_search,
        channel=search_ch,
        interaction_type='Bot Click',
        timestamp=datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc),
        is_valid=False,
    )
    # C. Touchpoint attached to unverified session
    Touchpoint.objects.create(
        contact=contact,
        campaign=cmp_search,
        channel=search_ch,
        session=unverified_session,
        interaction_type='Anonymous Visit',
        timestamp=datetime(2026, 6, 25, 9, 5, tzinfo=timezone.utc),
    )
    # D. Outside 30-day window (120 days prior to 2026-07-15)
    Touchpoint.objects.create(
        contact=contact,
        campaign=cmp_search,
        channel=search_ch,
        interaction_type='Old Awareness Touch',
        timestamp=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
    )
    # E. Unrelated contact touchpoint (must never leak across contacts)
    Touchpoint.objects.create(
        contact=other_contact,
        campaign=cmp_search,
        channel=search_ch,
        interaction_type='Wrong Contact Click',
        timestamp=datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc),
    )

    result = execute_attribution_run(
        model_id='position_based',
        conversion_window_days=30,
        persist=False,
    )

    assert result['valid_orders_processed'] == 1
    assert result['excluded_duplicate_orders'] == 1
    assert result['excluded_other_orders'] == 1
    assert result['excluded_post_conversion_touches'] == 1
    assert result['excluded_invalid_touches'] == 1
    assert result['excluded_unverified_session_touches'] == 1
    assert result['excluded_outside_window_touches'] == 1
    assert result['total_closed_valid_revenue'] == Decimal('1000.00')
    assert result['total_attributed_revenue'] == Decimal('1000.00')
    assert result['unattributed_valid_revenue'] == Decimal('0.00')

    # Only the 3 eligible touchpoints for this contact (40% online search, 20% offline event, 40% unassigned campaign)
    credits_by_tp = {row['touchpoint_id']: row for row in result['order_credits']}
    assert set(credits_by_tp.keys()) == {tp_online.id, tp_offline.id, tp_no_campaign.id}
    assert credits_by_tp[tp_online.id]['order_id'] == valid_order.id
    assert credits_by_tp[tp_online.id]['credit_weight'] == Decimal('0.400000')
    assert credits_by_tp[tp_online.id]['attributed_revenue'] == Decimal('400.00')
    assert credits_by_tp[tp_offline.id]['credit_weight'] == Decimal('0.200000')
    assert credits_by_tp[tp_offline.id]['attributed_revenue'] == Decimal('200.00')
    assert credits_by_tp[tp_no_campaign.id]['campaign_id'] is None
    assert credits_by_tp[tp_no_campaign.id]['campaign_name'] == 'Unassigned Campaign'
    assert credits_by_tp[tp_no_campaign.id]['credit_weight'] == Decimal('0.400000')
    assert credits_by_tp[tp_no_campaign.id]['attributed_revenue'] == Decimal('400.00')

    # Verify 5-model side-by-side comparison reconciles cleanly across every model
    comparison = compare_attribution_models(conversion_window_days=30)
    assert comparison['valid_orders_count'] == 1
    assert comparison['excluded_duplicate_orders'] == 1
    for m_key in ['first_touch', 'last_touch', 'linear', 'time_decay', 'position_based']:
        assert comparison['runs'][m_key]['total_attributed_revenue'] == Decimal('1000.00')


@pytest.mark.django_db
def test_attribution_http_apis_persistence_filtering_and_rbac():
    anon = APIClient()
    assert anon.get('/api/v1/attribution/models/').status_code == 401
    assert anon.get('/api/v1/attribution/run/').status_code == 401
    assert anon.get('/api/v1/attribution/compare/').status_code == 401

    viewer = _client_for_role('viewer8@attributioniq.io', UserProfile.Role.VIEWER)
    analyst = _client_for_role('analyst8@attributioniq.io', UserProfile.Role.MARKETING_ANALYST)
    manager = _client_for_role('manager8@attributioniq.io', UserProfile.Role.MARKETING_MANAGER)

    ch1 = Channel.objects.create(name='Paid Social 8', channel_type=Channel.ChannelType.PAID_SOCIAL)
    ch2 = Channel.objects.create(name='Email Lifecycle 8', channel_type=Channel.ChannelType.EMAIL)
    cmp1 = Campaign.objects.create(
        name='Social Demand Gen 8',
        channel=ch1,
        budget=Decimal('15000.00'),
        currency='USD',
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    cmp2 = Campaign.objects.create(
        name='Enterprise Nurture 8',
        channel=ch2,
        budget=Decimal('8000.00'),
        currency='USD',
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    contact = Contact.objects.create(
        name='Devon Brooks',
        email='devon.brooks@acme.io',
        company='Acme SaaS',
        created_date=date(2026, 3, 1),
    )
    lead = Lead.objects.create(
        contact=contact,
        campaign=cmp1,
        source='Paid Social',
        score=92,
        created_date=date(2026, 5, 1),
        status=Lead.Status.CONVERTED,
    )
    opp = Opportunity.objects.create(
        lead=lead,
        contact=contact,
        name='Acme Annual Plan',
        stage=Opportunity.Stage.CLOSED_WON,
        expected_revenue=Decimal('2400.00'),
        actual_revenue=Decimal('2400.00'),
        closing_date=date(2026, 6, 15),
        status=Opportunity.Status.WON,
    )
    order = Order.objects.create(
        opportunity=opp,
        contact=contact,
        order_date=date(2026, 6, 15),
        revenue=Decimal('2400.00'),
        currency='USD',
        payment_status=Order.PaymentStatus.PAID,
        verification_status=Order.VerificationStatus.VALID,
    )
    Touchpoint.objects.create(
        contact=contact,
        campaign=cmp1,
        channel=ch1,
        interaction_type='Social Ad Click',
        timestamp=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
    )
    Touchpoint.objects.create(
        contact=contact,
        campaign=cmp2,
        channel=ch2,
        interaction_type='Case Study Email',
        timestamp=datetime(2026, 6, 14, 15, 0, tzinfo=timezone.utc),
    )

    # Models endpoint seeds all 5 models; Viewer & Analyst cannot mutate model config
    models_resp = viewer.get('/api/v1/attribution/models/')
    assert models_resp.status_code == 200
    assert models_resp.data['count'] == 5
    model_ids = {m['id'] for m in models_resp.data['results']}
    assert model_ids == {
        'first_touch',
        'last_touch',
        'linear',
        'time_decay',
        'position_based',
    }
    assert (
        viewer.patch('/api/v1/attribution/models/time_decay/', {'config': {'half_life_days': 14}}, format='json').status_code
        == 403
    )
    assert (
        analyst.patch('/api/v1/attribution/models/time_decay/', {'config': {'half_life_days': 14}}, format='json').status_code
        == 403
    )

    # Manager CAN update model config and audit log records the change
    upd_resp = manager.patch(
        '/api/v1/attribution/models/time_decay/',
        {'config': {'half_life_days': 14}, 'rule_version': '1.1.0'},
        format='json',
    )
    assert upd_resp.status_code == 200
    assert upd_resp.data['data']['rule_version'] == '1.1.0'
    assert AuditLog.objects.filter(
        entity_type='AttributionModel',
        entity_id='time_decay',
        action=AuditLog.Action.UPDATE,
    ).exists()

    # Viewer CAN preview via GET /run/ and /compare/, without creating persisted DB rows
    preview_resp = viewer.get('/api/v1/attribution/run/?modelId=first_touch&conversionWindowDays=90')
    assert preview_resp.status_code == 200
    assert preview_resp.data['data']['persisted'] is False
    assert preview_resp.data['data']['run_id'] is None
    assert AttributionRun.objects.count() == 0

    compare_resp = viewer.get('/api/v1/attribution/compare/?conversionWindowDays=90')
    assert compare_resp.status_code == 200
    comp_data = compare_resp.data['data']
    assert comp_data['valid_orders_count'] == 1
    assert len(comp_data['campaign_comparison']) == 2
    assert len(comp_data['channel_comparison']) == 2
    cmp_by_id = {row['campaign_id']: row for row in comp_data['campaign_comparison']}
    assert Decimal(cmp_by_id[cmp1.id]['first_touch']) == Decimal('2400.00')
    assert Decimal(cmp_by_id[cmp1.id]['last_touch']) == Decimal('0.00')
    assert Decimal(cmp_by_id[cmp2.id]['last_touch']) == Decimal('2400.00')
    assert Decimal(cmp_by_id[cmp1.id]['position_based']) == Decimal('1200.00')
    assert Decimal(cmp_by_id[cmp2.id]['position_based']) == Decimal('1200.00')

    # Recharts JSON output emits numeric values rather than formatted strings
    cmp_json_by_id = {
        row['campaign_id']: row for row in compare_resp.json()['data']['campaign_comparison']
    }
    assert isinstance(cmp_json_by_id[cmp1.id]['first_touch'], (int, float))
    assert cmp_json_by_id[cmp1.id]['first_touch'] == 2400.0

    # Viewer cannot execute persisted POST /run/, whereas Marketing Analyst can
    assert viewer.post('/api/v1/attribution/run/', {'model_id': 'linear'}, format='json').status_code == 403

    run_resp = analyst.post(
        '/api/v1/attribution/run/',
        {'model_id': 'linear', 'conversion_window_days': 90, 'period_label': 'Q2 2026 Audit'},
        format='json',
    )
    assert run_resp.status_code == 201
    run_id = run_resp.data['data']['run_id']
    assert run_id == 'ATTR-RUN-2026-000001'
    assert run_resp.data['data']['persisted'] is True
    assert Decimal(run_resp.data['data']['total_attributed_revenue']) == Decimal('2400.00')
    assert AttributionRun.objects.count() == 1
    assert AttributionResult.objects.filter(run_id=run_id).count() == 2
    assert AuditLog.objects.filter(
        entity_type='AttributionRun',
        entity_id=run_id,
        action=AuditLog.Action.CREATE,
    ).exists()

    # Viewer can read persisted runs, breakdowns, and filtered results
    runs_list = viewer.get(f'/api/v1/attribution/runs/?attribution_model=linear')
    assert runs_list.status_code == 200
    assert runs_list.data['count'] == 1

    run_detail = viewer.get(f'/api/v1/attribution/runs/{run_id}/')
    assert run_detail.status_code == 200
    assert run_detail.data['data']['result_count'] == 2
    assert len(run_detail.data['data']['campaign_breakdown']) == 2
    assert len(run_detail.data['data']['channel_breakdown']) == 2

    res_list = viewer.get(f'/api/v1/attribution/results/?run={run_id}&order={order.id}')
    assert res_list.status_code == 200
    assert res_list.data['count'] == 2
    total_w = sum(Decimal(r['credit_weight']) for r in res_list.data['results'])
    total_rev = sum(Decimal(r['attributed_revenue']) for r in res_list.data['results'])
    assert total_w == Decimal('1.000000')
    assert total_rev == Decimal('2400.00')

    # Input validation & inactive model protection
    assert (
        analyst.post('/api/v1/attribution/run/', {'model_id': 'nonexistent'}, format='json').status_code
        == 400
    )
    assert (
        analyst.post(
            '/api/v1/attribution/run/',
            {'date_from': '2026-06-15', 'date_to': '2026-06-01'},
            format='json',
        ).status_code
        == 400
    )
    AttributionModel.objects.filter(id='first_touch').update(is_active=False)
    assert (
        analyst.post('/api/v1/attribution/run/', {'model_id': 'first_touch'}, format='json').status_code
        == 400
    )

