from django.contrib.gis.db import models as gis
from django.db import models

from core.models import TimeStampedModel, TranslatedNameMixin


class Category(TranslatedNameMixin, TimeStampedModel):
    """Taxonomie administrable (ADM-06), hiérarchique, traduite FR/NL/EN."""

    slug = models.SlugField(max_length=60, unique=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    icon = models.CharField(max_length=40, blank=True, help_text="Nom d'icône du design system")
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_launch_niche = models.BooleanField(
        default=False, help_text="Niche de lancement (§2.3) : alimentation active"
    )

    class Meta:
        ordering = ["order", "name_fr"]
        verbose_name = "catégorie"
        verbose_name_plural = "catégories"

    def descendant_ids(self) -> list[int]:
        ids = [self.pk]
        for child in self.children.all():
            ids.extend(child.descendant_ids())
        return ids


class Tag(TranslatedNameMixin, TimeStampedModel):
    slug = models.SlugField(max_length=60, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name_fr"]


class AreaKind(models.TextChoices):
    REGION = "REGION", "Région"
    MUNICIPALITY = "MUNICIPALITY", "Commune"
    NEIGHBOURHOOD = "NEIGHBOURHOOD", "Quartier"


class Area(TranslatedNameMixin, TimeStampedModel):
    """Communes et quartiers (§5.1 Filtres, GET /api/v1/areas)."""

    slug = models.SlugField(max_length=80, unique=True)
    kind = models.CharField(max_length=14, choices=AreaKind.choices)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    postal_codes = models.JSONField(default=list, blank=True)
    country = models.CharField(max_length=2, default="BE")
    centroid = gis.PointField(geography=True, null=True, blank=True)
    boundary = gis.MultiPolygonField(geography=True, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["kind", "order", "name_fr"]
        verbose_name = "territoire"
        verbose_name_plural = "territoires"

    def self_and_descendant_ids(self) -> list[int]:
        ids = [self.pk]
        for child in self.children.all():
            ids.extend(child.self_and_descendant_ids())
        return ids


ACCESSIBILITY_KEYS = (
    "wheelchair",  # accès PMR
    "adapted_toilets",  # toilettes adaptées
    "hearing_loop",  # boucle magnétique
    "sign_language",  # interprétation LSFB / VGT
    "sensory_friendly",  # adapté aux sensibilités sensorielles
)


def default_accessibility() -> dict:
    return {key: None for key in ACCESSIBILITY_KEYS} | {"notes": ""}


class Venue(TimeStampedModel):
    """Lieu : adresse structurée, point géographique, accessibilité (§5.2, §9.1)."""

    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    street = models.CharField(max_length=160, blank=True)
    house_number = models.CharField(max_length=16, blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    city = models.CharField(max_length=80, default="Bruxelles")
    country = models.CharField(max_length=2, default="BE")
    area = models.ForeignKey(
        Area, null=True, blank=True, on_delete=models.SET_NULL, related_name="venues"
    )
    location = gis.PointField(geography=True, null=True, blank=True)
    geocoded_at = models.DateTimeField(null=True, blank=True)
    accessibility = models.JSONField(default=default_accessibility, blank=True)
    website = models.URLField(blank=True)
    organization = models.ForeignKey(
        "organizations.Organization",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="venues",
    )
    created_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "lieu"
        verbose_name_plural = "lieux"

    def __str__(self):
        return self.name

    @property
    def address_line(self) -> str:
        parts = [
            f"{self.street} {self.house_number}".strip(),
            f"{self.postal_code} {self.city}".strip(),
        ]
        return ", ".join(p for p in parts if p)


class TicketingDomainStatus(models.TextChoices):
    ALLOWLISTED = "ALLOWLISTED", "Liste blanche"
    REVIEW = "REVIEW", "À revoir"
    BLOCKED = "BLOCKED", "Bloqué"


class TicketingDomain(TimeStampedModel):
    """Liste blanche et réputation des billetteries (TRU-01, RG-21)."""

    domain = models.CharField(max_length=253, unique=True)
    status = models.CharField(
        max_length=12, choices=TicketingDomainStatus.choices, default=TicketingDomainStatus.REVIEW
    )
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["domain"]

    def __str__(self):
        return f"{self.domain} ({self.status})"

    @classmethod
    def status_for(cls, domain: str) -> str:
        domain = domain.lower()
        candidates = [domain]
        parts = domain.split(".")
        for i in range(1, len(parts) - 1):
            candidates.append(".".join(parts[i:]))
        rows = {d.domain: d.status for d in cls.objects.filter(domain__in=candidates)}
        for c in candidates:
            if c in rows:
                return rows[c]
        return TicketingDomainStatus.REVIEW
