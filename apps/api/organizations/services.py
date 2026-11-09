from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from core.audit import log_action
from core.exceptions import BusinessRuleViolation

from .models import ClaimStatus, MemberRole, Organization, OrganizationMember, OwnershipClaim


def unique_slug(name: str) -> str:
    base = slugify(name)[:160] or "organisation"
    slug, i = base, 2
    while Organization.objects.filter(slug=slug).exists():
        slug, i = f"{base}-{i}", i + 1
    return slug


@transaction.atomic
def create_organization(owner, **fields) -> Organization:
    org = Organization.objects.create(slug=unique_slug(fields["name"]), created_by=owner, **fields)
    OrganizationMember.objects.create(organization=org, user=owner, role=MemberRole.OWNER)
    log_action(owner, "organization.create", org, after={"name": org.name})
    return org


def submit_claim(org: Organization, user, evidence: str) -> OwnershipClaim:
    if org.members.filter(role=MemberRole.OWNER).exists() and not org.is_claimable:
        raise BusinessRuleViolation("Cette page a déjà un propriétaire.")
    if org.claims.filter(claimant=user, status=ClaimStatus.PENDING).exists():
        raise BusinessRuleViolation("Une revendication est déjà en cours.")
    claim = OwnershipClaim.objects.create(organization=org, claimant=user, evidence=evidence)
    log_action(user, "organization.claim.submit", org)
    return claim


@transaction.atomic
def decide_claim(claim: OwnershipClaim, moderator, approve: bool, note: str = "") -> OwnershipClaim:
    """RG-27 : transfert après validation d'un modérateur, historique conservé."""
    if claim.status != ClaimStatus.PENDING:
        raise BusinessRuleViolation("Revendication déjà traitée.")
    before = {
        "owners": list(
            claim.organization.members.filter(role=MemberRole.OWNER).values_list(
                "user__email", flat=True
            )
        )
    }
    claim.status = ClaimStatus.APPROVED if approve else ClaimStatus.REJECTED
    claim.decided_by = moderator
    claim.decided_at = timezone.now()
    claim.decision_note = note
    claim.save()
    if approve:
        org = claim.organization
        org.members.filter(role=MemberRole.OWNER).update(role=MemberRole.EDITOR)
        OrganizationMember.objects.update_or_create(
            organization=org, user=claim.claimant, defaults={"role": MemberRole.OWNER}
        )
        org.is_claimable = False
        org.claimed_at = timezone.now()
        org.save(update_fields=["is_claimable", "claimed_at", "updated_at"])
        org.claims.filter(status=ClaimStatus.PENDING).exclude(pk=claim.pk).update(
            status=ClaimStatus.REJECTED,
            decided_by=moderator,
            decided_at=timezone.now(),
            decision_note="Une autre revendication a été approuvée.",
        )
    log_action(
        moderator,
        "organization.claim.approve" if approve else "organization.claim.reject",
        claim.organization,
        before=before,
        after={"claimant": claim.claimant.email, "note": note},
    )
    return claim
