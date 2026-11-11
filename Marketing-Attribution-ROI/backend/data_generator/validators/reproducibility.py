"""Reproducibility and deterministic SHA-256 dataset checksum verification."""

import hashlib
import json

from apps.audiences.models import Audience
from apps.campaigns.models import Campaign
from apps.channels.models import Channel
from apps.contacts.models import Contact
from apps.costs.models import CostRecord
from apps.creatives.models import Creative
from apps.leads.models import Lead
from apps.opportunities.models import Opportunity
from apps.orders.models import Order
from apps.touchpoints.models import Touchpoint
from apps.web_sessions.models import WebSession


def compute_dataset_fingerprint() -> dict:
    """
    Compute deterministic row counts and per-entity SHA-256 checksums across all
    canonical domain columns (excluding wall-clock auto_now timestamps).
    """
    specs = [
        ('channels', Channel.objects.order_by('id').values_list('id', 'name', 'channel_type', 'status')),
        (
            'campaigns',
            Campaign.objects.order_by('id').values_list(
                'id', 'name', 'channel_id', 'budget', 'currency', 'start_date', 'end_date', 'is_paid_campaign'
            ),
        ),
        ('creatives', Creative.objects.order_by('id').values_list('id', 'name', 'primary_campaign_id', 'creative_type')),
        ('audiences', Audience.objects.order_by('id').values_list('id', 'name', 'audience_type', 'estimated_size')),
        ('contacts', Contact.objects.order_by('id').values_list('id', 'name', 'email', 'company', 'created_date')),
        (
            'web_sessions',
            WebSession.objects.order_by('id').values_list(
                'id', 'anonymous_id', 'contact_id', 'campaign_id', 'timestamp', 'identity_status', 'has_evidence'
            ),
        ),
        (
            'touchpoints',
            Touchpoint.objects.order_by('id').values_list(
                'id', 'contact_id', 'campaign_id', 'channel_id', 'interaction_type', 'timestamp', 'is_online', 'is_post_conversion'
            ),
        ),
        ('leads', Lead.objects.order_by('id').values_list('id', 'contact_id', 'campaign_id', 'score', 'status', 'created_date')),
        (
            'opportunities',
            Opportunity.objects.order_by('id').values_list(
                'id', 'lead_id', 'contact_id', 'stage', 'status', 'expected_revenue', 'actual_revenue', 'closing_date'
            ),
        ),
        (
            'orders',
            Order.objects.order_by('id').values_list(
                'id', 'opportunity_id', 'contact_id', 'order_date', 'revenue', 'currency', 'payment_status', 'verification_status'
            ),
        ),
        (
            'costs',
            CostRecord.objects.order_by('id').values_list(
                'id', 'campaign_id', 'channel_id', 'category', 'amount', 'currency', 'spend_date'
            ),
        ),
    ]

    row_counts: dict[str, int] = {}
    table_hashes: dict[str, str] = {}
    overall = hashlib.sha256()

    for table_name, qs in specs:
        hasher = hashlib.sha256()
        count = 0
        for row in qs.iterator(chunk_size=5000):
            count += 1
            encoded = json.dumps([str(v) if v is not None else None for v in row]).encode('utf-8')
            hasher.update(encoded)
            hasher.update(b'\n')
        digest = hasher.hexdigest()
        row_counts[table_name] = count
        table_hashes[table_name] = digest
        overall.update(f'{table_name}:{count}:{digest}\n'.encode('utf-8'))

    return {
        'row_counts': row_counts,
        'table_checksums': table_hashes,
        'overall_checksum': overall.hexdigest(),
    }

