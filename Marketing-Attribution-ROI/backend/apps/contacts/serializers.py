"""Serializers for Contact CRUD, lifecycle history, metrics, and customer journey tracking."""

from decimal import Decimal

from rest_framework import serializers

from apps.contacts.models import Contact, ContactLifecycleHistory
from apps.leads.models import Lead
from apps.opportunities.models import Opportunity
from apps.orders.models import Order
from apps.touchpoints.models import Touchpoint
from apps.web_sessions.models import WebSession


class ContactLifecycleHistorySerializer(serializers.ModelSerializer):
    """Read serializer for historical Contact lifecycle stage transitions."""

    class Meta:
        model = ContactLifecycleHistory
        fields = [
            'id',
            'previous_status',
            'new_status',
            'effective_at',
            'notes',
        ]
        read_only_fields = fields


class ContactSerializer(serializers.ModelSerializer):
    """Read/write serializer for Contacts with O(1) engagement and revenue rollups."""

    created_date = serializers.DateField(required=False)
    status_reason = serializers.CharField(write_only=True, required=False, allow_blank=True)
    touchpoint_count = serializers.SerializerMethodField()
    session_count = serializers.SerializerMethodField()
    lead_count = serializers.SerializerMethodField()
    order_count = serializers.SerializerMethodField()
    total_revenue = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = [
            'id',
            'name',
            'email',
            'phone',
            'company',
            'source',
            'created_date',
            'lifecycle_status',
            'status_reason',
            'touchpoint_count',
            'session_count',
            'lead_count',
            'order_count',
            'total_revenue',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError('Contact name cannot be blank.')
        return cleaned

    def validate_email(self, value: str) -> str:
        cleaned = value.strip().lower()
        qs = Contact.objects.filter(email__iexact=cleaned)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A contact with this email address already exists.')
        return cleaned

    def _metrics(self, obj: Contact) -> dict:
        metrics_map = self.context.get('metrics_map') or {}
        return metrics_map.get(obj.id, {})

    def get_touchpoint_count(self, obj: Contact) -> int:
        return self._metrics(obj).get('touchpoint_count', 0)

    def get_session_count(self, obj: Contact) -> int:
        return self._metrics(obj).get('session_count', 0)

    def get_lead_count(self, obj: Contact) -> int:
        return self._metrics(obj).get('lead_count', 0)

    def get_order_count(self, obj: Contact) -> int:
        return self._metrics(obj).get('order_count', 0)

    def get_total_revenue(self, obj: Contact) -> Decimal:
        return self._metrics(obj).get('total_revenue', Decimal('0.00'))


class JourneyTouchpointSerializer(serializers.ModelSerializer):
    """Compact touchpoint summary embedded inside a Contact journey timeline."""

    campaign_name = serializers.SerializerMethodField()
    channel_name = serializers.SerializerMethodField()
    creative_name = serializers.SerializerMethodField()

    class Meta:
        model = Touchpoint
        fields = [
            'id',
            'campaign',
            'campaign_name',
            'channel',
            'channel_name',
            'creative',
            'creative_name',
            'session',
            'interaction_type',
            'timestamp',
            'device',
            'is_online',
            'source',
            'is_post_conversion',
            'is_valid',
            'validation_notes',
        ]
        read_only_fields = fields

    def get_campaign_name(self, obj: Touchpoint) -> str | None:
        return obj.campaign.name if obj.campaign else None

    def get_channel_name(self, obj: Touchpoint) -> str | None:
        return obj.channel.name if obj.channel else None

    def get_creative_name(self, obj: Touchpoint) -> str | None:
        return obj.creative.name if obj.creative else None


class JourneySessionSerializer(serializers.ModelSerializer):
    """Compact web session summary embedded inside a Contact journey."""

    campaign_name = serializers.SerializerMethodField()

    class Meta:
        model = WebSession
        fields = [
            'id',
            'anonymous_id',
            'campaign',
            'campaign_name',
            'landing_page',
            'referrer',
            'timestamp',
            'device_type',
            'identity_status',
            'has_evidence',
            'evidence_type',
            'linking_issue',
        ]
        read_only_fields = fields

    def get_campaign_name(self, obj: WebSession) -> str | None:
        return obj.campaign.name if obj.campaign else None


class JourneyLeadSerializer(serializers.ModelSerializer):
    """Compact Lead summary embedded inside a Contact journey."""

    campaign_name = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = ['id', 'campaign', 'campaign_name', 'source', 'score', 'created_date', 'status']
        read_only_fields = fields

    def get_campaign_name(self, obj: Lead) -> str | None:
        return obj.campaign.name if obj.campaign else None


class JourneyOpportunitySerializer(serializers.ModelSerializer):
    """Compact Opportunity summary embedded inside a Contact journey."""

    class Meta:
        model = Opportunity
        fields = [
            'id',
            'lead',
            'name',
            'stage',
            'expected_revenue',
            'actual_revenue',
            'closing_date',
            'status',
        ]
        read_only_fields = fields


class JourneyOrderSerializer(serializers.ModelSerializer):
    """Compact Order summary embedded inside a Contact journey."""

    class Meta:
        model = Order
        fields = [
            'id',
            'opportunity',
            'order_date',
            'revenue',
            'currency',
            'payment_status',
            'verification_status',
        ]
        read_only_fields = fields


class JourneyAttributionCreditSerializer(serializers.Serializer):
    """Attribution credit entry attached to a Contact journey."""

    touchpoint_id = serializers.CharField()
    order_id = serializers.CharField()
    campaign_id = serializers.CharField(allow_null=True)
    campaign_name = serializers.CharField(allow_null=True)
    channel_id = serializers.CharField(allow_null=True)
    channel_name = serializers.CharField(allow_null=True)
    timestamp = serializers.DateTimeField()
    weight = serializers.FloatField()
    weight_percent = serializers.FloatField()
    attributed_revenue = serializers.DecimalField(max_digits=14, decimal_places=2)


class JourneyTimelineEventSerializer(serializers.Serializer):
    """Unified chronological timeline entry for UI rendering."""

    id = serializers.CharField()
    timestamp = serializers.DateTimeField()
    stage_type = serializers.CharField()
    title = serializers.CharField()
    subtitle = serializers.CharField()
    meta = serializers.CharField()
    badge = serializers.CharField()
    is_invalid = serializers.BooleanField()


class ContactJourneySerializer(serializers.Serializer):
    """Complete multi-entity customer journey response for Contact Detail UI."""

    contact = ContactSerializer()
    model_id = serializers.CharField()
    attribution_run_id = serializers.CharField(allow_null=True)
    touchpoints = JourneyTouchpointSerializer(many=True)
    sessions = JourneySessionSerializer(many=True)
    leads = JourneyLeadSerializer(many=True)
    opportunities = JourneyOpportunitySerializer(many=True)
    orders = JourneyOrderSerializer(many=True)
    attribution_results = JourneyAttributionCreditSerializer(many=True)
    timeline = JourneyTimelineEventSerializer(many=True)

