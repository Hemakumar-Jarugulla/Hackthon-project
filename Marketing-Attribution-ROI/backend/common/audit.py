"""Shared audit trail helpers for domain mutations and lifecycle transitions."""

from apps.audit.models import AuditLog


def get_request_ip(request) -> str | None:
    """Safely extract caller IP address from Django/DRF request metadata."""
    if request is None:
        return None
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def record_audit_log(
    *,
    entity_type: str,
    entity_id: str,
    action: str,
    actor=None,
    previous_state=None,
    new_state=None,
    changed_fields=None,
    source_ip: str | None = None,
    notes: str = '',
) -> AuditLog:
    """Persist an immutable AuditLog record cleanly with authenticated actor resolution."""
    resolved_actor = actor if (actor and getattr(actor, 'is_authenticated', False)) else None
    return AuditLog.objects.create(
        entity_type=entity_type,
        entity_id=str(entity_id),
        action=action,
        actor=resolved_actor,
        previous_state=previous_state,
        new_state=new_state,
        changed_fields=changed_fields or [],
        source_ip=source_ip,
        notes=notes,
    )

