"""Serializers for Data Validation runs, check results, and validation reports."""

from rest_framework import serializers

from apps.validation.models import ValidationCheckResult, ValidationRun


class ValidationCheckResultSerializer(serializers.ModelSerializer):
    """Serializer for individual validation check outcomes."""

    last_run = serializers.DateTimeField(source='run.executed_at', read_only=True)

    class Meta:
        model = ValidationCheckResult
        fields = [
            'check_code',
            'check_name',
            'category',
            'entity',
            'records_checked',
            'failed_records',
            'status',
            'details',
            'last_run',
        ]


class ValidationRunSerializer(serializers.ModelSerializer):
    """Summary serializer for persisted ValidationRun history."""

    class Meta:
        model = ValidationRun
        fields = [
            'id',
            'executed_at',
            'triggered_by',
            'total_checks',
            'passed_checks',
            'failed_checks',
            'warning_checks',
            'total_records_checked',
            'total_invalid_records',
            'duration_ms',
        ]
        read_only_fields = fields


class ValidationRunRequestSerializer(serializers.Serializer):
    """Input options for triggering a validation suite execution."""

    triggered_by = serializers.CharField(
        max_length=100,
        required=False,
        default='Manual Validation Trigger',
    )
    sync_exceptions = serializers.BooleanField(required=False, default=True)


class ValidationReportResponseSerializer(serializers.Serializer):
    """Full validation report payload covering counts, exceptions, checks, and history."""

    run_id = serializers.CharField(allow_null=True)
    executed_at = serializers.CharField()
    triggered_by = serializers.CharField()
    total_checks = serializers.IntegerField()
    passed_checks = serializers.IntegerField()
    failed_checks = serializers.IntegerField()
    warning_checks = serializers.IntegerField()
    total_records_checked = serializers.IntegerField()
    valid_records = serializers.IntegerField()
    invalid_records = serializers.IntegerField()
    warnings = serializers.IntegerField()
    errors = serializers.IntegerField()
    exception_counts = serializers.DictField()
    checks = serializers.ListField(child=serializers.DictField())
    history = serializers.ListField(child=serializers.DictField())

