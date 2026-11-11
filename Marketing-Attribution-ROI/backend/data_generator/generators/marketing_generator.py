"""
Deterministic synthetic B2B marketing dataset generator (default seed: 20261022).

Supports:
  - `starter` mode: compact development/testing dataset with edge cases & 4 anomalies
  - `full` mode: 500 campaigns, 50,000 contacts, 200,000 touchpoints, 10,000 opportunities

Generates valid baseline records strictly before injecting labelled anomalies,
keeps ground-truth anomaly metadata isolated from input records, and derives
attribution results solely via the deterministic attribution engine.
"""

from datetime import date, datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
import random

from django.db import transaction

from apps.attribution.models import AttributionResult, AttributionRun
from apps.attribution.services import ensure_attribution_models_seeded, execute_attribution_run
from apps.audiences.models import Audience
from apps.audit.models import IdSequence
from apps.campaigns.models import (
    Campaign,
    CampaignAudience,
    CampaignCreative,
    CampaignStatusHistory,
)
from apps.channels.models import Channel
from apps.contacts.models import Contact, ContactLifecycleHistory
from apps.costs.models import CostRecord
from apps.creatives.models import Creative
from apps.exceptions.models import DataException
from apps.leads.models import Lead, LeadStatusHistory
from apps.opportunities.models import Opportunity, OpportunityStageHistory
from apps.orders.models import Order
from apps.touchpoints.models import Touchpoint
from apps.validation.models import ValidationCheckResult, ValidationRun
from apps.web_sessions.models import WebSession

DEFAULT_SEED = 20261022
BASE_YEAR = 2026

MODE_PRESETS = {
    'starter': {
        'campaigns': 15,
        'creatives': 20,
        'audiences': 10,
        'contacts': 60,
        'sessions': 120,
        'touchpoints': 220,
        'leads': 40,
        'opportunities': 28,
        'post_touches': 3,
        'currency_mismatches': 2,
        'omitted_cost_campaigns': 2,
        'unverified_sessions': 2,
    },
    'full': {
        'campaigns': 500,
        'creatives': 150,
        'audiences': 50,
        'contacts': 50000,
        'sessions': 65000,
        'touchpoints': 200000,
        'leads': 16000,
        'opportunities': 10000,
        'post_touches': 80,
        'currency_mismatches': 35,
        'omitted_cost_campaigns': 12,
        'unverified_sessions': 50,
    },
}

CHANNEL_DEFINITIONS = [
    ('Paid Search', Channel.ChannelType.PAID_SEARCH),
    ('Paid Social', Channel.ChannelType.PAID_SOCIAL),
    ('Lifecycle Email', Channel.ChannelType.EMAIL),
    ('Programmatic Display', Channel.ChannelType.DISPLAY),
    ('Field Events & Webinars', Channel.ChannelType.EVENTS),
    ('Organic Search & SEO', Channel.ChannelType.ORGANIC),
    ('Direct Web Traffic', Channel.ChannelType.DIRECT),
    ('Partner Referrals', Channel.ChannelType.REFERRAL),
]

COMPANIES = [
    'ApexCloud', 'FinScale', 'HeliosData', 'OrbitCloud', 'MatrixSys',
    'NordicSoft', 'VeritasFin', 'QuantumGrid', 'CobaltHealth', 'StrideAI',
    'BluePeak', 'SolsticePay', 'VanguardOps', 'ClearLedger', 'NexusBI',
]

INTERACTION_BY_CHANNEL = {
    Channel.ChannelType.PAID_SEARCH: 'Paid Search Click',
    Channel.ChannelType.PAID_SOCIAL: 'Sponsored Social Click',
    Channel.ChannelType.EMAIL: 'Nurture Email Click',
    Channel.ChannelType.DISPLAY: 'Display Banner Impression',
    Channel.ChannelType.EVENTS: 'Executive Briefing Attendance',
    Channel.ChannelType.ORGANIC: 'Organic Article Visit',
    Channel.ChannelType.DIRECT: 'Direct Pricing Visit',
    Channel.ChannelType.REFERRAL: 'Partner Referral Click',
}


def _fmt_id(prefix: str, seq: int) -> str:
    return f'{prefix}-{BASE_YEAR}-{seq:06d}'


@transaction.atomic
def reset_marketing_dataset() -> None:
    """Safely wipe generated marketing domain data in reverse foreign-key dependency order."""
    AttributionResult.objects.all().delete()
    AttributionRun.objects.all().delete()
    ValidationCheckResult.objects.all().delete()
    ValidationRun.objects.all().delete()
    DataException.objects.all().delete()
    CostRecord.objects.all().delete()
    Order.objects.all().delete()
    OpportunityStageHistory.objects.all().delete()
    Opportunity.objects.all().delete()
    LeadStatusHistory.objects.all().delete()
    Lead.objects.all().delete()
    Touchpoint.objects.all().delete()
    WebSession.objects.all().delete()
    ContactLifecycleHistory.objects.all().delete()
    Contact.objects.all().delete()
    CampaignCreative.objects.all().delete()
    CampaignAudience.objects.all().delete()
    CampaignStatusHistory.objects.all().delete()
    Campaign.objects.all().delete()
    Creative.objects.all().delete()
    Audience.objects.all().delete()
    Channel.objects.all().delete()
    IdSequence.objects.all().delete()


def _upsert_sequences(seq_map: dict[str, int]) -> None:
    """Synchronize IdSequence table so subsequent single-row API saves never collide."""
    objs = [IdSequence(scope_key=key, last_value=val) for key, val in seq_map.items()]
    IdSequence.objects.bulk_create(
        objs,
        batch_size=5000,
        update_conflicts=True,
        update_fields=['last_value'],
    )


def generate_marketing_dataset(
    *,
    mode: str = 'starter',
    seed: int = DEFAULT_SEED,
    reset: bool = True,
    with_attribution: bool = False,
) -> dict:
    """
    Deterministically generate a complete relational marketing & attribution dataset.
    Returns summary counts plus isolated ground-truth anomaly manifest.
    """
    if mode not in MODE_PRESETS:
        raise ValueError(f'Unsupported generator mode "{mode}". Expected starter or full.')

    preset = MODE_PRESETS[mode]
    rng = random.Random(seed)
    ensure_attribution_models_seeded()

    if reset:
        reset_marketing_dataset()

    # 1. Channels
    channels = [
        Channel(
            id=_fmt_id('CH', idx),
            name=name,
            channel_type=ch_type,
            status=Channel.Status.ACTIVE,
        )
        for idx, (name, ch_type) in enumerate(CHANNEL_DEFINITIONS, start=1)
    ]
    Channel.objects.bulk_create(channels, batch_size=100)

    # 2. Campaigns (Baseline valid parent campaigns)
    num_campaigns = preset['campaigns']
    omitted_cost_target = preset['omitted_cost_campaigns']
    campaigns: list[Campaign] = []
    omitted_cost_campaign_ids: set[str] = set()

    for idx in range(1, num_campaigns + 1):
        ch = channels[(idx - 1) % len(channels)]
        is_organic = ch.channel_type in (
            Channel.ChannelType.ORGANIC,
            Channel.ChannelType.DIRECT,
            Channel.ChannelType.REFERRAL,
        )
        is_paid = not is_organic
        start_month = rng.randint(1, 5)
        start_d = date(BASE_YEAR, start_month, rng.randint(1, 20))
        end_d = date(BASE_YEAR, min(12, start_month + rng.randint(4, 7)), rng.randint(21, 28))
        budget = Decimal('0.00') if is_organic else Decimal(rng.randint(8, 120) * 1000)

        cmp_id = _fmt_id('CMP', idx)
        # Reserve the last K paid campaigns as dedicated omitted-cost baseline campaigns
        # (valid campaign entity, but no CostRecord entries generated)
        campaigns.append(
            Campaign(
                id=cmp_id,
                name=f'{ch.name} Initiative {idx:03d}',
                channel=ch,
                budget=budget,
                currency='USD',
                start_date=start_d,
                end_date=end_d,
                objective='Demand Generation' if idx % 2 else 'Pipeline Generation',
                status=Campaign.Status.ACTIVE,
                is_paid_campaign=is_paid,
            )
        )

    Campaign.objects.bulk_create(campaigns, batch_size=1000)
    paid_campaigns = [c for c in campaigns if c.is_paid_campaign]
    for cmp_obj in paid_campaigns[-omitted_cost_target:]:
        omitted_cost_campaign_ids.add(cmp_obj.id)

    # 3. Creatives & Audiences + M2M Bridges
    creatives = [
        Creative(
            id=_fmt_id('CRT', idx),
            name=f'Creative Asset {idx:03d}',
            primary_campaign=campaigns[(idx - 1) % len(campaigns)],
            creative_type=list(Creative.CreativeType.values)[(idx - 1) % len(Creative.CreativeType.values)],
            status=Creative.Status.ACTIVE,
        )
        for idx in range(1, preset['creatives'] + 1)
    ]
    Creative.objects.bulk_create(creatives, batch_size=1000)

    audiences = [
        Audience(
            id=_fmt_id('AUD', idx),
            name=f'Target Segment {idx:03d}',
            audience_type=list(Audience.AudienceType.values)[(idx - 1) % len(Audience.AudienceType.values)],
            estimated_size=rng.randint(2500, 95000),
            status=Audience.Status.ACTIVE,
        )
        for idx in range(1, preset['audiences'] + 1)
    ]
    Audience.objects.bulk_create(audiences, batch_size=1000)

    cc_bridges = [
        CampaignCreative(
            campaign=c,
            creative=creatives[idx % len(creatives)],
            is_primary=True,
            effective_from=c.start_date,
            effective_to=c.end_date,
        )
        for idx, c in enumerate(campaigns)
    ]
    CampaignCreative.objects.bulk_create(cc_bridges, batch_size=2000)

    ca_bridges = [
        CampaignAudience(
            campaign=c,
            audience=audiences[idx % len(audiences)],
            is_primary=True,
            effective_from=c.start_date,
            effective_to=c.end_date,
        )
        for idx, c in enumerate(campaigns)
    ]
    CampaignAudience.objects.bulk_create(ca_bridges, batch_size=2000)

    # 4. Contacts
    num_contacts = preset['contacts']
    contacts: list[Contact] = []
    lifecycle_choices = list(Contact.LifecycleStatus.values)
    for idx in range(1, num_contacts + 1):
        c_date = date(BASE_YEAR, 1, 1) + timedelta(days=rng.randint(0, 210))
        company = COMPANIES[idx % len(COMPANIES)]
        contacts.append(
            Contact(
                id=_fmt_id('CON', idx),
                name=f'Buyer Contact {idx:05d}',
                email=f'buyer.{idx:06d}@{company.lower()}.example',
                company=company,
                source='Paid Search' if idx % 3 == 0 else 'Organic',
                created_date=c_date,
                lifecycle_status=lifecycle_choices[idx % len(lifecycle_choices)],
            )
        )
    Contact.objects.bulk_create(contacts, batch_size=5000)

    # 5. Baseline Valid WebSessions (identified with deterministic evidence)
    num_sessions = preset['sessions']
    sessions: list[WebSession] = []
    evidence_types = ('Form Submission', 'Login Token', 'Email Click ID')
    for idx in range(1, num_sessions + 1):
        con = contacts[(idx - 1) % num_contacts]
        cmp_obj = campaigns[(idx - 1) % num_campaigns]
        ts = datetime(
            BASE_YEAR, 1, 1, 8, 0, tzinfo=dt_timezone.utc
        ) + timedelta(days=rng.randint(5, 250), hours=rng.randint(0, 12))
        sessions.append(
            WebSession(
                id=_fmt_id('SES', idx),
                anonymous_id=f'anon-{seed % 10000}-{idx:06d}',
                contact=con,
                campaign=cmp_obj,
                landing_page='/pricing' if idx % 2 == 0 else '/demo',
                referrer='google.com' if idx % 2 == 0 else 'linkedin.com',
                timestamp=ts,
                device_type=WebSession.DeviceType.DESKTOP if idx % 3 else WebSession.DeviceType.MOBILE,
                identity_status=WebSession.IdentityStatus.IDENTIFIED,
                has_evidence=True,
                evidence_type=evidence_types[idx % len(evidence_types)],
            )
        )
    WebSession.objects.bulk_create(sessions, batch_size=5000)

    # 6. Leads, Opportunities & Valid Paid Orders (generated with anchored closing dates
    # so baseline pre-conversion touchpoints naturally precede conversion chronologically!)
    num_leads = preset['leads']
    leads: list[Lead] = []
    lead_by_id: dict[str, Lead] = {}
    lead_opps_count = preset['opportunities']

    for idx in range(1, num_leads + 1):
        con = contacts[(idx - 1) % num_contacts]
        cmp_obj = campaigns[(idx - 1) % num_campaigns]
        created_d = date(BASE_YEAR, 3, 1) + timedelta(days=rng.randint(0, 140))
        if idx <= lead_opps_count:
            l_status = Lead.Status.CONVERTED
            conv_dt = datetime(
                created_d.year, created_d.month, created_d.day, 14, 0, tzinfo=dt_timezone.utc
            ) + timedelta(days=rng.randint(1, 5))
        else:
            l_status = Lead.Status.MQL if idx % 2 == 0 else Lead.Status.SQL
            conv_dt = None
        ld = Lead(
            id=_fmt_id('LEAD', idx),
            contact=con,
            campaign=cmp_obj,
            source=cmp_obj.channel.channel_type,
            score=rng.randint(55, 98),
            created_date=created_d,
            status=l_status,
            converted_at=conv_dt,
        )
        leads.append(ld)
        lead_by_id[ld.id] = ld
    Lead.objects.bulk_create(leads, batch_size=5000)

    opportunities: list[Opportunity] = []
    valid_orders: list[Order] = []
    order_seq = 0
    contact_conversion_cutoff: dict[str, date] = {}
    open_stages = (
        Opportunity.Stage.QUALIFICATION,
        Opportunity.Stage.PROPOSAL,
        Opportunity.Stage.NEGOTIATION,
    )

    for idx in range(1, lead_opps_count + 1):
        ld = leads[idx - 1]
        base_d = ld.created_date
        close_d = base_d + timedelta(days=rng.randint(25, 75))
        if close_d > date(BASE_YEAR, 10, 28):
            close_d = date(BASE_YEAR, 10, rng.randint(15, 28))

        roll = idx % 10
        if roll < 6:
            stage = Opportunity.Stage.CLOSED_WON
            status_val = Opportunity.Status.WON
            expected_rev = Decimal(rng.randint(4, 30) * 1000)
            actual_rev = expected_rev
        elif roll < 8:
            stage = Opportunity.Stage.CLOSED_LOST
            status_val = Opportunity.Status.LOST
            expected_rev = Decimal(rng.randint(4, 25) * 1000)
            actual_rev = Decimal('0.00')
        else:
            stage = open_stages[idx % len(open_stages)]
            status_val = Opportunity.Status.OPEN
            expected_rev = Decimal(rng.randint(5, 35) * 1000)
            actual_rev = Decimal('0.00')

        opp = Opportunity(
            id=_fmt_id('OPP', idx),
            lead=ld,
            contact_id=ld.contact_id,
            name=f'Enterprise Deal {idx:05d}',
            stage=stage,
            expected_revenue=expected_rev,
            actual_revenue=actual_rev,
            closing_date=close_d,
            status=status_val,
        )
        opportunities.append(opp)

        if status_val == Opportunity.Status.WON:
            order_seq += 1
            valid_orders.append(
                Order(
                    id=_fmt_id('ORD', order_seq),
                    opportunity=opp,
                    contact_id=opp.contact_id,
                    order_date=close_d,
                    revenue=actual_rev,
                    currency='USD',
                    payment_status=Order.PaymentStatus.PAID,
                    verification_status=Order.VerificationStatus.VALID,
                )
            )
            prev = contact_conversion_cutoff.get(opp.contact_id)
            if prev is None or close_d < prev:
                contact_conversion_cutoff[opp.contact_id] = close_d

    Opportunity.objects.bulk_create(opportunities, batch_size=5000)
    Order.objects.bulk_create(valid_orders, batch_size=5000)

    # 7. Baseline Eligible Touchpoints (online + offline + missing campaign + long conversion windows)
    # Guarantee converted contacts have multi-campaign pre-conversion journeys strictly <= order_date!
    num_tps = preset['touchpoints']
    touchpoints: list[Touchpoint] = []
    tp_seq_by_contact: dict[str, int] = {}

    def _next_tp_id(con_id: str) -> str:
        next_val = tp_seq_by_contact.get(con_id, 0) + 1
        tp_seq_by_contact[con_id] = next_val
        return f'TOUCH-{con_id}-{next_val:06d}'

    # Guarantee 3 pre-conversion touches (including offline and multi-campaign) for early converted contacts,
    # and distribute remaining baseline touchpoints uniformly across all contacts.
    sessions_by_contact: dict[str, WebSession] = {}
    for s in sessions:
        if s.contact_id:
            sessions_by_contact.setdefault(s.contact_id, s)

    for ord_idx, ord_obj in enumerate(valid_orders):
        if len(touchpoints) + 3 > num_tps:
            break
        order_dt = datetime(
            ord_obj.order_date.year,
            ord_obj.order_date.month,
            ord_obj.order_date.day,
            12,
            0,
            tzinfo=dt_timezone.utc,
        )
        # Span long conversion window (up to 75 days) & multi-campaign touches
        offsets = [rng.randint(35, 75), rng.randint(12, 30), rng.randint(1, 10)]
        for step_idx, days_back in enumerate(offsets):
            tp_dt = order_dt - timedelta(days=days_back, hours=rng.randint(1, 6))
            cmp_obj = campaigns[(ord_idx + step_idx * 3) % num_campaigns]
            is_missing_cmp = (ord_idx % 12 == 0 and step_idx == 1)
            is_offline = (step_idx == 1 and ord_idx % 4 == 0)
            ch_obj = cmp_obj.channel
            crt_obj = creatives[(ord_idx + step_idx) % len(creatives)]
            ses_obj = None if is_offline else sessions_by_contact.get(ord_obj.contact_id)
            if ses_obj and ses_obj.timestamp > tp_dt:
                ses_obj = None

            touchpoints.append(
                Touchpoint(
                    id=_next_tp_id(ord_obj.contact_id),
                    contact_id=ord_obj.contact_id,
                    campaign=None if is_missing_cmp else cmp_obj,
                    channel=ch_obj,
                    creative=crt_obj,
                    session=ses_obj,
                    interaction_type=INTERACTION_BY_CHANNEL[ch_obj.channel_type],
                    timestamp=tp_dt,
                    device=Touchpoint.DeviceType.OFFLINE if is_offline else Touchpoint.DeviceType.DESKTOP,
                    is_online=not is_offline,
                    source=ch_obj.channel_type,
                    is_post_conversion=False,
                    is_valid=True,
                )
            )

    remaining_tps = max(0, num_tps - len(touchpoints))
    for i in range(remaining_tps):
        con = contacts[i % num_contacts]
        cutoff_d = contact_conversion_cutoff.get(con.id)
        if cutoff_d is not None:
            # Anchor strictly pre-conversion so baseline contains zero accidental post-conversion touches
            max_dt = datetime(cutoff_d.year, cutoff_d.month, cutoff_d.day, 18, 0, tzinfo=dt_timezone.utc)
            tp_dt = max_dt - timedelta(days=rng.randint(1, 80), hours=rng.randint(0, 12))
        else:
            tp_dt = datetime(BASE_YEAR, 1, 5, 10, 0, tzinfo=dt_timezone.utc) + timedelta(
                days=rng.randint(0, 260), hours=rng.randint(0, 12)
            )
        cmp_obj = campaigns[i % num_campaigns]
        is_offline = (i % 7 == 0)
        is_missing_cmp = (i % 15 == 0)
        ch_obj = cmp_obj.channel
        crt_obj = creatives[i % len(creatives)]

        touchpoints.append(
            Touchpoint(
                id=_next_tp_id(con.id),
                contact=con,
                campaign=None if is_missing_cmp else cmp_obj,
                channel=ch_obj,
                creative=crt_obj,
                interaction_type=INTERACTION_BY_CHANNEL[ch_obj.channel_type],
                timestamp=tp_dt,
                device=Touchpoint.DeviceType.OFFLINE if is_offline else Touchpoint.DeviceType.DESKTOP,
                is_online=not is_offline,
                source=ch_obj.channel_type,
                is_post_conversion=False,
                is_valid=True,
            )
        )

    Touchpoint.objects.bulk_create(touchpoints, batch_size=5000)

    # 8. Baseline CostRecords (USD matched to paid non-omitted campaigns)
    cost_seq = 0
    baseline_costs: list[CostRecord] = []
    for cmp_obj in paid_campaigns:
        if cmp_obj.id in omitted_cost_campaign_ids:
            continue
        for m_offset in range(3):
            cost_seq += 1
            spend_d = min(
                date(BASE_YEAR, 10, 25),
                cmp_obj.start_date + timedelta(days=m_offset * 28 + 3),
            )
            baseline_costs.append(
                CostRecord(
                    id=_fmt_id('COST', cost_seq),
                    campaign=cmp_obj,
                    channel_id=cmp_obj.channel_id,
                    category=CostRecord.Category.MEDIA_SPEND,
                    amount=Decimal(rng.randint(800, 4500)),
                    currency='USD',
                    spend_date=spend_d,
                    description=f'Verified monthly media invoice for {cmp_obj.id}',
                )
            )
    CostRecord.objects.bulk_create(baseline_costs, batch_size=5000)

    # =========================================================================
    # STAGE B: Isolated Anomaly Injection (Strictly AFTER Baseline Generation)
    # Ground-truth labels kept ONLY in `anomaly_manifest`, never in model features.
    # =========================================================================
    anomaly_manifest: list[dict] = []

    # Anomaly 2: Post-conversion Touchpoints
    injected_post_tps: list[Touchpoint] = []
    for idx in range(min(preset['post_touches'], len(valid_orders))):
        src_ord = valid_orders[idx]
        cmp_obj = paid_campaigns[idx % len(paid_campaigns)]
        tp_id = _next_tp_id(src_ord.contact_id)
        post_dt = datetime(
            src_ord.order_date.year,
            src_ord.order_date.month,
            src_ord.order_date.day,
            10,
            0,
            tzinfo=dt_timezone.utc,
        ) + timedelta(days=4)
        injected_post_tps.append(
            Touchpoint(
                id=tp_id,
                contact_id=src_ord.contact_id,
                campaign=cmp_obj,
                channel_id=cmp_obj.channel_id,
                interaction_type='Post-Purchase Retargeting Impression',
                timestamp=post_dt,
                is_online=True,
                is_post_conversion=True,
                is_valid=False,
                validation_notes='Post-conversion touchpoint occurred after closed order date.',
            )
        )
        anomaly_manifest.append(
            {
                'issue_type': 'Touchpoint after conversion attributed',
                'entity_type': 'Touchpoint',
                'entity_id': tp_id,
                'order_id': src_ord.id,
            }
        )
    Touchpoint.objects.bulk_create(injected_post_tps, batch_size=1000)

    # Anomaly 3: Spend Currency Mismatch
    injected_fx_costs: list[CostRecord] = []
    eligible_paid = [c for c in paid_campaigns if c.id not in omitted_cost_campaign_ids]
    for idx in range(min(preset['currency_mismatches'], len(eligible_paid))):
        cmp_obj = eligible_paid[idx]
        cost_seq += 1
        cost_id = _fmt_id('COST', cost_seq)
        injected_fx_costs.append(
            CostRecord(
                id=cost_id,
                campaign=cmp_obj,
                channel_id=cmp_obj.channel_id,
                category=CostRecord.Category.AGENCY,
                amount=Decimal('2500.00'),
                currency='EUR' if idx % 2 == 0 else 'GBP',
                spend_date=min(date(BASE_YEAR, 10, 20), cmp_obj.start_date + timedelta(days=15)),
                description='Unconverted foreign agency invoice',
            )
        )
        anomaly_manifest.append(
            {
                'issue_type': 'Spend currency mismatch',
                'entity_type': 'Cost',
                'entity_id': cost_id,
                'campaign_id': cmp_obj.id,
            }
        )
    CostRecord.objects.bulk_create(injected_fx_costs, batch_size=1000)

    # Anomaly 4: Omitted Paid Campaign Costs (ensure touchpoints exist for those campaigns)
    for cmp_id in sorted(omitted_cost_campaign_ids):
        anomaly_manifest.append(
            {
                'issue_type': 'Campaign costs omitted',
                'entity_type': 'Campaign',
                'entity_id': cmp_id,
            }
        )

    # Anomaly 5: Anonymous Sessions Linked Without Evidence
    ses_seq = num_sessions
    injected_unverified_sessions: list[WebSession] = []
    injected_unverified_tps: list[Touchpoint] = []
    for idx in range(preset['unverified_sessions']):
        ses_seq += 1
        ses_id = _fmt_id('SES', ses_seq)
        con = contacts[(idx + 10) % num_contacts]
        cmp_obj = campaigns[idx % num_campaigns]
        ts = datetime(BASE_YEAR, 4, 15, 11, 0, tzinfo=dt_timezone.utc) + timedelta(days=idx)
        ses = WebSession(
            id=ses_id,
            anonymous_id=f'anon-unverified-{seed}-{idx:04d}',
            contact=con,
            campaign=cmp_obj,
            landing_page='/whitepaper',
            referrer='Direct',
            timestamp=ts,
            identity_status=WebSession.IdentityStatus.UNVERIFIED_LINK,
            has_evidence=False,
            linking_issue='Probabilistic IP correlation without login or form token.',
        )
        injected_unverified_sessions.append(ses)
        tp_id = _next_tp_id(con.id)
        injected_unverified_tps.append(
            Touchpoint(
                id=tp_id,
                contact=con,
                campaign=cmp_obj,
                channel_id=cmp_obj.channel_id,
                session_id=ses_id,
                interaction_type='Unverified Anonymous Visit',
                timestamp=ts + timedelta(minutes=2),
                is_online=True,
                is_valid=True,
            )
        )
        anomaly_manifest.append(
            {
                'issue_type': 'Anonymous session linked without evidence',
                'entity_type': 'Session',
                'entity_id': ses_id,
                'contact_id': con.id,
            }
        )
    WebSession.objects.bulk_create(injected_unverified_sessions, batch_size=1000)
    Touchpoint.objects.bulk_create(injected_unverified_tps, batch_size=1000)

    # Sync IdSequence counters for collision-free future API inserts
    seq_updates = {
        f'CH:{BASE_YEAR}': len(channels),
        f'CRT:{BASE_YEAR}': len(creatives),
        f'AUD:{BASE_YEAR}': len(audiences),
        f'CMP:{BASE_YEAR}': len(campaigns),
        f'CON:{BASE_YEAR}': len(contacts),
        f'SES:{BASE_YEAR}': ses_seq,
        f'LEAD:{BASE_YEAR}': len(leads),
        f'OPP:{BASE_YEAR}': len(opportunities),
        f'ORD:{BASE_YEAR}': order_seq,
        f'COST:{BASE_YEAR}': cost_seq,
    }
    for con_id, tp_last in tp_seq_by_contact.items():
        seq_updates[f'TOUCH:{con_id}'] = tp_last
    _upsert_sequences(seq_updates)

    attribution_summary = None
    if with_attribution:
        attr_run = execute_attribution_run(
            model_id='position_based',
            conversion_window_days=90,
            period_label=f'Seed {seed} ({mode})',
            persist=True,
        )
        attribution_summary = {
            'run_id': attr_run['run_id'],
            'valid_orders_processed': attr_run['valid_orders_processed'],
            'total_attributed_revenue': str(attr_run['total_attributed_revenue']),
        }

    return {
        'mode': mode,
        'seed': seed,
        'counts': {
            'channels': len(channels),
            'campaigns': len(campaigns),
            'creatives': len(creatives),
            'audiences': len(audiences),
            'contacts': len(contacts),
            'web_sessions': ses_seq,
            'touchpoints': len(touchpoints) + len(injected_post_tps) + len(injected_unverified_tps),
            'leads': len(leads),
            'opportunities': len(opportunities),
            'orders': len(valid_orders),
            'cost_records': len(baseline_costs) + len(injected_fx_costs),
            'injected_anomalies': len(anomaly_manifest),
        },
        'anomaly_manifest': anomaly_manifest,
        'attribution_run': attribution_summary,
    }
