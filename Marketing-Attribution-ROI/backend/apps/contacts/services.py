"""Contact lifecycle management, audit logging, O(1) engagement metrics, and customer journey services."""

from datetime import datetime, time, timezone as dt_timezone
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import Count, ProtectedError, Sum
from django.utils import timezone

from apps.attribution.models import AttributionResult, AttributionRun
from apps.audit.models import AuditLog
from apps.contacts.models import Contact, ContactLifecycleHistory
from apps.leads.models import Lead
from apps.opportunities.models import Opportunity
from apps.orders.models import Order
from apps.touchpoints.models import Touchpoint
from apps.web_sessions.models import WebSession
from common.audit import record_audit_log
from common.exceptions import ConflictException


def serialize_contact_snapshot(contact: Contact) -> dict:
    """Capture scalar Contact fields for AuditLog tracking."""
    return {
        'id': contact.id,
        'name': contact.name,
        'email': contact.email,
        'phone': contact.phone,
        'company': contact.company,
        'source': contact.source,
        'created_date': contact.created_date.isoformat() if contact.created_date else None,
        'lifecycle_status': contact.lifecycle_status,
    }


def get_contact_metrics_map(contacts: list[Contact]) -> dict[str, dict]:
    """
    Compute touchpoint, session, lead, verified-paid order counts, and realized revenue
    for a batch of contacts using constant-count GROUP BY queries (no N+1 queries).
    """
    if not contacts:
        return {}

    contact_ids = [c.id for c in contacts]

    tp_counts = {
        row['contact_id']: row['cnt']
        for row in Touchpoint.objects.filter(contact_id__in=contact_ids)
        .order_by()
        .values('contact_id')
        .annotate(cnt=Count('id'))
    }
    ses_counts = {
        row['contact_id']: row['cnt']
        for row in WebSession.objects.filter(contact_id__in=contact_ids)
        .order_by()
        .values('contact_id')
        .annotate(cnt=Count('id'))
    }
    lead_counts = {
        row['contact_id']: row['cnt']
        for row in Lead.objects.filter(contact_id__in=contact_ids)
        .order_by()
        .values('contact_id')
        .annotate(cnt=Count('id'))
    }
    order_stats = {
        row['contact_id']: {
            'cnt': row['cnt'],
            'rev': (row['rev'] or Decimal('0.00')).quantize(Decimal('0.01')),
        }
        for row in Order.objects.filter(
            contact_id__in=contact_ids,
            verification_status=Order.VerificationStatus.VALID,
            payment_status=Order.PaymentStatus.PAID,
        )
        .order_by()
        .values('contact_id')
        .annotate(cnt=Count('id'), rev=Sum('revenue'))
    }

    metrics: dict[str, dict] = {}
    for cid in contact_ids:
        o_stat = order_stats.get(cid, {'cnt': 0, 'rev': Decimal('0.00')})
        metrics[cid] = {
            'touchpoint_count': tp_counts.get(cid, 0),
            'session_count': ses_counts.get(cid, 0),
            'lead_count': lead_counts.get(cid, 0),
            'order_count': o_stat['cnt'],
            'total_revenue': o_stat['rev'],
        }
    return metrics


@transaction.atomic
def create_contact(
    *,
    validated_data: dict,
    actor=None,
    source_ip: str | None = None,
) -> Contact:
    """Create a Contact, record initial lifecycle history entry, and log AuditLog."""
    reason = validated_data.pop('status_reason', '') or 'Contact created.'
    if not validated_data.get('created_date'):
        validated_data['created_date'] = timezone.localdate()

    contact = Contact.objects.create(**validated_data)

    ContactLifecycleHistory.objects.create(
        contact=contact,
        previous_status='',
        new_status=contact.lifecycle_status,
        notes=reason,
    )
    snapshot = serialize_contact_snapshot(contact)
    record_audit_log(
        entity_type='Contact',
        entity_id=contact.id,
        action=AuditLog.Action.CREATE,
        actor=actor,
        previous_state=None,
        new_state=snapshot,
        changed_fields=list(snapshot.keys()),
        source_ip=source_ip,
        notes=reason,
    )
    return contact


@transaction.atomic
def update_contact(
    *,
    contact: Contact,
    validated_data: dict,
    actor=None,
    source_ip: str | None = None,
) -> Contact:
    """Update Contact metadata, log lifecycle transitions, and persist AuditLog diff."""
    previous_state = serialize_contact_snapshot(contact)
    previous_status = contact.lifecycle_status
    reason = validated_data.pop('status_reason', '')

    changed_fields = []
    for field, value in validated_data.items():
        if getattr(contact, field) != value:
            setattr(contact, field, value)
            changed_fields.append(field)

    if changed_fields:
        contact.save()

    if contact.lifecycle_status != previous_status:
        note = reason or f'Lifecycle moved from {previous_status} to {contact.lifecycle_status}.'
        ContactLifecycleHistory.objects.create(
            contact=contact,
            previous_status=previous_status,
            new_status=contact.lifecycle_status,
            notes=note,
        )

    if changed_fields:
        action = (
            AuditLog.Action.STATUS_CHANGE
            if contact.lifecycle_status != previous_status
            else AuditLog.Action.UPDATE
        )
        record_audit_log(
            entity_type='Contact',
            entity_id=contact.id,
            action=action,
            actor=actor,
            previous_state=previous_state,
            new_state=serialize_contact_snapshot(contact),
            changed_fields=changed_fields,
            source_ip=source_ip,
            notes=reason or 'Contact updated.',
        )
    return contact


@transaction.atomic
def delete_contact_safely(*, contact: Contact, actor=None, source_ip: str | None = None):
    """Delete an unreferenced Contact or raise HTTP 409 Conflict if protected children exist."""
    snapshot = serialize_contact_snapshot(contact)
    cid = contact.id
    try:
        contact.delete()
    except ProtectedError as exc:
        raise ConflictException(
            'Cannot delete this contact because dependent touchpoints, leads, '
            'opportunities, or orders reference it.'
        ) from exc

    record_audit_log(
        entity_type='Contact',
        entity_id=cid,
        action=AuditLog.Action.DELETE,
        actor=actor,
        previous_state=snapshot,
        new_state=None,
        changed_fields=['deleted'],
        source_ip=source_ip,
        notes='Contact deleted.',
    )


def _date_to_utc_iso(date_val, hour: int = 12) -> datetime:
    """Convert a Date value to a timezone-aware UTC datetime for unified timeline sorting."""
    return datetime.combine(date_val, time(hour, 0, 0), tzinfo=dt_timezone.utc)


def _ensure_utc(dt: datetime) -> datetime:
    """Normalize any datetime to timezone-aware UTC."""
    if timezone.is_naive(dt):
        return dt.replace(tzinfo=dt_timezone.utc)
    return dt.astimezone(dt_timezone.utc)


def get_contact_journey(contact: Contact, *, model_id: str | None = None) -> dict:
    """
    Assemble a complete chronological customer journey across touchpoints, sessions,
    leads, opportunities, orders, lifecycle history, and persisted attribution credits.
    """
    target_model = model_id or settings.ATTRIBUTION_SETTINGS.get('DEFAULT_MODEL', 'position_based')

    touchpoints = list(
        Touchpoint.objects.filter(contact=contact)
        .select_related('campaign', 'channel', 'creative', 'session')
        .order_by('timestamp', 'id')
    )
    sessions = list(
        WebSession.objects.filter(contact=contact)
        .select_related('campaign')
        .order_by('timestamp', 'id')
    )
    leads = list(
        Lead.objects.filter(contact=contact)
        .select_related('campaign')
        .order_by('created_date', 'id')
    )
    opportunities = list(
        Opportunity.objects.filter(contact=contact)
        .order_by('closing_date', 'id')
    )
    orders = list(
        Order.objects.filter(contact=contact)
        .order_by('order_date', 'id')
    )

    latest_run = (
        AttributionRun.objects.filter(
            attribution_model_id=target_model,
            status=AttributionRun.Status.COMPLETED,
        )
        .order_by('-executed_at')
        .first()
    )
    attr_results = []
    if latest_run is not None and orders:
        order_ids = [o.id for o in orders]
        attr_results = list(
            AttributionResult.objects.filter(run=latest_run, order_id__in=order_ids)
            .select_related('touchpoint', 'campaign', 'channel')
            .order_by('touchpoint__timestamp', 'id')
        )

    timeline_entries = []

    for tp in touchpoints:
        ts = _ensure_utc(tp.timestamp)
        campaign_label = tp.campaign.name if tp.campaign else 'Unassigned Campaign'
        creative_label = tp.creative.name if tp.creative else 'No Creative'
        channel_label = tp.channel.name if tp.channel else 'Unassigned Channel'
        badge = (
            'Post-Conversion'
            if tp.is_post_conversion
            else ('Online' if tp.is_online else 'Offline')
        )
        timeline_entries.append(
            {
                'id': f'TL-{tp.id}',
                'timestamp': ts,
                'stage_type': 'Campaign Touchpoint' if tp.is_online else 'Offline Event',
                'title': f'{tp.interaction_type} · {channel_label}',
                'subtitle': f'{campaign_label} ({creative_label})',
                'meta': tp.source or tp.device,
                'badge': badge,
                'is_invalid': bool(tp.is_post_conversion or not tp.is_valid),
            }
        )

    for ses in sessions:
        ts = _ensure_utc(ses.timestamp)
        timeline_entries.append(
            {
                'id': f'TL-{ses.id}',
                'timestamp': ts,
                'stage_type': 'Website Visit',
                'title': f'Visited {ses.landing_page}',
                'subtitle': f'Session {ses.id} · Referrer: {ses.referrer}',
                'meta': ses.device_type,
                'badge': ses.identity_status,
                'is_invalid': ses.identity_status == WebSession.IdentityStatus.UNVERIFIED_LINK,
            }
        )

    for ld in leads:
        ts = _date_to_utc_iso(ld.created_date, hour=12)
        camp_label = ld.campaign.name if ld.campaign else 'Unattributed'
        timeline_entries.append(
            {
                'id': f'TL-{ld.id}',
                'timestamp': ts,
                'stage_type': 'Lead Created',
                'title': f'Lead {ld.id} Created (Score: {ld.score})',
                'subtitle': f'Source: {ld.source} · Campaign: {camp_label}',
                'meta': ld.status,
                'badge': ld.status,
                'is_invalid': False,
            }
        )

    for opp in opportunities:
        ts = _date_to_utc_iso(opp.closing_date, hour=15)
        timeline_entries.append(
            {
                'id': f'TL-{opp.id}',
                'timestamp': ts,
                'stage_type': 'Opportunity',
                'title': opp.name,
                'subtitle': f'Stage: {opp.stage} · Expected ${opp.expected_revenue:,.2f}',
                'meta': opp.status,
                'badge': opp.stage,
                'is_invalid': False,
            }
        )

    for ord_obj in orders:
        ts = _date_to_utc_iso(ord_obj.order_date, hour=18)
        timeline_entries.append(
            {
                'id': f'TL-{ord_obj.id}',
                'timestamp': ts,
                'stage_type': 'Closed Order',
                'title': f'Order {ord_obj.id} · ${ord_obj.revenue:,.2f} {ord_obj.currency}',
                'subtitle': f'Payment: {ord_obj.payment_status} · Verification: {ord_obj.verification_status}',
                'meta': ord_obj.verification_status,
                'badge': ord_obj.verification_status,
                'is_invalid': ord_obj.verification_status == Order.VerificationStatus.DUPLICATE,
            }
        )

    timeline_entries.sort(key=lambda item: (item['timestamp'], item['id']))

    return {
        'contact': contact,
        'model_id': target_model,
        'attribution_run_id': latest_run.id if latest_run else None,
        'touchpoints': touchpoints,
        'sessions': sessions,
        'leads': leads,
        'opportunities': opportunities,
        'orders': orders,
        'attribution_results': [
            {
                'touchpoint_id': res.touchpoint_id,
                'order_id': res.order_id,
                'campaign_id': res.campaign_id,
                'campaign_name': res.campaign.name if res.campaign else None,
                'channel_id': res.channel_id,
                'channel_name': res.channel.name if res.channel else None,
                'timestamp': res.touchpoint.timestamp,
                'weight': float(res.credit_weight),
                'weight_percent': round(float(res.credit_weight) * 100, 2),
                'attributed_revenue': res.attributed_revenue,
            }
            for res in attr_results
        ],
        'timeline': timeline_entries,
    }

