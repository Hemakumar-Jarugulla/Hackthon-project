"""Serializers for Marketing Cost Records and aggregated spend summaries."""

from decimal import Decimal

from rest_framework import serializers

from apps.costs.models import CostRecord


class CostRecordSerializer(serializers.ModelSerializer):
    """Read/write serializer flagging campaign FX mismatches and resolving channels."""

    campaign_name = serializers.SerializerMethodField()
    campaign_currency = serializers.SerializerMethodField()
    channel_name = serializers.SerializerMethodField()
    currency_mismatch = serializers.SerializerMethodField()

    class Meta:
        model = CostRecord
        fields = [
            'id',
            'campaign',
            'campaign_name',
            'campaign_currency',
            'channel',
            'channel_name',
            'category',
            'amount',
            'currency',
            'currency_mismatch',
            'spend_date',
            'description',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_campaign_name(self, obj: CostRecord) -> str | None:
        return obj.campaign.name if obj.campaign else None

    def get_campaign_currency(self, obj: CostRecord) -> str | None:
        return obj.campaign.currency if obj.campaign else None

    def get_channel_name(self, obj: CostRecord) -> str | None:
        return obj.channel.name if obj.channel else None

    def get_currency_mismatch(self, obj: CostRecord) -> bool:
        return bool(obj.campaign and obj.currency != obj.campaign.currency)

    def validate_amount(self, value: Decimal) -> Decimal:
        if value < Decimal('0.00'):
            raise serializers.ValidationError('Cost amount must be greater than or equal to 0.')
        return value

    def validate(self, attrs):
        campaign = attrs.get(
            'campaign',
            self.instance.campaign if self.instance else None,
        )
        channel = attrs.get(
            'channel',
            self.instance.channel if self.instance else None,
        )
        if campaign is not None:
            if channel is None:
                attrs['channel'] = campaign.channel
            elif channel.id != campaign.channel_id:
                raise serializers.ValidationError(
                    {
                        'channel': [
                            f'Channel {channel.id} does not match campaign '
                            f'channel {campaign.channel_id}.'
                        ]
                    }
                )
        return attrs


class CostSpendByCurrencySerializer(serializers.Serializer):
    """Schema item representing currency-separated cost ledger totals."""

    currency = serializers.CharField()
    total_spend = serializers.DecimalField(max_digits=16, decimal_places=2)
    matched_spend = serializers.DecimalField(max_digits=16, decimal_places=2)
    mismatched_spend = serializers.DecimalField(max_digits=16, decimal_places=2)
    record_count = serializers.IntegerField()


class CostSpendByCategorySerializer(serializers.Serializer):
    """Schema item representing matched-currency spend grouped by cost category."""

    category = serializers.CharField()
    matched_spend = serializers.DecimalField(max_digits=16, decimal_places=2)
    record_count = serializers.IntegerField()


class CostSummarySerializer(serializers.Serializer):
    """Summary envelope returned by GET /api/v1/costs/summary/."""

    total_records = serializers.IntegerField()
    matched_currency_records = serializers.IntegerField()
    mismatched_currency_records = serializers.IntegerField()
    spend_by_currency = CostSpendByCurrencySerializer(many=True)
    matched_spend_by_category = CostSpendByCategorySerializer(many=True)

