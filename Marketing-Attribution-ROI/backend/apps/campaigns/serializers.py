"""Serializers for Campaign CRUD, M2M Creative/Audience bridges, history, and ROI metrics."""

from decimal import Decimal

from rest_framework import serializers

from apps.audiences.models import Audience
from apps.campaigns.models import Campaign, CampaignStatusHistory
from apps.channels.models import Channel
from apps.creatives.models import Creative


class CampaignStatusHistorySerializer(serializers.ModelSerializer):
    """Read serializer for historical campaign lifecycle transitions."""

    changed_by_username = serializers.SerializerMethodField()

    class Meta:
        model = CampaignStatusHistory
        fields = [
            'id',
            'previous_status',
            'new_status',
            'changed_by',
            'changed_by_username',
            'reason',
            'changed_at',
        ]
        read_only_fields = fields

    def get_changed_by_username(self, obj: CampaignStatusHistory) -> str | None:
        return obj.changed_by.username if obj.changed_by else None


class CampaignReadSerializer(serializers.ModelSerializer):
    """Read serializer combining Campaign metadata, M2M linkages, and live ROI telemetry."""

    channel_name = serializers.CharField(source='channel.name', read_only=True)
    channel_type = serializers.CharField(source='channel.channel_type', read_only=True)
    creatives = serializers.SerializerMethodField()
    audiences = serializers.SerializerMethodField()
    primary_creative_id = serializers.SerializerMethodField()
    primary_creative_name = serializers.SerializerMethodField()
    primary_audience_id = serializers.SerializerMethodField()
    primary_audience_name = serializers.SerializerMethodField()
    spend = serializers.SerializerMethodField()
    attributed_revenue = serializers.SerializerMethodField()
    leads_count = serializers.SerializerMethodField()
    conversions_count = serializers.SerializerMethodField()
    touchpoints_count = serializers.SerializerMethodField()
    roi = serializers.SerializerMethodField()
    roas = serializers.SerializerMethodField()
    has_currency_mismatch = serializers.SerializerMethodField()
    missing_cost_alert = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            'id',
            'name',
            'description',
            'channel',
            'channel_name',
            'channel_type',
            'budget',
            'currency',
            'start_date',
            'end_date',
            'objective',
            'status',
            'is_paid_campaign',
            'created_by',
            'primary_creative_id',
            'primary_creative_name',
            'primary_audience_id',
            'primary_audience_name',
            'creatives',
            'audiences',
            'spend',
            'attributed_revenue',
            'leads_count',
            'conversions_count',
            'touchpoints_count',
            'roi',
            'roas',
            'has_currency_mismatch',
            'missing_cost_alert',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def _metrics(self, obj: Campaign) -> dict:
        metrics_map = self.context.get('metrics_map') or {}
        return metrics_map.get(obj.id, {})

    def _primary_creative_link(self, obj: Campaign):
        links = list(obj.campaign_creatives.all())
        for link in links:
            if link.is_primary:
                return link
        return links[0] if links else None

    def _primary_audience_link(self, obj: Campaign):
        links = list(obj.campaign_audiences.all())
        for link in links:
            if link.is_primary:
                return link
        return links[0] if links else None

    def get_creatives(self, obj: Campaign) -> list[dict]:
        return [
            {
                'id': link.creative_id,
                'name': link.creative.name,
                'creative_type': link.creative.creative_type,
                'status': link.creative.status,
                'is_primary': link.is_primary,
            }
            for link in obj.campaign_creatives.all()
        ]

    def get_audiences(self, obj: Campaign) -> list[dict]:
        return [
            {
                'id': link.audience_id,
                'name': link.audience.name,
                'audience_type': link.audience.audience_type,
                'estimated_size': link.audience.estimated_size,
                'status': link.audience.status,
                'is_primary': link.is_primary,
            }
            for link in obj.campaign_audiences.all()
        ]

    def get_primary_creative_id(self, obj: Campaign) -> str | None:
        link = self._primary_creative_link(obj)
        return link.creative_id if link else None

    def get_primary_creative_name(self, obj: Campaign) -> str | None:
        link = self._primary_creative_link(obj)
        return link.creative.name if link else None

    def get_primary_audience_id(self, obj: Campaign) -> str | None:
        link = self._primary_audience_link(obj)
        return link.audience_id if link else None

    def get_primary_audience_name(self, obj: Campaign) -> str | None:
        link = self._primary_audience_link(obj)
        return link.audience.name if link else None

    def get_spend(self, obj: Campaign) -> Decimal:
        return self._metrics(obj).get('spend', Decimal('0.00'))

    def get_attributed_revenue(self, obj: Campaign) -> Decimal:
        return self._metrics(obj).get('attributed_revenue', Decimal('0.00'))

    def get_leads_count(self, obj: Campaign) -> int:
        return self._metrics(obj).get('leads_count', 0)

    def get_conversions_count(self, obj: Campaign) -> int:
        return self._metrics(obj).get('conversions_count', 0)

    def get_touchpoints_count(self, obj: Campaign) -> int:
        return self._metrics(obj).get('touchpoints_count', 0)

    def get_roi(self, obj: Campaign) -> float | None:
        return self._metrics(obj).get('roi')

    def get_roas(self, obj: Campaign) -> float | None:
        return self._metrics(obj).get('roas')

    def get_has_currency_mismatch(self, obj: Campaign) -> bool:
        return self._metrics(obj).get('has_currency_mismatch', False)

    def get_missing_cost_alert(self, obj: Campaign) -> bool:
        return self._metrics(obj).get('missing_cost_alert', False)


class CampaignWriteSerializer(serializers.ModelSerializer):
    """Write serializer validating Campaign constraints and M2M Creative/Audience assignments."""

    channel = serializers.PrimaryKeyRelatedField(queryset=Channel.objects.all())
    creative_ids = serializers.ListField(
        child=serializers.CharField(max_length=32),
        required=False,
    )
    primary_creative_id = serializers.CharField(
        max_length=32,
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    audience_ids = serializers.ListField(
        child=serializers.CharField(max_length=32),
        required=False,
    )
    primary_audience_id = serializers.CharField(
        max_length=32,
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    status_reason = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Campaign
        fields = [
            'name',
            'description',
            'channel',
            'budget',
            'currency',
            'start_date',
            'end_date',
            'objective',
            'status',
            'is_paid_campaign',
            'creative_ids',
            'primary_creative_id',
            'audience_ids',
            'primary_audience_id',
            'status_reason',
        ]

    def validate_budget(self, value: Decimal) -> Decimal:
        if value < Decimal('0.00'):
            raise serializers.ValidationError('Budget must be greater than or equal to 0.')
        return value

    def _validate_existing_ids(self, model_cls, ids: list[str], label: str) -> list[str]:
        unique_ids = list(dict.fromkeys(ids))
        if unique_ids:
            found = set(
                model_cls.objects.filter(id__in=unique_ids).values_list('id', flat=True)
            )
            missing = [item for item in unique_ids if item not in found]
            if missing:
                raise serializers.ValidationError(f'Unknown {label} IDs: {", ".join(missing)}')
        return unique_ids

    def validate_creative_ids(self, value: list[str]) -> list[str]:
        return self._validate_existing_ids(Creative, value, 'creative')

    def validate_primary_creative_id(self, value: str | None) -> str | None:
        if not value:
            return None
        self._validate_existing_ids(Creative, [value], 'creative')
        return value

    def validate_audience_ids(self, value: list[str]) -> list[str]:
        return self._validate_existing_ids(Audience, value, 'audience')

    def validate_primary_audience_id(self, value: str | None) -> str | None:
        if not value:
            return None
        self._validate_existing_ids(Audience, [value], 'audience')
        return value

    def validate(self, attrs):
        start_date = attrs.get(
            'start_date',
            self.instance.start_date if self.instance else None,
        )
        end_date = attrs.get(
            'end_date',
            self.instance.end_date if self.instance else None,
        )
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                {'end_date': ['End date must be on or after start date.']}
            )
        return attrs


class CampaignArchiveSerializer(serializers.Serializer):
    """Optional payload when archiving a Campaign."""

    reason = serializers.CharField(required=False, allow_blank=True, default='')

