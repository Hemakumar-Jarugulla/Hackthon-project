"""
Structured CSV, JSON, SQL snapshot, Source Manifest, Validation Summary & Data Dictionary exporter
plus HTTP dataset download helpers.
"""

import csv
import io
import json
from pathlib import Path
from typing import Any

from django.conf import settings

from apps.analytics.services.roi_analytics import build_roi_analytics
from apps.attribution.models import AttributionResult
from apps.audiences.models import Audience
from apps.campaigns.models import Campaign
from apps.channels.models import Channel
from apps.contacts.models import Contact
from apps.costs.models import CostRecord
from apps.creatives.models import Creative
from apps.exceptions.models import DataException
from apps.leads.models import Lead
from apps.opportunities.models import Opportunity
from apps.orders.models import Order
from apps.touchpoints.models import Touchpoint
from apps.validation.services import get_latest_validation_report
from apps.web_sessions.models import WebSession
from data_generator.validators.reproducibility import compute_dataset_fingerprint

SUPPORTED_EXPORT_ENTITIES = (
    'campaigns',
    'channels',
    'creatives',
    'audiences',
    'contacts',
    'sessions',
    'touchpoints',
    'leads',
    'opportunities',
    'orders',
    'costs',
    'exceptions',
    'attribution_results',
    'roi_summary',
)


def _format_cell(val: Any) -> str:
    if val is None:
        return ''
    if hasattr(val, 'isoformat'):
        text = val.isoformat()
    else:
        text = str(val)
    # Mitigate spreadsheet CSV formula injection on untrusted string cells
    if isinstance(val, str) and text.startswith(('=', '+', '@')):
        return f"'{text}"
    return text


def serialize_entity_rows(entity: str) -> list[dict]:
    """Return ordered, flat JSON/CSV-ready dictionaries for a requested domain entity."""
    if entity == 'roi_summary':
        roi_data = build_roi_analytics()
        return [
            {
                'campaign_id': r['campaign_id'],
                'name': r['name'],
                'channel_name': r['channel_name'],
                'status': r['status'],
                'currency': r['currency'],
                'marketing_spend': str(r['marketing_spend']),
                'attributed_revenue': str(r['attributed_revenue']),
                'roi': r['roi'],
                'roas': r['roas'],
                'cpl': str(r['cpl']) if r['cpl'] is not None else None,
                'leads': r['leads'],
                'conversions': r['conversions'],
                'missing_cost_alert': r['missing_cost_alert'],
                'has_currency_mismatch': r['has_currency_mismatch'],
            }
            for r in roi_data['campaign_rows']
        ]

    queryset_specs = {
        'channels': (Channel.objects.order_by('id'), ('id', 'name', 'channel_type', 'status')),
        'campaigns': (
            Campaign.objects.order_by('id'),
            ('id', 'name', 'channel_id', 'budget', 'currency', 'start_date', 'end_date', 'objective', 'status', 'is_paid_campaign'),
        ),
        'creatives': (
            Creative.objects.order_by('id'),
            ('id', 'name', 'primary_campaign_id', 'creative_type', 'status'),
        ),
        'audiences': (
            Audience.objects.order_by('id'),
            ('id', 'name', 'audience_type', 'estimated_size', 'status'),
        ),
        'contacts': (
            Contact.objects.order_by('id'),
            ('id', 'name', 'email', 'company', 'source', 'created_date', 'lifecycle_status'),
        ),
        'sessions': (
            WebSession.objects.order_by('id'),
            ('id', 'anonymous_id', 'contact_id', 'campaign_id', 'landing_page', 'timestamp', 'device_type', 'identity_status', 'has_evidence'),
        ),
        'touchpoints': (
            Touchpoint.objects.order_by('timestamp', 'id'),
            ('id', 'contact_id', 'campaign_id', 'channel_id', 'creative_id', 'session_id', 'interaction_type', 'timestamp', 'device', 'is_online', 'is_post_conversion', 'is_valid'),
        ),
        'leads': (
            Lead.objects.order_by('id'),
            ('id', 'contact_id', 'campaign_id', 'source', 'score', 'created_date', 'status', 'converted_at'),
        ),
        'opportunities': (
            Opportunity.objects.order_by('id'),
            ('id', 'lead_id', 'contact_id', 'name', 'stage', 'expected_revenue', 'actual_revenue', 'closing_date', 'status'),
        ),
        'orders': (
            Order.objects.order_by('id'),
            ('id', 'opportunity_id', 'contact_id', 'order_date', 'revenue', 'currency', 'payment_status', 'verification_status'),
        ),
        'costs': (
            CostRecord.objects.order_by('spend_date', 'id'),
            ('id', 'campaign_id', 'channel_id', 'category', 'amount', 'currency', 'spend_date', 'description'),
        ),
        'exceptions': (
            DataException.objects.order_by('id'),
            ('id', 'issue_type', 'entity_type', 'entity_id', 'severity', 'resolution_status', 'created_date', 'resolved_at', 'resolution_notes'),
        ),
        'attribution_results': (
            AttributionResult.objects.order_by('order_id', 'id'),
            ('id', 'run_id', 'attribution_model_id', 'order_id', 'touchpoint_id', 'campaign_id', 'channel_id', 'contact_id', 'rule_version', 'credit_weight', 'attributed_revenue', 'source_order_revenue', 'currency'),
        ),
    }
    if entity not in queryset_specs:
        raise ValueError(f'Unsupported export entity "{entity}".')

    qs, fields = queryset_specs[entity]
    rows: list[dict] = []
    for raw in qs.values(*fields).iterator(chunk_size=5000):
        rows.append(
            {
                key: (val.isoformat() if hasattr(val, 'isoformat') else (str(val) if hasattr(val, 'quantize') else val))
                for key, val in raw.items()
            }
        )
    return rows


def render_rows_to_csv_string(rows: list[dict]) -> str:
    """Render flat dict rows to RFC-4180 UTF-8 CSV string."""
    if not rows:
        return ''
    buf = io.StringIO()
    fieldnames = list(rows[0].keys())
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: _format_cell(v) for k, v in row.items()})
    return buf.getvalue()


def _sql_literal(value: Any) -> str:
    if value is None:
        return 'NULL'
    if isinstance(value, bool):
        return '1' if value else '0'
    if isinstance(value, (int, float)):
        return str(value)
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def export_marketing_bundle(
    output_dir: str | Path | None = None,
    *,
    mode: str = 'starter',
    seed: int = 20261022,
    anomaly_manifest: list[dict] | None = None,
    validation_report: dict | None = None,
) -> dict:
    """Write full CSV, JSON, SQL snapshot, manifest, data dictionary, validation summary & README bundle."""
    target_root = Path(output_dir) if output_dir else (Path(settings.BASE_DIR) / 'exports')
    csv_dir = target_root / 'csv'
    json_dir = target_root / 'json'
    sql_dir = target_root / 'sql'
    for d in (target_root, csv_dir, json_dir, sql_dir):
        d.mkdir(parents=True, exist_ok=True)

    exported_files: list[str] = []
    entity_counts: dict[str, int] = {}

    for entity in SUPPORTED_EXPORT_ENTITIES:
        rows = serialize_entity_rows(entity)
        entity_counts[entity] = len(rows)

        csv_path = csv_dir / f'{entity}.csv'
        csv_path.write_text(render_rows_to_csv_string(rows), encoding='utf-8')
        exported_files.append(str(csv_path))

        json_path = json_dir / f'{entity}.json'
        json_path.write_text(json.dumps(rows, indent=2, default=str), encoding='utf-8')
        exported_files.append(str(json_path))

    # SQL insert snapshot for core lookup & campaign tables
    sql_lines = ['-- AttributionIQ Deterministic Marketing Seed Snapshot', f'-- Seed: {seed} | Mode: {mode}', '']
    sql_tables = [
        ('channels_channel', serialize_entity_rows('channels')),
        ('campaigns_campaign', serialize_entity_rows('campaigns')),
    ]
    for tbl, rows in sql_tables:
        if not rows:
            continue
        cols = ', '.join(rows[0].keys())
        for r in rows:
            vals = ', '.join(_sql_literal(v) for v in r.values())
            sql_lines.append(f'INSERT INTO {tbl} ({cols}) VALUES ({vals});')
        sql_lines.append('')
    sql_path = sql_dir / 'marketing_seed_snapshot.sql'
    sql_path.write_text('\n'.join(sql_lines), encoding='utf-8')
    exported_files.append(str(sql_path))

    fingerprint = compute_dataset_fingerprint()
    manifest_path = target_root / 'source_manifest.json'
    manifest_payload = {
        'mode': mode,
        'seed': seed,
        'entity_counts': entity_counts,
        'fingerprint': fingerprint,
        'ground_truth_anomaly_manifest': anomaly_manifest or [],
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2), encoding='utf-8')
    exported_files.append(str(manifest_path))

    val_summary = validation_report or get_latest_validation_report()
    val_path = target_root / 'validation_summary.json'
    val_path.write_text(json.dumps(val_summary, indent=2, default=str), encoding='utf-8')
    exported_files.append(str(val_path))

    dict_path = target_root / 'data_dictionary.md'
    dict_path.write_text(
        '\n'.join(
            [
                '# AttributionIQ Synthetic Dataset Dictionary',
                '',
                f'- Seed: `{seed}` | Mode: `{mode}`',
                f'- Overall SHA-256 Checksum: `{fingerprint["overall_checksum"]}`',
                '',
                '| Export Dataset | Rows |',
                '| :--- | ---: |',
                *[f'| `{ent}` | {cnt} |' for ent, cnt in entity_counts.items()],
            ]
        ),
        encoding='utf-8',
    )
    exported_files.append(str(dict_path))

    readme_path = target_root / 'README.md'
    readme_path.write_text(
        '\n'.join(
            [
                '# AttributionIQ Export Bundle',
                '',
                f'Generated deterministically with seed `{seed}` (`mode={mode}`).',
                '',
                '- `csv/`: Individual RFC-4180 CSV extracts per entity',
                '- `json/`: Structured JSON arrays per entity',
                '- `sql/marketing_seed_snapshot.sql`: SQL snapshot statements',
                '- `source_manifest.json`: Checksums and isolated ground-truth anomaly manifest',
                '- `validation_summary.json`: Latest 11-rule validation summary',
                '- `data_dictionary.md`: Dataset schema counts and checksum reference',
            ]
        ),
        encoding='utf-8',
    )
    exported_files.append(str(readme_path))

    return {
        'output_dir': str(target_root),
        'files_count': len(exported_files),
        'entity_counts': entity_counts,
        'overall_checksum': fingerprint['overall_checksum'],
    }

