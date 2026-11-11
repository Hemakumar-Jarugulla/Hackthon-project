"""Stage 9 verification tests covering ROI, Revenue, Creative, Audience, Funnel, Trends & Dashboard APIs."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import UserProfile
from apps.accounts.services import build_token_pair_for_user, create_user_with_profile
from apps.analytics.services.metrics import (
    calculate_aov,
    calculate_conversion_rate,
    calculate_cpl,
    calculate_roas,
    calculate_roi,
)
from apps.audiences.models import Audience
from apps.campaigns.models import Campaign, CampaignAudience, CampaignCreative
from apps.channels.models import Channel
from apps.contacts.models import Contact
from apps.costs.models import CostRecord
from apps.creatives.models import Creative
from apps.exceptions.models import DataException
from apps.leads.models import Lead
from apps.opportunities.models import Opportunity
from apps.orders.models import Order
from apps.touchpoints.models import Touchpoint


def _client_for_role(email: str, role: str, *, status: str = UserProfile.AccountStatus.ACTIVE) -> APIClient:
    user = create_user_with_profile(
        email=email,
        password='StrongPass!2026',
        name=email.split('@')[0],
        role=role,
        status=status,
    )
    tokens = build_token_pair_for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


def test_roi_math_zero_spend_null_and_edge_cases():
    # Standard ROI = ((2500 - 500) / 500) * 100 = 400.00
    assert calculate_roi(Decimal('2500.00'), Decimal('500.00')) == 400.0
    assert calculate_roi(Decimal('200.00'), Decimal('500.00')) == -60.0
    # Zero / null / negative spend guard (never divides by zero)
    assert calculate_roi(Decimal('1000.00'), Decimal('0.00')) is None
    assert calculate_roi(Decimal('1000.00'), None) is None
    assert calculate_roi(Decimal('1000.00'), Decimal('-10.00')) is None

    # ROAS
    assert calculate_roas(Decimal('2500.00'), Decimal('500.00')) == 5.0
    assert calculate_roas(Decimal('2500.00'), Decimal('0.00')) is None
    assert calculate_roas(Decimal('2500.00'), None) is None

    # CPL
    assert calculate_cpl(Decimal('500.00'), 10) == Decimal('50.00')
    assert calculate_cpl(Decimal('0.00'), 5) == Decimal('0.00')
    assert calculate_cpl(Decimal('500.00'), 0) is None
    assert calculate_cpl(None, 5) is None

    # Conversion Rate
    assert calculate_conversion_rate(4, 10) == 40.0
    assert calculate_conversion_rate(0, 0) == 0.0

    # AOV
    assert calculate_aov(Decimal('3000.00'), 3) == Decimal('1000.00')
    assert calculate_aov(Decimal('0.00'), 0) == Decimal('0.00')


@pytest.mark.django_db
def test_stage9_analytics_apis_filters_fx_guards_pandas_trends_and_rbac():
    anon = APIClient()
    for url in (
        '/api/v1/analytics/roi/',
        '/api/v1/analytics/overview/',
        '/api/v1/analytics/campaigns/',
        '/api/v1/analytics/channels/',
        '/api/v1/analytics/creatives/',
        '/api/v1/analytics/audiences/',
        '/api/v1/analytics/funnel/',
        '/api/v1/analytics/trends/',
        '/api/v1/analytics/dashboard/',
    ):
        assert anon.get(url).status_code == 401

    suspended = _client_for_role(
        'suspended9@attributioniq.io',
        UserProfile.Role.VIEWER,
        status=UserProfile.AccountStatus.SUSPENDED,
    )
    assert suspended.get('/api/v1/analytics/roi/').status_code in (401, 403)

    viewer = _client_for_role('viewer9@attributioniq.io', UserProfile.Role.VIEWER)
    analyst = _client_for_role('analyst9@attributioniq.io', UserProfile.Role.MARKETING_ANALYST)

    ch_search = Channel.objects.create(
        name='Paid Search 9',
        channel_type=Channel.ChannelType.PAID_SEARCH,
    )
    ch_email = Channel.objects.create(
        name='Email Growth 9',
        channel_type=Channel.ChannelType.EMAIL,
    )

    cmp_search = Campaign.objects.create(
        name='High Intent Search 9',
        channel=ch_search,
        budget=Decimal('10000.00'),
        currency='USD',
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_paid_campaign=True,
    )
    # Omitted cost paid campaign (0 CostRecords despite budget + touchpoint)
    cmp_email = Campaign.objects.create(
        name='Email Omitted Cost 9',
        channel=ch_email,
        budget=Decimal('6000.00'),
        currency='USD',
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_paid_campaign=True,
    )

    crt_search = Creative.objects.create(
        name='RSA Cloud Security',
        primary_campaign=cmp_search,
        creative_type=Creative.CreativeType.RESPONSIVE_SEARCH_AD,
    )
    crt_email = Creative.objects.create(
        name='Executive Briefing Nurture',
        primary_campaign=cmp_email,
        creative_type=Creative.CreativeType.EMAIL_TEMPLATE,
    )
    CampaignCreative.objects.create(campaign=cmp_search, creative=crt_search, is_primary=True)
    CampaignCreative.objects.create(campaign=cmp_email, creative=crt_email, is_primary=True)

    aud_abm = Audience.objects.create(
        name='Enterprise CTO ABM',
        audience_type=Audience.AudienceType.ABM,
        estimated_size=12000,
    )
    aud_lifecycle = Audience.objects.create(
        name='Lifecycle Prospects',
        audience_type=Audience.AudienceType.LIFECYCLE,
        estimated_size=45000,
    )
    CampaignAudience.objects.create(campaign=cmp_search, audience=aud_abm, is_primary=True)
    CampaignAudience.objects.create(campaign=cmp_email, audience=aud_lifecycle, is_primary=True)

    c1 = Contact.objects.create(
        name='Clara Chen',
        email='clara@nordiccloud.io',
        company='NordicCloud',
        created_date=date(2026, 6, 1),
        lifecycle_status=Contact.LifecycleStatus.CUSTOMER,
    )
    c2 = Contact.objects.create(
        name='Liam Vance',
        email='liam@veritasfin.io',
        company='VeritasFin',
        created_date=date(2026, 6, 15),
        lifecycle_status=Contact.LifecycleStatus.OPPORTUNITY,
    )

    # Leads: 1 Converted (cmp_search) + 1 MQL (cmp_email) => 50% Lead Conversion Rate
    lead1 = Lead.objects.create(
        contact=c1,
        campaign=cmp_search,
        source='Paid Search',
        score=91,
        created_date=date(2026, 6, 5),
        status=Lead.Status.CONVERTED,
    )
    lead2 = Lead.objects.create(
        contact=c2,
        campaign=cmp_email,
        source='Email',
        score=72,
        created_date=date(2026, 7, 2),
        status=Lead.Status.MQL,
    )

    # Opportunities: 1 Won ($1000 actual) + 1 Open pipeline ($1200 expected)
    opp_won = Opportunity.objects.create(
        lead=lead1,
        contact=c1,
        name='NordicCloud Enterprise Deal',
        stage=Opportunity.Stage.CLOSED_WON,
        expected_revenue=Decimal('1000.00'),
        actual_revenue=Decimal('1000.00'),
        closing_date=date(2026, 7, 10),
        status=Opportunity.Status.WON,
    )
    Opportunity.objects.create(
        lead=lead2,
        contact=c2,
        name='VeritasFin Q3 Pipeline',
        stage=Opportunity.Stage.PROPOSAL,
        expected_revenue=Decimal('1200.00'),
        actual_revenue=Decimal('0.00'),
        closing_date=date(2026, 7, 25),
        status=Opportunity.Status.OPEN,
    )

    # Orders: 1 Valid Paid ($1000.00 on 2026-07-10) + 1 Duplicate ($1000.00 excluded!)
    Order.objects.create(
        opportunity=opp_won,
        contact=c1,
        order_date=date(2026, 7, 10),
        revenue=Decimal('1000.00'),
        currency='USD',
        payment_status=Order.PaymentStatus.PAID,
        verification_status=Order.VerificationStatus.VALID,
    )
    Order.objects.create(
        opportunity=opp_won,
        contact=c1,
        order_date=date(2026, 7, 10),
        revenue=Decimal('1000.00'),
        currency='USD',
        payment_status=Order.PaymentStatus.PAID,
        verification_status=Order.VerificationStatus.DUPLICATE,
    )

    # Costs: $200 USD (2026-06) + $200 USD (2026-07) matched = $400.00 USD total spend
    # + $300 EUR mismatched record that MUST NOT pollute USD spend
    CostRecord.objects.create(
        campaign=cmp_search,
        channel=ch_search,
        category=CostRecord.Category.MEDIA_SPEND,
        amount=Decimal('200.00'),
        currency='USD',
        spend_date=date(2026, 6, 10),
    )
    CostRecord.objects.create(
        campaign=cmp_search,
        channel=ch_search,
        category=CostRecord.Category.MEDIA_SPEND,
        amount=Decimal('200.00'),
        currency='USD',
        spend_date=date(2026, 7, 5),
    )
    CostRecord.objects.create(
        campaign=cmp_search,
        channel=ch_search,
        category=CostRecord.Category.AGENCY,
        amount=Decimal('300.00'),
        currency='EUR',
        spend_date=date(2026, 7, 6),
    )

    # Buyer Journey for c1 -> Position-Based 50/50 split between cmp_search (crt_search) & cmp_email (crt_email)
    Touchpoint.objects.create(
        contact=c1,
        campaign=cmp_search,
        channel=ch_search,
        creative=crt_search,
        interaction_type='Paid Ad Click',
        timestamp=datetime(2026, 6, 5, 10, 0, tzinfo=timezone.utc),
    )
    Touchpoint.objects.create(
        contact=c1,
        campaign=cmp_email,
        channel=ch_email,
        creative=crt_email,
        interaction_type='Briefing Email Click',
        timestamp=datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc),
    )

    # Seed one DataException for Dashboard widget coverage
    DataException.objects.create(
        issue_type=DataException.IssueType.CURRENCY_MISMATCH,
        entity_type=DataException.EntityType.COST,
        entity_id='COST-2026-000003',
        severity=DataException.Severity.HIGH,
        description='EUR spend attached to USD campaign.',
        expected_decision='Isolate mismatched FX record.',
        actual_decision='Excluded from USD spend totals.',
    )

    # 1. Overall ROI / Overview API (Position-Based default)
    roi_resp = viewer.get('/api/v1/analytics/roi/')
    assert roi_resp.status_code == 200
    summary = roi_resp.data['data']['summary']
    assert Decimal(summary['marketing_spend']) == Decimal('400.00')
    assert Decimal(summary['actual_closed_revenue']) == Decimal('1000.00')
    assert Decimal(summary['attributed_revenue']) == Decimal('1000.00')
    assert Decimal(summary['pipeline_value']) == Decimal('1200.00')
    assert Decimal(summary['won_pipeline_value']) == Decimal('1000.00')
    assert Decimal(summary['duplicate_revenue_excluded']) == Decimal('1000.00')
    assert summary['excluded_duplicate_orders'] == 1
    assert summary['valid_orders_count'] == 1
    # Blended ROI = ((1000 - 400) / 400) * 100 = 150.0% ; ROAS = 2.5 ; CPL = 400 / 2 = 200.00
    assert summary['roi'] == 150.0
    assert summary['roas'] == 2.5
    assert Decimal(summary['cpl']) == Decimal('200.00')
    assert summary['conversion_rate'] == 50.0
    assert Decimal(summary['aov']) == Decimal('1000.00')
    assert summary['currency_mismatches_count'] == 1
    assert summary['missing_cost_campaigns_count'] == 1

    # Overview alias matches identically
    assert viewer.get('/api/v1/analytics/overview/').data['data']['summary'] == summary

    # First-Touch model allocates 100% ($1000) to cmp_search => ROI = ((1000 - 400)/400)*100 = 150%
    # vs Position-Based allocates $500 to cmp_search => ROI = ((500 - 400)/400)*100 = 25%
    ft_cmp = analyst.get('/api/v1/analytics/campaigns/?modelId=first_touch')
    assert ft_cmp.status_code == 200
    ft_by_id = {r['campaign_id']: r for r in ft_cmp.data['data']['campaigns']}
    assert Decimal(ft_by_id[cmp_search.id]['attributed_revenue']) == Decimal('1000.00')
    assert ft_by_id[cmp_search.id]['roi'] == 150.0
    assert ft_by_id[cmp_search.id]['has_currency_mismatch'] is True

    pb_by_id = {r['campaign_id']: r for r in roi_resp.data['data']['campaign_rows']}
    assert Decimal(pb_by_id[cmp_search.id]['attributed_revenue']) == Decimal('500.00')
    assert pb_by_id[cmp_search.id]['roi'] == 25.0
    assert pb_by_id[cmp_email.id]['roi'] is None
    assert pb_by_id[cmp_email.id]['roas'] is None
    assert pb_by_id[cmp_email.id]['missing_cost_alert'] is True

    # 2. Channels endpoint
    ch_resp = viewer.get('/api/v1/analytics/channels/')
    assert ch_resp.status_code == 200
    ch_by_id = {r['channel_id']: r for r in ch_resp.data['data']['channels']}
    assert Decimal(ch_by_id[ch_search.id]['attributed_revenue']) == Decimal('500.00')
    assert ch_by_id[ch_search.id]['revenue_share_percent'] == 50.0
    assert ch_by_id[ch_email.id]['roi'] is None

    # 3. Creatives & Audiences endpoints
    cr_resp = viewer.get('/api/v1/analytics/creatives/')
    assert cr_resp.status_code == 200
    cr_by_id = {r['creative_id']: r for r in cr_resp.data['data']['creatives']}
    assert Decimal(cr_by_id[crt_search.id]['attributed_revenue']) == Decimal('500.00')
    assert Decimal(cr_by_id[crt_email.id]['attributed_revenue']) == Decimal('500.00')

    aud_resp = viewer.get('/api/v1/analytics/audiences/')
    assert aud_resp.status_code == 200
    aud_by_id = {r['audience_id']: r for r in aud_resp.data['data']['audiences']}
    assert Decimal(aud_by_id[aud_abm.id]['marketing_spend']) == Decimal('400.00')
    assert Decimal(aud_by_id[aud_abm.id]['attributed_revenue']) == Decimal('500.00')
    assert aud_by_id[aud_lifecycle.id]['roi'] is None

    # 4. Funnel endpoint
    funnel_resp = viewer.get('/api/v1/analytics/funnel/')
    assert funnel_resp.status_code == 200
    funnel_data = funnel_resp.data['data']
    assert funnel_data['lead_summary']['total_leads'] == 2
    assert funnel_data['lead_summary']['lead_conversion_rate'] == 50.0
    assert Decimal(funnel_data['opportunity_summary']['open_pipeline_value']) == Decimal('1200.00')
    assert Decimal(funnel_data['opportunity_summary']['won_revenue']) == Decimal('1000.00')
    assert len(funnel_data['opportunity_summary']['by_stage']) == 6

    # 5. Trends endpoint (Pandas + NumPy across 2026-06 & 2026-07)
    trends_resp = viewer.get('/api/v1/analytics/trends/')
    assert trends_resp.status_code == 200
    series = trends_resp.data['data']['monthly_series']
    by_month = {m['month_key']: m for m in series}
    assert set(by_month.keys()) == {'2026-06', '2026-07'}
    assert Decimal(by_month['2026-06']['spend']) == Decimal('200.00')
    assert Decimal(by_month['2026-07']['closed_revenue']) == Decimal('1000.00')
    assert Decimal(by_month['2026-07']['cumulative_spend']) == Decimal('400.00')
    stats = trends_resp.data['data']['statistics']
    assert stats['total_months'] == 2
    assert Decimal(stats['avg_monthly_spend']) == Decimal('200.00')
    assert stats['best_month']['month_key'] == '2026-07'

    # Recharts JSON outputs numbers rather than formatted strings
    trends_json = trends_resp.json()['data']
    assert isinstance(trends_json['monthly_series'][1]['closed_revenue'], (int, float))

    # 6. Dashboard endpoint + campaign/date filter checks
    dash_resp = viewer.get('/api/v1/analytics/dashboard/')
    assert dash_resp.status_code == 200
    dash_data = dash_resp.data['data']
    assert Decimal(dash_data['kpis']['actual_closed_revenue']) == Decimal('1000.00')
    assert len(dash_data['charts']['monthly_series']) == 2
    assert len(dash_data['widgets']['data_quality_alerts']) == 1

    # Filter specifically to July + cmp_search
    filtered = viewer.get(
        f'/api/v1/analytics/roi/?campaign_id={cmp_search.id}&date_from=2026-07-01&date_to=2026-07-31'
    )
    assert filtered.status_code == 200
    assert Decimal(filtered.data['data']['summary']['marketing_spend']) == Decimal('200.00')
    assert Decimal(filtered.data['data']['summary']['attributed_revenue']) == Decimal('500.00')

    # Query validation errors
    assert (
        viewer.get('/api/v1/analytics/roi/?date_from=2026-07-31&date_to=2026-07-01').status_code
        == 400
    )
    assert viewer.get('/api/v1/analytics/roi/?model_id=invalid_model').status_code == 400

