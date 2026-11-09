import secrets
from datetime import date, timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.enums import Language
from core.models import TimeStampedModel, UUIDModel


class SubscriptionStatus(models.TextChoices):
    PENDING = "PENDING", "En attente de confirmation"
    CONFIRMED = "CONFIRMED", "Confirmée"
    UNSUBSCRIBED = "UNSUBSCRIBED", "Désinscrite"


def _token() -> str:
    return secrets.token_urlsafe(32)


class NewsletterSubscription(UUIDModel):
    """RET-02 : double opt-in, désinscription en un clic, consentement horodaté (§8.2)."""

    email = models.EmailField(unique=True)
    area = models.ForeignKey("catalog.Area", null=True, blank=True, on_delete=models.SET_NULL)
    language = models.CharField(max_length=2, choices=Language.choices, default=Language.FR)
    status = models.CharField(
        max_length=12, choices=SubscriptionStatus.choices, default=SubscriptionStatus.PENDING
    )
    consent_at = models.DateTimeField(default=timezone.now)
    consent_source = models.CharField(max_length=60, default="web")
    confirmed_at = models.DateTimeField(null=True, blank=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    confirm_token = models.CharField(max_length=64, default=_token, unique=True)
    unsubscribe_token = models.CharField(max_length=64, default=_token, unique=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "abonnement newsletter"

    def __str__(self):
        return f"{self.email} ({self.status})"

    def confirm(self):
        self.status = SubscriptionStatus.CONFIRMED
        self.confirmed_at = timezone.now()
        self.save(update_fields=["status", "confirmed_at", "updated_at"])

    def unsubscribe(self):
        self.status = SubscriptionStatus.UNSUBSCRIBED
        self.unsubscribed_at = timezone.now()
        self.save(update_fields=["status", "unsubscribed_at", "updated_at"])


class SendStatus(models.TextChoices):
    DRAFT = "DRAFT", "Brouillon"
    READY = "READY", "Prête à l'envoi"
    SENT = "SENT", "Envoyée"


class WeekendSelection(TimeStampedModel):
    """ADM-09 / §5.8 : sélection cochée par l'équipe, source de la newsletter du jeudi."""

    week_start = models.DateField(unique=True, help_text="Lundi de la semaine concernée")
    title = models.CharField(max_length=160, blank=True)
    intro = models.TextField(blank=True)
    events = models.ManyToManyField(
        "events.Event", through="WeekendSelectionItem", related_name="selections"
    )
    editor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    send_status = models.CharField(
        max_length=6, choices=SendStatus.choices, default=SendStatus.DRAFT
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    recipients_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-week_start"]

    def __str__(self):
        return f"Sélection semaine du {self.week_start:%d/%m/%Y}"

    @staticmethod
    def week_start_for(day: date) -> date:
        return day - timedelta(days=day.weekday())

    @classmethod
    def current(cls):
        return cls.objects.filter(week_start=cls.week_start_for(timezone.localdate())).first()


class WeekendSelectionItem(models.Model):
    selection = models.ForeignKey(WeekendSelection, on_delete=models.CASCADE, related_name="items")
    event = models.ForeignKey("events.Event", on_delete=models.CASCADE)
    order = models.PositiveSmallIntegerField(default=0)
    blurb = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["order"]
        unique_together = [("selection", "event")]

    def __str__(self):
        return f"{self.selection_id} — {self.event_id}"


class ImportSource(TimeStampedModel):
    """§5.6 Partenariats de données : licence, attribution, fréquence ; pas de scraping sauvage."""

    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    kind = models.CharField(max_length=40, help_text="uitdatabank, agenda_brussels, ics, csv…")
    url = models.URLField(blank=True)
    licence = models.CharField(max_length=120, blank=True)
    attribution = models.CharField(max_length=200, blank=True)
    config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    sync_interval_hours = models.PositiveSmallIntegerField(default=24)
    last_run_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name


class ImportRunStatus(models.TextChoices):
    RUNNING = "RUNNING", "En cours"
    SUCCESS = "SUCCESS", "Terminé"
    FAILED = "FAILED", "Échec"


class ImportRun(models.Model):
    source = models.ForeignKey(ImportSource, on_delete=models.CASCADE, related_name="runs")
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=8, choices=ImportRunStatus.choices, default=ImportRunStatus.RUNNING
    )
    created_count = models.PositiveIntegerField(default=0)
    updated_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    log = models.TextField(blank=True)
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.source} — {self.started_at:%Y-%m-%d %H:%M} ({self.status})"
