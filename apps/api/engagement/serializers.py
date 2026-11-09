from rest_framework import serializers

from catalog.models import Area
from events.models import Event
from events.serializers import EventCardSerializer

from .models import (
    ImportRun,
    ImportSource,
    NewsletterSubscription,
    WeekendSelection,
    WeekendSelectionItem,
)


class NewsletterSubscribeSerializer(serializers.ModelSerializer):
    area = serializers.SlugRelatedField(
        slug_field="slug", queryset=Area.objects.all(), required=False, allow_null=True
    )
    consent = serializers.BooleanField(write_only=True)

    class Meta:
        model = NewsletterSubscription
        fields = ["email", "area", "language", "consent"]

    def validate_consent(self, value):
        if not value:
            raise serializers.ValidationError("Le consentement est requis.")
        return value


class SelectionItemSerializer(serializers.ModelSerializer):
    event = EventCardSerializer(read_only=True)

    class Meta:
        model = WeekendSelectionItem
        fields = ["event", "order", "blurb"]


class SelectionSerializer(serializers.ModelSerializer):
    items = SelectionItemSerializer(many=True, read_only=True)
    editor = serializers.StringRelatedField()

    class Meta:
        model = WeekendSelection
        fields = [
            "id",
            "week_start",
            "title",
            "intro",
            "send_status",
            "sent_at",
            "recipients_count",
            "editor",
            "items",
        ]


class SelectionWriteSerializer(serializers.Serializer):
    week_start = serializers.DateField(required=False)
    title = serializers.CharField(required=False, allow_blank=True, max_length=160)
    intro = serializers.CharField(required=False, allow_blank=True)
    events = serializers.ListField(child=serializers.DictField(), required=False)
    send_status = serializers.ChoiceField(choices=["DRAFT", "READY"], required=False)

    def validate_events(self, items):
        slugs = [i.get("event") for i in items]
        found = {e.slug: e for e in Event.objects.filter(slug__in=slugs, status="PUBLISHED")}
        missing = [s for s in slugs if s not in found]
        if missing:
            raise serializers.ValidationError(
                f"Événements inconnus ou non publiés : {', '.join(missing)}"
            )
        return [
            {"event": found[i["event"]], "order": i.get("order", n), "blurb": i.get("blurb", "")}
            for n, i in enumerate(items)
        ]


class ImportRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportRun
        fields = [
            "id",
            "started_at",
            "finished_at",
            "status",
            "created_count",
            "updated_count",
            "skipped_count",
            "log",
        ]


class ImportSourceSerializer(serializers.ModelSerializer):
    last_run = serializers.SerializerMethodField()

    class Meta:
        model = ImportSource
        fields = [
            "id",
            "name",
            "slug",
            "kind",
            "url",
            "licence",
            "attribution",
            "is_active",
            "sync_interval_hours",
            "last_run_at",
            "last_run",
        ]

    def get_last_run(self, src) -> dict | None:
        run = src.runs.first()
        return ImportRunSerializer(run).data if run else None


class ImportTriggerSerializer(serializers.Serializer):
    source = serializers.SlugField()
