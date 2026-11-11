"""Serializers for Sales Opportunity CRUD, stage-status alignment, and pipeline history."""

from decimal import Decimal

from rest_framework import serializers

from apps.contacts.models import Contact
from apps.opportunities.models import Opportunity, OpportunityStageHistory


class OpportunityStageHistorySerializer(serializers.ModelSerializer):
    """Read serializer for historical Opportunity stage transitions."""

    class Meta:
        model = OpportunityStageHistory
        fields = [
            'id',
            'previous_stage',
            'new_stage',
            'changed_at',
        ]
        read_only_fields = fields


class OpportunitySerializer(serializers.ModelSerializer):
    """Read/write serializer validating relational lead-contact integrity and stage-status sync."""

    contact = serializers.PrimaryKeyRelatedField(
        queryset=Contact.objects.all(),
        required=False,
    )
    lead_campaign_id = serializers.SerializerMethodField()
    contact_name = serializers.SerializerMethodField()
    orders_count = serializers.SerializerMethodField()

    class Meta:
        model = Opportunity
        fields = [
            'id',
            'lead',
            'lead_campaign_id',
            'contact',
            'contact_name',
            'name',
            'stage',
            'expected_revenue',
            'actual_revenue',
            'closing_date',
            'status',
            'orders_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_lead_campaign_id(self, obj: Opportunity) -> str | None:
        return obj.lead.campaign_id if obj.lead else None

    def get_contact_name(self, obj: Opportunity) -> str | None:
        return obj.contact.name if obj.contact else None

    def get_orders_count(self, obj: Opportunity) -> int:
        annotated = getattr(obj, 'orders_count', None)
        if isinstance(annotated, int):
            return annotated
        return obj.orders.count()

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError('Opportunity name cannot be blank.')
        return cleaned

    def validate_expected_revenue(self, value: Decimal) -> Decimal:
        if value < Decimal('0.00'):
            raise serializers.ValidationError('Expected revenue cannot be negative.')
        return value

    def validate_actual_revenue(self, value: Decimal) -> Decimal:
        if value < Decimal('0.00'):
            raise serializers.ValidationError('Actual revenue cannot be negative.')
        return value

    def validate(self, attrs):
        lead = attrs.get('lead', self.instance.lead if self.instance else None)
        contact = attrs.get('contact', self.instance.contact if self.instance else None)

        if lead is not None:
            if contact is None:
                attrs['contact'] = lead.contact
            elif lead.contact_id != contact.id:
                raise serializers.ValidationError(
                    {
                        'contact': [
                            f'Contact {contact.id} does not match lead contact {lead.contact_id}.'
                        ]
                    }
                )
        elif contact is None:
            raise serializers.ValidationError({'contact': ['Contact is required.']})

        stage = attrs.get('stage', self.instance.stage if self.instance else Opportunity.Stage.NEW)
        explicit_status = 'status' in attrs
        status_val = attrs.get(
            'status',
            self.instance.status if self.instance else None,
        )

        expected_status_by_stage = {
            Opportunity.Stage.CLOSED_WON: Opportunity.Status.WON,
            Opportunity.Stage.CLOSED_LOST: Opportunity.Status.LOST,
        }
        required_status = expected_status_by_stage.get(stage, Opportunity.Status.OPEN)

        if not explicit_status:
            attrs['status'] = required_status
        elif status_val != required_status:
            raise serializers.ValidationError(
                {
                    'status': [
                        f'Stage "{stage}" requires status "{required_status}" '
                        f'(received "{status_val}").'
                    ]
                }
            )

        return attrs

