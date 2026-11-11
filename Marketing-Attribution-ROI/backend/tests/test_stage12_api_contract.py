"""Stage 12 API contract & CORS verification suite for React frontend integration."""

from django.core.management import call_command
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import UserProfile
from apps.accounts.services import create_user_with_profile
from apps.channels.models import Channel
from apps.contacts.models import Contact


@pytest.mark.django_db
def test_stage12_frontend_api_contract_cors_jwt_and_endpoints():
    # Generate compact deterministic dataset as live API backend source
    call_command('generate_marketing_data', '--mode', 'starter', '--seed', '20261022', '--with-attribution')

    # Verify CORS preflight / Origin header for React Vite origin
    anon = APIClient()
    health = anon.get('/api/v1/health/', HTTP_ORIGIN='http://localhost:5173')
    assert health.status_code == 200
    assert health.headers.get('Access-Control-Allow-Origin') == 'http://localhost:5173'

    # 1. Self-registration -> JWT access/refresh/user envelope
    reg_resp = anon.post(
        '/api/v1/auth/register/',
        {
            'name': 'Frontend Tester',
            'email': 'frontend.viewer@example.com',
            'role': 'Viewer',
            'password': 'StrongPassword!2026',
            'department': 'Revenue Operations',
            'timezone': 'UTC+05:30',
        },
        format='json',
    )
    assert reg_resp.status_code == 201, reg_resp.json()
    reg_data = reg_resp.json()['data']
    assert 'access' in reg_data and 'refresh' in reg_data
    assert reg_data['user']['role'] == UserProfile.Role.VIEWER

    # 2. Login + Refresh + Profile update + Logout lifecycle
    create_user_with_profile(
        email='admin12@example.com',
        password='AdminPassword!2026',
        name='Workspace Admin',
        role=UserProfile.Role.ADMIN,
    )
    login_resp = anon.post(
        '/api/v1/auth/login/',
        {'email': 'admin12@example.com', 'password': 'AdminPassword!2026'},
        format='json',
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()['data']
    access_token = login_data['access']
    refresh_token = login_data['refresh']

    refresh_resp = anon.post(
        '/api/v1/auth/refresh/',
        {'refresh': refresh_token},
        format='json',
    )
    assert refresh_resp.status_code == 200
    rotated_access = refresh_resp.json()['access']
    rotated_refresh = refresh_resp.json().get('refresh', refresh_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {rotated_access}')

    prof_resp = client.patch(
        '/api/v1/auth/profile/',
        {'department': 'Marketing Analytics'},
        format='json',
    )
    assert prof_resp.status_code == 200

    # 3. Core paginated endpoints consumed by fetchAllPaginated + snake_case adapters
    cmp_list = client.get('/api/v1/campaigns/', {'page_size': 100})
    assert cmp_list.status_code == 200
    assert 'results' in cmp_list.json()
    assert cmp_list.json()['count'] == 15

    first_channel = Channel.objects.order_by('id').first()
    create_cmp = client.post(
        '/api/v1/campaigns/',
        {
            'name': 'React Live Integration Campaign',
            'channel': first_channel.id,
            'budget': 9500,
            'currency': 'USD',
            'start_date': '2026-06-01',
            'end_date': '2026-06-30',
            'objective': 'Pipeline Generation',
            'status': 'Active',
            'is_paid_campaign': True,
        },
        format='json',
    )
    assert create_cmp.status_code == 201
    new_cmp_id = create_cmp.json()['data']['id']

    archive_cmp = client.patch(
        f'/api/v1/campaigns/{new_cmp_id}/',
        {'status': 'Archived'},
        format='json',
    )
    assert archive_cmp.status_code == 200
    assert archive_cmp.json()['data']['status'] == 'Archived'

    # 4. Contact Journey supporting both camelCase `modelId` and `model_id`
    first_contact = Contact.objects.order_by('id').first()
    journey_resp = client.get(
        f'/api/v1/contacts/{first_contact.id}/journey/',
        {'modelId': 'position_based'},
    )
    assert journey_resp.status_code == 200
    j_data = journey_resp.json()['data']
    assert 'timeline' in j_data and 'attribution_results' in j_data

    # 5. Attribution Run & 5-Model Compare endpoints consumed by AttributionPages
    attr_run = client.get(
        '/api/v1/attribution/run/',
        {'modelId': 'position_based', 'conversionWindowDays': 90, 'dateRange': 'all_time'},
    )
    assert attr_run.status_code == 200
    attr_data = attr_run.json()['data']
    assert 'campaign_results' in attr_data and 'channel_results' in attr_data

    attr_comp = client.get(
        '/api/v1/attribution/compare/',
        {'conversionWindowDays': 90, 'dateRange': 'all_time'},
    )
    assert attr_comp.status_code == 200
    comp_data = attr_comp.json()['data']
    assert len(comp_data['channel_comparison']) > 0
    for key in ('first_touch', 'last_touch', 'linear', 'time_decay', 'position_based'):
        assert key in comp_data['channel_comparison'][0]

    # 6. Dashboard, ROI, Trends, Exceptions, Validation & Report exports
    dash = client.get('/api/v1/analytics/dashboard/', {'dateRange': 'all_time'})
    assert dash.status_code == 200
    dash_data = dash.json()['data']
    assert 'kpis' in dash_data and 'charts' in dash_data and 'widgets' in dash_data
    assert 'recent_attribution_runs' in dash_data['widgets']

    roi = client.get('/api/v1/analytics/roi/', {'dateRange': 'all_time', 'modelId': 'position_based'})
    assert roi.status_code == 200
    assert 'campaign_rows' in roi.json()['data']

    trends = client.get('/api/v1/analytics/trends/', {'dateRange': 'all_time'})
    assert trends.status_code == 200
    assert 'monthly_series' in trends.json()['data']

    val_run = client.post(
        '/api/v1/validation/run/',
        {'triggered_by': 'Stage12 Contract Check', 'sync_exceptions': True},
        format='json',
    )
    assert val_run.status_code == 201
    assert len(val_run.json()['data']['checks']) == 11

    contacts_export = client.get('/api/v1/reports/export/json/', {'entity': 'contacts'})
    assert contacts_export.status_code == 200
    assert isinstance(contacts_export.json(), list)

    # 7. Logout blacklists refresh token
    logout_resp = client.post('/api/v1/auth/logout/', {'refresh': rotated_refresh}, format='json')
    assert logout_resp.status_code == 200
    reuse_resp = anon.post('/api/v1/auth/refresh/', {'refresh': rotated_refresh}, format='json')
    assert reuse_resp.status_code == 401
