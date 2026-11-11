"""Serializers for Closed Order CRUD and verification state transitions."""

from decimal import Decimal

from rest_framework import serializers

from apps.contacts.models import Contact
from apps.orders.models import Order
from apps.orders.services import ensure_single_valid_order_per_opportunity


class OrderSerializer(serializers.ModelSerializer):
    """Read/write serializer enforcing opportunity-contact integrity and duplicate-revenue guards."""

    contact = serializers.PrimaryKeyRelatedField(
        queryset=Contact.objects.all(),
        required=False,
    )
    opportunity_name = serializers.SerializerMethodField()
    contact_name = serializers.SerializerMethodField()
    is_attributable = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id',
            'opportunity',
            'opportunity_name',
            'contact',
            'contact_name',
            'order_date',
            'revenue',
            'currency',
            'payment_status',
            'verification_status',
            'is_attributable',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_opportunity_name(self, obj: Order) -> str | None:
        return obj.opportunity.name if obj.opportunity else None

    def get_contact_name(self, obj: Order) -> str | None:
        return obj.contact.name if obj.contact else None

    def get_is_attributable(self, obj: Order) -> bool:
        return (
            obj.verification_status == Order.VerificationStatus.VALID
            and obj.payment_status == Order.PaymentStatus.PAID
        )

    def validate_revenue(self, value: Decimal) -> Decimal:
        if value < Decimal('0.00'):
            raise serializers.ValidationError('Order revenue cannot be negative.')
        return value

    def validate(self, attrs):
        opportunity = attrs.get(
            'opportunity',
            self.instance.opportunity if self.instance else None,
        )
        contact = attrs.get(
            'contact',
            self.instance.contact if self.instance else None,
        )
        if opportunity is not None:
            if contact is None:
                attrs['contact'] = opportunity.contact
            elif opportunity.contact_id != contact.id:
                raise serializers.ValidationError(
                    {
                        'contact': [
                            f'Contact {contact.id} does not match opportunity '
                            f'contact {opportunity.contact_id}.'
                        ]
                    }
                )
        elif contact is None:
            raise serializers.ValidationError({'contact': ['Contact is required.']})

        verification_status = attrs.get(
            'verification_status',
            self.instance.verification_status if self.instance else Order.VerificationStatus.VALID,
        )
        if opportunity is not None:
            ensure_single_valid_order_per_opportunity(
                opportunity_id=opportunity.id,
                verification_status=verification_status,
                exclude_order_id=self.instance.id if self.instance else None,
            )

        return attrs


class OrderVerificationSerializer(serializers.Serializer):
    """Payload for updating Order verification_status with audit notes."""

    verification_status = serializers.ChoiceField(choices=Order.VerificationStatus.choices)
    notes = serializers.CharField(required=False, allow_blank=True, default='')

