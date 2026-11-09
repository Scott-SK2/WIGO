"""QA-01 : règles métier et transitions de statut (§6)."""

from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from core.enums import TrustLevel
from core.exceptions import BusinessRuleViolation, InvalidTransition
from events import workflow
from events.models import AgePolicy, EventOccurrence, EventStatus, OccurrenceStatus
from moderation.models import AuditLog, ModerationDecision

pytestmark = pytest.mark.django_db


def test_rg06_end_must_be_after_start(make_event, confirmed_user):
    event = make_event(confirmed_user, status=EventStatus.DRAFT)
    now = timezone.now()
    with pytest.raises(IntegrityError):
        EventOccurrence.objects.create(event=event, starts_at=now, ends_at=now)


def test_rg04_new_account_goes_to_moderation(make_event, new_user):
    event = make_event(new_user, status=EventStatus.DRAFT)
    workflow.submit(event, new_user)
    assert event.status == EventStatus.PENDING_REVIEW
    assert event.published_at is None
    assert AuditLog.objects.filter(action="event.submit", target_id=str(event.pk)).exists()


def test_rg04_confirmed_account_publishes_immediately(make_event, confirmed_user):
    event = make_event(confirmed_user, status=EventStatus.DRAFT)
    workflow.submit(event, confirmed_user)
    assert event.status == EventStatus.PUBLISHED
    assert event.published_at is not None


def test_organization_trust_level_wins_over_user(make_event, new_user, organization):
    """Un compte Nouveau publiant pour une organisation Confirmée publie immédiatement."""
    event = make_event(new_user, status=EventStatus.DRAFT, organization=organization)
    workflow.submit(event, new_user)
    assert event.status == EventStatus.PUBLISHED


def test_submit_requires_complete_event(make_event, confirmed_user):
    event = make_event(confirmed_user, status=EventStatus.DRAFT, description="")
    with pytest.raises(BusinessRuleViolation):
        workflow.submit(event, confirmed_user)


def test_rg26_adult_event_needs_moderation_unless_verified(
    make_event, confirmed_user, organization
):
    event = make_event(confirmed_user, status=EventStatus.DRAFT, age_policy=AgePolicy.ADULTS_ONLY)
    workflow.submit(event, confirmed_user)
    assert event.status == EventStatus.PENDING_REVIEW
    organization.trust_level = TrustLevel.VERIFIED
    organization.save()
    event2 = make_event(
        confirmed_user,
        title="Soiree 18",
        status=EventStatus.DRAFT,
        age_policy=AgePolicy.ADULTS_ONLY,
        organization=organization,
    )
    workflow.submit(event2, confirmed_user)
    assert event2.status == EventStatus.PUBLISHED


def test_rg21_blocked_ticketing_domain_rejected(make_event, confirmed_user, ticketing_domains):
    event = make_event(confirmed_user, status=EventStatus.DRAFT, ticketing_url="https://bit.ly/x")
    with pytest.raises(BusinessRuleViolation):
        workflow.submit(event, confirmed_user)


def test_rg21_unknown_domain_flags_review_for_new_account(
    make_event, new_user, confirmed_user, ticketing_domains
):
    event = make_event(
        new_user, status=EventStatus.DRAFT, ticketing_url="https://inconnu-billets.example/x"
    )
    workflow.submit(event, new_user)
    assert event.link_review_required is True
    # Un compte Confirmé avec un domaine inconnu publie, mais une liste blanche connue ne lève aucune alerte
    event2 = make_event(
        confirmed_user,
        title="Autre",
        status=EventStatus.DRAFT,
        ticketing_url="https://www.eventbrite.be/e/1",
    )
    workflow.submit(event2, confirmed_user)
    assert event2.link_review_required is False and event2.status == EventStatus.PUBLISHED


def test_reject_requires_reason_and_records_decision(make_event, new_user, moderator):
    event = make_event(new_user, status=EventStatus.PENDING_REVIEW)
    with pytest.raises(BusinessRuleViolation):
        workflow.reject(event, moderator, "", "")
    workflow.reject(event, moderator, "INCOMPLETE", "Il manque le lieu.")
    assert event.status == EventStatus.REJECTED
    decision = ModerationDecision.objects.get(event=event)
    assert decision.reason_code == "INCOMPLETE" and decision.moderator == moderator


def test_request_changes_then_resubmit(make_event, new_user, moderator):
    event = make_event(new_user, status=EventStatus.PENDING_REVIEW)
    workflow.request_changes(event, moderator, "WRONG_DATE_PLACE", "Vérifiez la date.")
    assert event.status == EventStatus.CHANGES_REQUESTED
    workflow.submit(event, new_user)
    assert event.status == EventStatus.PENDING_REVIEW


def test_trust_promotion_after_three_approvals(make_event, new_user, moderator):
    for i in range(3):
        event = make_event(new_user, title=f"Event {i}", status=EventStatus.PENDING_REVIEW)
        workflow.approve(event, moderator)
        new_user.refresh_from_db()
        assert new_user.trust_level == (TrustLevel.CONFIRMED if i == 2 else TrustLevel.NEW)


def test_unpublish_demotes_trust(make_event, confirmed_user, moderator):
    event = make_event(confirmed_user)
    workflow.unpublish(event, moderator, "SUSPICIOUS_LINK", "Lien douteux")
    confirmed_user.refresh_from_db()
    assert event.status == EventStatus.PENDING_REVIEW
    assert confirmed_user.trust_level == TrustLevel.NEW


def test_cancel_marks_occurrences_and_stays_visible(make_event, confirmed_user):
    event = make_event(confirmed_user, occurrences=2)
    workflow.cancel(event, confirmed_user, "Météo")
    assert event.status == EventStatus.CANCELLED
    assert event.occurrences.filter(status=OccurrenceStatus.CANCELLED).count() == 2


def test_invalid_transitions(make_event, confirmed_user, moderator):
    event = make_event(confirmed_user, status=EventStatus.DRAFT)
    with pytest.raises(InvalidTransition):
        workflow.approve(event, moderator)
    with pytest.raises(InvalidTransition):
        workflow.archive(event)
    with pytest.raises(InvalidTransition):
        workflow.confirm_freshness(event, confirmed_user)


def test_archive_from_published_and_cancelled(make_event, confirmed_user):
    e1 = make_event(confirmed_user, title="A")
    e2 = make_event(confirmed_user, title="B", status=EventStatus.CANCELLED)
    workflow.archive(e1)
    workflow.archive(e2)
    assert e1.status == e2.status == EventStatus.ARCHIVED


def test_rg11_major_change_sends_new_account_back_to_review(make_event, new_user, far_venue):
    event = make_event(new_user)  # publié (approuvé auparavant)
    before = {"venue_id": event.venue_id, "occurrences": []}
    after = {"venue_id": far_venue.pk, "occurrences": []}
    workflow.after_edit(event, new_user, before, after)
    assert event.status == EventStatus.PENDING_REVIEW


def test_rg11_major_change_keeps_confirmed_account_published(make_event, confirmed_user, far_venue):
    event = make_event(confirmed_user)
    workflow.after_edit(
        event, confirmed_user, {"venue_id": event.venue_id}, {"venue_id": far_venue.pk}
    )
    assert event.status == EventStatus.PUBLISHED
    assert AuditLog.objects.filter(action="event.major_change").exists()


def test_annex_a2_time_shift_threshold():
    t = timezone.now()
    small = [(t, t + timedelta(hours=2))]
    shifted_1h = [(t + timedelta(hours=1), t + timedelta(hours=3))]
    shifted_3h = [(t + timedelta(hours=3), t + timedelta(hours=5))]
    assert workflow.is_major_change({"occurrences": small}, {"occurrences": shifted_1h}) is False
    assert workflow.is_major_change({"occurrences": small}, {"occurrences": shifted_3h}) is True
    assert workflow.is_major_change({"pricing_type": "PAID"}, {"pricing_type": "PWYW"}) is False
    assert workflow.is_major_change({"pricing_type": "FREE"}, {"pricing_type": "PAID"}) is True
    assert workflow.is_major_change({"age_policy": "ALL"}, {"age_policy": "MIN_AGE"}) is False
    assert workflow.is_major_change({"age_policy": "ALL"}, {"age_policy": "ADULTS_ONLY"}) is True


def test_daily_quota_for_new_accounts(make_event, new_user, settings):
    settings.WIGO_RULES = {**settings.WIGO_RULES, "NEW_ACCOUNT_DAILY_SUBMISSIONS": 2}
    for i in range(2):
        workflow.submit(
            make_event(new_user, title=f"Quota {i}", status=EventStatus.DRAFT), new_user
        )
    with pytest.raises(BusinessRuleViolation):
        workflow.submit(make_event(new_user, title="Quota 3", status=EventStatus.DRAFT), new_user)


def test_archive_task_archives_finished_events(make_event, confirmed_user):
    from events.tasks import archive_finished_events

    done = make_event(confirmed_user, title="Fini", start_in_hours=-48)
    upcoming = make_event(confirmed_user, title="Bientot")
    assert archive_finished_events() == 1
    done.refresh_from_db()
    upcoming.refresh_from_db()
    assert done.status == EventStatus.ARCHIVED and upcoming.status == EventStatus.PUBLISHED
