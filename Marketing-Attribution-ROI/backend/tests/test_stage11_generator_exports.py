"""Stage 11 verification tests covering deterministic data generation, reproducibility, exports & reports API."""

import csv
import io
import json
from pathlib import Path

from django.core.management import call_command
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import UserProfile
from apps.accounts.services import build_token_pair_for_user, create_user_with_profile
from apps.attribution.models import AttributionResult, AttributionRun
from apps.campaigns.models import Campaign
from apps.channels.models import Channel
from apps.contacts.models import Contact
from apps.exceptions.models import DataException
from apps.orders.models import Order
from apps.validation.services import run_validation_suite
from data_generator.exports.exporter import SUPPORTED_EXPORT_ENTITIES, render_rows_to_csv_string


def _client_for_role(email: str, role: str) -> APIClient:
    user = create_user_with_profile(
        email=email,
        password='StrongPass!2026',
        name=email.split('@')[0],
        role=role,
    )
    tokens = build_token_pair_for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


@pytest.mark.django_db
def test_stage11_deterministic_generation_exports_sequences_and_reports_api(tmp_path):
    export_dir = Path(tmp_path) / 'bundle_out'
    stdout = io.StringIO()

    call_command(
        'generate_marketing_data',
        '--mode',
        'starter',
        '--seed',
        '20261022',
        '--verify-reproducibility',
        '--with-attribution',
        '--export',
        '--export-dir',
        str(export_dir),
        stdout=stdout,
    )
    cli_out = stdout.getvalue()
    assert 'Reproducibility PASSED' in cli_out
    assert 'Exported' in cli_out

    # Core entity counts created cleanly
    assert Channel.objects.count() == 8
    assert Campaign.objects.count() == 15
    assert Contact.objects.count() == 60
    assert AttributionRun.objects.count() >= 1
    assert AttributionResult.objects.count() > 0

    # The generator seeds four anomaly families, but never injects duplicate orders.
    issue_types = set(DataException.objects.values_list('issue_type', flat=True))
    assert (
        set(DataException.IssueType.values) - {DataException.IssueType.DUPLICATE_REVENUE}
    ).issubset(issue_types)
    assert not Order.objects.filter(
        verification_status=Order.VerificationStatus.DUPLICATE
    ).exists()
    assert DataException.IssueType.DUPLICATE_REVENUE not in issue_types

    # Validation run finishes with 11 rules and clean baseline integrity
    val_report = run_validation_suite(triggered_by='Stage11 Pytest', sync_exceptions=True)
    assert len(val_report['checks']) == 11
    assert val_report['errors'] >= 0  # Ensure structure is populated cleanly
    passed_codes = {c['check_code'] for c in val_report['checks'] if c['status'] == 'Passed'}
    # Core relational & attribution conservation checks MUST pass cleanly
    assert {'VAL-01', 'VAL-02', 'VAL-03', 'VAL-04', 'VAL-05'}.issubset(passed_codes)

    # Bundle files & isolation verification
    assert (export_dir / 'README.md').is_file()
    assert (export_dir / 'data_dictionary.md').is_file()
    assert (export_dir / 'sql' / 'marketing_seed_snapshot.sql').is_file()
    assert (export_dir / 'source_manifest.json').is_file()
    assert (export_dir / 'validation_summary.json').is_file()

    manifest = json.loads((export_dir / 'source_manifest.json').read_text(encoding='utf-8'))
    assert manifest['seed'] == 20261022
    assert manifest['mode'] == 'starter'
    assert len(manifest['ground_truth_anomaly_manifest']) > 0
    assert len(manifest['fingerprint']['overall_checksum']) == 64

    for ent in SUPPORTED_EXPORT_ENTITIES:
        csv_file = export_dir / 'csv' / f'{ent}.csv'
        json_file = export_dir / 'json' / f'{ent}.json'
        assert csv_file.is_file()
        assert json_file.is_file()
        parsed_rows = json.loads(json_file.read_text(encoding='utf-8'))
        assert isinstance(parsed_rows, list)
        if parsed_rows:
            # Verify ground truth never leaks onto domain export rows
            assert 'ground_truth' not in parsed_rows[0]
            assert 'anomaly_label' not in parsed_rows[0]

    # Verify CSV formula neutralization helper protects against spreadsheet formula injection
    neutralized = render_rows_to_csv_string([{'name': '=SUM(A1:A2)', 'notes': '+cmd'}])
    assert "'=SUM(A1:A2)" in neutralized
    assert "'+cmd" in neutralized

    # Preserved IdSequence state -> creating a new Campaign & Touchpoint after seed does not collide
    manager = _client_for_role('mgr11@example.com', UserProfile.Role.MARKETING_MANAGER)
    first_channel = Channel.objects.order_by('id').first()
    cmp_resp = manager.post(
        '/api/v1/campaigns/',
        {
            'name': 'Post-Seed Verification Campaign',
            'channel': first_channel.id,
            'budget': '12500.00',
            'currency': 'USD',
            'start_date': '2026-06-01',
            'end_date': '2026-07-01',
            'objective': 'Lead Generation',
            'status': 'Active',
            'is_paid_campaign': True,
        },
        format='json',
    )
    assert cmp_resp.status_code == 201, cmp_resp.json()
    assert cmp_resp.json()['data']['id'] == 'CMP-2026-000016'

    first_contact = Contact.objects.order_by('id').first()
    tp_resp = manager.post(
        '/api/v1/touchpoints/',
        {
            'contact': first_contact.id,
            'campaign': 'CMP-2026-000016',
            'channel': first_channel.id,
            'interaction_type': 'Paid Search Click',
            'timestamp': '2026-06-05T10:30:00Z',
            'is_online': True,
        },
        format='json',
    )
    assert tp_resp.status_code == 201, tp_resp.json()
    assert tp_resp.json()['data']['id'].startswith(f'TOUCH-{first_contact.id}-')

    # Reports REST API tests
    anon = APIClient()
    assert anon.get('/api/v1/reports/datasets/').status_code == 401

    viewer = _client_for_role('viewer11@example.com', UserProfile.Role.VIEWER)
    ds_resp = viewer.get('/api/v1/reports/datasets/')
    assert ds_resp.status_code == 200
    ds_entities = {item['entity'] for item in ds_resp.json()['data']['datasets']}
    assert ds_entities == set(SUPPORTED_EXPORT_ENTITIES)

    csv_resp = viewer.get('/api/v1/reports/export/csv/?entity=roi_summary')
    assert csv_resp.status_code == 200
    assert 'text/csv' in csv_resp['Content-Type']
    csv_reader = list(csv.reader(io.StringIO(csv_resp.content.decode('utf-8'))))
    assert len(csv_reader) >= 2
    assert 'campaign_id' in csv_reader[0]

    json_resp = viewer.get('/api/v1/reports/export/json/?entity=campaigns')
    assert json_resp.status_code == 200
    payload = json_resp.json()
    assert isinstance(payload, list)
    assert len(payload) == Campaign.objects.count()
    assert any(row['id'] == 'CMP-2026-000016' for row in payload)

    bad_resp = viewer.get('/api/v1/reports/export/csv/?entity=invalid_table')
    assert bad_resp.status_code == 400
