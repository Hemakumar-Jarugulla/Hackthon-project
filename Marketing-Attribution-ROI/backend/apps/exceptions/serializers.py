"""Serializers for DataException CRUD, scanning, summary metrics, and resolution actions."""

from rest_framework import serializers

from apps.exceptions.models import DataException


class DataExceptionSerializer(serializers.ModelSerializer):
    """Read/create serializer for persisted data quality anomalies."""

    resolved_by_username = serializers.SerializerMethodField()

    class Meta:
        model = DataException
        fields = [
            'id',
            'issue_type',
            'entity_type',
            'entity_id',
            'severity',
            'description',
            'expected_decision',
            'actual_decision',
            'resolution_status',
            'created_date',
            'resolved_at',
            'resolved_by',
            'resolved_by_username',
            'resolution_notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'resolved_at',
            'resolved_by',
            'resolved_by_username',
            'created_at',
            'updated_at',
        ]

    def get_resolved_by_username(self, obj: DataException) -> str | None:
        return obj.resolved_by.username if obj.resolved_by else None


class ExceptionResolveRequestSerializer(serializers.Serializer):
    """Input payload for resolving, reviewing, or reopening an exception."""

    resolution_status = serializers.ChoiceField(
        choices=DataException.ResolutionStatus.choices,
        required=False,
        default=DataException.ResolutionStatus.RESOLVED,
    )
    resolution_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
    )


class ExceptionSummarySerializer(serializers.Serializer):
    """Exception telemetry grouped by status, severity, and business problem."""

    total_exceptions = serializers.IntegerField()
    open_exceptions = serializers.IntegerField()
    reviewed_exceptions = serializers.IntegerField()
    resolved_exceptions = serializers.IntegerField()
    open_critical_high = serializers.IntegerField()
    by_severity = serializers.DictField(child=serializers.IntegerField())
    by_status = serializers.DictField(child=serializers.IntegerField())
    by_issue_type = serializers.DictField(child=serializers.IntegerField())

