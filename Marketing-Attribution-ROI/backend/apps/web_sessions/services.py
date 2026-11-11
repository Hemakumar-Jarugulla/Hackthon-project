"""Web session lifecycle, verified identity linking, and audit logging services."""

from django.db import transaction

from apps.audit.models import AuditLog
from apps.contacts.models import Contact
from apps.web_sessions.models import WebSession
from common.audit import record_audit_log


def serialize_session_snapshot(session: WebSession) -> dict:
    """Capture scalar WebSession fields for AuditLog tracking."""
    return {
        'id': session.id,
        'anonymous_id': session.anonymous_id,
        'contact_id': session.contact_id,
        'campaign_id': session.campaign_id,
        'landing_page': session.landing_page,
        'referrer': session.referrer,
        'timestamp': session.timestamp.isoformat() if session.timestamp else None,
        'device_type': session.device_type,
        'identity_status': session.identity_status,
        'has_evidence': session.has_evidence,
        'evidence_type': session.evidence_type,
        'linking_issue': session.linking_issue,
    }


@transaction.atomic
def create_web_session(
    *,
    validated_data: dict,
    actor=None,
    source_ip: str | None = None,
) -> WebSession:
    """Persist a WebSession and record CREATE AuditLog entry."""
    session = WebSession.objects.create(**validated_data)
    snapshot = serialize_session_snapshot(session)
    record_audit_log(
        entity_type='WebSession',
        entity_id=session.id,
        action=AuditLog.Action.CREATE,
        actor=actor,
        previous_state=None,
        new_state=snapshot,
        changed_fields=list(snapshot.keys()),
        source_ip=source_ip,
        notes=f'Web session created ({session.identity_status}).',
    )
    return session


@transaction.atomic
def update_web_session(
    *,
    session: WebSession,
    validated_data: dict,
    actor=None,
    source_ip: str | None = None,
) -> WebSession:
    """Update a WebSession and log field-level changes to AuditLog."""
    previous_state = serialize_session_snapshot(session)
    changed_fields = []
    for field, value in validated_data.items():
        if getattr(session, field) != value:
            setattr(session, field, value)
            changed_fields.append(field)

    if changed_fields:
        session.save()
        record_audit_log(
            entity_type='WebSession',
            entity_id=session.id,
            action=AuditLog.Action.UPDATE,
            actor=actor,
            previous_state=previous_state,
            new_state=serialize_session_snapshot(session),
            changed_fields=changed_fields,
            source_ip=source_ip,
            notes='Web session updated.',
        )
    return session


@transaction.atomic
def link_session_to_contact(
    *,
    session: WebSession,
    contact: Contact,
    evidence_type: str,
    notes: str = '',
    actor=None,
    source_ip: str | None = None,
) -> WebSession:
    """
    Resolve an anonymous or unverified WebSession to a Contact strictly using
    verifiable identity-linking evidence.
    """
    previous_state = serialize_session_snapshot(session)
    session.contact = contact
    session.has_evidence = True
    session.evidence_type = evidence_type.strip()
    session.identity_status = WebSession.IdentityStatus.IDENTIFIED
    session.linking_issue = ''
    session.save(
        update_fields=[
            'contact',
            'has_evidence',
            'evidence_type',
            'identity_status',
            'linking_issue',
            'updated_at',
        ]
    )

    note = notes.strip() or f'Session linked to {contact.id} using {session.evidence_type}.'
    record_audit_log(
        entity_type='WebSession',
        entity_id=session.id,
        action=AuditLog.Action.UPDATE,
        actor=actor,
        previous_state=previous_state,
        new_state=serialize_session_snapshot(session),
        changed_fields=[
            'contact',
            'has_evidence',
            'evidence_type',
            'identity_status',
            'linking_issue',
        ],
        source_ip=source_ip,
        notes=note,
    )
    return session


@transaction.atomic
def delete_web_session(*, session: WebSession, actor=None, source_ip: str | None = None):
    """Delete a WebSession (Touchpoint.session uses SET_NULL) and log AuditLog."""
    snapshot = serialize_session_snapshot(session)
    sid = session.id
    session.delete()
    record_audit_log(
        entity_type='WebSession',
        entity_id=sid,
        action=AuditLog.Action.DELETE,
        actor=actor,
        previous_state=snapshot,
        new_state=None,
        changed_fields=['deleted'],
        source_ip=source_ip,
        notes='Web session deleted.',
    )

