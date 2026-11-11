"""Stage 3 verification tests covering normalized models, constraints, FKs, M2M bridges, and ID generation."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from apps.accounts.models import UserProfile
from apps.attribution.models import AttributionModel, AttributionResult, AttributionRun
from apps.audiences.models import Audience
from apps.audit.models import AuditLog, IdSequence
from apps.campaigns.models import (
    Campaign,
    CampaignAudience,
    CampaignCreative,
    CampaignStatusHistory,
)
from apps.channels.models import Channel
from apps.contacts.models import Contact
from apps.costs.models import CostRecord
from apps.creatives.models import Creative
from apps.exceptions.models import DataException
from apps.leads.models import Lead
from apps.opportunities.models import Opportunity
from apps.orders.models import Order
from apps.touchpoints.models import Touchpoint
from apps.validation.models import ValidationCheckResult, ValidationRun
from apps.web_sessions.models import WebSession

User = get_user_model()


@pytest.mark.django_db
def test_end_to_end_relational_hierarchy_and_deterministic_ids():
    user = User.objects.create_user(username='alex', email='alex@attributioniq.io', password='pw')
    profile = UserProfile.objects.create(
        user=user,
        role=UserProfile.Role.ADMIN,
        department='Revenue Operations',
    )
    assert profile.user_code == 'USR-2026-0001'

    channel = Channel.objects.create(
        name='Google Paid Search',
        channel_type=Channel.ChannelType.PAID_SEARCH,
        owner='Sarah Chen',
    )
    assert channel.id == 'CHN-2026-000001'

    audience = Audience.objects.create(
        name='North America RevOps',
        audience_type=Audience.AudienceType.INTENT_KEYWORDS,
        estimated_size=48500,
    )
    assert audience.id == 'AUD-2026-000001'

    campaign = Campaign.objects.create(
        name='Q1 Enterprise Search Intent',
        channel=channel,
        budget=Decimal('50000.00'),
        currency='USD',
        start_date=date(2026, 1, 5),
        end_date=date(2026, 3, 31),
        status=Campaign.Status.ACTIVE,
        created_by=user,
    )
    assert campaign.id == 'CMP-2026-000001'

    creative = Creative.objects.create(
        name='Search RSA',
        primary_campaign=campaign,
        creative_type=Creative.CreativeType.RESPONSIVE_SEARCH_AD,
        start_date=date(2026, 1, 5),
        end_date=date(2026, 3, 31),
    )
    assert creative.id == 'CRT-2026-000001'

    # Many-to-Many bridge tables
    cc = CampaignCreative.objects.create(campaign=campaign, creative=creative, is_primary=True)
    ca = CampaignAudience.objects.create(campaign=campaign, audience=audience, is_primary=True)
    assert campaign.creatives.count() == 1
    assert campaign.audiences.count() == 1
    assert cc.is_primary and ca.is_primary

    CampaignStatusHistory.objects.create(
        campaign=campaign,
        previous_status='Draft',
        new_status='Active',
        changed_by=user,
        reason='Launch approved',
    )

    contact = Contact.objects.create(
        name='Claire Bennett',
        email='c.bennett@northstarcloud.io',
        company='NorthStar Cloud Inc.',
        created_date=date(2026, 1, 18),
        lifecycle_status=Contact.LifecycleStatus.CUSTOMER,
    )
    assert contact.id == 'CON-2026-000001'

    session = WebSession.objects.create(
        anonymous_id='anon-8f12a9',
        contact=contact,
        campaign=campaign,
        landing_page='/solutions/attribution',
        timestamp=datetime(2026, 1, 18, 10, 14, tzinfo=timezone.utc),
        identity_status=WebSession.IdentityStatus.IDENTIFIED,
        has_evidence=True,
        evidence_type='Form Submission',
    )
    assert session.id == 'SES-2026-000001'

    tp1 = Touchpoint.objects.create(
        contact=contact,
        campaign=campaign,
        channel=channel,
        creative=creative,
        session=session,
        interaction_type='Paid Search Ad Click',
        timestamp=datetime(2026, 1, 18, 10, 14, tzinfo=timezone.utc),
    )
    tp2 = Touchpoint.objects.create(
        contact=contact,
        campaign=None,  # Missing campaign identifier allowed cleanly
        channel=channel,
        interaction_type='Offline Event',
        timestamp=datetime(2026, 2, 10, 12, 0, tzinfo=timezone.utc),
        device=Touchpoint.DeviceType.OFFLINE,
        is_online=False,
    )
    assert tp1.id == 'TOUCH-CON-2026-000001-000001'
    assert tp2.id == 'TOUCH-CON-2026-000001-000002'

    lead = Lead.objects.create(
        contact=contact,
        campaign=campaign,
        source='Paid Search',
        score=92,
        created_date=date(2026, 2, 26),
        status=Lead.Status.CONVERTED,
    )
    assert lead.id == 'LEAD-2026-000001'

    opp = Opportunity.objects.create(
        lead=lead,
        contact=contact,
        name='NorthStar Cloud License',
        stage=Opportunity.Stage.CLOSED_WON,
        expected_revenue=Decimal('115000.00'),
        actual_revenue=Decimal('120000.00'),
        closing_date=date(2026, 3, 18),
        status=Opportunity.Status.WON,
    )
    assert opp.id == 'OPP-2026-000001'

    order = Order.objects.create(
        opportunity=opp,
        contact=contact,
        order_date=date(2026, 3, 18),
        revenue=Decimal('120000.00'),
        currency='USD',
        payment_status=Order.PaymentStatus.PAID,
        verification_status=Order.VerificationStatus.VALID,
    )
    assert order.id == 'ORD-2026-000001'

    # Duplicate revenue scenario: sharing same opportunity FK is allowed and flagged cleanly
    dup_order = Order.objects.create(
        opportunity=opp,
        contact=contact,
        order_date=date(2026, 3, 19),
        revenue=Decimal('120000.00'),
        currency='USD',
        verification_status=Order.VerificationStatus.DUPLICATE,
    )
    assert dup_order.id == 'ORD-2026-000002'

    cost = CostRecord.objects.create(
        campaign=campaign,
        channel=channel,
        amount=Decimal('28000.00'),
        currency='USD',
        spend_date=date(2026, 1, 31),
    )
    assert cost.id == 'COST-2026-000001'

    model_cfg = AttributionModel.objects.create(
        id=AttributionModel.ModelCode.POSITION_BASED,
        name='Position Based',
        short_label='Position Based',
        description='40/20/40 U-shaped attribution',
    )
    run = AttributionRun.objects.create(
        attribution_model=model_cfg,
        conversion_window_days=90,
        valid_orders_processed=1,
        total_attributed_revenue=Decimal('120000.00'),
        executed_by=user,
    )
    assert run.id == 'ATTR-RUN-2026-000001'

    res = AttributionResult.objects.create(
        run=run,
        attribution_model=model_cfg,
        order=order,
        touchpoint=tp1,
        campaign=campaign,
        channel=channel,
        contact=contact,
        credit_weight=Decimal('1.000000'),
        attributed_revenue=Decimal('120000.00'),
        source_order_revenue=Decimal('120000.00'),
    )
    assert res.id == 'ATTR-RES-2026-000001'

    exc = DataException.objects.create(
        issue_type=DataException.IssueType.DUPLICATE_REVENUE,
        entity_type=DataException.EntityType.ORDER,
        entity_id=dup_order.id,
        severity=DataException.Severity.CRITICAL,
        description='Duplicate order detected',
        expected_decision='Exclude from attribution',
        actual_decision='Flagged pending sign-off',
    )
    assert exc.id == 'EXC-2026-000001'

    val_run = ValidationRun.objects.create(total_checks=1, passed_checks=1)
    ValidationCheckResult.objects.create(
        run=val_run,
        check_code='VAL-001',
        check_name='Primary Key Uniqueness',
        category='Primary key uniqueness',
        entity='All Entities',
        records_checked=10,
        failed_records=0,
        status=ValidationCheckResult.Status.PASSED,
    )
    AuditLog.objects.create(
        entity_type='Campaign',
        entity_id=campaign.id,
        action=AuditLog.Action.CREATE,
        actor=user,
        new_state={'budget': '50000.00'},
    )
    assert IdSequence.objects.filter(scope_key='CMP-2026').exists()


@pytest.mark.django_db
def test_seed_collision_prevention_and_db_constraints():
    channel = Channel.objects.create(
        name='LinkedIn Ads',
        channel_type=Channel.ChannelType.PAID_SOCIAL,
    )
    # Seed explicit higher ID manually, then ensure next auto-ID skips cleanly
    Campaign.objects.create(
        id='CMP-2026-000008',
        name='Seeded Higher ID Campaign',
        channel=channel,
        budget=Decimal('1000.00'),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 2, 1),
    )
    next_cmp = Campaign.objects.create(
        name='Auto Increment Campaign',
        channel=channel,
        budget=Decimal('2000.00'),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 2, 1),
    )
    assert next_cmp.id == 'CMP-2026-000009'

    # Foreign-key PROTECT enforcement on referenced channel
    with pytest.raises(ProtectedError):
        channel.delete()

    # Negative budget check constraint
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Campaign.objects.create(
                name='Invalid Negative Budget',
                channel=channel,
                budget=Decimal('-100.00'),
                start_date=date(2026, 1, 1),
                end_date=date(2026, 2, 1),
            )

    # Invalid date range check constraint (end_date < start_date)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Campaign.objects.create(
                name='Invalid Date Range',
                channel=channel,
                budget=Decimal('500.00'),
                start_date=date(2026, 5, 1),
                end_date=date(2026, 4, 1),
            )

    # Duplicate M2M bridge constraint
    creative = Creative.objects.create(
        name='Carousel',
        creative_type=Creative.CreativeType.CAROUSEL_AD,
    )
    CampaignCreative.objects.create(campaign=next_cmp, creative=creative)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CampaignCreative.objects.create(campaign=next_cmp, creative=creative)

    # Lead score out of [0, 100] bounds
    contact = Contact.objects.create(
        name='Test Buyer',
        email='buyer@example.com',
        created_date=date(2026, 2, 1),
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Lead.objects.create(
                contact=contact,
                campaign=next_cmp,
                source='Organic',
                score=150,
                created_date=date(2026, 2, 2),
            )

