from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from drf_spectacular.utils import extend_schema_field, inline_serializer
from rest_framework import serializers

from catalog.models import Category, Tag, Venue
from catalog.serializers import VenueSerializer
from core.urlsafety import validate_https_url
from organizations.models import Organization

from .models import (
    AgePolicy,
    Event,
    EventFormat,
    EventMedia,
    EventOccurrence,
    EventStatus,
    OccurrenceStatus,
    PricingType,
    Visibility,
)


class CategoryMiniSerializer(serializers.ModelSerializer):
    name = serializers.DictField(source="names", child=serializers.CharField(), read_only=True)

    class Meta:
        model = Category
        fields = ["slug", "name", "icon"]


class TagMiniSerializer(serializers.ModelSerializer):
    name = serializers.DictField(source="names", child=serializers.CharField(), read_only=True)

    class Meta:
        model = Tag
        fields = ["slug", "name"]


class OccurrenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventOccurrence
        fields = ["id", "starts_at", "ends_at", "timezone", "status", "capacity", "note"]
        read_only_fields = ["id"]

    def validate_timezone(self, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise serializers.ValidationError("Fuseau horaire IANA inconnu.")
        return value

    def validate(self, attrs):
        tz = ZoneInfo(attrs.get("timezone") or settings.WIGO_DEFAULT_TIMEZONE)
        for key in ("starts_at", "ends_at"):
            if attrs.get(key) is not None and timezone.is_naive(attrs[key]):
                attrs[key] = attrs[key].replace(tzinfo=tz)
        if (
            attrs.get("ends_at")
            and attrs.get("starts_at")
            and attrs["ends_at"] <= attrs["starts_at"]
        ):
            raise serializers.ValidationError(
                {"ends_at": "La fin doit être postérieure au début (RG-06)."}
            )
        return attrs


class MediaSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = EventMedia
        fields = [
            "id",
            "url",
            "kind",
            "order",
            "credits",
            "alt_text",
            "rights_confirmed",
            "width",
            "height",
        ]
        read_only_fields = ["id", "url", "width", "height"]

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_url(self, media) -> str | None:
        if not media.image:
            return None
        request = self.context.get("request")
        url = media.image.url
        return request.build_absolute_uri(url) if request and url.startswith("/") else url


class MediaUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventMedia
        fields = ["image", "kind", "order", "credits", "alt_text", "rights_confirmed"]

    def validate_image(self, image):
        if image.size > settings.WIGO_MAX_UPLOAD_BYTES:
            raise serializers.ValidationError("Image trop lourde (8 Mo maximum).")
        if image.content_type not in settings.WIGO_ALLOWED_IMAGE_TYPES:
            raise serializers.ValidationError("Format accepté : JPEG, PNG ou WebP.")
        return image

    def validate_rights_confirmed(self, value):
        if not value:
            raise serializers.ValidationError(
                "Vous devez confirmer détenir les droits sur ce visuel."
            )
        return value


class OrganizerSerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.CharField(allow_null=True)
    verified = serializers.BooleanField()
    trust_level = serializers.CharField()


def organizer_payload(event: Event) -> dict:
    if event.organization_id:
        org = event.organization
        return {
            "name": org.name,
            "slug": org.slug,
            "verified": org.is_verified,
            "trust_level": org.trust_level,
        }
    return {
        "name": event.owner_user.public_name,
        "slug": None,
        "verified": False,
        "trust_level": event.owner_user.trust_level,
    }


class PricingSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=PricingType.choices)
    min = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True)
    max = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True)
    currency = serializers.CharField()
    details = serializers.CharField(allow_blank=True)


class LatLonSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lon = serializers.FloatField()


class VenueMiniSerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.CharField()
    city = serializers.CharField()
    area = serializers.CharField(allow_null=True)
    location = LatLonSerializer(allow_null=True)


class TicketingSerializer(serializers.Serializer):
    url = serializers.URLField()
    external = serializers.BooleanField()
    note = serializers.CharField()


class EventUrlsSerializer(serializers.Serializer):
    canonical = serializers.URLField()
    ics = serializers.CharField()
    fr = serializers.URLField()
    nl = serializers.URLField()
    en = serializers.URLField()


class EventCardSerializer(serializers.ModelSerializer):
    """Carte événement (UI-03) : liste, carte, favoris, sélection."""

    languages = serializers.ListField(child=serializers.CharField(), read_only=True)
    visibility = serializers.ChoiceField(choices=Visibility.choices, read_only=True)

    primary_category = CategoryMiniSerializer(read_only=True)
    organizer = serializers.SerializerMethodField()
    venue = serializers.SerializerMethodField()
    poster = serializers.SerializerMethodField()
    pricing = serializers.SerializerMethodField()
    next_start = serializers.DateTimeField(read_only=True, allow_null=True)
    first_start = serializers.DateTimeField(read_only=True, allow_null=True)
    last_end = serializers.DateTimeField(read_only=True, allow_null=True)
    is_long = serializers.BooleanField(read_only=True, default=False)
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id",
            "slug",
            "title",
            "status",
            "format",
            "primary_category",
            "organizer",
            "venue",
            "poster",
            "pricing",
            "age_policy",
            "min_age",
            "is_family_friendly",
            "visibility",
            "languages",
            "next_start",
            "first_start",
            "last_end",
            "is_long",
            "distance_km",
        ]

    @extend_schema_field(OrganizerSerializer)
    def get_organizer(self, event) -> dict:
        return organizer_payload(event)

    @extend_schema_field(VenueMiniSerializer(allow_null=True))
    def get_venue(self, event) -> dict | None:
        v = event.venue
        if v is None:
            return None
        return {
            "name": v.name,
            "slug": v.slug,
            "city": v.city,
            "area": v.area.slug if v.area_id else None,
            "location": {"lat": v.location.y, "lon": v.location.x} if v.location else None,
        }

    @extend_schema_field(MediaSerializer(allow_null=True))
    def get_poster(self, event) -> dict | None:
        media = next((m for m in event.media.all() if m.kind == "POSTER"), None) or next(
            iter(event.media.all()), None
        )
        if media is None or not media.image:
            return None
        return MediaSerializer(media, context=self.context).data

    @extend_schema_field(PricingSerializer)
    def get_pricing(self, event) -> dict:
        return {
            "type": event.pricing_type,
            "min": event.price_min,
            "max": event.price_max,
            "currency": event.currency,
            "details": event.price_details,
        }

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_distance_km(self, event) -> float | None:
        d = getattr(event, "distance", None)
        return round(d.km, 2) if d is not None else None


class EventDetailSerializer(EventCardSerializer):
    """Fiche événement (SCR-04, §5.2)."""

    secondary_categories = CategoryMiniSerializer(many=True, read_only=True)
    tags = TagMiniSerializer(many=True, read_only=True)
    venue = VenueSerializer(read_only=True)
    occurrences = OccurrenceSerializer(many=True, read_only=True)
    media = MediaSerializer(many=True, read_only=True)
    ticketing = serializers.SerializerMethodField()
    accessibility = serializers.SerializerMethodField()
    urls = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()

    description = serializers.CharField(read_only=True)

    class Meta(EventCardSerializer.Meta):
        fields = EventCardSerializer.Meta.fields + [
            "description",
            "secondary_categories",
            "tags",
            "occurrences",
            "media",
            "online_url",
            "ticketing",
            "registration_required",
            "accessibility",
            "urls",
            "is_favorite",
            "published_at",
            "cancelled_at",
            "updated_at",
        ]

    @extend_schema_field(TicketingSerializer(allow_null=True))
    def get_ticketing(self, event) -> dict | None:
        if not event.ticketing_url:
            return None
        # RG-17 : clic distinct d'une vente, achat chez l'organisateur
        return {"url": event.ticketing_url, "external": True, "note": "Achat chez l'organisateur"}

    @extend_schema_field(
        inline_serializer(
            "EventAccessibility",
            fields={
                "wheelchair": serializers.BooleanField(allow_null=True, required=False),
                "adapted_toilets": serializers.BooleanField(allow_null=True, required=False),
                "hearing_loop": serializers.BooleanField(allow_null=True, required=False),
                "sign_language": serializers.BooleanField(allow_null=True, required=False),
                "sensory_friendly": serializers.BooleanField(allow_null=True, required=False),
                "notes": serializers.CharField(required=False, allow_blank=True),
                "event_notes": serializers.CharField(required=False, allow_blank=True),
            },
        )
    )
    def get_accessibility(self, event) -> dict:
        base = (
            dict(event.venue.accessibility) if event.venue_id and event.venue.accessibility else {}
        )
        base["event_notes"] = event.accessibility_notes
        return base

    @extend_schema_field(EventUrlsSerializer)
    def get_urls(self, event) -> dict:
        web = settings.PUBLIC_WEB_URL
        return {
            "canonical": f"{web}/fr/evenements/{event.slug}",
            "ics": f"/api/v1/events/{event.slug}/ics",
            "fr": f"{web}/fr/evenements/{event.slug}",
            "nl": f"{web}/nl/evenementen/{event.slug}",
            "en": f"{web}/en/events/{event.slug}",
        }

    def get_is_favorite(self, event) -> bool:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return event.favorites.filter(user=request.user).exists()


class EventWriteSerializer(serializers.ModelSerializer):
    """Création et édition par l'organisateur (EVT-02). Séances imbriquées, remplacées en bloc."""

    primary_category = serializers.SlugRelatedField(
        slug_field="slug", queryset=Category.objects.filter(is_active=True)
    )
    secondary_categories = serializers.SlugRelatedField(
        slug_field="slug",
        many=True,
        required=False,
        queryset=Category.objects.filter(is_active=True),
    )
    tags = serializers.SlugRelatedField(
        slug_field="slug", many=True, required=False, queryset=Tag.objects.filter(is_active=True)
    )
    venue = serializers.PrimaryKeyRelatedField(
        queryset=Venue.objects.filter(is_active=True), required=False, allow_null=True
    )
    organization = serializers.SlugRelatedField(
        slug_field="slug", queryset=Organization.objects.all(), required=False, allow_null=True
    )
    occurrences = OccurrenceSerializer(many=True, required=False)

    class Meta:
        model = Event
        fields = [
            "title",
            "description",
            "languages",
            "primary_category",
            "secondary_categories",
            "tags",
            "format",
            "venue",
            "online_url",
            "pricing_type",
            "price_min",
            "price_max",
            "currency",
            "price_details",
            "ticketing_url",
            "registration_required",
            "age_policy",
            "min_age",
            "is_family_friendly",
            "accessibility_notes",
            "organization",
            "occurrences",
            "draft_step",
        ]

    def validate_title(self, value):
        value = value.strip()
        if len(value) > 160:
            raise serializers.ValidationError("160 caractères maximum.")
        return value

    def validate_secondary_categories(self, value):
        if len(value) > 2:
            raise serializers.ValidationError("Deux catégories secondaires maximum (RG-25).")
        return value

    def validate_ticketing_url(self, value):
        if value:
            try:
                validate_https_url(value)
            except DjangoValidationError as exc:
                raise serializers.ValidationError(exc.messages[0])
        return value

    def validate_online_url(self, value):
        if value:
            try:
                validate_https_url(value)
            except DjangoValidationError as exc:
                raise serializers.ValidationError(exc.messages[0])
        return value

    def validate_organization(self, org):
        if org is None:
            return org
        user = self.context["request"].user
        if not org.can_edit(user) and not user.is_catalog_editor and not user.is_moderator:
            raise serializers.ValidationError("Vous n'êtes pas membre de cette organisation.")
        return org

    def validate(self, attrs):
        inst = self.instance
        get = lambda k, d=None: attrs.get(k, getattr(inst, k, d) if inst else d)  # noqa: E731
        if get("pricing_type") == PricingType.FREE:
            attrs["price_min"] = attrs["price_max"] = None
        pmin, pmax = get("price_min"), get("price_max")
        if pmin is not None and pmax is not None and pmax < pmin:
            raise serializers.ValidationError(
                {"price_max": "Le prix maximum doit être ≥ au minimum."}
            )
        if get("age_policy") == AgePolicy.MIN_AGE and not get("min_age"):
            raise serializers.ValidationError({"min_age": "Indiquez l'âge minimum."})
        if get("age_policy") != AgePolicy.MIN_AGE:
            attrs["min_age"] = None
        if get("format") == EventFormat.ONLINE:
            attrs["venue"] = None
        primary = get("primary_category")
        if primary and primary in attrs.get("secondary_categories", []):
            raise serializers.ValidationError(
                {"secondary_categories": "Déjà la catégorie principale."}
            )
        return attrs

    @staticmethod
    def _unique_slug(title: str) -> str:
        base = slugify(title)[:150] or "evenement"
        slug, i = base, 2
        while Event.objects.filter(slug=slug).exists():
            slug, i = f"{base}-{i}", i + 1
        return slug

    @transaction.atomic
    def create(self, validated):
        occurrences = validated.pop("occurrences", [])
        secondary = validated.pop("secondary_categories", [])
        tags = validated.pop("tags", [])
        validated["owner_user"] = self.context["request"].user
        validated["slug"] = self._unique_slug(validated["title"])
        event = Event.objects.create(**validated)
        event.secondary_categories.set(secondary)
        event.tags.set(tags)
        for occ in occurrences:
            EventOccurrence.objects.create(event=event, **occ)
        return event

    @transaction.atomic
    def update(self, event, validated):
        occurrences = validated.pop("occurrences", None)
        secondary = validated.pop("secondary_categories", None)
        tags = validated.pop("tags", None)
        for k, v in validated.items():
            setattr(event, k, v)
        event.save()
        if secondary is not None:
            event.secondary_categories.set(secondary)
        if tags is not None:
            event.tags.set(tags)
        if occurrences is not None:
            # RG-13 : séances indépendantes ; on conserve les séances annulées pour l'historique
            event.occurrences.exclude(status=OccurrenceStatus.CANCELLED).delete()
            for occ in occurrences:
                EventOccurrence.objects.create(event=event, **occ)
        return event


class EventOwnerSerializer(EventDetailSerializer):
    """Vue organisateur : inclut les champs de gestion."""

    organization = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    submission_errors = serializers.SerializerMethodField()

    class Meta(EventDetailSerializer.Meta):
        fields = EventDetailSerializer.Meta.fields + [
            "organization",
            "draft_step",
            "source",
            "link_review_required",
            "submitted_at",
            "last_confirmed_at",
            "submission_errors",
            "created_at",
        ]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_submission_errors(self, event) -> list[str]:
        from .workflow import validate_ready_for_submission

        if event.status in (EventStatus.DRAFT, EventStatus.CHANGES_REQUESTED, EventStatus.REJECTED):
            return validate_ready_for_submission(event)
        return []


class StatsSerializer(serializers.Serializer):
    views = serializers.IntegerField()
    ticket_clicks = serializers.IntegerField()
    favorites = serializers.IntegerField()
    calendar_adds = serializers.IntegerField()
    shares = serializers.IntegerField()
    per_day = serializers.ListField(child=serializers.DictField())


class FavoriteWriteSerializer(serializers.Serializer):
    event = serializers.SlugRelatedField(slug_field="slug", queryset=Event.objects.published())


class FavoriteMergeSerializer(serializers.Serializer):
    """UI-05 : fusion des favoris locaux à la connexion."""

    events = serializers.ListField(child=serializers.SlugField(), max_length=500)


class DecisionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)
