"""Serializers for Creative CRUD and CampaignCreative linkage."""

from rest_framework import serializers

from apps.campaigns.models import Campaign
from apps.creatives.models import Creative


class CreativeSerializer(serializers.ModelSerializer):
    """Read/write serializer for marketing creatives with date validation and M2M campaign IDs."""

    primary_campaign_name = serializers.SerializerMethodField()
    campaign_ids = serializers.ListField(
        child=serializers.CharField(max_length=32),
        required=False,
    )

    class Meta:
        model = Creative
        fields = [
            'id',
            'name',
            'primary_campaign',
            'primary_campaign_name',
            'creative_type',
            'description',
            'start_date',
            'end_date',
            'status',
            'campaign_ids',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_primary_campaign_name(self, obj: Creative) -> str | None:
        return obj.primary_campaign.name if obj.primary_campaign else None

    def to_representation(self, instance: Creative) -> dict:
        rep = super().to_representation(instance)
        rep['campaign_ids'] = [
            link.campaign_id for link in instance.creative_campaigns.all()
        ]
        return rep

    def validate_campaign_ids(self, value: list[str]) -> list[str]:
        unique_ids = list(dict.fromkeys(value))
        if unique_ids:
            found = set(
                Campaign.objects.filter(id__in=unique_ids).values_list('id', flat=True)
            )
            missing = [cid for cid in unique_ids if cid not in found]
            if missing:
                raise serializers.ValidationError(
                    f'Unknown campaign IDs: {", ".join(missing)}'
                )
        return unique_ids

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

