"""Serializers for Channel CRUD and ROI metrics representation."""

from decimal import Decimal

from rest_framework import serializers

from apps.channels.models import Channel


class ChannelSerializer(serializers.ModelSerializer):
    """Read/write serializer returning normalized channel fields and optional live ROI metrics."""

    total_campaigns = serializers.SerializerMethodField()
    total_spend = serializers.SerializerMethodField()
    attributed_revenue = serializers.SerializerMethodField()
    total_leads = serializers.SerializerMethodField()
    conversions_count = serializers.SerializerMethodField()
    roi = serializers.SerializerMethodField()
    roas = serializers.SerializerMethodField()
    has_currency_mismatch = serializers.SerializerMethodField()

    class Meta:
        model = Channel
        fields = [
            'id',
            'name',
            'channel_type',
            'status',
            'owner',
            'description',
            'total_campaigns',
            'total_spend',
            'attributed_revenue',
            'total_leads',
            'conversions_count',
            'roi',
            'roas',
            'has_currency_mismatch',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        qs = Channel.objects.filter(name__iexact=cleaned)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A marketing channel with this name already exists.')
        return cleaned

    def _metrics(self, obj: Channel) -> dict:
        metrics_map = self.context.get('metrics_map') or {}
        return metrics_map.get(obj.id, {})

    def get_total_campaigns(self, obj: Channel) -> int:
        return self._metrics(obj).get('total_campaigns', 0)

    def get_total_spend(self, obj: Channel) -> Decimal:
        return self._metrics(obj).get('total_spend', Decimal('0.00'))

    def get_attributed_revenue(self, obj: Channel) -> Decimal:
        return self._metrics(obj).get('attributed_revenue', Decimal('0.00'))

    def get_total_leads(self, obj: Channel) -> int:
        return self._metrics(obj).get('total_leads', 0)

    def get_conversions_count(self, obj: Channel) -> int:
        return self._metrics(obj).get('conversions_count', 0)

    def get_roi(self, obj: Channel) -> float | None:
        return self._metrics(obj).get('roi')

    def get_roas(self, obj: Channel) -> float | None:
        return self._metrics(obj).get('roas')

    def get_has_currency_mismatch(self, obj: Channel) -> bool:
        return self._metrics(obj).get('has_currency_mismatch', False)

