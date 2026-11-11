"""Stage 4 verification tests covering JWT auth, profile security, user management, and RBAC."""

import re

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import UserProfile
from apps.accounts.services import create_user_with_profile
from apps.audit.models import AuditLog

User = get_user_model()


def _auth_client(access_token: str) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
    return client


@pytest.mark.django_db
def test_register_login_jwt_claims_refresh_rotation_and_logout_blacklist():
    client = APIClient()

    # Self-registration must block Admin/Manager privilege escalation
    bad_reg = client.post(
        '/api/v1/auth/register/',
        {
            'name': 'Jordan Taylor',
            'email': 'jordan@attributioniq.io',
            'password': 'StrongPass!2026',
            'role': UserProfile.Role.ADMIN,
        },
        format='json',
    )
    assert bad_reg.status_code == 400
    assert 'role' in bad_reg.data['error']['details']

    # Valid registration defaults to Viewer (or Analyst) cleanly and issues JWT tokens
    reg = client.post(
        '/api/v1/auth/register/',
        {
            'name': 'Jordan Taylor',
            'email': 'Jordan.Taylor@AttributionIQ.io',
            'password': 'StrongPass!2026',
            'department': 'Growth Analytics',
            'timezone': 'UTC+05:30',
        },
        format='json',
    )
    assert reg.status_code == 201
    body = reg.data['data']
    assert body['user']['email'] == 'jordan.taylor@attributioniq.io'
    assert body['user']['role'] == UserProfile.Role.VIEWER
    assert body['user']['user_code'] == 'USR-2026-0001'
    assert body['access']
    assert body['refresh']

    # Case-insensitive email uniqueness check
    dup_reg = client.post(
        '/api/v1/auth/register/',
        {
            'name': 'Dup',
            'email': 'JORDAN.TAYLOR@attributioniq.io',
            'password': 'StrongPass!2026',
        },
        format='json',
    )
    assert dup_reg.status_code == 400

    # JWT access token contains custom RBAC claims
    decoded = AccessToken(body['access'])
    assert decoded['role'] == UserProfile.Role.VIEWER
    assert decoded['user_code'] == 'USR-2026-0001'
    assert decoded['email'] == 'jordan.taylor@attributioniq.io'

    # Login via email
    login_resp = client.post(
        '/api/v1/auth/login/',
        {'email': 'jordan.taylor@attributioniq.io', 'password': 'StrongPass!2026'},
        format='json',
    )
    assert login_resp.status_code == 200
    old_refresh = login_resp.data['data']['refresh']
    access = login_resp.data['data']['access']

    # Refresh token rotates and blacklists the old refresh token
    refresh_resp = client.post(
        '/api/v1/auth/refresh/',
        {'refresh': old_refresh},
        format='json',
    )
    assert refresh_resp.status_code == 200
    new_refresh = refresh_resp.data['refresh']
    new_access = refresh_resp.data['access']
    assert new_refresh != old_refresh

    reused_old_refresh = client.post(
        '/api/v1/auth/refresh/',
        {'refresh': old_refresh},
        format='json',
    )
    assert reused_old_refresh.status_code == 401

    # Logout blacklists the active refresh token
    authed = _auth_client(new_access)
    logout_resp = authed.post('/api/v1/auth/logout/', {'refresh': new_refresh}, format='json')
    assert logout_resp.status_code == 200

    after_logout_refresh = client.post(
        '/api/v1/auth/refresh/',
        {'refresh': new_refresh},
        format='json',
    )
    assert after_logout_refresh.status_code == 401
    assert access  # initial access token verified above


@pytest.mark.django_db
def test_profile_update_cannot_escalate_role_and_password_flows():
    user = create_user_with_profile(
        email='analyst@attributioniq.io',
        password='InitialPass!2026',
        name='Sarah Chen',
        role=UserProfile.Role.MARKETING_ANALYST,
        department='Growth Analytics',
    )
    client = APIClient()
    login_resp = client.post(
        '/api/v1/auth/login/',
        {'username': user.username, 'password': 'InitialPass!2026'},
        format='json',
    )
    assert login_resp.status_code == 200
    token = login_resp.data['data']['access']

    authed = _auth_client(token)
    me_get = authed.get('/api/v1/auth/me/')
    assert me_get.status_code == 200
    assert me_get.data['data']['role'] == UserProfile.Role.MARKETING_ANALYST

    # Attempt to pass role/status during self-service PATCH; role must stay unchanged
    me_patch = authed.patch(
        '/api/v1/auth/me/',
        {
            'name': 'Sarah L. Chen',
            'timezone': 'America/New_York',
            'role': UserProfile.Role.ADMIN,
            'status': UserProfile.AccountStatus.SUSPENDED,
        },
        format='json',
    )
    assert me_patch.status_code == 200
    assert me_patch.data['data']['name'] == 'Sarah L. Chen'
    assert me_patch.data['data']['timezone'] == 'America/New_York'
    assert me_patch.data['data']['role'] == UserProfile.Role.MARKETING_ANALYST
    assert me_patch.data['data']['status'] == UserProfile.AccountStatus.ACTIVE

    # Change password
    cp_resp = authed.post(
        '/api/v1/auth/change-password/',
        {
            'current_password': 'InitialPass!2026',
            'new_password': 'RotatedPass!2026',
            'confirm_password': 'RotatedPass!2026',
        },
        format='json',
    )
    assert cp_resp.status_code == 200

    # Forgot password + reset password via Django token email
    mail.outbox.clear()
    forgot = client.post(
        '/api/v1/auth/forgot-password/',
        {'email': 'analyst@attributioniq.io'},
        format='json',
    )
    assert forgot.status_code == 200
    assert len(mail.outbox) == 1
    email_body = mail.outbox[0].body
    uid_match = re.search(r'uid:\s*(\S+)', email_body)
    token_match = re.search(r'token:\s*(\S+)', email_body)
    assert uid_match and token_match

    reset = client.post(
        '/api/v1/auth/reset-password/',
        {
            'uid': uid_match.group(1),
            'token': token_match.group(1),
            'new_password': 'FinalResetPass!2026',
            'confirm_password': 'FinalResetPass!2026',
        },
        format='json',
    )
    assert reset.status_code == 200

    # Login with final password succeeds; old fails
    assert client.post(
        '/api/v1/auth/login/',
        {'email': 'analyst@attributioniq.io', 'password': 'RotatedPass!2026'},
        format='json',
    ).status_code == 400
    assert client.post(
        '/api/v1/auth/login/',
        {'email': 'analyst@attributioniq.io', 'password': 'FinalResetPass!2026'},
        format='json',
    ).status_code == 200


@pytest.mark.django_db
def test_admin_user_management_and_rbac_enforcement_across_all_roles():
    admin_user = create_user_with_profile(
        email='admin@attributioniq.io',
        password='AdminPass!2026',
        name='Alex Morgan',
        role=UserProfile.Role.ADMIN,
        department='Revenue Operations',
    )
    manager_user = create_user_with_profile(
        email='manager@attributioniq.io',
        password='ManagerPass!2026',
        name='Marcus Vance',
        role=UserProfile.Role.MARKETING_MANAGER,
    )
    analyst_user = create_user_with_profile(
        email='analyst2@attributioniq.io',
        password='AnalystPass!2026',
        name='Priya Nair',
        role=UserProfile.Role.MARKETING_ANALYST,
    )
    viewer_user = create_user_with_profile(
        email='viewer@attributioniq.io',
        password='ViewerPass!2026',
        name='Elena Rostova',
        role=UserProfile.Role.VIEWER,
    )

    anon = APIClient()
    assert anon.get('/api/v1/users/').status_code == 401
    assert anon.get('/api/v1/auth/roles/').status_code == 401

    def login_token(email: str, password: str) -> str:
        resp = anon.post('/api/v1/auth/login/', {'email': email, 'password': password}, format='json')
        assert resp.status_code == 200
        return resp.data['data']['access']

    admin_client = _auth_client(login_token(admin_user.email, 'AdminPass!2026'))
    mgr_client = _auth_client(login_token(manager_user.email, 'ManagerPass!2026'))
    analyst_client = _auth_client(login_token(analyst_user.email, 'AnalystPass!2026'))
    viewer_client = _auth_client(login_token(viewer_user.email, 'ViewerPass!2026'))

    # All authenticated active users can read canonical role matrix
    assert viewer_client.get('/api/v1/auth/roles/').status_code == 200

    # Non-Admin roles receive 403 Forbidden on /api/v1/users/
    for non_admin in (mgr_client, analyst_client, viewer_client):
        assert non_admin.get('/api/v1/users/').status_code == 403
        assert non_admin.post(
            '/api/v1/users/',
            {'email': 'blocked@attributioniq.io', 'role': UserProfile.Role.VIEWER},
            format='json',
        ).status_code == 403

    # Admin cannot remove or deactivate the last active workspace Admin
    demote_last_admin = admin_client.patch(
        f'/api/v1/users/{admin_user.pk}/role/',
        {'role': UserProfile.Role.VIEWER},
        format='json',
    )
    assert demote_last_admin.status_code == 400

    delete_last_admin = admin_client.delete(f'/api/v1/users/{admin_user.pk}/')
    assert delete_last_admin.status_code == 400

    # Admin provisions a second user cleanly with Manager role
    created = admin_client.post(
        '/api/v1/users/',
        {
            'name': 'Devon Brooks',
            'email': 'devon@attributioniq.io',
            'password': 'DevonPass!2026',
            'role': UserProfile.Role.MARKETING_MANAGER,
            'department': 'Demand Generation',
        },
        format='json',
    )
    assert created.status_code == 201
    new_user_id = created.data['data']['id']

    # Admin filters users by role
    filtered = admin_client.get('/api/v1/users/?role=Marketing%20Manager')
    assert filtered.status_code == 200
    assert filtered.data['count'] == 2

    # Admin updates role of newly created user via /role/ action
    promoted = admin_client.patch(
        f'/api/v1/users/{new_user_id}/role/',
        {'role': UserProfile.Role.ADMIN},
        format='json',
    )
    assert promoted.status_code == 200
    assert promoted.data['data']['role'] == UserProfile.Role.ADMIN

    # Now Admin soft-deactivates the viewer user; viewer can no longer log in or call APIs
    soft_del = admin_client.delete(f'/api/v1/users/{viewer_user.pk}/')
    assert soft_del.status_code == 200
    assert soft_del.data['data']['is_active'] is False
    assert soft_del.data['data']['status'] == UserProfile.AccountStatus.SUSPENDED

    assert viewer_client.get('/api/v1/auth/me/').status_code == 401
    assert anon.post(
        '/api/v1/auth/login/',
        {'email': viewer_user.email, 'password': 'ViewerPass!2026'},
        format='json',
    ).status_code == 400

    # Verify AuditLog recorded CREATE, STATUS_CHANGE, and ARCHIVE actions
    assert AuditLog.objects.filter(entity_type='User', action=AuditLog.Action.CREATE).count() >= 5
    assert AuditLog.objects.filter(entity_type='User', action=AuditLog.Action.STATUS_CHANGE).exists()
    assert AuditLog.objects.filter(entity_type='User', action=AuditLog.Action.ARCHIVE).exists()

