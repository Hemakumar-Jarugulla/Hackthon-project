"""DRF views exposing downloadable CSV and JSON entity/report exports."""

import json

from django.http import HttpResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView

from common.permissions import IsActiveUser
from common.responses import success_response
from data_generator.exports.exporter import (
    SUPPORTED_EXPORT_ENTITIES,
    render_rows_to_csv_string,
    serialize_entity_rows,
)


def _resolve_requested_entity(request) -> str:
    entity = (request.query_params.get('entity') or 'roi_summary').strip().lower()
    if entity not in SUPPORTED_EXPORT_ENTITIES:
        raise ValidationError(
            {
                'entity': [
                    f'Unsupported export entity "{entity}". Choose from: '
                    + ', '.join(SUPPORTED_EXPORT_ENTITIES)
                ]
            }
        )
    return entity


class ReportDatasetsListView(APIView):
    """List available downloadable datasets with live row counts and export links."""

    permission_classes = [IsActiveUser]

    @extend_schema(
        tags=['Reports'],
        summary='List Exportable Marketing Datasets',
        responses={200: dict},
    )
    def get(self, request):
        datasets = [
            {
                'entity': ent,
                'row_count': len(serialize_entity_rows(ent)),
                'csv_url': f'/api/v1/reports/export/csv/?entity={ent}',
                'json_url': f'/api/v1/reports/export/json/?entity={ent}',
            }
            for ent in SUPPORTED_EXPORT_ENTITIES
        ]
        return success_response(
            data={'datasets': datasets},
            message='Export datasets listed successfully.',
        )


class ReportCsvExportView(APIView):
    """Download any entity or ROI summary dataset as UTF-8 CSV."""

    permission_classes = [IsActiveUser]

    @extend_schema(
        tags=['Reports'],
        summary='Export Dataset as CSV',
        parameters=[
            OpenApiParameter(
                'entity',
                str,
                required=False,
                description='Dataset key (default: roi_summary)',
            )
        ],
        responses={200: bytes},
    )
    def get(self, request):
        entity = _resolve_requested_entity(request)
        rows = serialize_entity_rows(entity)
        csv_content = render_rows_to_csv_string(rows)
        response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{entity}.csv"'
        return response


class ReportJsonExportView(APIView):
    """Download any entity or ROI summary dataset as structured JSON."""

    permission_classes = [IsActiveUser]

    @extend_schema(
        tags=['Reports'],
        summary='Export Dataset as JSON',
        parameters=[
            OpenApiParameter(
                'entity',
                str,
                required=False,
                description='Dataset key (default: roi_summary)',
            )
        ],
        responses={200: dict},
    )
    def get(self, request):
        entity = _resolve_requested_entity(request)
        rows = serialize_entity_rows(entity)
        payload = json.dumps(rows, indent=2, default=str)
        response = HttpResponse(payload, content_type='application/json; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{entity}.json"'
        return response
