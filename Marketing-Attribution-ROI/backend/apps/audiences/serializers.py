"""Serializers for Audience CRUD and CampaignAudience linkage."""

from rest_framework import serializers

from apps.audiences.models import Audience
from apps.campaigns.models import Campaign


class AudienceSerializer(serializers.ModelSerializer):
    """Read/write serializer for target marketing audiences."""

    campaign_ids = serializers.ListField(
        child=serializers.CharField(max_length=32),
        required=False,
    )

    class Meta:
        model = Audience
        fields = [
            'id',
            'name',
            'audience_type',
            'estimated_size',
            'criteria',
            'status',
            'effective_from',
            'effective_to',
            'campaign_ids',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def to_representation(self, instance: Audience) -> dict:
        rep = super().to_representation(instance)
        rep['campaign_ids'] = [
            link.campaign_id for link in instance.audience_campaigns.all()
        ]
        return rep

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        qs = Audience.objects.filter(name__iexact=cleaned)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('An audience segment with this name already exists.')
        return cleaned

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
        effective_from = attrs.get(
            'effective_from',
            self.instance.effective_from if self.instance else None,
        )
        effective_to = attrs.get(
            'effective_to',
            self.instance.effective_to if self.instance else None,
        )
        if effective_from and effective_to and effective_to < effective_from:
            raise serializers.ValidationError(
                {'effective_to': ['Effective end date must be on or after effective start date.']}
            )
        return attrs

