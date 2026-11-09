from rest_framework import serializers

from events.models import Event
from events.serializers import EventOwnerSerializer
from organizations.models import Organization

from .models import REASON_CODES, AuditLog, DecisionAction, ModerationDecision, Report


class ReportCreateSerializer(serializers.ModelSerializer):
    event = serializers.SlugRelatedField(
        slug_field="slug", queryset=Event.objects.all(), required=False
    )
    organization = serializers.SlugRelatedField(
        slug_field="slug", queryset=Organization.objects.all(), required=False
    )

    class Meta:
        model = Report
        fields = [
            "id",
            "event",
            "organization",
            "category",
            "description",
            "reporter_email",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]

    def validate(self, attrs):
        if not attrs.get("event") and not attrs.get("organization"):
            raise serializers.ValidationError("Indiquez un événement ou une organisation.")
        return attrs


class ReportSerializer(serializers.ModelSerializer):
    event = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    organization = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    reporter = serializers.StringRelatedField()
    handled_by = serializers.StringRelatedField()

    class Meta:
        model = Report
        fields = "__all__"


class DecisionSerializer(serializers.ModelSerializer):
    moderator = serializers.StringRelatedField()
    reason_label = serializers.SerializerMethodField()

    class Meta:
        model = ModerationDecision
        fields = [
            "id",
            "action",
            "reason_code",
            "reason_label",
            "comment",
            "moderator",
            "created_at",
        ]

    def get_reason_label(self, d) -> str:
        return dict(REASON_CODES).get(d.reason_code, "")


class ModerationQueueItemSerializer(EventOwnerSerializer):
    """Élément de la file « À valider » (SCR-10) : confiance, alerte lien, doublons, historique."""

    trust_level = serializers.CharField(read_only=True)
    decisions = DecisionSerializer(many=True, read_only=True)
    duplicates = serializers.SerializerMethodField()
    open_reports = serializers.SerializerMethodField()
    owner_email = serializers.EmailField(source="owner_user.email", read_only=True)

    class Meta(EventOwnerSerializer.Meta):
        fields = EventOwnerSerializer.Meta.fields + [
            "trust_level",
            "decisions",
            "duplicates",
            "open_reports",
            "owner_email",
        ]

    def get_duplicates(self, event) -> list[dict]:
        from .services import find_duplicates

        return [
            {"slug": e.slug, "title": e.title, "similarity": round(e.similarity, 2)}
            for e in find_duplicates(event)
        ]

    def get_open_reports(self, event) -> int:
        return event.reports.filter(status="OPEN").count()


class ModerationActionSerializer(serializers.Serializer):
    event = serializers.UUIDField()
    action = serializers.ChoiceField(choices=[a for a in DecisionAction.values if a != "SUSPEND"])
    reason_code = serializers.ChoiceField(choices=REASON_CODES, required=False, allow_blank=True)
    comment = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs["action"] in ("REJECT", "REQUEST_CHANGES", "UNPUBLISH") and not attrs.get(
            "reason_code"
        ):
            raise serializers.ValidationError(
                {"reason_code": "Un motif est obligatoire pour cette décision."}
            )
        return attrs


class ReportDecisionSerializer(serializers.Serializer):
    founded = serializers.BooleanField()
    note = serializers.CharField(required=False, allow_blank=True)


class ClaimDecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    note = serializers.CharField(required=False, allow_blank=True)


class AuditLogSerializer(serializers.ModelSerializer):
    actor = serializers.StringRelatedField()

    class Meta:
        model = AuditLog
        fields = "__all__"
