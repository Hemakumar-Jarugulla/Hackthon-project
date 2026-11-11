"""Serializers for Touchpoint CRUD, channel resolution, offline checks, and session evidence."""

from rest_framework import serializers

from apps.touchpoints.models import Touchpoint
from apps.web_sessions.models import WebSession


class TouchpointSerializer(serializers.ModelSerializer):
    """Read/write serializer validating Touchpoint online/offline and session-evidence rules."""

    contact_name = serializers.SerializerMethodField()
    campaign_name = serializers.SerializerMethodField()
    channel_name = serializers.SerializerMethodField()
    creative_name = serializers.SerializerMethodField()
    session_anonymous_id = serializers.SerializerMethodField()

    class Meta:
        model = Touchpoint
        fields = [
            'id',
            'contact',
            'contact_name',
            'campaign',
            'campaign_name',
            'channel',
            'channel_name',
            'creative',
            'creative_name',
            'session',
            'session_anonymous_id',
            'interaction_type',
            'timestamp',
            'device',
            'is_online',
            'source',
            'is_post_conversion',
            'is_valid',
            'validation_notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_contact_name(self, obj: Touchpoint) -> str | None:
        return obj.contact.name if obj.contact else None

    def get_campaign_name(self, obj: Touchpoint) -> str | None:
        return obj.campaign.name if obj.campaign else None

    def get_channel_name(self, obj: Touchpoint) -> str | None:
        return obj.channel.name if obj.channel else None

    def get_creative_name(self, obj: Touchpoint) -> str | None:
        return obj.creative.name if obj.creative else None

    def get_session_anonymous_id(self, obj: Touchpoint) -> str | None:
        return obj.session.anonymous_id if obj.session else None

    def validate_interaction_type(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError('interaction_type cannot be blank.')
        return cleaned

    def validate(self, attrs):
        contact = attrs.get(
            'contact',
            self.instance.contact if self.instance else None,
        )
        campaign = attrs.get(
            'campaign',
            self.instance.campaign if self.instance else None,
        )
        channel = attrs.get(
            'channel',
            self.instance.channel if self.instance else None,
        )
        session = attrs.get(
            'session',
            self.instance.session if self.instance else None,
        )
        is_online = attrs.get(
            'is_online',
            self.instance.is_online if self.instance else True,
        )

        # Auto-derive Offline device when creating an offline touchpoint without an explicit device
        if not is_online and 'device' not in attrs and self.instance is None:
            attrs['device'] = Touchpoint.DeviceType.OFFLINE

        device = attrs.get(
            'device',
            self.instance.device if self.instance else Touchpoint.DeviceType.DESKTOP,
        )

        if is_online and device == Touchpoint.DeviceType.OFFLINE:
            raise serializers.ValidationError(
                {'device': ['Online touchpoints cannot use the Offline device type.']}
            )
        if not is_online and device != Touchpoint.DeviceType.OFFLINE:
            raise serializers.ValidationError(
                {'device': ['Offline touchpoints must use the Offline device type.']}
            )

        # Resolve and verify channel against campaign when campaign is present
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

        # Enforce session linking evidence rules when a WebSession is attached
        if session is not None and contact is not None:
            if session.contact_id != contact.id:
                raise serializers.ValidationError(
                    {
                        'session': [
                            'Attached WebSession must be linked to the same Contact '
                            '(anonymous or cross-contact sessions cannot be attributed).'
                        ]
                    }
                )
            if (
                not session.has_evidence
                or session.identity_status != WebSession.IdentityStatus.IDENTIFIED
            ):
                raise serializers.ValidationError(
                    {
                        'session': [
                            'Cannot attach a touchpoint to a WebSession lacking verified '
                            'identity-linking evidence.'
                        ]
                    }
                )

        return attrs

