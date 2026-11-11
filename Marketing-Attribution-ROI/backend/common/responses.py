"""Standardized API response envelope builders for consistent frontend consumption."""

from rest_framework import status as http_status
from rest_framework.response import Response


def success_response(
    data=None,
    message='Success',
    status_code=http_status.HTTP_200_OK,
    meta=None,
):
    """Return a consistent success JSON response."""
    payload = {
        'success': True,
        'message': message,
        'data': data,
    }
    if meta is not None:
        payload['meta'] = meta
    return Response(payload, status=status_code)


def error_response(
    message='An error occurred.',
    code='error',
    details=None,
    status_code=http_status.HTTP_400_BAD_REQUEST,
):
    """Return a consistent error JSON response."""
    return Response(
        {
            'success': False,
            'error': {
                'code': code,
                'message': message,
                'details': details,
            },
        },
        status=status_code,
    )

