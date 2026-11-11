"""Serializers for Attribution Models, Runs, Results, Execution Payloads, and 5-Model Comparisons."""

from rest_framework import serializers

from apps.attribution.models import AttributionModel, AttributionResult, AttributionRun


class AttributionModelSerializer(serializers.ModelSerializer):
    """Read/write serializer for the 5 attribution methodology definitions."""

    class Meta:
        model = AttributionModel
        fields = [
            'id',
            'name',
            'short_label',
            'description',
            'rule_version',
            'config',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AttributionRunSerializer(serializers.ModelSerializer):
    """Summary serializer for persisted AttributionRun audit snapshots."""

    model_name = serializers.CharField(source='attribution_model.name', read_only=True)
    executed_by_username = serializers.SerializerMethodField()
    result_rows_count = serializers.SerializerMethodField()

    class Meta:
        model = AttributionRun
        fields = [
            'id',
            'attribution_model',
            'model_name',
            'rule_version',
            'period_label',
            'conversion_window_days',
            'half_life_days',
            'valid_orders_processed',
            'excluded_duplicate_orders',
            'excluded_post_conversion_touches',
            'total_attributed_revenue',
            'status',
            'executed_by',
            'executed_by_username',
            'executed_at',
            'result_rows_count',
        ]
        read_only_fields = fields

    def get_executed_by_username(self, obj: AttributionRun) -> str | None:
        return obj.executed_by.username if obj.executed_by else None

    def get_result_rows_count(self, obj: AttributionRun) -> int:
        annotated = getattr(obj, 'result_rows_count', None)
        if isinstance(annotated, int):
            return annotated
        return obj.results.count()


class AttributionResultSerializer(serializers.ModelSerializer):
    """Traceable per-touchpoint attribution result ledger row."""

    model_name = serializers.CharField(source='attribution_model.name', read_only=True)
    campaign_name = serializers.SerializerMethodField()
    channel_name = serializers.SerializerMethodField()
    contact_name = serializers.CharField(source='contact.name', read_only=True)
    interaction_type = serializers.CharField(source='touchpoint.interaction_type', read_only=True)
    touchpoint_timestamp = serializers.DateTimeField(source='touchpoint.timestamp', read_only=True)
    is_online = serializers.BooleanField(source='touchpoint.is_online', read_only=True)
    order_date = serializers.DateField(source='order.order_date', read_only=True)
    weight_percent = serializers.SerializerMethodField()

    class Meta:
        model = AttributionResult
        fields = [
            'id',
            'run',
            'attribution_model',
            'model_name',
            'order',
            'order_date',
            'touchpoint',
            'interaction_type',
            'touchpoint_timestamp',
            'is_online',
            'campaign',
            'campaign_name',
            'channel',
            'channel_name',
            'contact',
            'contact_name',
            'rule_version',
            'credit_weight',
            'weight_percent',
            'attributed_revenue',
            'source_order_revenue',
            'currency',
            'calculated_at',
        ]
        read_only_fields = fields

    def get_campaign_name(self, obj: AttributionResult) -> str | None:
        return obj.campaign.name if obj.campaign else None

    def get_channel_name(self, obj: AttributionResult) -> str | None:
        return obj.channel.name if obj.channel else None

    def get_weight_percent(self, obj: AttributionResult) -> float:
        return round(float(obj.credit_weight) * 100.0, 2)


class AttributionCampaignResultSerializer(serializers.Serializer):
    """Aggregated attributed revenue & conversions per Campaign."""

    campaign_id = serializers.CharField(allow_null=True)
    campaign_name = serializers.CharField()
    channel_id = serializers.CharField(allow_null=True)
    channel_name = serializers.CharField()
    attributed_revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    conversions = serializers.IntegerField()
    touch_credit_count = serializers.FloatField()
    share_percent = serializers.FloatField()


class AttributionChannelResultSerializer(serializers.Serializer):
    """Aggregated attributed revenue & conversions per Channel."""

    channel_id = serializers.CharField(allow_null=True)
    channel_name = serializers.CharField()
    channel_type = serializers.CharField()
    attributed_revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    conversions = serializers.IntegerField()
    share_percent = serializers.FloatField()


class AttributionOrderCreditSerializer(serializers.Serializer):
    """Individual touchpoint-to-order credit split row inside a run calculation."""

    order_id = serializers.CharField()
    contact_id = serializers.CharField()
    order_date = serializers.DateField()
    order_revenue = serializers.DecimalField(max_digits=14, decimal_places=2)
    currency = serializers.CharField()
    touchpoint_id = serializers.CharField()
    campaign_id = serializers.CharField(allow_null=True)
    campaign_name = serializers.CharField()
    channel_id = serializers.CharField(allow_null=True)
    channel_name = serializers.CharField()
    timestamp = serializers.DateTimeField()
    is_online = serializers.BooleanField()
    credit_weight = serializers.DecimalField(max_digits=7, decimal_places=6)
    weight_percent = serializers.FloatField()
    attributed_revenue = serializers.DecimalField(max_digits=14, decimal_places=2)


class AttributionExecuteRequestSerializer(serializers.Serializer):
    """Validated parameters for triggering an attribution calculation run."""

    model_id = serializers.ChoiceField(
        choices=AttributionModel.ModelCode.choices,
        required=False,
        default=AttributionModel.ModelCode.POSITION_BASED,
    )
    conversion_window_days = serializers.IntegerField(
        required=False,
        default=90,
        min_value=1,
        max_value=365,
    )
    half_life_days = serializers.IntegerField(
        required=False,
        default=7,
        min_value=1,
        max_value=90,
    )
    period_label = serializers.CharField(max_length=60, required=False, allow_blank=True, default='')
    date_range = serializers.CharField(max_length=30, required=False, allow_blank=True, default='all_time')
    date_from = serializers.DateField(required=False, allow_null=True)
    date_to = serializers.DateField(required=False, allow_null=True)
    persist = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        date_from = attrs.get('date_from')
        date_to = attrs.get('date_to')
        if date_from and date_to and date_to < date_from:
            raise serializers.ValidationError({'date_to': ['date_to must be on or after date_from.']})
        return attrs


class AttributionExecuteResponseSerializer(serializers.Serializer):
    """Response structure for an executed or previewed attribution run."""

    run_id = serializers.CharField(allow_null=True)
    persisted = serializers.BooleanField()
    executed_at = serializers.DateTimeField()
    period_label = serializers.CharField()
    model_id = serializers.CharField()
    model_name = serializers.CharField()
    rule_version = serializers.CharField()
    conversion_window_days = serializers.IntegerField()
    half_life_days = serializers.IntegerField()
    valid_orders_processed = serializers.IntegerField()
    orders_without_eligible_touches = serializers.IntegerField()
    excluded_duplicate_orders = serializers.IntegerField()
    excluded_other_orders = serializers.IntegerField()
    excluded_post_conversion_touches = serializers.IntegerField()
    excluded_outside_window_touches = serializers.IntegerField()
    excluded_unverified_session_touches = serializers.IntegerField()
    excluded_invalid_touches = serializers.IntegerField()
    total_closed_valid_revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    total_attributed_revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    unattributed_valid_revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    campaign_results = AttributionCampaignResultSerializer(many=True)
    channel_results = AttributionChannelResultSerializer(many=True)
    order_credits = AttributionOrderCreditSerializer(many=True)


class AttributionRunDetailSerializer(serializers.Serializer):
    """Detailed persisted AttributionRun view including reconstructed rollups and results."""

    run = AttributionRunSerializer()
    result_count = serializers.IntegerField()
    campaign_breakdown = AttributionCampaignResultSerializer(many=True)
    channel_breakdown = AttributionChannelResultSerializer(many=True)
    results = AttributionResultSerializer(many=True)


class ComparisonCampaignRowSerializer(serializers.Serializer):
    """Side-by-side 5-model attributed revenue matrix row per Campaign."""

    campaign_id = serializers.CharField(allow_null=True)
    campaign_name = serializers.CharField()
    channel_name = serializers.CharField()
    first_touch = serializers.DecimalField(max_digits=16, decimal_places=2)
    last_touch = serializers.DecimalField(max_digits=16, decimal_places=2)
    linear = serializers.DecimalField(max_digits=16, decimal_places=2)
    time_decay = serializers.DecimalField(max_digits=16, decimal_places=2)
    position_based = serializers.DecimalField(max_digits=16, decimal_places=2)


class ComparisonChannelRowSerializer(serializers.Serializer):
    """Side-by-side 5-model attributed revenue matrix row per Channel."""

    channel_id = serializers.CharField(allow_null=True)
    channel_name = serializers.CharField()
    channel_type = serializers.CharField()
    first_touch = serializers.DecimalField(max_digits=16, decimal_places=2)
    last_touch = serializers.DecimalField(max_digits=16, decimal_places=2)
    linear = serializers.DecimalField(max_digits=16, decimal_places=2)
    time_decay = serializers.DecimalField(max_digits=16, decimal_places=2)
    position_based = serializers.DecimalField(max_digits=16, decimal_places=2)


class AttributionComparisonResponseSerializer(serializers.Serializer):
    """Complete 5-model attribution comparison matrix formatted for Recharts & tables."""

    period_label = serializers.CharField()
    conversion_window_days = serializers.IntegerField()
    half_life_days = serializers.IntegerField()
    valid_orders_count = serializers.IntegerField()
    excluded_duplicate_orders = serializers.IntegerField()
    campaign_comparison = ComparisonCampaignRowSerializer(many=True)
    channel_comparison = ComparisonChannelRowSerializer(many=True)

