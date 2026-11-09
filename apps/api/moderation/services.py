from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import UserStatus
from core.audit import log_action
from core.exceptions import BusinessRuleViolation
from events import workflow
from events.models import Event, EventStatus
from organizations.models import Organization

from .models import Report, ReportStatus


def _organizer_of(target):
    if isinstance(target, Event):
        return target.organization if target.organization_id else target.owner_user
    return target


@transaction.atomic
def handle_report(report: Report, moderator, founded: bool, note: str = "") -> Report:
    """Traite un signalement ; fondé -> dépublication + éventuelle suspension (annexe A.3)."""
    if report.status != ReportStatus.OPEN:
        raise BusinessRuleViolation("Signalement déjà traité.")
    report.status = ReportStatus.FOUNDED if founded else ReportStatus.DISMISSED
    report.handled_by = moderator
    report.handled_at = timezone.now()
    report.decision_note = note
    report.save()
    log_action(
        moderator,
        "report.founded" if founded else "report.dismissed",
        report.target,
        after={"note": note},
    )
    if founded and report.event_id and report.event.status == EventStatus.PUBLISHED:
        workflow.unpublish(report.event, moderator, "OTHER", note or "Signalement fondé")
    if founded:
        check_suspension(report.target, moderator)
    return report


def check_suspension(target, moderator) -> bool:
    """Annexe A.3 : suspension temporaire après N signalements fondés en 30 jours."""
    rules = settings.WIGO_RULES
    since = timezone.now() - timedelta(days=rules["SUSPENSION_WINDOW_DAYS"])
    organizer = _organizer_of(target)
    if isinstance(organizer, Organization):
        founded = (
            Report.objects.filter(status=ReportStatus.FOUNDED, handled_at__gte=since)
            .filter(Q(event__organization=organizer) | Q(organization=organizer))
            .count()
        )
        if founded >= rules["SUSPENSION_REPORTS"] and not organizer.is_suspended:
            organizer.is_suspended = True
            organizer.save(update_fields=["is_suspended"])
            log_action(
                moderator,
                "organization.suspend",
                organizer,
                after={"days": rules["SUSPENSION_DURATION_DAYS"]},
            )
            return True
        return False
    founded = Report.objects.filter(
        status=ReportStatus.FOUNDED,
        handled_at__gte=since,
        event__owner_user=organizer,
        event__organization__isnull=True,
    ).count()
    if founded >= rules["SUSPENSION_REPORTS"] and organizer.status == UserStatus.ACTIVE:
        organizer.status = UserStatus.SUSPENDED
        organizer.suspended_until = timezone.now() + timedelta(
            days=rules["SUSPENSION_DURATION_DAYS"]
        )
        organizer.save(update_fields=["status", "suspended_until"])
        log_action(
            moderator,
            "user.suspend",
            organizer,
            after={"until": organizer.suspended_until.isoformat()},
        )
        return True
    return False


def find_duplicates(event: Event):
    """ADM-08 / RG-20 : même lieu, même jour, titre proche -> fusion proposée au modérateur."""
    from django.contrib.postgres.search import TrigramSimilarity

    occ = event.occurrences.order_by("starts_at").first()
    if occ is None:
        return Event.objects.none()
    day_start = occ.starts_at.replace(hour=0, minute=0, second=0, microsecond=0)
    qs = Event.objects.exclude(pk=event.pk).filter(
        status__in=[EventStatus.PUBLISHED, EventStatus.PENDING_REVIEW],
        occurrences__starts_at__range=(
            day_start - timedelta(hours=12),
            day_start + timedelta(hours=36),
        ),
    )
    if event.venue_id:
        qs = qs.filter(venue_id=event.venue_id)
    return (
        qs.annotate(similarity=TrigramSimilarity("title", event.title))
        .filter(similarity__gte=0.45)
        .order_by("-similarity")
        .distinct()[:5]
    )
