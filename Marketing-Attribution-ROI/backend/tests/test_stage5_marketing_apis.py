"""Stage 5 verification tests covering Channels, Campaigns, Creatives, Audiences, RBAC, M2M & ROI metrics."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import UserProfile
from apps.accounts.services import build_token_pair_for_user, create_user_with_profile
from apps.attribution.models import AttributionModel, AttributionResult, AttributionRun
from apps.audit.models import AuditLog
from apps.contacts.models import Contact
from apps.costs.models import CostRecord
from apps.leads.models import Lead
from apps.opportunities.models import Opportunity
from apps.orders.models import Order
from apps.touchpoints.models import Touchpoint


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
def test_marketing_crud_m2m_validation_archive_and_rbac():
    anon = APIClient()
    assert anon.get('/api/v1/campaigns/').status_code == 401

    viewer = _client_for_role('viewer5@attributioniq.io', UserProfile.Role.VIEWER)
    analyst = _client_for_role('analyst5@attributioniq.io', UserProfile.Role.MARKETING_ANALYST)
    manager = _client_for_role('manager5@attributioniq.io', UserProfile.Role.MARKETING_MANAGER)

    # Manager creates channel, creatives, and audiences
    ch_resp = manager.post(
        '/api/v1/channels/',
        {
            'name': 'Google Paid Search',
            'channel_type': 'Paid Search',
            'owner': 'Sarah Chen',
            'description': 'High-intent commercial keywords',
        },
        format='json',
    )
    assert ch_resp.status_code == 201
    channel_id = ch_resp.data['data']['id']

    # Case-insensitive duplicate channel name blocked
    assert (
        manager.post(
            '/api/v1/channels/',
            {'name': 'google paid search', 'channel_type': 'Paid Search'},
            format='json',
        ).status_code
        == 400
    )

    crt1 = manager.post(
        '/api/v1/creatives/',
        {
            'name': 'Search RSA Headline A',
            'creative_type': 'Responsive Search Ad',
            'start_date': '2026-01-05',
            'end_date': '2026-03-31',
        },
        format='json',
    )
    crt2 = manager.post(
        '/api/v1/creatives/',
        {
            'name': 'Search RSA Headline B',
            'creative_type': 'Responsive Search Ad',
            'start_date': '2026-01-10',
            'end_date': '2026-03-31',
        },
        format='json',
    )
    assert crt1.status_code == 201 and crt2.status_code == 201
    crt1_id = crt1.data['data']['id']
    crt2_id = crt2.data['data']['id']

    # Invalid creative date range blocked
    assert (
        manager.post(
            '/api/v1/creatives/',
            {
                'name': 'Bad Dates',
                'creative_type': 'Video Ad',
                'start_date': '2026-04-10',
                'end_date': '2026-04-01',
            },
            format='json',
        ).status_code
        == 400
    )

    aud1 = manager.post(
        '/api/v1/audiences/',
        {
            'name': 'NA RevOps Leaders',
            'audience_type': 'Intent Keywords',
            'estimated_size': 48500,
            'effective_from': '2026-01-01',
            'effective_to': '2026-06-30',
        },
        format='json',
    )
    assert aud1.status_code == 201
    aud1_id = aud1.data['data']['id']

    # Invalid audience effective date window blocked
    assert (
        manager.post(
            '/api/v1/audiences/',
            {
                'name': 'Bad Audience Dates',
                'audience_type': 'Lookalike',
                'effective_from': '2026-06-01',
                'effective_to': '2026-05-01',
            },
            format='json',
        ).status_code
        == 400
    )

    # Validation checks on Campaign creation
    assert (
        manager.post(
            '/api/v1/campaigns/',
            {
                'name': 'Negative Budget',
                'channel': channel_id,
                'budget': '-500.00',
                'start_date': '2026-01-05',
                'end_date': '2026-03-31',
            },
            format='json',
        ).status_code
        == 400
    )
    assert (
        manager.post(
            '/api/v1/campaigns/',
            {
                'name': 'Inverted Dates',
                'channel': channel_id,
                'budget': '5000.00',
                'start_date': '2026-05-01',
                'end_date': '2026-04-01',
            },
            format='json',
        ).status_code
        == 400
    )

    # Valid campaign creation with M2M Creative & Audience bridges
    cmp_resp = manager.post(
        '/api/v1/campaigns/',
        {
            'name': 'Q1 Enterprise Search Intent',
            'description': 'High-intent enterprise attribution campaigns',
            'channel': channel_id,
            'budget': '50000.00',
            'currency': 'USD',
            'start_date': '2026-01-05',
            'end_date': '2026-03-31',
            'objective': 'Lead Generation',
            'status': 'Active',
            'creative_ids': [crt1_id, crt2_id],
            'primary_creative_id': crt2_id,
            'audience_ids': [aud1_id],
            'primary_audience_id': aud1_id,
        },
        format='json',
    )
    assert cmp_resp.status_code == 201
    cmp_data = cmp_resp.data['data']
    cmp_id = cmp_data['id']
    assert cmp_data['primary_creative_id'] == crt2_id
    assert len(cmp_data['creatives']) == 2
    assert cmp_data['primary_audience_id'] == aud1_id

    # RBAC: Viewer & Analyst can read all 4 resources, cannot mutate
    for ro_client in (viewer, analyst):
        assert ro_client.get('/api/v1/channels/').status_code == 200
        assert ro_client.get('/api/v1/campaigns/').status_code == 200
        assert ro_client.get('/api/v1/creatives/').status_code == 200
        assert ro_client.get('/api/v1/audiences/').status_code == 200

        assert (
            ro_client.post(
                '/api/v1/campaigns/',
                {
                    'name': 'Blocked',
                    'channel': channel_id,
                    'budget': '100.00',
                    'start_date': '2026-01-01',
                    'end_date': '2026-02-01',
                },
                format='json',
            ).status_code
            == 403
        )
        assert ro_client.post(f'/api/v1/campaigns/{cmp_id}/archive/').status_code == 403

    # Referenced Channel cannot be hard-deleted (409 Conflict), must be archived instead
    del_channel = manager.delete(f'/api/v1/channels/{channel_id}/')
    assert del_channel.status_code == 409
    assert del_channel.data['error']['code'] == 'protected_reference'

    # Pause & Archive campaign and verify transition history
    pause_resp = manager.patch(
        f'/api/v1/campaigns/{cmp_id}/',
        {'status': 'Paused', 'status_reason': 'Mid-quarter budget review'},
        format='json',
    )
    assert pause_resp.status_code == 200
    assert pause_resp.data['data']['status'] == 'Paused'

    arch_resp = manager.post(
        f'/api/v1/campaigns/{cmp_id}/archive/',
        {'reason': 'Quarter closed'},
        format='json',
    )
    assert arch_resp.status_code == 200
    assert arch_resp.data['data']['status'] == 'Archived'

    hist_resp = viewer.get(f'/api/v1/campaigns/{cmp_id}/history/')
    assert hist_resp.status_code == 200
    statuses = [row['new_status'] for row in hist_resp.data['data']]
    assert statuses == ['Archived', 'Paused', 'Active']

    # Draft campaign with no cost references deletes cleanly
    draft_resp = manager.post(
        '/api/v1/campaigns/',
        {
            'name': 'Ephemeral Draft',
            'channel': channel_id,
            'budget': '0.00',
            'start_date': '2026-06-01',
            'end_date': '2026-06-30',
            'status': 'Draft',
        },
        format='json',
    )
    assert draft_resp.status_code == 201
    draft_id = draft_resp.data['data']['id']
    assert manager.delete(f'/api/v1/campaigns/{draft_id}/').status_code == 200


@pytest.mark.django_db
def test_campaign_and_channel_live_roi_currency_mismatch_and_missing_cost_alerts():
    manager = _client_for_role('mgr_roi@attributioniq.io', UserProfile.Role.MARKETING_MANAGER)
    ch = manager.post(
        '/api/v1/channels/',
        {'name': 'LinkedIn Ads', 'channel_type': 'Paid Social'},
        format='json',
    ).data['data']

    cmp_main = manager.post(
        '/api/v1/campaigns/',
        {
            'name': 'ABM Enterprise',
            'channel': ch['id'],
            'budget': '40000.00',
            'currency': 'USD',
            'start_date': '2026-01-15',
            'end_date': '2026-06-30',
            'status': 'Active',
        },
        format='json',
    ).data['data']

    cmp_no_cost = manager.post(
        '/api/v1/campaigns/',
        {
            'name': 'Missing Cost Alert Campaign',
            'channel': ch['id'],
            'budget': '15000.00',
            'currency': 'USD',
            'start_date': '2026-01-15',
            'end_date': '2026-06-30',
            'status': 'Active',
        },
        format='json',
    ).data['data']

    # Cost records: 20,000 USD valid + 5,000 EUR mismatched currency (excluded from USD spend, flagged!)
    CostRecord.objects.create(
        campaign_id=cmp_main['id'],
        channel_id=ch['id'],
        amount=Decimal('20000.00'),
        currency='USD',
        spend_date=date(2026, 2, 1),
    )
    CostRecord.objects.create(
        campaign_id=cmp_main['id'],
        channel_id=ch['id'],
        amount=Decimal('5000.00'),
        currency='EUR',
        spend_date=date(2026, 2, 15),
    )

    contact = Contact.objects.create(
        name='Claire Bennett',
        email='claire@northstar.io',
        created_date=date(2026, 1, 18),
        lifecycle_status=Contact.LifecycleStatus.CUSTOMER,
    )
    tp_main = Touchpoint.objects.create(
        contact=contact,
        campaign_id=cmp_main['id'],
        channel_id=ch['id'],
        interaction_type='LinkedIn Ad Click',
        timestamp=datetime(2026, 2, 2, 10, 0, tzinfo=timezone.utc),
    )
    Touchpoint.objects.create(
        contact=contact,
        campaign_id=cmp_no_cost['id'],
        channel_id=ch['id'],
        interaction_type='LinkedIn Ad Click',
        timestamp=datetime(2026, 2, 3, 10, 0, tzinfo=timezone.utc),
    )
    lead = Lead.objects.create(
        contact=contact,
        campaign_id=cmp_main['id'],
        source='Paid Social',
        score=88,
        created_date=date(2026, 2, 4),
        status=Lead.Status.CONVERTED,
    )
    opp = Opportunity.objects.create(
        lead=lead,
        contact=contact,
        name='NorthStar Deal',
        stage=Opportunity.Stage.CLOSED_WON,
        expected_revenue=Decimal('60000.00'),
        actual_revenue=Decimal('60000.00'),
        closing_date=date(2026, 3, 1),
        status=Opportunity.Status.WON,
    )
    order = Order.objects.create(
        opportunity=opp,
        contact=contact,
        order_date=date(2026, 3, 1),
        revenue=Decimal('60000.00'),
        currency='USD',
    )

    attr_model = AttributionModel.objects.create(
        id=AttributionModel.ModelCode.POSITION_BASED,
        name='Position Based',
        short_label='Position Based',
        description='40/20/40 model',
    )
    run = AttributionRun.objects.create(
        attribution_model=attr_model,
        valid_orders_processed=1,
        total_attributed_revenue=Decimal('60000.00'),
    )
    AttributionResult.objects.create(
        run=run,
        attribution_model=attr_model,
        order=order,
        touchpoint=tp_main,
        campaign_id=cmp_main['id'],
        channel_id=ch['id'],
        contact=contact,
        credit_weight=Decimal('1.000000'),
        attributed_revenue=Decimal('60000.00'),
        source_order_revenue=Decimal('60000.00'),
    )

    # Verify enriched Campaign metrics: spend=20000, rev=60000 -> ROI = 200%, ROAS = 3.0
    cmp_detail = manager.get(f"/api/v1/campaigns/{cmp_main['id']}/")
    assert cmp_detail.status_code == 200
    d = cmp_detail.data['data']
    assert Decimal(str(d['spend'])) == Decimal('20000.00')
    assert Decimal(str(d['attributed_revenue'])) == Decimal('60000.00')
    assert d['leads_count'] == 1
    assert d['conversions_count'] == 1
    assert d['roi'] == 200.0
    assert d['roas'] == 3.0
    assert d['has_currency_mismatch'] is True
    assert d['missing_cost_alert'] is False

    # Verify missing_cost_alert=True when budget > 0, spend == 0, and touchpoints exist
    no_cost_detail = manager.get(f"/api/v1/campaigns/{cmp_no_cost['id']}/").data['data']
    assert no_cost_detail['missing_cost_alert'] is True

    # Referenced Campaign with CostRecord cannot be hard-deleted (409 Conflict)
    assert manager.delete(f"/api/v1/campaigns/{cmp_main['id']}/").status_code == 409

    # Verify Channel aggregates match
    ch_detail = manager.get(f"/api/v1/channels/{ch['id']}/")
    assert ch_detail.status_code == 200
    cd = ch_detail.data['data']
    assert cd['total_campaigns'] == 2
    assert Decimal(str(cd['total_spend'])) == Decimal('20000.00')
    assert Decimal(str(cd['attributed_revenue'])) == Decimal('60000.00')
    assert cd['total_leads'] == 1
    assert cd['roi'] == 200.0
    assert AuditLog.objects.filter(entity_type='Campaign', action=AuditLog.Action.CREATE).count() >= 2

