"""Touchpoint ingestion, post-conversion detection, audit logging, and safe deletion services."""

from datetime import date, timezone as dt_timezone

from django.db import transaction
from django.db.models import ProtectedError
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.orders.models import Order
from apps.touchpoints.models import Touchpoint
from common.audit import record_audit_log
from common.exceptions import ConflictException


def serialize_touchpoint_snapshot(touchpoint: Touchpoint) -> dict:
    """Capture scalar Touchpoint fields for AuditLog tracking."""
    return {
        'id': touchpoint.id,
        'contact_id': touchpoint.contact_id,
        'campaign_id': touchpoint.campaign_id,
        'channel_id': touchpoint.channel_id,
        'creative_id': touchpoint.creative_id,
        'session_id': touchpoint.session_id,
        'interaction_type': touchpoint.interaction_type,
        'timestamp': touchpoint.timestamp.isoformat() if touchpoint.timestamp else None,
        'device': touchpoint.device,
        'is_online': touchpoint.is_online,
        'source': touchpoint.source,
        'is_post_conversion': touchpoint.is_post_conversion,
        'is_valid': touchpoint.is_valid,
        'validation_notes': touchpoint.validation_notes,
    }


def _to_utc_date(dt) -> date:
    """Normalize a datetime to its UTC calendar date."""
    if timezone.is_naive(dt):
        return dt.replace(tzinfo=dt_timezone.utc).date()
    return dt.astimezone(dt_timezone.utc).date()


def _apply_touchpoint_integrity_flags(touchpoint: Touchpoint) -> None:
    """
    Detect post-conversion timing against verified paid Orders and annotate
    missing campaign metadata without dropping telemetry records.
    """
    earliest_valid_order = (
        Order.objects.filter(
            contact_id=touchpoint.contact_id,
            verification_status=Order.VerificationStatus.VALID,
            payment_status=Order.PaymentStatus.PAID,
        )
        .order_by('order_date')
        .first()
    )
    tp_date = _to_utc_date(touchpoint.timestamp)
    if earliest_valid_order is not None and tp_date > earliest_valid_order.order_date:
        touchpoint.is_post_conversion = True
        touchpoint.is_valid = False
        if not touchpoint.validation_notes:
            touchpoint.validation_notes = (
                f'Post-conversion touchpoint recorded after valid order '
                f'{earliest_valid_order.id} ({earliest_valid_order.order_date.isoformat()}); '
                'excluded from attribution.'
            )
    elif touchpoint.campaign_id is None and not touchpoint.validation_notes:
        touchpoint.validation_notes = 'Missing campaign identifier; retained for unattributed analysis.'


@transaction.atomic
def create_touchpoint(
    *,
    validated_data: dict,
    actor=None,
    source_ip: str | None = None,
) -> Touchpoint:
    """Create an online or offline Touchpoint with post-conversion checks and AuditLog."""
    touchpoint = Touchpoint(**validated_data)
    _apply_touchpoint_integrity_flags(touchpoint)
    touchpoint.save()

    snapshot = serialize_touchpoint_snapshot(touchpoint)
    record_audit_log(
        entity_type='Touchpoint',
        entity_id=touchpoint.id,
        action=AuditLog.Action.CREATE,
        actor=actor,
        previous_state=None,
        new_state=snapshot,
        changed_fields=list(snapshot.keys()),
        source_ip=source_ip,
        notes=f'Touchpoint recorded ({touchpoint.interaction_type}).',
    )
    return touchpoint


@transaction.atomic
def update_touchpoint(
    *,
    touchpoint: Touchpoint,
    validated_data: dict,
    actor=None,
    source_ip: str | None = None,
) -> Touchpoint:
    """Update Touchpoint fields, re-evaluate post-conversion status, and record AuditLog."""
    previous_state = serialize_touchpoint_snapshot(touchpoint)

    changed_fields = []
    for field, value in validated_data.items():
        if getattr(touchpoint, field) != value:
            setattr(touchpoint, field, value)
            changed_fields.append(field)

    prev_post = touchpoint.is_post_conversion
    prev_valid = touchpoint.is_valid
    prev_notes = touchpoint.validation_notes
    _apply_touchpoint_integrity_flags(touchpoint)

    if touchpoint.is_post_conversion != prev_post:
        changed_fields.append('is_post_conversion')
    if touchpoint.is_valid != prev_valid:
        changed_fields.append('is_valid')
    if touchpoint.validation_notes != prev_notes:
        changed_fields.append('validation_notes')

    dedup_changed = list(dict.fromkeys(changed_fields))
    if dedup_changed:
        touchpoint.save()
        record_audit_log(
            entity_type='Touchpoint',
            entity_id=touchpoint.id,
            action=AuditLog.Action.UPDATE,
            actor=actor,
            previous_state=previous_state,
            new_state=serialize_touchpoint_snapshot(touchpoint),
            changed_fields=dedup_changed,
            source_ip=source_ip,
            notes='Touchpoint updated.',
        )
    return touchpoint


@transaction.atomic
def delete_touchpoint_safely(
    *,
    touchpoint: Touchpoint,
    actor=None,
    source_ip: str | None = None,
):
    """Delete an unreferenced Touchpoint or raise HTTP 409 Conflict if attribution results exist."""
    snapshot = serialize_touchpoint_snapshot(touchpoint)
    tid = touchpoint.id
    try:
        touchpoint.delete()
    except ProtectedError as exc:
        raise ConflictException(
            'Cannot delete this touchpoint because persisted attribution results reference it.'
        ) from exc

    record_audit_log(
        entity_type='Touchpoint',
        entity_id=tid,
        action=AuditLog.Action.DELETE,
        actor=actor,
        previous_state=snapshot,
        new_state=None,
        changed_fields=['deleted'],
        source_ip=source_ip,
        notes='Touchpoint deleted.',
    )

