"""Serializers for WebSession CRUD and verified Contact identity resolution."""

from rest_framework import serializers

from apps.contacts.models import Contact
from apps.web_sessions.models import WebSession


class WebSessionSerializer(serializers.ModelSerializer):
    """Read/write serializer enforcing deterministic identity-linking evidence rules."""

    contact_name = serializers.SerializerMethodField()
    campaign_name = serializers.SerializerMethodField()
    touchpoints_count = serializers.SerializerMethodField()

    class Meta:
        model = WebSession
        fields = [
            'id',
            'anonymous_id',
            'contact',
            'contact_name',
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
            'touchpoints_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_contact_name(self, obj: WebSession) -> str | None:
        return obj.contact.name if obj.contact else None

    def get_campaign_name(self, obj: WebSession) -> str | None:
        return obj.campaign.name if obj.campaign else None

    def get_touchpoints_count(self, obj: WebSession) -> int:
        annotated = getattr(obj, 'touchpoints_count', None)
        if isinstance(annotated, int):
            return annotated
        return obj.touchpoints.count()

    def validate_anonymous_id(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError('anonymous_id cannot be blank.')
        return cleaned

    def validate_landing_page(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError('landing_page cannot be blank.')
        return cleaned

    def validate(self, attrs):
        contact = attrs.get(
            'contact',
            self.instance.contact if self.instance else None,
        )
        has_evidence = attrs.get(
            'has_evidence',
            self.instance.has_evidence if self.instance else False,
        )
        evidence_type = attrs.get(
            'evidence_type',
            self.instance.evidence_type if self.instance else '',
        ).strip()
        linking_issue = attrs.get(
            'linking_issue',
            self.instance.linking_issue if self.instance else '',
        ).strip()

        explicit_status = 'identity_status' in attrs
        identity_status = attrs.get(
            'identity_status',
            self.instance.identity_status if self.instance else None,
        )

        if contact is None:
            if explicit_status and identity_status in (
                WebSession.IdentityStatus.IDENTIFIED,
                WebSession.IdentityStatus.UNVERIFIED_LINK,
            ):
                raise serializers.ValidationError(
                    {
                        'contact': [
                            f'Sessions with identity_status "{identity_status}" require a contact.'
                        ]
                    }
                )
            attrs['identity_status'] = WebSession.IdentityStatus.ANONYMOUS
            attrs['has_evidence'] = False
            attrs['evidence_type'] = ''
            attrs['linking_issue'] = ''
            return attrs

        # Contact is present
        if not explicit_status and self.instance is None:
            identity_status = (
                WebSession.IdentityStatus.IDENTIFIED
                if has_evidence
                else None
            )

        if identity_status == WebSession.IdentityStatus.ANONYMOUS:
            raise serializers.ValidationError(
                {
                    'identity_status': [
                        'Anonymous sessions cannot remain linked to a contact. '
                        'Either set identity_status="Identified" with valid evidence or clear contact.'
                    ]
                }
            )

        if identity_status == WebSession.IdentityStatus.IDENTIFIED or (
            identity_status is None and has_evidence
        ):
            if not has_evidence or not evidence_type:
                raise serializers.ValidationError(
                    {
                        'evidence_type': [
                            'Linking a session as Identified requires has_evidence=True '
                            'and a non-empty evidence_type (e.g., Form Submission, Login Token).'
                        ]
                    }
                )
            attrs['identity_status'] = WebSession.IdentityStatus.IDENTIFIED
            attrs['evidence_type'] = evidence_type
            attrs['linking_issue'] = ''
            return attrs

        if identity_status == WebSession.IdentityStatus.UNVERIFIED_LINK:
            if has_evidence:
                raise serializers.ValidationError(
                    {
                        'has_evidence': [
                            'Sessions marked Unverified Link must have has_evidence=False.'
                        ]
                    }
                )
            if not linking_issue:
                attrs['linking_issue'] = (
                    f'Linked to {contact.id} without deterministic email, login, '
                    'or form-submit verification evidence.'
                )
            return attrs

        raise serializers.ValidationError(
            {
                'has_evidence': [
                    'Linking a session to a contact requires valid linking evidence '
                    '(has_evidence=True and evidence_type) unless explicitly ingested as '
                    'identity_status="Unverified Link".'
                ]
            }
        )


class WebSessionLinkContactSerializer(serializers.Serializer):
    """Payload validating explicit verified Contact identity resolution on a WebSession."""

    contact_id = serializers.PrimaryKeyRelatedField(queryset=Contact.objects.all())
    has_evidence = serializers.BooleanField(required=False, default=True)
    evidence_type = serializers.CharField(max_length=80)
    notes = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_has_evidence(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError(
                'Anonymous sessions can only be linked to a contact when valid linking evidence exists.'
            )
        return value

    def validate_evidence_type(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError(
                'evidence_type is required (e.g., Form Submission, Login Token, Email Click ID).'
            )
        return cleaned

