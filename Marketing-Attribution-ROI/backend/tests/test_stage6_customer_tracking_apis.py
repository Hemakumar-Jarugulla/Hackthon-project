"""Stage 6 verification tests covering Contacts, Web Sessions, Touchpoints, RBAC & Customer Journeys."""

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
def test_contacts_crud_lifecycle_history_metrics_protected_delete_and_rbac():
    anon = APIClient()
    assert anon.get('/api/v1/contacts/').status_code == 401

    viewer = _client_for_role('viewer6@attributioniq.io', UserProfile.Role.VIEWER)
    analyst = _client_for_role('analyst6@attributioniq.io', UserProfile.Role.MARKETING_ANALYST)
    manager = _client_for_role('manager6@attributioniq.io', UserProfile.Role.MARKETING_MANAGER)

    # Create contact (email normalized to lowercase)
    create_resp = manager.post(
        '/api/v1/contacts/',
        {
            'name': 'Claire Bennett',
            'email': 'C.Bennett@NorthStarCloud.io',
            'phone': '+1 415 555 0142',
            'company': 'NorthStar Cloud Inc.',
            'source': 'Paid Search',
            'created_date': '2026-01-18',
            'lifecycle_status': 'Subscriber',
        },
        format='json',
    )
    assert create_resp.status_code == 201
    contact_id = create_resp.data['data']['id']
    assert contact_id == 'CON-2026-000001'
    assert create_resp.data['data']['email'] == 'c.bennett@northstarcloud.io'

    # Case-insensitive duplicate email blocked
    dup_resp = manager.post(
        '/api/v1/contacts/',
        {
            'name': 'Duplicate Claire',
            'email': 'c.bennett@northstarcloud.io',
        },
        format='json',
    )
    assert dup_resp.status_code == 400

    # RBAC read vs write checks
    assert viewer.get(f'/api/v1/contacts/{contact_id}/').status_code == 200
    assert analyst.get('/api/v1/contacts/').status_code == 200
    assert (
        viewer.post(
            '/api/v1/contacts/',
            {'name': 'Blocked', 'email': 'blocked@example.com'},
            format='json',
        ).status_code
        == 403
    )
    assert (
        analyst.patch(
            f'/api/v1/contacts/{contact_id}/',
            {'company': 'Blocked Corp'},
            format='json',
        ).status_code
        == 403
    )

    # Lifecycle updates create history + AuditLog
    assert (
        manager.patch(
            f'/api/v1/contacts/{contact_id}/',
            {'lifecycle_status': 'Lead', 'status_reason': 'Submitted demo request'},
            format='json',
        ).status_code
        == 200
    )
    assert (
        manager.patch(
            f'/api/v1/contacts/{contact_id}/',
            {'lifecycle_status': 'Customer', 'status_reason': 'Closed annual contract'},
            format='json',
        ).status_code
        == 200
    )

    hist_resp = analyst.get(f'/api/v1/contacts/{contact_id}/lifecycle/')
    assert hist_resp.status_code == 200
    transitions = [(h['previous_status'], h['new_status']) for h in hist_resp.data['data']]
    assert ('', 'Subscriber') in transitions
    assert ('Subscriber', 'Lead') in transitions
    assert ('Lead', 'Customer') in transitions

    # Populate engagement & order metrics: only Valid+Paid orders count toward total_revenue
    contact_obj = Contact.objects.get(pk=contact_id)
    lead_obj = Lead.objects.create(
        contact=contact_obj,
        source='Paid Search',
        score=88,
        created_date=date(2026, 2, 1),
        status=Lead.Status.CONVERTED,
    )
    opp_obj = Opportunity.objects.create(
        lead=lead_obj,
        contact=contact_obj,
        name='NorthStar Annual Enterprise',
        stage=Opportunity.Stage.CLOSED_WON,
        expected_revenue=Decimal('120000.00'),
        actual_revenue=Decimal('120000.00'),
        closing_date=date(2026, 3, 18),
        status=Opportunity.Status.WON,
    )
    Order.objects.create(
        opportunity=opp_obj,
        contact=contact_obj,
        order_date=date(2026, 3, 18),
        revenue=Decimal('120000.00'),
        currency='USD',
        payment_status=Order.PaymentStatus.PAID,
        verification_status=Order.VerificationStatus.VALID,
    )
    # Duplicate order must NOT inflate revenue/count
    Order.objects.create(
        opportunity=opp_obj,
        contact=contact_obj,
        order_date=date(2026, 3, 19),
        revenue=Decimal('120000.00'),
        currency='USD',
        payment_status=Order.PaymentStatus.PAID,
        verification_status=Order.VerificationStatus.DUPLICATE,
    )

    detail_resp = viewer.get(f'/api/v1/contacts/{contact_id}/')
    assert detail_resp.status_code == 200
    assert detail_resp.data['data']['lead_count'] == 1
    assert detail_resp.data['data']['order_count'] == 1
    assert Decimal(detail_resp.data['data']['total_revenue']) == Decimal('120000.00')

    # Protected delete returns 409 Conflict
    del_protected = manager.delete(f'/api/v1/contacts/{contact_id}/')
    assert del_protected.status_code == 409
    assert del_protected.data['error']['code'] == 'protected_reference'

    # Unreferenced contact can be deleted cleanly
    temp_resp = manager.post(
        '/api/v1/contacts/',
        {'name': 'Temp Contact', 'email': 'temp@example.com'},
        format='json',
    )
    temp_id = temp_resp.data['data']['id']
    assert manager.delete(f'/api/v1/contacts/{temp_id}/').status_code == 200
    assert AuditLog.objects.filter(
        entity_type='Contact',
        entity_id=temp_id,
        action=AuditLog.Action.DELETE,
    ).exists()


@pytest.mark.django_db
def test_web_sessions_identity_evidence_rules_and_touchpoint_tracking():
    analyst = _client_for_role('analyst6b@attributioniq.io', UserProfile.Role.MARKETING_ANALYST)
    manager = _client_for_role('manager6b@attributioniq.io', UserProfile.Role.MARKETING_MANAGER)

    channel = Channel.objects.create(name='Google Search', channel_type=Channel.ChannelType.PAID_SEARCH)
    other_channel = Channel.objects.create(name='LinkedIn Ads', channel_type=Channel.ChannelType.PAID_SOCIAL)
    campaign = Campaign.objects.create(
        name='Q1 Search Intent',
        channel=channel,
        budget=Decimal('30000.00'),
        currency='USD',
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status=Campaign.Status.ACTIVE,
    )
    contact = Contact.objects.create(
        name='Marcus Sterling',
        email='m.sterling@veridianops.com',
        company='Veridian Ops',
        created_date=date(2026, 2, 14),
    )

    # Reject Identified session without contact or without evidence
    assert (
        manager.post(
            '/api/v1/sessions/',
            {
                'anonymous_id': 'anon-1',
                'landing_page': '/pricing',
                'timestamp': '2026-02-14T09:05:00Z',
                'identity_status': 'Identified',
            },
            format='json',
        ).status_code
        == 400
    )
    assert (
        manager.post(
            '/api/v1/sessions/',
            {
                'anonymous_id': 'anon-1',
                'contact': contact.id,
                'landing_page': '/pricing',
                'timestamp': '2026-02-14T09:05:00Z',
                'identity_status': 'Identified',
                'has_evidence': False,
            },
            format='json',
        ).status_code
        == 400
    )

    # Create Anonymous session
    anon_ses_resp = manager.post(
        '/api/v1/sessions/',
        {
            'anonymous_id': 'anon-3c44d1',
            'campaign': campaign.id,
            'landing_page': '/platform/abm-analytics',
            'referrer': 'https://www.google.com/',
            'timestamp': '2026-02-14T09:05:00Z',
            'device_type': 'Mobile',
        },
        format='json',
    )
    assert anon_ses_resp.status_code == 201
    ses_id = anon_ses_resp.data['data']['id']
    assert anon_ses_resp.data['data']['identity_status'] == 'Anonymous'
    assert anon_ses_resp.data['data']['has_evidence'] is False

    # Create an explicit Unverified Link telemetry session (for anomaly triage)
    unverified_resp = manager.post(
        '/api/v1/sessions/',
        {
            'anonymous_id': 'anon-bad-link',
            'contact': contact.id,
            'campaign': campaign.id,
            'landing_page': '/solutions',
            'timestamp': '2026-02-15T10:00:00Z',
            'identity_status': 'Unverified Link',
            'has_evidence': False,
        },
        format='json',
    )
    assert unverified_resp.status_code == 201
    unverified_ses_id = unverified_resp.data['data']['id']
    assert 'without deterministic' in unverified_resp.data['data']['linking_issue']

    # Reject linking Touchpoint to Anonymous or Unverified session
    assert (
        manager.post(
            '/api/v1/touchpoints/',
            {
                'contact': contact.id,
                'campaign': campaign.id,
                'session': ses_id,
                'interaction_type': 'Paid Search Click',
                'timestamp': '2026-02-14T09:06:00Z',
            },
            format='json',
        ).status_code
        == 400
    )
    assert (
        manager.post(
            '/api/v1/touchpoints/',
            {
                'contact': contact.id,
                'campaign': campaign.id,
                'session': unverified_ses_id,
                'interaction_type': 'Paid Search Click',
                'timestamp': '2026-02-15T10:01:00Z',
            },
            format='json',
        ).status_code
        == 400
    )

    # Analyst forbidden from link-contact; Manager without evidence returns 400
    assert (
        analyst.post(
            f'/api/v1/sessions/{ses_id}/link-contact/',
            {'contact_id': contact.id, 'evidence_type': 'Form Submission'},
            format='json',
        ).status_code
        == 403
    )
    assert (
        manager.post(
            f'/api/v1/sessions/{ses_id}/link-contact/',
            {'contact_id': contact.id, 'has_evidence': False, 'evidence_type': 'Form Submission'},
            format='json',
        ).status_code
        == 400
    )

    # Link anonymous session with valid Form Submission evidence
    link_ok = manager.post(
        f'/api/v1/sessions/{ses_id}/link-contact/',
        {'contact_id': contact.id, 'has_evidence': True, 'evidence_type': 'Form Submission'},
        format='json',
    )
    assert link_ok.status_code == 200
    assert link_ok.data['data']['identity_status'] == 'Identified'
    assert link_ok.data['data']['has_evidence'] is True

    # Reject mismatched campaign channel
    assert (
        manager.post(
            '/api/v1/touchpoints/',
            {
                'contact': contact.id,
                'campaign': campaign.id,
                'channel': other_channel.id,
                'interaction_type': 'Mismatch Click',
                'timestamp': '2026-02-14T09:10:00Z',
            },
            format='json',
        ).status_code
        == 400
    )

    # Reject Online touchpoint with Offline device
    assert (
        manager.post(
            '/api/v1/touchpoints/',
            {
                'contact': contact.id,
                'campaign': campaign.id,
                'interaction_type': 'Invalid Online Device',
                'timestamp': '2026-02-14T09:10:00Z',
                'device': 'Offline',
                'is_online': True,
            },
            format='json',
        ).status_code
        == 400
    )

    # Record valid Online touchpoint attached to verified session (auto-resolves channel)
    tp_online = manager.post(
        '/api/v1/touchpoints/',
        {
            'contact': contact.id,
            'campaign': campaign.id,
            'session': ses_id,
            'interaction_type': 'Paid Search Ad Click',
            'timestamp': '2026-02-14T09:05:00Z',
            'device': 'Mobile',
            'is_online': True,
            'source': 'Google Ads',
        },
        format='json',
    )
    assert tp_online.status_code == 201
    assert tp_online.data['data']['id'] == f'TOUCH-{contact.id}-000001'
    assert tp_online.data['data']['channel'] == channel.id

    # Record Offline touchpoint (auto-sets device='Offline') and Missing-Campaign touchpoint
    tp_offline = manager.post(
        '/api/v1/touchpoints/',
        {
            'contact': contact.id,
            'channel': other_channel.id,
            'interaction_type': 'Summit Booth Badge Scan',
            'timestamp': '2026-03-20T16:20:00Z',
            'is_online': False,
            'source': 'Event Field App',
        },
        format='json',
    )
    assert tp_offline.status_code == 201
    assert tp_offline.data['data']['device'] == 'Offline'
    assert tp_offline.data['data']['campaign'] is None

    # Create Valid Paid order BEFORE a post-conversion touchpoint to test auto-flagging
    lead_obj = Lead.objects.create(
        contact=contact,
        campaign=campaign,
        source='Paid Search',
        created_date=date(2026, 2, 14),
    )
    opp_obj = Opportunity.objects.create(
        lead=lead_obj,
        contact=contact,
        name='Veridian Deal',
        closing_date=date(2026, 4, 22),
    )
    ord_obj = Order.objects.create(
        opportunity=opp_obj,
        contact=contact,
        order_date=date(2026, 4, 22),
        revenue=Decimal('85000.00'),
        payment_status=Order.PaymentStatus.PAID,
        verification_status=Order.VerificationStatus.VALID,
    )

    tp_post = manager.post(
        '/api/v1/touchpoints/',
        {
            'contact': contact.id,
            'campaign': campaign.id,
            'interaction_type': 'Retargeting Banner Impression',
            'timestamp': '2026-04-29T10:15:00Z',
            'device': 'Desktop',
            'is_online': True,
        },
        format='json',
    )
    assert tp_post.status_code == 201
    assert tp_post.data['data']['is_post_conversion'] is True
    assert tp_post.data['data']['is_valid'] is False

    # Filters work properly
    missing_camp = analyst.get('/api/v1/touchpoints/?missing_campaign=true')
    assert missing_camp.status_code == 200
    assert missing_camp.data['count'] == 1

    post_conv_list = analyst.get('/api/v1/touchpoints/?is_post_conversion=true')
    assert post_conv_list.status_code == 200
    assert post_conv_list.data['count'] == 1

    # Protected delete when AttributionResult references Touchpoint returns 409 Conflict
    model_obj = AttributionModel.objects.create(
        id=AttributionModel.ModelCode.POSITION_BASED,
        name='Position Based',
        short_label='U-Shaped',
        description='40/20/40 model',
    )
    run_obj = AttributionRun.objects.create(attribution_model=model_obj)
    tp_instance = Touchpoint.objects.get(pk=tp_online.data['data']['id'])
    AttributionResult.objects.create(
        run=run_obj,
        attribution_model=model_obj,
        order=ord_obj,
        touchpoint=tp_instance,
        campaign=campaign,
        channel=channel,
        contact=contact,
        credit_weight=Decimal('1.000000'),
        attributed_revenue=Decimal('85000.00'),
        source_order_revenue=Decimal('85000.00'),
    )
    assert manager.delete(f'/api/v1/touchpoints/{tp_instance.id}/').status_code == 409


@pytest.mark.django_db
def test_contact_customer_journey_endpoint_chronology_and_attribution_credits():
    analyst = _client_for_role('analyst6c@attributioniq.io', UserProfile.Role.MARKETING_ANALYST)

    channel = Channel.objects.create(name='Email Nurture', channel_type=Channel.ChannelType.EMAIL)
    campaign = Campaign.objects.create(
        name='Q2 Executive Nurture',
        channel=channel,
        budget=Decimal('15000.00'),
        currency='USD',
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    contact = Contact.objects.create(
        name='Hannah Lindqvist',
        email='hannah@nordicpay.eu',
        company='NordicPay Systems',
        created_date=date(2026, 3, 10),
        lifecycle_status=Contact.LifecycleStatus.CUSTOMER,
    )
    tp = Touchpoint.objects.create(
        contact=contact,
        campaign=campaign,
        channel=channel,
        interaction_type='Case Study Email Click',
        timestamp=datetime(2026, 3, 15, 11, 20, tzinfo=timezone.utc),
        device=Touchpoint.DeviceType.DESKTOP,
        is_online=True,
    )
    lead_obj = Lead.objects.create(
        contact=contact,
        campaign=campaign,
        source='Email',
        score=90,
        created_date=date(2026, 3, 20),
        status=Lead.Status.CONVERTED,
    )
    opp_obj = Opportunity.objects.create(
        lead=lead_obj,
        contact=contact,
        name='NordicPay Platform License',
        stage=Opportunity.Stage.CLOSED_WON,
        expected_revenue=Decimal('64000.00'),
        actual_revenue=Decimal('64000.00'),
        closing_date=date(2026, 5, 19),
        status=Opportunity.Status.WON,
    )
    ord_obj = Order.objects.create(
        opportunity=opp_obj,
        contact=contact,
        order_date=date(2026, 5, 19),
        revenue=Decimal('64000.00'),
        payment_status=Order.PaymentStatus.PAID,
        verification_status=Order.VerificationStatus.VALID,
    )
    model_obj = AttributionModel.objects.create(
        id=AttributionModel.ModelCode.FIRST_TOUCH,
        name='First Touch',
        short_label='First',
        description='100% first touch',
    )
    run_obj = AttributionRun.objects.create(
        attribution_model=model_obj,
        valid_orders_processed=1,
        total_attributed_revenue=Decimal('64000.00'),
    )
    AttributionResult.objects.create(
        run=run_obj,
        attribution_model=model_obj,
        order=ord_obj,
        touchpoint=tp,
        campaign=campaign,
        channel=channel,
        contact=contact,
        credit_weight=Decimal('1.000000'),
        attributed_revenue=Decimal('64000.00'),
        source_order_revenue=Decimal('64000.00'),
    )

    resp = analyst.get(f'/api/v1/contacts/{contact.id}/journey/?model_id=first_touch')
    assert resp.status_code == 200
    payload = resp.data['data']
    assert payload['contact']['id'] == contact.id
    assert payload['model_id'] == 'first_touch'
    assert payload['attribution_run_id'] == run_obj.id
    assert len(payload['attribution_results']) == 1
    assert Decimal(payload['attribution_results'][0]['attributed_revenue']) == Decimal('64000.00')

    stages = [e['stage_type'] for e in payload['timeline']]
    assert stages == ['Campaign Touchpoint', 'Lead Created', 'Opportunity', 'Closed Order']

