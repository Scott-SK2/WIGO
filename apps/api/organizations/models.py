from django.conf import settings
from django.db import models

from core.enums import TrustLevel
from core.models import TimeStampedModel, UUIDModel


class OrganizationType(models.TextChoices):
    VENUE = "VENUE", "Salle / lieu"
    ASSOCIATION = "ASSOCIATION", "Association"
    COLLECTIVE = "COLLECTIVE", "Collectif"
    COMPANY = "COMPANY", "Entreprise"
    PUBLIC = "PUBLIC", "Institution publique"
    OTHER = "OTHER", "Autre"


class VerificationStatus(models.TextChoices):
    UNVERIFIED = "UNVERIFIED", "Non vérifiée"
    PENDING = "PENDING", "En cours"
    VERIFIED = "VERIFIED", "Vérifiée"


class Organization(UUIDModel):
    """Organisation (§9.1) : propriétaire, membres, vérification, niveau de confiance."""

    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    type = models.CharField(
        max_length=12, choices=OrganizationType.choices, default=OrganizationType.OTHER
    )
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to="organizations/logos/", blank=True)
    website = models.URLField(blank=True)
    contact_email = models.EmailField(blank=True)
    bce_number = models.CharField("Numéro BCE", max_length=12, blank=True)
    verification_status = models.CharField(
        max_length=10, choices=VerificationStatus.choices, default=VerificationStatus.UNVERIFIED
    )
    trust_level = models.CharField(
        max_length=10, choices=TrustLevel.choices, default=TrustLevel.NEW
    )
    is_suspended = models.BooleanField(default=False)
    # Pages créées par l'équipe WIGO pour des lieux connus, revendiquables (§5.6)
    is_claimable = models.BooleanField(default=False)
    claimed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "organisation"

    def __str__(self):
        return self.name

    @property
    def is_verified(self) -> bool:
        return self.verification_status == VerificationStatus.VERIFIED

    def role_of(self, user) -> str | None:
        if not user or not user.is_authenticated:
            return None
        m = self.members.filter(user=user).first()
        return m.role if m else None

    def can_edit(self, user) -> bool:
        return self.role_of(user) in (MemberRole.OWNER, MemberRole.EDITOR)

    def is_owner(self, user) -> bool:
        return self.role_of(user) == MemberRole.OWNER


class MemberRole(models.TextChoices):
    OWNER = "OWNER", "Propriétaire"
    EDITOR = "EDITOR", "Éditeur"


class OrganizationMember(TimeStampedModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=8, choices=MemberRole.choices, default=MemberRole.EDITOR)

    class Meta:
        unique_together = [("organization", "user")]

    def __str__(self):
        return f"{self.user} — {self.organization} ({self.role})"


class ClaimStatus(models.TextChoices):
    PENDING = "PENDING", "En attente"
    APPROVED = "APPROVED", "Approuvée"
    REJECTED = "REJECTED", "Refusée"


class OwnershipClaim(UUIDModel):
    """Revendication d'une page (CAT-03, RG-27)."""

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="claims")
    claimant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="claims"
    )
    evidence = models.TextField(help_text="E-mail de domaine, contact officiel, preuve…")
    status = models.CharField(
        max_length=8, choices=ClaimStatus.choices, default=ClaimStatus.PENDING
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
