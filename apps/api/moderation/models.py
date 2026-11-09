from django.conf import settings
from django.db import models

from core.models import TimeStampedModel, UUIDModel


class ReportCategory(models.TextChoices):
    SPAM = "SPAM", "Spam ou publicité déguisée"
    ILLEGAL = "ILLEGAL", "Contenu illégal"
    HATE = "HATE", "Discrimination ou haine"
    WRONG_INFO = "WRONG_INFO", "Informations fausses ou périmées"
    DUPLICATE = "DUPLICATE", "Doublon"
    RIGHTS = "RIGHTS", "Droits d'auteur / image"
    SUSPICIOUS_LINK = "SUSPICIOUS_LINK", "Lien suspect"
    OTHER = "OTHER", "Autre"


class ReportStatus(models.TextChoices):
    OPEN = "OPEN", "Ouvert"
    FOUNDED = "FOUNDED", "Fondé"
    DISMISSED = "DISMISSED", "Classé sans suite"


class Report(UUIDModel):
    """Signalement (ADM-04, RG-16) : traçable, anti-abus par limitation de débit."""

    event = models.ForeignKey(
        "events.Event", null=True, blank=True, on_delete=models.CASCADE, related_name="reports"
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="reports",
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reports",
    )
    reporter_email = models.EmailField(blank=True)
    category = models.CharField(max_length=16, choices=ReportCategory.choices)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=10, choices=ReportStatus.choices, default=ReportStatus.OPEN
    )
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    handled_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(event__isnull=False) | models.Q(organization__isnull=False),
                name="report_has_target",
            )
        ]

    @property
    def target(self):
        return self.event or self.organization


# Motifs de décision (ADM-02, DSA : exposé des motifs)
REASON_CODES = [
    ("INCOMPLETE", "Informations incomplètes ou incompréhensibles"),
    ("NOT_PUBLIC", "Événement non public / non ouvert sur inscription"),
    ("WRONG_DATE_PLACE", "Date ou lieu invalide"),
    ("COMMERCIAL", "Publicité commerciale déguisée"),
    ("ILLEGAL", "Promotion d'activités illégales"),
    ("HATE", "Contenu discriminatoire ou haineux"),
    ("DUPLICATE", "Doublon d'un événement existant"),
    ("SUSPICIOUS_LINK", "Lien de billetterie suspect ou hors liste blanche"),
    ("RIGHTS", "Droits sur les visuels non garantis"),
    ("ADULT_VISUAL", "Visuel inadapté (18+)"),
    ("OTHER", "Autre (voir commentaire)"),
]


class DecisionAction(models.TextChoices):
    APPROVE = "APPROVE", "Approuvé"
    REJECT = "REJECT", "Refusé"
    REQUEST_CHANGES = "REQUEST_CHANGES", "Corrections demandées"
    UNPUBLISH = "UNPUBLISH", "Dépublié"
    SUSPEND = "SUSPEND", "Organisateur suspendu"


class ModerationDecision(TimeStampedModel):
    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="decisions")
    moderator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="decisions",
    )
    action = models.CharField(max_length=16, choices=DecisionAction.choices)
    reason_code = models.CharField(max_length=20, blank=True, choices=REASON_CODES)
    comment = models.TextField(blank=True, help_text="Exposé des motifs transmis à l'organisateur")

    class Meta:
        ordering = ["-created_at"]


class AuditLog(models.Model):
    """ADM-05 : acteur, action, cible, avant/après limité, date. Conservation 3 ans (A.4)."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_entries",
    )
    action = models.CharField(max_length=60, db_index=True)
    target_type = models.CharField(max_length=60, blank=True)
    target_id = models.CharField(max_length=64, blank=True, db_index=True)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action} {self.target_type}#{self.target_id}"
