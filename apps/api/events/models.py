from datetime import timedelta

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.db.models import F, Max, Min, OuterRef, Q, Subquery
from django.utils import timezone

from core.enums import Language, TrustLevel
from core.models import TimeStampedModel, UUIDModel


class EventStatus(models.TextChoices):
    DRAFT = "DRAFT", "Brouillon"
    PENDING_REVIEW = "PENDING_REVIEW", "En attente de modération"
    CHANGES_REQUESTED = "CHANGES_REQUESTED", "Corrections demandées"
    REJECTED = "REJECTED", "Refusé"
    PUBLISHED = "PUBLISHED", "Publié"
    CANCELLED = "CANCELLED", "Annulé"
    ARCHIVED = "ARCHIVED", "Archivé"


class OccurrenceStatus(models.TextChoices):
    SCHEDULED = "SCHEDULED", "Prévue"
    CANCELLED = "CANCELLED", "Annulée"
    POSTPONED = "POSTPONED", "Reportée"
    SOLD_OUT = "SOLD_OUT", "Complet"


class EventFormat(models.TextChoices):
    ONSITE = "ONSITE", "Présentiel"
    ONLINE = "ONLINE", "En ligne"
    HYBRID = "HYBRID", "Hybride"


class PricingType(models.TextChoices):
    FREE = "FREE", "Gratuit"
    PAID = "PAID", "Payant"
    PAY_WHAT_YOU_WANT = "PWYW", "Participation libre"


class AgePolicy(models.TextChoices):
    ALL = "ALL", "Tout public"
    MIN_AGE = "MIN_AGE", "Dès N ans"
    ADULTS_ONLY = "ADULTS_ONLY", "18+"


class Visibility(models.TextChoices):
    STANDARD = "STANDARD", "Standard"
    FEATURED = "FEATURED", "Sélection WIGO"
    PARTNER = "PARTNER", "Partenaire"


class EventSource(models.TextChoices):
    MANUAL = "MANUAL", "Saisie organisateur"
    IMPORT = "IMPORT", "Import partenaire"
    INTERNAL = "INTERNAL", "Saisie catalogue WIGO"


class EventQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=EventStatus.PUBLISHED)

    def with_schedule(self, now=None):
        """Annotations : première/dernière séance, prochaine séance non terminée, durée totale."""
        now = now or timezone.now()
        active = Q(occurrences__status__in=[OccurrenceStatus.SCHEDULED, OccurrenceStatus.SOLD_OUT])
        next_occ = (
            EventOccurrence.objects.filter(
                event=OuterRef("pk"),
                ends_at__gte=now,
                status__in=[OccurrenceStatus.SCHEDULED, OccurrenceStatus.SOLD_OUT],
            )
            .order_by("starts_at")
            .values("starts_at")[:1]
        )
        return self.annotate(
            first_start=Min("occurrences__starts_at", filter=active),
            last_end=Max("occurrences__ends_at", filter=active),
            next_start=Subquery(next_occ),
        ).annotate(
            is_long=Q(
                last_end__gt=F("first_start")
                + timedelta(days=settings.WIGO_RULES["LONG_EVENT_DAYS"])
            ),
        )

    def public(self, now=None):
        """RG-05 / RG-07 : publié et dont la dernière séance n'est pas terminée."""
        now = now or timezone.now()
        return self.published().with_schedule(now).filter(last_end__gte=now)


class Event(UUIDModel):
    """Événement (§9.1). Les séances sont dans EventOccurrence (RG-13)."""

    slug = models.SlugField(max_length=200, unique=True)
    owner_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="events"
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="events",
    )
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    languages = ArrayField(
        models.CharField(max_length=2, choices=Language.choices), default=list, blank=True
    )
    primary_category = models.ForeignKey(
        "catalog.Category", on_delete=models.PROTECT, related_name="primary_events"
    )
    secondary_categories = models.ManyToManyField(
        "catalog.Category", blank=True, related_name="secondary_events"
    )
    tags = models.ManyToManyField("catalog.Tag", blank=True, related_name="events")

    format = models.CharField(max_length=6, choices=EventFormat.choices, default=EventFormat.ONSITE)
    venue = models.ForeignKey(
        "catalog.Venue", null=True, blank=True, on_delete=models.PROTECT, related_name="events"
    )
    online_url = models.URLField(blank=True)

    pricing_type = models.CharField(
        max_length=4, choices=PricingType.choices, default=PricingType.FREE
    )
    price_min = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    price_max = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="EUR")
    price_details = models.CharField(max_length=200, blank=True)
    ticketing_url = models.URLField(blank=True)
    registration_required = models.BooleanField(default=False)
    link_review_required = models.BooleanField(
        default=False, help_text="Lien billetterie hors liste blanche à revoir (RG-21)"
    )

    age_policy = models.CharField(max_length=11, choices=AgePolicy.choices, default=AgePolicy.ALL)
    min_age = models.PositiveSmallIntegerField(null=True, blank=True)
    is_family_friendly = models.BooleanField(default=False)
    accessibility_notes = models.CharField(max_length=300, blank=True)

    visibility = models.CharField(
        max_length=8, choices=Visibility.choices, default=Visibility.STANDARD
    )
    status = models.CharField(max_length=17, choices=EventStatus.choices, default=EventStatus.DRAFT)
    source = models.CharField(max_length=8, choices=EventSource.choices, default=EventSource.MANUAL)
    external_id = models.CharField(max_length=120, blank=True)
    import_source = models.ForeignKey(
        "engagement.ImportSource",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="events",
    )

    draft_step = models.PositiveSmallIntegerField(
        default=1, help_text="Dernière étape du formulaire"
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    last_confirmed_at = models.DateTimeField(null=True, blank=True)
    freshness_reminder_sent_at = models.DateTimeField(null=True, blank=True)

    search_vector = SearchVectorField(null=True, editable=False)

    objects = EventQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "événement"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["primary_category", "status"]),
            GinIndex(fields=["search_vector"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(price_max__isnull=True)
                | Q(price_min__isnull=True)
                | Q(price_max__gte=F("price_min")),
                name="event_price_range_valid",
            ),
        ]

    def __str__(self):
        return self.title

    @property
    def trust_level(self) -> str:
        if self.organization_id:
            return self.organization.trust_level
        return self.owner_user.trust_level

    @property
    def is_online_only(self) -> bool:
        return self.format == EventFormat.ONLINE

    @property
    def is_public(self) -> bool:
        return self.status == EventStatus.PUBLISHED

    def can_view(self, user) -> bool:
        return self.is_public or self.can_edit(user)

    def can_edit(self, user) -> bool:
        if not user or not user.is_authenticated:
            return False
        if user.is_moderator or user.is_superuser:
            return True
        if self.owner_user_id == user.id:
            return True
        return bool(self.organization_id and self.organization.can_edit(user))

    def is_verified_organizer(self) -> bool:
        return bool(self.organization_id and self.organization.is_verified)

    @property
    def organizer_name(self) -> str:
        return self.organization.name if self.organization_id else self.owner_user.public_name


class EventOccurrence(TimeStampedModel):
    """Séance (RG-13). Dates en UTC, fuseau IANA conservé (RG-19)."""

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="occurrences")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    timezone = models.CharField(max_length=40, default="Europe/Brussels")
    status = models.CharField(
        max_length=9, choices=OccurrenceStatus.choices, default=OccurrenceStatus.SCHEDULED
    )
    capacity = models.PositiveIntegerField(null=True, blank=True)
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["starts_at"]
        indexes = [models.Index(fields=["starts_at", "ends_at"])]
        constraints = [
            # RG-06 : fin strictement postérieure au début
            models.CheckConstraint(
                condition=Q(ends_at__gt=F("starts_at")), name="occurrence_ends_after_start"
            ),
        ]

    def __str__(self):
        return f"{self.event.title} — {self.starts_at:%Y-%m-%d %H:%M}"


class MediaKind(models.TextChoices):
    POSTER = "POSTER", "Affiche"
    GALLERY = "GALLERY", "Galerie"


class EventMedia(TimeStampedModel):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="media")
    image = models.ImageField(upload_to="events/%Y/%m/")
    kind = models.CharField(max_length=7, choices=MediaKind.choices, default=MediaKind.POSTER)
    order = models.PositiveSmallIntegerField(default=0)
    credits = models.CharField(max_length=200, blank=True)
    rights_confirmed = models.BooleanField(default=False)
    alt_text = models.CharField(max_length=200, blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "média"


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites"
    )
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="favorites")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "event")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_id} ♥ {self.event_id}"


class EventDailyStat(models.Model):
    """Compteurs journaliers pour les statistiques organisateur (§5.4)."""

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="daily_stats")
    date = models.DateField()
    views = models.PositiveIntegerField(default=0)
    ticket_clicks = models.PositiveIntegerField(default=0)
    favorites_added = models.PositiveIntegerField(default=0)
    calendar_adds = models.PositiveIntegerField(default=0)
    shares = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("event", "date")]

    def __str__(self):
        return f"{self.event_id} {self.date}"

    @classmethod
    def bump(cls, event, field: str, by: int = 1):
        today = timezone.now().date()
        row, _ = cls.objects.get_or_create(event=event, date=today)
        cls.objects.filter(pk=row.pk).update(**{field: F(field) + by})


# Pour mémoire : niveaux de confiance des organisateurs (§5.4)
TRUST_IMMEDIATE_PUBLISH = {TrustLevel.CONFIRMED, TrustLevel.VERIFIED}
