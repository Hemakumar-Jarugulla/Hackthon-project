"""DRF views for triggering and reading Data Validation suite reports and run history."""

from drf_spectacular.utils import extend_schema
from rest_framework import filters, status, viewsets
from rest_framework.views import APIView

from apps.validation.models import ValidationRun
from apps.validation.serializers import (
    ValidationReportResponseSerializer,
    ValidationRunRequestSerializer,
    ValidationRunSerializer,
)
from apps.validation.services import get_latest_validation_report, run_validation_suite
from common.audit import get_request_ip
from common.permissions import IsActiveUser, IsAnalystOrAbove
from common.responses import success_response


class ValidationRunView(APIView):
    """Trigger the 11-rule validation framework and persist a ValidationRun snapshot."""

    permission_classes = [IsAnalystOrAbove]

    @extend_schema(
        tags=['Validation'],
        summary='Execute Full Data Validation Suite',
        request=ValidationRunRequestSerializer,
        responses={201: ValidationReportResponseSerializer},
    )
    def post(self, request):
        req_ser = ValidationRunRequestSerializer(data=request.data)
        req_ser.is_valid(raise_exception=True)
        report = run_validation_suite(
            triggered_by=req_ser.validated_data.get('triggered_by', 'Manual Validation Trigger'),
            sync_exceptions=req_ser.validated_data.get('sync_exceptions', True),
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        out = ValidationReportResponseSerializer(report)
        return success_response(
            data=out.data,
            message='Data validation suite executed successfully.',
            status_code=status.HTTP_201_CREATED,
        )


class ValidationReportView(APIView):
    """Retrieve the latest persisted validation suite report (or live preview snapshot)."""

    permission_classes = [IsActiveUser]

    @extend_schema(
        tags=['Validation'],
        summary='Get Latest Data Validation Report',
        responses={200: ValidationReportResponseSerializer},
    )
    def get(self, request):
        report = get_latest_validation_report()
        out = ValidationReportResponseSerializer(report)
        return success_response(
            data=out.data,
            message='Validation report retrieved.',
        )


class ValidationRunViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only paginated list and detail of historical ValidationRuns."""

    queryset = ValidationRun.objects.all().order_by('-executed_at', 'id')
    serializer_class = ValidationRunSerializer
    permission_classes = [IsActiveUser]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['id', 'executed_at', 'passed_checks', 'failed_checks']
    ordering = ['-executed_at', 'id']

