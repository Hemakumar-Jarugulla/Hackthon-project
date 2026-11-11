"""Centralized DRF exception handler with structured logging."""

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class ConflictException(APIException):
    """HTTP 409 Conflict exception raised when deleting protected relational records."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Operation conflicts with existing dependent records.'
    default_code = 'protected_reference'


def custom_exception_handler(exc, context):
    """
    Wrap DRF and unexpected server exceptions into a consistent JSON error envelope
    without leaking internal stack traces to API clients.
    """
    if isinstance(exc, DjangoValidationError):
        detail = exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
        return Response(
            {
                'success': False,
                'error': {
                    'code': 'validation_error',
                    'message': 'Validation failed.',
                    'details': detail,
                },
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    response = exception_handler(exc, context)
    view = context.get('view')
    view_name = view.__class__.__name__ if view is not None else 'UnknownView'

    if response is None:
        logger.exception('Unhandled exception in %s: %s', view_name, exc)
        return Response(
            {
                'success': False,
                'error': {
                    'code': 'internal_server_error',
                    'message': 'An unexpected internal server error occurred.',
                    'details': None,
                },
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    code = exc.default_code if isinstance(exc, APIException) else 'api_error'
    detail = response.data
    if isinstance(detail, dict) and 'detail' in detail:
        message = str(detail['detail'])
    elif isinstance(detail, list) and detail:
        message = str(detail[0])
    else:
        message = 'Request could not be processed.'

    if response.status_code >= 500:
        logger.error('Server error (%s) in %s: %s', response.status_code, view_name, exc)

    response.data = {
        'success': False,
        'error': {
            'code': str(code),
            'message': message,
            'details': detail,
        },
    }
    return response

