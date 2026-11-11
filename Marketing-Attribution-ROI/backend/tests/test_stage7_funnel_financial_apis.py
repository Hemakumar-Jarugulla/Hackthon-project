"""Stage 7 verification tests covering Leads, Opportunities, Orders, Marketing Costs, and RBAC."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import UserProfile
from apps.accounts.services import build_token_pair_for_user, create_user_with_profile
from apps.attribution.models import AttributionModel, AttributionResult, AttributionRun
from apps.audit.models import AuditLog
from apps.campaigns.models import Campaign
from apps.channels.models import Channel
from apps.contacts.models import Contact
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
def test_leads_and_opportunities_crud_history_relational_checks_and_rbac():
    anon = APIClient()
    assert anon.get('/api/v1/leads/').status_code == 401
    assert anon.get('/api/v1/opportunities/').status_code == 401

    viewer = _client_for_role('viewer7@attributioniq.io', UserProfile.Role.VIEWER)
    analyst = _client_for_role('analyst7@attributioniq.io', UserProfile.Role.MARKETING_ANALYST)
    manager = _client_for_role('manager7@attributioniq.io', UserProfile.Role.MARKETING_MANAGER)

    channel = Channel.objects.create(
        name='Paid Search 7',
        channel_type=Channel.ChannelType.PAID_SEARCH,
    )
    campaign = Campaign.objects.create(
        name='Pipeline Search 2026',
        channel=channel,
        budget=Decimal('50000.00'),
        currency='USD',
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    contact = Contact.objects.create(
        name='Daniel Okafor',
        email='d.okafor@finscale.co.uk',
        company='FinScale UK',
        created_date=date(2026, 5, 15),
    )
    other_contact = Contact.objects.create(
        name='Sophia Martinez',
        email='smartinez@heliosdata.ai',
        company='Helios Data AI',
        created_date=date(2026, 4, 10),
    )

    # Reject invalid Lead score
    assert (
        manager.post(
            '/api/v1/leads/',
            {
                'contact': contact.id,
                'campaign': campaign.id,
                'source': 'Paid Search',
                'score': 150,
            },
            format='json',
        ).status_code
        == 400
    )

    # Create Lead cleanly
    lead_resp = manager.post(
        '/api/v1/leads/',
        {
            'contact': contact.id,
            'campaign': campaign.id,
            'source': 'Paid Search',
            'score': 90,
            'created_date': '2026-07-09',
            'status': 'New',
        },
        format='json',
    )
    assert lead_resp.status_code == 201
    lead_id = lead_resp.data['data']['id']
    assert lead_id == 'LEAD-2026-000001'

    # RBAC read vs write checks
    assert viewer.get(f'/api/v1/leads/{lead_id}/').status_code == 200
    assert (
        analyst.patch(
            f'/api/v1/leads/{lead_id}/',
            {'status': 'MQL'},
            format='json',
        ).status_code
        == 403
    )

    # Progress Lead status and verify converted_at + history
    assert (
        manager.patch(
            f'/api/v1/leads/{lead_id}/',
            {'status': 'MQL', 'status_reason': 'High intent pricing download'},
            format='json',
        ).status_code
        == 200
    )
    conv_resp = manager.patch(
        f'/api/v1/leads/{lead_id}/',
        {'status': 'Converted', 'status_reason': 'Qualified sales opportunity created'},
        format='json',
    )
    assert conv_resp.status_code == 200
    assert conv_resp.data['data']['converted_at'] is not None

    lead_hist = analyst.get(f'/api/v1/leads/{lead_id}/history/')
    assert lead_hist.status_code == 200
    transitions = [(h['previous_status'], h['new_status']) for h in lead_hist.data['data']]
    assert ('', 'New') in transitions
    assert ('New', 'MQL') in transitions
    assert ('MQL', 'Converted') in transitions

    # Reject Opportunity with mismatched contact vs lead.contact
    assert (
        manager.post(
            '/api/v1/opportunities/',
            {
                'lead': lead_id,
                'contact': other_contact.id,
                'name': 'Mismatched Contact Deal',
                'expected_revenue': '50000.00',
                'closing_date': '2026-09-30',
            },
            format='json',
        ).status_code
        == 400
    )

    # Reject Opportunity with conflicting stage/status or negative expected_revenue
    assert (
        manager.post(
            '/api/v1/opportunities/',
            {
                'lead': lead_id,
                'name': 'Bad Status Deal',
                'stage': 'Closed Won',
                'status': 'Open',
                'expected_revenue': '50000.00',
                'closing_date': '2026-09-30',
            },
            format='json',
        ).status_code
        == 400
    )
    assert (
        manager.post(
            '/api/v1/opportunities/',
            {
                'lead': lead_id,
                'name': 'Negative Deal',
                'expected_revenue': '-10.00',
                'closing_date': '2026-09-30',
            },
            format='json',
        ).status_code
        == 400
    )

    # Create Opportunity omitting contact (auto-resolved from lead)
    opp_resp = manager.post(
        '/api/v1/opportunities/',
        {
            'lead': lead_id,
            'name': 'FinScale UK EMEA Attribution Platform',
            'stage': 'Qualification',
            'expected_revenue': '95000.00',
            'closing_date': '2026-07-28',
        },
        format='json',
    )
    assert opp_resp.status_code == 201
    opp_id = opp_resp.data['data']['id']
    assert opp_id == 'OPP-2026-000001'
    assert opp_resp.data['data']['contact'] == contact.id
    assert opp_resp.data['data']['status'] == 'Open'

    # Move Opportunity stage -> Closed Won (auto-syncs status='Won')
    assert (
        manager.patch(
            f'/api/v1/opportunities/{opp_id}/',
            {'stage': 'Negotiation'},
            format='json',
        ).status_code
        == 200
    )
    won_resp = manager.patch(
        f'/api/v1/opportunities/{opp_id}/',
        {'stage': 'Closed Won', 'actual_revenue': '96000.00'},
        format='json',
    )
    assert won_resp.status_code == 200
    assert won_resp.data['data']['status'] == 'Won'

    opp_hist = viewer.get(f'/api/v1/opportunities/{opp_id}/history/')
    assert opp_hist.status_code == 200
    stage_moves = [(h['previous_stage'], h['new_stage']) for h in opp_hist.data['data']]
    assert ('', 'Qualification') in stage_moves
    assert ('Qualification', 'Negotiation') in stage_moves
    assert ('Negotiation', 'Closed Won') in stage_moves

    # Protected delete: Lead cannot be deleted while referenced by Opportunity
    assert manager.delete(f'/api/v1/leads/{lead_id}/').status_code == 409


@pytest.mark.django_db
def test_orders_duplicate_revenue_guard_verification_and_protected_delete():
    analyst = _client_for_role('analyst7b@attributioniq.io', UserProfile.Role.MARKETING_ANALYST)
    manager = _client_for_role('manager7b@attributioniq.io', UserProfile.Role.MARKETING_MANAGER)

    channel = Channel.objects.create(name='LinkedIn 7', channel_type=Channel.ChannelType.PAID_SOCIAL)
    campaign = Campaign.objects.create(
        name='ABM Program',
        channel=channel,
        budget=Decimal('40000.00'),
        currency='USD',
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    contact = Contact.objects.create(
        name='Claire Bennett',
        email='c.bennett@northstarcloud.io',
        created_date=date(2026, 1, 18),
    )
    other_contact = Contact.objects.create(
        name='Liam Gallagher',
        email='liam@apexlogistics.com',
        created_date=date(2026, 8, 5),
    )
    lead_resp = manager.post(
        '/api/v1/leads/',
        {'contact': contact.id, 'campaign': campaign.id, 'source': 'Paid Social'},
        format='json',
    )
    opp_resp = manager.post(
        '/api/v1/opportunities/',
        {
            'lead': lead_resp.data['data']['id'],
            'name': 'NorthStar Enterprise License',
            'stage': 'Closed Won',
            'expected_revenue': '115000.00',
            'actual_revenue': '120000.00',
            'closing_date': '2026-03-18',
        },
        format='json',
    )
    opp_id = opp_resp.data['data']['id']

    # Reject Order with wrong contact for Opportunity
    assert (
        manager.post(
            '/api/v1/orders/',
            {
                'opportunity': opp_id,
                'contact': other_contact.id,
                'order_date': '2026-03-18',
                'revenue': '120000.00',
            },
            format='json',
        ).status_code
        == 400
    )

    # Create primary Valid + Paid Order (auto-deriving contact)
    ord1_resp = manager.post(
        '/api/v1/orders/',
        {
            'opportunity': opp_id,
            'order_date': '2026-03-18',
            'revenue': '120000.00',
            'currency': 'USD',
            'payment_status': 'Paid',
            'verification_status': 'Valid',
        },
        format='json',
    )
    assert ord1_resp.status_code == 201
    ord1_id = ord1_resp.data['data']['id']
    assert ord1_resp.data['data']['contact'] == contact.id
    assert ord1_resp.data['data']['is_attributable'] is True

    # Reject creating a second 'Valid' order for the same Opportunity (prevents double counting)
    assert (
        manager.post(
            '/api/v1/orders/',
            {
                'opportunity': opp_id,
                'order_date': '2026-03-19',
                'revenue': '120000.00',
                'verification_status': 'Valid',
            },
            format='json',
        ).status_code
        == 400
    )

    # Permit recording explicit 'Duplicate' anomaly row in ledger
    dup_ord_resp = manager.post(
        '/api/v1/orders/',
        {
            'opportunity': opp_id,
            'order_date': '2026-03-19',
            'revenue': '120000.00',
            'payment_status': 'Paid',
            'verification_status': 'Duplicate',
            'notes': 'Duplicate CRM webhook retry',
        },
        format='json',
    )
    assert dup_ord_resp.status_code == 201
    dup_ord_id = dup_ord_resp.data['data']['id']
    assert dup_ord_resp.data['data']['is_attributable'] is False

    # Analyst cannot mutate verification status via /verify/
    assert (
        analyst.post(
            f'/api/v1/orders/{dup_ord_id}/verify/',
            {'verification_status': 'Invalid'},
            format='json',
        ).status_code
        == 403
    )

    # Manager cannot promote duplicate order to Valid while ord1 is still Valid
    assert (
        manager.post(
            f'/api/v1/orders/{dup_ord_id}/verify/',
            {'verification_status': 'Valid'},
            format='json',
        ).status_code
        == 400
    )

    # Once ord1 is marked Invalid, duplicate can cleanly be verified as Valid
    assert (
        manager.post(
            f'/api/v1/orders/{ord1_id}/verify/',
            {'verification_status': 'Invalid', 'notes': 'Superseded by corrected invoice'},
            format='json',
        ).status_code
        == 200
    )
    promote_resp = manager.post(
        f'/api/v1/orders/{dup_ord_id}/verify/',
        {'verification_status': 'Valid', 'notes': 'Verified canonical closed order'},
        format='json',
    )
    assert promote_resp.status_code == 200
    assert promote_resp.data['data']['is_attributable'] is True

    # Opportunity cannot be deleted while referenced by Orders -> 409
    assert manager.delete(f'/api/v1/opportunities/{opp_id}/').status_code == 409

    # Order referenced by AttributionResult cannot be deleted -> 409
    tp = Touchpoint.objects.create(
        contact=contact,
        campaign=campaign,
        channel=channel,
        interaction_type='ABM Ad Click',
        timestamp=datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc),
    )
    model_obj = AttributionModel.objects.create(
        id=AttributionModel.ModelCode.LAST_TOUCH,
        name='Last Touch',
        short_label='Last',
        description='100% last touch',
    )
    run_obj = AttributionRun.objects.create(attribution_model=model_obj)
    AttributionResult.objects.create(
        run=run_obj,
        attribution_model=model_obj,
        order_id=dup_ord_id,
        touchpoint=tp,
        campaign=campaign,
        channel=channel,
        contact=contact,
        credit_weight=Decimal('1.000000'),
        attributed_revenue=Decimal('120000.00'),
        source_order_revenue=Decimal('120000.00'),
    )
    assert manager.delete(f'/api/v1/orders/{dup_ord_id}/').status_code == 409


@pytest.mark.django_db
def test_costs_ledger_fx_mismatch_filters_summary_and_channel_checks():
    viewer = _client_for_role('viewer7c@attributioniq.io', UserProfile.Role.VIEWER)
    manager = _client_for_role('manager7c@attributioniq.io', UserProfile.Role.MARKETING_MANAGER)

    ch_search = Channel.objects.create(name='Google Search 7', channel_type=Channel.ChannelType.PAID_SEARCH)
    ch_email = Channel.objects.create(name='Email 7', channel_type=Channel.ChannelType.EMAIL)
    cmp_usd = Campaign.objects.create(
        name='EMEA Commercial Search',
        channel=ch_search,
        budget=Decimal('40000.00'),
        currency='USD',
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    # Reject negative amount or mismatched channel vs campaign
    assert (
        manager.post(
            '/api/v1/costs/',
            {
                'campaign': cmp_usd.id,
                'amount': '-500.00',
                'currency': 'USD',
                'spend_date': '2026-08-15',
            },
            format='json',
        ).status_code
        == 400
    )
    assert (
        manager.post(
            '/api/v1/costs/',
            {
                'campaign': cmp_usd.id,
                'channel': ch_email.id,
                'amount': '5000.00',
                'currency': 'USD',
                'spend_date': '2026-08-15',
            },
            format='json',
        ).status_code
        == 400
    )

    # Matched USD spend items (auto-deriving channel from campaign)
    c1 = manager.post(
        '/api/v1/costs/',
        {
            'campaign': cmp_usd.id,
            'category': 'Media Spend',
            'amount': '16000.00',
            'currency': 'USD',
            'spend_date': '2026-08-15',
            'description': 'EMEA commercial search ad spend settled in USD.',
        },
        format='json',
    )
    assert c1.status_code == 201
    assert c1.data['data']['channel'] == ch_search.id
    assert c1.data['data']['currency_mismatch'] is False

    c2 = manager.post(
        '/api/v1/costs/',
        {
            'campaign': cmp_usd.id,
            'category': 'Creative Production',
            'amount': '4000.00',
            'currency': 'USD',
            'spend_date': '2026-08-20',
        },
        format='json',
    )
    assert c2.status_code == 201

    # EUR cost recorded against USD campaign succeeds AND flags currency_mismatch=True
    c_fx = manager.post(
        '/api/v1/costs/',
        {
            'campaign': cmp_usd.id,
            'category': 'Agency & Bid Management',
            'amount': '4500.00',
            'currency': 'EUR',
            'spend_date': '2026-09-02',
            'description': 'EUR invoice recorded against USD campaign.',
        },
        format='json',
    )
    assert c_fx.status_code == 201
    assert c_fx.data['data']['currency_mismatch'] is True
    assert c_fx.data['data']['campaign_currency'] == 'USD'

    # Filter currency_mismatch=true vs false
    fx_only = viewer.get('/api/v1/costs/?currency_mismatch=true')
    assert fx_only.status_code == 200
    assert fx_only.data['count'] == 1
    assert fx_only.data['results'][0]['currency'] == 'EUR'

    matched_only = viewer.get('/api/v1/costs/?currency_mismatch=false')
    assert matched_only.status_code == 200
    assert matched_only.data['count'] == 2

    # Verify FX-aware summary endpoint
    summary_resp = viewer.get(f'/api/v1/costs/summary/?campaign={cmp_usd.id}')
    assert summary_resp.status_code == 200
    summary = summary_resp.data['data']
    assert summary['total_records'] == 3
    assert summary['matched_currency_records'] == 2
    assert summary['mismatched_currency_records'] == 1

    by_curr = {item['currency']: item for item in summary['spend_by_currency']}
    assert Decimal(by_curr['USD']['matched_spend']) == Decimal('20000.00')
    assert Decimal(by_curr['EUR']['mismatched_spend']) == Decimal('4500.00')

    # Clean delete logs DELETE in AuditLog
    cost_id = c2.data['data']['id']
    assert manager.delete(f'/api/v1/costs/{cost_id}/').status_code == 200
    assert AuditLog.objects.filter(
        entity_type='CostRecord',
        entity_id=cost_id,
        action=AuditLog.Action.DELETE,
    ).exists()
