"""
Machine à états des événements (§6) et règles de publication (§5.4, annexes A.2, A.3).
Chaque transition autorisée est journalisée (AuditLog) et testée (tests/test_workflow.py).
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from catalog.models import TicketingDomain, TicketingDomainStatus
from core.audit import log_action
from core.enums import TrustLevel
from core.exceptions import BusinessRuleViolation, InvalidTransition
from core.urlsafety import registrable_domain

from .models import AgePolicy, Event, EventStatus, OccurrenceStatus, PricingType

S = EventStatus

TRANSITIONS: dict[str, set[str]] = {
    "submit": {S.DRAFT, S.CHANGES_REQUESTED, S.REJECTED},
    "approve": {S.PENDING_REVIEW},
    "request_changes": {S.PENDING_REVIEW, S.PUBLISHED},
    "reject": {S.PENDING_REVIEW},
    "unpublish": {S.PUBLISHED},  # retour en modération après signalement fondé
    "cancel": {S.PUBLISHED, S.PENDING_REVIEW, S.CHANGES_REQUESTED, S.DRAFT},
    "archive": {S.PUBLISHED, S.CANCELLED},
    "back_to_draft": {S.CHANGES_REQUESTED, S.REJECTED},
}

MAJOR_CHANGE_FIELDS = (
    "venue_id",
    "ticketing_url",
    "primary_category_id",
    "age_policy",
    "pricing_type",
    "format",
)


def _check(event: Event, action: str) -> None:
    if event.status not in TRANSITIONS[action]:
        raise InvalidTransition(f"Transition « {action} » impossible depuis {event.status}.")


def validate_ready_for_submission(event: Event) -> list[str]:
    """Contrôles de complétude avant soumission (étapes 1 à 3 du formulaire)."""
    errors = []
    if not event.title.strip():
        errors.append("Le titre est obligatoire.")
    if not event.description.strip():
        errors.append("La description est obligatoire.")
    if event.primary_category_id is None:
        errors.append("Une catégorie principale est obligatoire (RG-25).")
    if event.secondary_categories.count() > 2:
        errors.append("Deux catégories secondaires maximum (RG-25).")
    if event.format != "ONLINE" and event.venue_id is None:
        errors.append("Un lieu est obligatoire pour un événement présentiel ou hybride.")
    if event.format != "ONSITE" and not event.online_url:
        errors.append(
            "Une URL de participation est obligatoire pour un événement en ligne ou hybride."
        )
    if not event.occurrences.filter(status=OccurrenceStatus.SCHEDULED).exists():
        errors.append("Au moins une séance est requise.")
    if (
        event.pricing_type == PricingType.PAID
        and event.price_min is None
        and not event.price_details
    ):
        errors.append("Un prix indicatif est requis pour un événement payant (RG-08).")
    if event.age_policy == AgePolicy.MIN_AGE and not event.min_age:
        errors.append("Indiquez l'âge minimum.")
    if (
        event.media.exists()
        and not event.media.filter(rights_confirmed=True).count() == event.media.count()
    ):
        errors.append("Confirmez détenir les droits sur tous les visuels.")
    return errors


def check_daily_quota(event: Event) -> None:
    """ADM-07 : quota de soumissions par jour pour un compte Nouveau."""
    if event.trust_level != TrustLevel.NEW:
        return
    since = timezone.now() - timedelta(days=1)
    count = (
        Event.objects.filter(owner_user=event.owner_user, submitted_at__gte=since)
        .exclude(pk=event.pk)
        .count()
    )
    if count >= settings.WIGO_RULES["NEW_ACCOUNT_DAILY_SUBMISSIONS"]:
        raise BusinessRuleViolation("Quota quotidien de soumissions atteint. Réessayez demain.")


def evaluate_ticketing_link(event: Event) -> bool:
    """RG-21 / TRU-01 : retourne True si une revue manuelle du lien est nécessaire."""
    if not event.ticketing_url:
        return False
    status = TicketingDomain.status_for(registrable_domain(event.ticketing_url))
    if status == TicketingDomainStatus.BLOCKED:
        raise BusinessRuleViolation("Ce domaine de billetterie est bloqué.")
    if status == TicketingDomainStatus.ALLOWLISTED:
        return False
    return event.trust_level == TrustLevel.NEW


def requires_moderation(event: Event) -> bool:
    """RG-04 (compte Nouveau), RG-21 (lien suspect), RG-26 (18+ hors organisation vérifiée)."""
    trust = event.trust_level
    if trust == TrustLevel.NEW:
        return True
    if event.link_review_required:
        return True
    if event.age_policy == AgePolicy.ADULTS_ONLY and trust != TrustLevel.VERIFIED:
        return True
    return False


@transaction.atomic
def submit(event: Event, actor) -> Event:
    """POST /events/{id}/submit : publication immédiate ou soumission selon la confiance."""
    _check(event, "submit")
    errors = validate_ready_for_submission(event)
    if errors:
        raise BusinessRuleViolation({"detail": "Événement incomplet.", "errors": errors})
    check_daily_quota(event)
    before = event.status
    event.link_review_required = evaluate_ticketing_link(event)
    event.submitted_at = timezone.now()
    if requires_moderation(event):
        event.status = S.PENDING_REVIEW
    else:
        event.status = S.PUBLISHED
        event.published_at = event.published_at or timezone.now()
        event.last_confirmed_at = timezone.now()
    event.save()
    log_action(
        actor, "event.submit", event, before={"status": before}, after={"status": event.status}
    )
    return event


@transaction.atomic
def approve(event: Event, moderator, comment: str = "") -> Event:
    _check(event, "approve")
    before = event.status
    event.status = S.PUBLISHED
    event.published_at = event.published_at or timezone.now()
    event.last_confirmed_at = timezone.now()
    event.link_review_required = False
    event.save()
    _record_decision(event, moderator, "APPROVE", "", comment)
    log_action(
        moderator, "event.approve", event, before={"status": before}, after={"status": event.status}
    )
    _maybe_promote_trust(event)
    return event


@transaction.atomic
def request_changes(event: Event, moderator, reason_code: str, comment: str) -> Event:
    _check(event, "request_changes")
    before = event.status
    event.status = S.CHANGES_REQUESTED
    event.save(update_fields=["status", "updated_at"])
    _record_decision(event, moderator, "REQUEST_CHANGES", reason_code, comment)
    log_action(
        moderator,
        "event.request_changes",
        event,
        before={"status": before},
        after={"status": event.status, "reason": reason_code},
    )
    return event


@transaction.atomic
def reject(event: Event, moderator, reason_code: str, comment: str) -> Event:
    """ADM-02 : refus motivé (exposé des motifs, DSA)."""
    _check(event, "reject")
    if not reason_code:
        raise BusinessRuleViolation("Un motif de refus est obligatoire.")
    before = event.status
    event.status = S.REJECTED
    event.save(update_fields=["status", "updated_at"])
    _record_decision(event, moderator, "REJECT", reason_code, comment)
    log_action(
        moderator,
        "event.reject",
        event,
        before={"status": before},
        after={"status": event.status, "reason": reason_code},
    )
    return event


@transaction.atomic
def unpublish(event: Event, moderator, reason_code: str, comment: str) -> Event:
    """Signalement fondé : retour en modération et rétrogradation du niveau de confiance (§5.4)."""
    _check(event, "unpublish")
    before = event.status
    event.status = S.PENDING_REVIEW
    event.save(update_fields=["status", "updated_at"])
    _record_decision(event, moderator, "UNPUBLISH", reason_code, comment)
    demote_trust(event, moderator)
    log_action(
        moderator,
        "event.unpublish",
        event,
        before={"status": before},
        after={"status": event.status, "reason": reason_code},
    )
    return event


@transaction.atomic
def cancel(event: Event, actor, reason: str = "") -> Event:
    """RG-12 : l'annulation reste visible sur l'URL existante."""
    _check(event, "cancel")
    before = event.status
    event.status = S.CANCELLED
    event.cancelled_at = timezone.now()
    event.save(update_fields=["status", "cancelled_at", "updated_at"])
    event.occurrences.filter(status=OccurrenceStatus.SCHEDULED).update(
        status=OccurrenceStatus.CANCELLED
    )
    log_action(
        actor,
        "event.cancel",
        event,
        before={"status": before},
        after={"status": event.status, "reason": reason},
    )
    return event


@transaction.atomic
def archive(event: Event, actor=None) -> Event:
    _check(event, "archive")
    before = event.status
    event.status = S.ARCHIVED
    event.archived_at = timezone.now()
    event.save(update_fields=["status", "archived_at", "updated_at"])
    log_action(
        actor, "event.archive", event, before={"status": before}, after={"status": event.status}
    )
    return event


@transaction.atomic
def back_to_draft(event: Event, actor) -> Event:
    _check(event, "back_to_draft")
    before = event.status
    event.status = S.DRAFT
    event.save(update_fields=["status", "updated_at"])
    log_action(
        actor,
        "event.back_to_draft",
        event,
        before={"status": before},
        after={"status": event.status},
    )
    return event


def confirm_freshness(event: Event, actor) -> Event:
    """POST /events/{id}/confirm — relance fraîcheur (§5.7)."""
    if event.status != S.PUBLISHED:
        raise InvalidTransition("Seul un événement publié peut être confirmé.")
    event.last_confirmed_at = timezone.now()
    event.freshness_reminder_sent_at = None
    event.save(update_fields=["last_confirmed_at", "freshness_reminder_sent_at", "updated_at"])
    log_action(actor, "event.confirm", event)
    return event


def is_major_change(before: dict, after: dict) -> bool:
    """Annexe A.2 : date/heure > 2 h, lieu, URL billetterie, gratuit -> payant, catégorie, 18+."""
    for field in MAJOR_CHANGE_FIELDS:
        if field in after and before.get(field) != after.get(field):
            if field == "pricing_type" and before.get(field) != PricingType.FREE:
                continue  # payant -> payant : mineur
            if (
                field == "age_policy"
                and after.get(field) != AgePolicy.ADULTS_ONLY
                and before.get(field) != AgePolicy.ADULTS_ONLY
            ):
                continue
            return True
    shift = timedelta(hours=settings.WIGO_RULES["MAJOR_CHANGE_TIME_SHIFT_HOURS"])
    b_occ, a_occ = before.get("occurrences"), after.get("occurrences")
    if b_occ is not None and a_occ is not None:
        if len(b_occ) != len(a_occ):
            return True
        for b, a in zip(sorted(b_occ), sorted(a_occ), strict=True):
            if abs(a[0] - b[0]) > shift or abs(a[1] - b[1]) > shift:
                return True
    return False


@transaction.atomic
def after_edit(event: Event, actor, before: dict, after: dict) -> Event:
    """RG-11 : modification importante d'un événement publié."""
    if event.status != S.PUBLISHED or not is_major_change(before, after):
        return event
    if event.trust_level == TrustLevel.NEW:
        event.status = S.PENDING_REVIEW
        event.save(update_fields=["status", "updated_at"])
    log_action(actor, "event.major_change", event, before=_jsonable(before), after=_jsonable(after))
    from .tasks import notify_favorites_of_change

    notify_favorites_of_change.delay(str(event.pk))
    return event


def _maybe_promote_trust(event: Event) -> None:
    """Nouveau -> Confirmé après N événements approuvés sans incident."""
    from moderation.models import ModerationDecision

    holder = event.organization if event.organization_id else event.owner_user
    if holder.trust_level != TrustLevel.NEW:
        return
    qs = ModerationDecision.objects.filter(action="APPROVE")
    qs = (
        qs.filter(event__organization=holder)
        if event.organization_id
        else qs.filter(event__owner_user=holder, event__organization__isnull=True)
    )
    if (
        qs.values("event").distinct().count()
        >= settings.WIGO_RULES["CONFIRMED_AFTER_APPROVED_EVENTS"]
    ):
        holder.trust_level = TrustLevel.CONFIRMED
        holder.save(update_fields=["trust_level"])
        log_action(None, "trust.promote", holder, after={"trust_level": holder.trust_level})


def demote_trust(event: Event, actor) -> None:
    holder = event.organization if event.organization_id else event.owner_user
    if holder.trust_level == TrustLevel.NEW:
        return
    before = holder.trust_level
    holder.trust_level = TrustLevel.NEW
    holder.save(update_fields=["trust_level"])
    log_action(
        actor,
        "trust.demote",
        holder,
        before={"trust_level": before},
        after={"trust_level": TrustLevel.NEW},
    )


def _record_decision(event: Event, moderator, action: str, reason_code: str, comment: str):
    from moderation.models import ModerationDecision

    return ModerationDecision.objects.create(
        event=event, moderator=moderator, action=action, reason_code=reason_code, comment=comment
    )


def _jsonable(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        if k == "occurrences":
            out[k] = [[a.isoformat(), b.isoformat()] for a, b in v]
        else:
            out[k] = str(v) if v is not None else None
    return out
