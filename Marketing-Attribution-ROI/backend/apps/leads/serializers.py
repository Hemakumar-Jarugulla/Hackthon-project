"""Serializers for Lead CRUD and status transition history."""

from rest_framework import serializers

from apps.leads.models import Lead, LeadStatusHistory


class LeadStatusHistorySerializer(serializers.ModelSerializer):
    """Read serializer for historical Lead qualification transitions."""

    class Meta:
        model = LeadStatusHistory
        fields = [
            'id',
            'previous_status',
            'new_status',
            'changed_at',
            'notes',
        ]
        read_only_fields = fields


class LeadSerializer(serializers.ModelSerializer):
    """Read/write serializer validating Lead score bounds and relational metadata."""

    created_date = serializers.DateField(required=False)
    status_reason = serializers.CharField(write_only=True, required=False, allow_blank=True)
    contact_name = serializers.SerializerMethodField()
    contact_email = serializers.SerializerMethodField()
    campaign_name = serializers.SerializerMethodField()
    opportunities_count = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            'id',
            'contact',
            'contact_name',
            'contact_email',
            'campaign',
            'campaign_name',
            'source',
            'score',
            'created_date',
            'status',
            'converted_at',
            'status_reason',
            'opportunities_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_contact_name(self, obj: Lead) -> str | None:
        return obj.contact.name if obj.contact else None

    def get_contact_email(self, obj: Lead) -> str | None:
        return obj.contact.email if obj.contact else None

    def get_campaign_name(self, obj: Lead) -> str | None:
        return obj.campaign.name if obj.campaign else None

    def get_opportunities_count(self, obj: Lead) -> int:
        annotated = getattr(obj, 'opportunities_count', None)
        if isinstance(annotated, int):
            return annotated
        return obj.opportunities.count()

    def validate_source(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError('Lead source cannot be blank.')
        return cleaned

    def validate_score(self, value: int) -> int:
        if value < 0 or value > 100:
            raise serializers.ValidationError('Lead score must be between 0 and 100.')
        return value

