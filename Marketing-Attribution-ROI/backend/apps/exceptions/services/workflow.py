"""Exception summary aggregation and audited resolve/reopen workflow services."""

from django.db import transaction
from django.db.models import Count, QuerySet
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.exceptions.models import DataException
from common.audit import record_audit_log


def serialize_exception_snapshot(exc: DataException) -> dict:
    """Capture scalar DataException state for AuditLog diffs."""
    return {
        'id': exc.id,
        'issue_type': exc.issue_type,
        'entity_type': exc.entity_type,
        'entity_id': exc.entity_id,
        'severity': exc.severity,
        'resolution_status': exc.resolution_status,
        'resolved_by_id': exc.resolved_by_id,
        'resolved_at': exc.resolved_at.isoformat() if exc.resolved_at else None,
        'resolution_notes': exc.resolution_notes,
    }


def build_exception_summary(queryset: QuerySet[DataException]) -> dict:
    """Aggregate DataException counts grouped by severity, resolution_status, and issue_type."""
    base = queryset.order_by()
    total = base.count()

    sev_counts = {sev.value: 0 for sev in DataException.Severity}
    for row in base.values('severity').annotate(cnt=Count('id')):
        if row['severity'] in sev_counts:
            sev_counts[row['severity']] = row['cnt']

    status_counts = {st.value: 0 for st in DataException.ResolutionStatus}
    for row in base.values('resolution_status').annotate(cnt=Count('id')):
        if row['resolution_status'] in status_counts:
            status_counts[row['resolution_status']] = row['cnt']

    issue_counts = {it.value: 0 for it in DataException.IssueType}
    for row in base.values('issue_type').annotate(cnt=Count('id')):
        if row['issue_type'] in issue_counts:
            issue_counts[row['issue_type']] = row['cnt']

    open_critical_high = base.filter(
        resolution_status=DataException.ResolutionStatus.OPEN,
        severity__in=[DataException.Severity.CRITICAL, DataException.Severity.HIGH],
    ).count()

    return {
        'total_exceptions': total,
        'open_exceptions': status_counts.get(DataException.ResolutionStatus.OPEN, 0),
        'reviewed_exceptions': status_counts.get(DataException.ResolutionStatus.REVIEWED, 0),
        'resolved_exceptions': status_counts.get(DataException.ResolutionStatus.RESOLVED, 0),
        'open_critical_high': open_critical_high,
        'by_severity': sev_counts,
        'by_status': status_counts,
        'by_issue_type': issue_counts,
    }


@transaction.atomic
def update_exception_resolution(
    *,
    exception_obj: DataException,
    resolution_status: str,
    resolution_notes: str = '',
    actor=None,
    source_ip: str | None = None,
) -> DataException:
    """Resolve, mark Reviewed, or reopen a DataException with immutable AuditLog tracking."""
    previous_state = serialize_exception_snapshot(exception_obj)
    resolved_actor = actor if (actor and getattr(actor, 'is_authenticated', False)) else None

    exception_obj.resolution_status = resolution_status
    if resolution_notes:
        exception_obj.resolution_notes = resolution_notes

    if resolution_status == DataException.ResolutionStatus.RESOLVED:
        exception_obj.resolved_at = timezone.now()
        exception_obj.resolved_by = resolved_actor
    else:
        exception_obj.resolved_at = None
        exception_obj.resolved_by = None

    exception_obj.save()
    new_state = serialize_exception_snapshot(exception_obj)
    changed_fields = [
        k for k in new_state if previous_state.get(k) != new_state.get(k)
    ]

    record_audit_log(
        entity_type='DataException',
        entity_id=exception_obj.id,
        action=AuditLog.Action.EXCEPTION_ACTION,
        actor=resolved_actor,
        previous_state=previous_state,
        new_state=new_state,
        changed_fields=changed_fields,
        source_ip=source_ip,
        notes=f'Exception {exception_obj.id} set to {resolution_status}.',
    )
    return exception_obj

