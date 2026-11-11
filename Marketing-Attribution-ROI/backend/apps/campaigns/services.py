"""Campaign lifecycle, M2M bridge synchronization, audit logging, and O(1) ROI metric services."""

from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import Count, ProtectedError, Sum

from apps.attribution.models import AttributionResult, AttributionRun
from apps.audit.models import AuditLog
from apps.audiences.models import Audience
from apps.campaigns.models import (
    Campaign,
    CampaignAudience,
    CampaignCreative,
    CampaignStatusHistory,
)
from apps.costs.models import CostRecord
from apps.creatives.models import Creative
from apps.leads.models import Lead
from apps.touchpoints.models import Touchpoint
from common.audit import record_audit_log
from common.exceptions import ConflictException
from common.utils import safe_divide


def serialize_campaign_snapshot(campaign: Campaign) -> dict:
    """Capture non-relational scalar snapshot for AuditLog comparison."""
    return {
        'id': campaign.id,
        'name': campaign.name,
        'channel_id': campaign.channel_id,
        'budget': str(campaign.budget),
        'currency': campaign.currency,
        'start_date': campaign.start_date.isoformat() if campaign.start_date else None,
        'end_date': campaign.end_date.isoformat() if campaign.end_date else None,
        'objective': campaign.objective,
        'status': campaign.status,
        'is_paid_campaign': campaign.is_paid_campaign,
    }


def _resolve_latest_completed_run(model_id: str | None = None) -> AttributionRun | None:
    """Find the most recent completed AttributionRun for a given model code."""
    target_model = model_id or settings.ATTRIBUTION_SETTINGS.get('DEFAULT_MODEL', 'position_based')
    return (
        AttributionRun.objects.filter(
            attribution_model_id=target_model,
            status=AttributionRun.Status.COMPLETED,
        )
        .order_by('-executed_at')
        .first()
    )


def get_campaign_metrics_map(
    campaigns: list[Campaign],
    *,
    model_id: str | None = None,
) -> dict[str, dict]:
    """
    Compute spend, leads, touchpoints, attributed revenue, ROI, ROAS, and alerts
    across a batch of campaigns using constant-count GROUP BY queries (no N+1).
    """
    if not campaigns:
        return {}

    campaign_ids = [c.id for c in campaigns]
    currency_map = {c.id: c.currency for c in campaigns}
    budget_map = {c.id: c.budget for c in campaigns}

    same_currency_spend: dict[str, Decimal] = {cid: Decimal('0.00') for cid in campaign_ids}
    mismatch_flags: dict[str, bool] = {cid: False for cid in campaign_ids}

    cost_rows = (
        CostRecord.objects.filter(campaign_id__in=campaign_ids)
        .order_by()
        .values('campaign_id', 'currency')
        .annotate(total=Sum('amount'))
    )
    for row in cost_rows:
        cid = row['campaign_id']
        total = row['total'] or Decimal('0.00')
        if row['currency'] == currency_map.get(cid):
            same_currency_spend[cid] += total
        else:
            mismatch_flags[cid] = True

    lead_counts = {
        row['campaign_id']: row['cnt']
        for row in Lead.objects.filter(campaign_id__in=campaign_ids)
        .order_by()
        .values('campaign_id')
        .annotate(cnt=Count('id'))
    }

    touchpoint_counts = {
        row['campaign_id']: row['cnt']
        for row in Touchpoint.objects.filter(campaign_id__in=campaign_ids)
        .order_by()
        .values('campaign_id')
        .annotate(cnt=Count('id'))
    }

    attr_revenue: dict[str, Decimal] = {cid: Decimal('0.00') for cid in campaign_ids}
    attr_conversions: dict[str, int] = {cid: 0 for cid in campaign_ids}
    latest_run = _resolve_latest_completed_run(model_id=model_id)
    if latest_run is not None:
        res_rows = (
            AttributionResult.objects.filter(run=latest_run, campaign_id__in=campaign_ids)
            .order_by()
            .values('campaign_id')
            .annotate(
                rev=Sum('attributed_revenue'),
                conversions=Count('order_id', distinct=True),
            )
        )
        for row in res_rows:
            cid = row['campaign_id']
            attr_revenue[cid] = row['rev'] or Decimal('0.00')
            attr_conversions[cid] = row['conversions'] or 0

    metrics: dict[str, dict] = {}
    for cid in campaign_ids:
        spend = same_currency_spend[cid].quantize(Decimal('0.01'))
        revenue = attr_revenue[cid].quantize(Decimal('0.01'))
        roi_raw = safe_divide((revenue - spend) * Decimal('100.00'), spend)
        roas_raw = safe_divide(revenue, spend)
        tp_cnt = touchpoint_counts.get(cid, 0)
        budget = budget_map.get(cid, Decimal('0.00'))

        metrics[cid] = {
            'spend': spend,
            'attributed_revenue': revenue,
            'leads_count': lead_counts.get(cid, 0),
            'conversions_count': attr_conversions.get(cid, 0),
            'touchpoints_count': tp_cnt,
            'roi': round(float(roi_raw), 2) if roi_raw is not None else None,
            'roas': round(float(roas_raw), 2) if roas_raw is not None else None,
            'has_currency_mismatch': mismatch_flags[cid],
            'missing_cost_alert': bool(budget > 0 and spend == 0 and tp_cnt > 0),
        }
    return metrics


def _sync_campaign_creatives(
    campaign: Campaign,
    *,
    creative_ids: list[str] | None,
    primary_creative_id: str | None,
):
    """Synchronize CampaignCreative bridge rows with explicit primary flag."""
    if creative_ids is None and primary_creative_id is None:
        return

    resolved_ids = list(dict.fromkeys(creative_ids or []))
    if primary_creative_id and primary_creative_id not in resolved_ids:
        resolved_ids.insert(0, primary_creative_id)

    CampaignCreative.objects.filter(campaign=campaign).delete()
    if not resolved_ids:
        return

    creatives_by_id = Creative.objects.in_bulk(resolved_ids)
    effective_primary = primary_creative_id or resolved_ids[0]
    bridge_rows = []
    for cid in resolved_ids:
        creative = creatives_by_id[cid]
        bridge_rows.append(
            CampaignCreative(
                campaign=campaign,
                creative=creative,
                is_primary=(cid == effective_primary),
                effective_from=campaign.start_date,
                effective_to=campaign.end_date,
            )
        )
    CampaignCreative.objects.bulk_create(bridge_rows)


def _sync_campaign_audiences(
    campaign: Campaign,
    *,
    audience_ids: list[str] | None,
    primary_audience_id: str | None,
):
    """Synchronize CampaignAudience bridge rows with explicit primary flag."""
    if audience_ids is None and primary_audience_id is None:
        return

    resolved_ids = list(dict.fromkeys(audience_ids or []))
    if primary_audience_id and primary_audience_id not in resolved_ids:
        resolved_ids.insert(0, primary_audience_id)

    CampaignAudience.objects.filter(campaign=campaign).delete()
    if not resolved_ids:
        return

    audiences_by_id = Audience.objects.in_bulk(resolved_ids)
    effective_primary = primary_audience_id or resolved_ids[0]
    bridge_rows = []
    for aid in resolved_ids:
        audience = audiences_by_id[aid]
        bridge_rows.append(
            CampaignAudience(
                campaign=campaign,
                audience=audience,
                is_primary=(aid == effective_primary),
                effective_from=campaign.start_date,
                effective_to=campaign.end_date,
            )
        )
    CampaignAudience.objects.bulk_create(bridge_rows)


@transaction.atomic
def create_campaign(
    *,
    validated_data: dict,
    actor=None,
    source_ip: str | None = None,
) -> Campaign:
    """Create a Campaign, sync creative/audience bridges, and log status + audit trail."""
    creative_ids = validated_data.pop('creative_ids', None)
    primary_creative_id = validated_data.pop('primary_creative_id', None)
    audience_ids = validated_data.pop('audience_ids', None)
    primary_audience_id = validated_data.pop('primary_audience_id', None)
    reason = validated_data.pop('status_reason', '') or 'Campaign created.'

    campaign = Campaign(**validated_data)
    if actor and getattr(actor, 'is_authenticated', False):
        campaign.created_by = actor
    campaign.save()

    _sync_campaign_creatives(
        campaign,
        creative_ids=creative_ids,
        primary_creative_id=primary_creative_id,
    )
    _sync_campaign_audiences(
        campaign,
        audience_ids=audience_ids,
        primary_audience_id=primary_audience_id,
    )

    CampaignStatusHistory.objects.create(
        campaign=campaign,
        previous_status='',
        new_status=campaign.status,
        changed_by=actor if (actor and getattr(actor, 'is_authenticated', False)) else None,
        reason=reason,
    )
    record_audit_log(
        entity_type='Campaign',
        entity_id=campaign.id,
        action=AuditLog.Action.CREATE,
        actor=actor,
        previous_state=None,
        new_state=serialize_campaign_snapshot(campaign),
        changed_fields=list(serialize_campaign_snapshot(campaign).keys()),
        source_ip=source_ip,
        notes='Campaign created.',
    )
    return campaign


@transaction.atomic
def update_campaign(
    *,
    campaign: Campaign,
    validated_data: dict,
    actor=None,
    source_ip: str | None = None,
) -> Campaign:
    """Update Campaign fields, M2M assignments, status history, and AuditLog."""
    previous_state = serialize_campaign_snapshot(campaign)
    previous_status = campaign.status

    creative_ids = validated_data.pop('creative_ids', None)
    primary_creative_id = validated_data.pop('primary_creative_id', None)
    audience_ids = validated_data.pop('audience_ids', None)
    primary_audience_id = validated_data.pop('primary_audience_id', None)
    reason = validated_data.pop('status_reason', '')

    changed_fields = []
    for field, val in validated_data.items():
        if getattr(campaign, field) != val:
            setattr(campaign, field, val)
            changed_fields.append(field)

    if changed_fields:
        campaign.save()

    if creative_ids is not None or primary_creative_id is not None:
        _sync_campaign_creatives(
            campaign,
            creative_ids=creative_ids,
            primary_creative_id=primary_creative_id,
        )
        changed_fields.append('creatives')

    if audience_ids is not None or primary_audience_id is not None:
        _sync_campaign_audiences(
            campaign,
            audience_ids=audience_ids,
            primary_audience_id=primary_audience_id,
        )
        changed_fields.append('audiences')

    if campaign.status != previous_status:
        CampaignStatusHistory.objects.create(
            campaign=campaign,
            previous_status=previous_status,
            new_status=campaign.status,
            changed_by=actor if (actor and getattr(actor, 'is_authenticated', False)) else None,
            reason=reason or f'Status updated from {previous_status} to {campaign.status}.',
        )

    if changed_fields:
        action = (
            AuditLog.Action.STATUS_CHANGE
            if campaign.status != previous_status
            else AuditLog.Action.UPDATE
        )
        record_audit_log(
            entity_type='Campaign',
            entity_id=campaign.id,
            action=action,
            actor=actor,
            previous_state=previous_state,
            new_state=serialize_campaign_snapshot(campaign),
            changed_fields=changed_fields,
            source_ip=source_ip,
            notes=reason or 'Campaign updated.',
        )

    return campaign


@transaction.atomic
def archive_campaign(
    *,
    campaign: Campaign,
    actor=None,
    source_ip: str | None = None,
    reason: str = '',
) -> Campaign:
    """Soft-archive a Campaign, preserving historical status and audit records."""
    if campaign.status == Campaign.Status.ARCHIVED:
        return campaign

    previous_state = serialize_campaign_snapshot(campaign)
    previous_status = campaign.status
    campaign.status = Campaign.Status.ARCHIVED
    campaign.save(update_fields=['status', 'updated_at'])

    note = reason or 'Campaign archived via API.'
    CampaignStatusHistory.objects.create(
        campaign=campaign,
        previous_status=previous_status,
        new_status=Campaign.Status.ARCHIVED,
        changed_by=actor if (actor and getattr(actor, 'is_authenticated', False)) else None,
        reason=note,
    )
    record_audit_log(
        entity_type='Campaign',
        entity_id=campaign.id,
        action=AuditLog.Action.ARCHIVE,
        actor=actor,
        previous_state=previous_state,
        new_state=serialize_campaign_snapshot(campaign),
        changed_fields=['status'],
        source_ip=source_ip,
        notes=note,
    )
    return campaign


@transaction.atomic
def delete_campaign_safely(*, campaign: Campaign, actor=None, source_ip: str | None = None):
    """Delete an unreferenced Campaign or raise 409 Conflict when protected data exists."""
    snapshot = serialize_campaign_snapshot(campaign)
    cid = campaign.id
    try:
        campaign.delete()
    except ProtectedError as exc:
        raise ConflictException(
            'Cannot delete this campaign because dependent cost records reference it. '
            'Archive the campaign instead via POST /api/v1/campaigns/{id}/archive/.'
        ) from exc

    record_audit_log(
        entity_type='Campaign',
        entity_id=cid,
        action=AuditLog.Action.DELETE,
        actor=actor,
        previous_state=snapshot,
        new_state=None,
        changed_fields=['deleted'],
        source_ip=source_ip,
        notes='Campaign deleted.',
    )
