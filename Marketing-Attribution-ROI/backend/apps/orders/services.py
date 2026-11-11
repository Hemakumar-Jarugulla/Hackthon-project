"""Order management, duplicate-revenue validation, audit logging, and safe deletion."""

from django.db import transaction
from django.db.models import ProtectedError
from rest_framework.exceptions import ValidationError

from apps.audit.models import AuditLog
from apps.orders.models import Order
from common.audit import record_audit_log
from common.exceptions import ConflictException


def serialize_order_snapshot(order: Order) -> dict:
    """Capture scalar Order fields for AuditLog tracking."""
    return {
        'id': order.id,
        'opportunity_id': order.opportunity_id,
        'contact_id': order.contact_id,
        'order_date': order.order_date.isoformat() if order.order_date else None,
        'revenue': str(order.revenue),
        'currency': order.currency,
        'payment_status': order.payment_status,
        'verification_status': order.verification_status,
        'notes': order.notes,
    }


def ensure_single_valid_order_per_opportunity(
    *,
    opportunity_id: str,
    verification_status: str,
    exclude_order_id: str | None = None,
) -> None:
    """
    Prevent double-counting closed revenue by rejecting multiple 'Valid' orders
    against the same Opportunity while permitting explicit 'Duplicate'/'Pending Review' flags.
    """
    if verification_status != Order.VerificationStatus.VALID:
        return
    qs = Order.objects.filter(
        opportunity_id=opportunity_id,
        verification_status=Order.VerificationStatus.VALID,
    )
    if exclude_order_id:
        qs = qs.exclude(pk=exclude_order_id)
    existing = qs.values_list('id', flat=True).first()
    if existing:
        raise ValidationError(
            {
                'verification_status': [
                    f'Opportunity {opportunity_id} already has active Valid order {existing}. '
                    'Mark duplicate entries as "Duplicate" or "Pending Review" to prevent '
                    'double-counted revenue.'
                ]
            }
        )


@transaction.atomic
def create_order(
    *,
    validated_data: dict,
    actor=None,
    source_ip: str | None = None,
) -> Order:
    """Create an Order after verifying single-Valid-order integrity and record AuditLog."""
    order = Order.objects.create(**validated_data)
    snapshot = serialize_order_snapshot(order)
    record_audit_log(
        entity_type='Order',
        entity_id=order.id,
        action=AuditLog.Action.CREATE,
        actor=actor,
        previous_state=None,
        new_state=snapshot,
        changed_fields=list(snapshot.keys()),
        source_ip=source_ip,
        notes=f'Order created ({order.verification_status}).',
    )
    return order


@transaction.atomic
def update_order(
    *,
    order: Order,
    validated_data: dict,
    actor=None,
    source_ip: str | None = None,
) -> Order:
    """Update Order attributes and log field/status diffs in AuditLog."""
    previous_state = serialize_order_snapshot(order)
    previous_verif = order.verification_status

    changed_fields = []
    for field, value in validated_data.items():
        if getattr(order, field) != value:
            setattr(order, field, value)
            changed_fields.append(field)

    if changed_fields:
        order.save()
        action = (
            AuditLog.Action.STATUS_CHANGE
            if order.verification_status != previous_verif or 'payment_status' in changed_fields
            else AuditLog.Action.UPDATE
        )
        record_audit_log(
            entity_type='Order',
            entity_id=order.id,
            action=action,
            actor=actor,
            previous_state=previous_state,
            new_state=serialize_order_snapshot(order),
            changed_fields=changed_fields,
            source_ip=source_ip,
            notes=f'Order updated ({order.verification_status}).',
        )
    return order


@transaction.atomic
def verify_order_status(
    *,
    order: Order,
    verification_status: str,
    notes: str = '',
    actor=None,
    source_ip: str | None = None,
) -> Order:
    """Transition an Order's verification_status cleanly while blocking duplicate Valid orders."""
    ensure_single_valid_order_per_opportunity(
        opportunity_id=order.opportunity_id,
        verification_status=verification_status,
        exclude_order_id=order.id,
    )
    previous_state = serialize_order_snapshot(order)
    changed_fields = []
    if order.verification_status != verification_status:
        order.verification_status = verification_status
        changed_fields.append('verification_status')
    if notes:
        order.notes = notes
        changed_fields.append('notes')

    if changed_fields:
        order.save(update_fields=[*changed_fields, 'updated_at'])
        record_audit_log(
            entity_type='Order',
            entity_id=order.id,
            action=AuditLog.Action.STATUS_CHANGE,
            actor=actor,
            previous_state=previous_state,
            new_state=serialize_order_snapshot(order),
            changed_fields=changed_fields,
            source_ip=source_ip,
            notes=notes or f'Verification status changed to {verification_status}.',
        )
    return order


@transaction.atomic
def delete_order_safely(*, order: Order, actor=None, source_ip: str | None = None):
    """Delete an unreferenced Order or raise HTTP 409 Conflict when attribution results exist."""
    snapshot = serialize_order_snapshot(order)
    oid = order.id
    try:
        order.delete()
    except ProtectedError as exc:
        raise ConflictException(
            'Cannot delete this order because persisted attribution results reference it.'
        ) from exc

    record_audit_log(
        entity_type='Order',
        entity_id=oid,
        action=AuditLog.Action.DELETE,
        actor=actor,
        previous_state=snapshot,
        new_state=None,
        changed_fields=['deleted'],
        source_ip=source_ip,
        notes='Order deleted.',
    )

