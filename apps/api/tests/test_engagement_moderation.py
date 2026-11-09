"""RET-02, ADM-04, ADM-09, annexe A.3 : newsletter, signalements, sélection du week-end, audit."""

import pytest
from django.core import mail

from engagement.models import NewsletterSubscription, SendStatus, WeekendSelection
from engagement.tasks import send_weekly_newsletter
from events.models import EventStatus
from moderation.models import AuditLog, Report

pytestmark = pytest.mark.django_db


def test_newsletter_double_opt_in_and_unsubscribe(api, area):
    r = api.post(
        "/api/v1/newsletter",
        {"email": "Fan@Test.be", "area": "ixelles", "language": "fr", "consent": True},
    )
    assert r.status_code == 202
    sub = NewsletterSubscription.objects.get(email="fan@test.be")
    assert (
        sub.status == "PENDING"
        and len(mail.outbox) == 1
        and sub.confirm_token in mail.outbox[0].body
    )
    assert api.get("/api/v1/newsletter/confirm", {"token": "bad"}).status_code == 404
    assert api.get("/api/v1/newsletter/confirm", {"token": sub.confirm_token}).status_code == 200
    sub.refresh_from_db()
    assert sub.status == "CONFIRMED" and sub.confirmed_at
    assert (
        api.get("/api/v1/newsletter/unsubscribe", {"token": sub.unsubscribe_token}).status_code
        == 200
    )
    sub.refresh_from_db()
    assert sub.status == "UNSUBSCRIBED"
    assert (
        api.post("/api/v1/newsletter", {"email": "x@test.be", "consent": False}).status_code == 400
    )


def test_weekend_selection_generates_newsletter(api, moderator, make_event, confirmed_user, area):
    e1 = make_event(confirmed_user, title="Un")
    e2 = make_event(confirmed_user, title="Deux")
    make_event(confirmed_user, title="Brouillon", status=EventStatus.DRAFT)
    api.force_authenticate(moderator)
    r = api.post(
        "/api/v1/admin/selection",
        {
            "title": "Ce week-end",
            "events": [{"event": e1.slug, "blurb": "Top"}, {"event": e2.slug}],
            "send_status": "READY",
        },
        format="json",
    )
    assert r.status_code == 200 and len(r.json()["items"]) == 2
    r = api.post("/api/v1/admin/selection", {"events": [{"event": "brouillon"}]}, format="json")
    assert r.status_code == 400
    api.force_authenticate(None)
    assert len(api.get("/api/v1/selection").json()["items"]) == 2

    NewsletterSubscription.objects.create(email="a@test.be", status="CONFIRMED", language="fr")
    NewsletterSubscription.objects.create(email="b@test.be", status="PENDING")
    NewsletterSubscription.objects.create(email="c@test.be", status="CONFIRMED", language="nl")
    assert send_weekly_newsletter() == 2
    sel = WeekendSelection.objects.get()
    assert sel.send_status == SendStatus.SENT and sel.recipients_count == 2
    body = mail.outbox[-1].body
    assert "Un" in body and "Se désinscrire" in body and "Sélection WIGO" in body
    assert send_weekly_newsletter() == 0  # pas de double envoi


def test_report_founded_unpublishes_and_suspends_after_two(
    api, confirmed_user, moderator, make_event, settings
):
    e1 = make_event(confirmed_user, title="Un")
    e2 = make_event(confirmed_user, title="Deux")
    r = api.post(
        "/api/v1/reports",
        {
            "event": e1.slug,
            "category": "SPAM",
            "description": "Pub déguisée",
            "reporter_email": "x@test.be",
        },
    )
    assert r.status_code == 201
    assert api.post("/api/v1/reports", {"category": "SPAM"}).status_code == 400
    r2 = api.post("/api/v1/reports", {"event": e2.slug, "category": "ILLEGAL"})
    assert api.get("/api/v1/admin/reports").status_code == 401

    api.force_authenticate(moderator)
    assert len(api.get("/api/v1/admin/reports").json()) == 2
    assert (
        api.post(
            f"/api/v1/admin/reports/{r.json()['id']}/decide", {"founded": True, "note": "Confirmé"}
        ).status_code
        == 200
    )
    e1.refresh_from_db()
    confirmed_user.refresh_from_db()
    assert e1.status == EventStatus.PENDING_REVIEW and confirmed_user.trust_level == "NEW"
    assert confirmed_user.status == "ACTIVE"
    api.post(f"/api/v1/admin/reports/{r2.json()['id']}/decide", {"founded": True})
    confirmed_user.refresh_from_db()
    assert confirmed_user.status == "SUSPENDED" and confirmed_user.suspended_until  # annexe A.3
    assert Report.objects.filter(status="FOUNDED").count() == 2
    assert AuditLog.objects.filter(action="user.suspend").exists()
    audit = api.get("/api/v1/admin/audit", {"action": "report"}).json()
    assert audit["results"]


def test_dismissed_report_changes_nothing(api, confirmed_user, moderator, make_event):
    e1 = make_event(confirmed_user)
    rid = api.post("/api/v1/reports", {"event": e1.slug, "category": "OTHER"}).json()["id"]
    api.force_authenticate(moderator)
    api.post(f"/api/v1/admin/reports/{rid}/decide", {"founded": False})
    e1.refresh_from_db()
    assert e1.status == EventStatus.PUBLISHED


def test_duplicate_detection(make_event, confirmed_user, new_user):
    from moderation.services import find_duplicates

    make_event(confirmed_user, title="Concert de jazz au Flagey", start_in_hours=24)
    candidate = make_event(
        new_user, title="Concert jazz Flagey", status=EventStatus.PENDING_REVIEW, start_in_hours=26
    )
    assert [e.title for e in find_duplicates(candidate)] == ["Concert de jazz au Flagey"]


def test_home_and_counts_endpoints(api, make_event, confirmed_user):
    make_event(confirmed_user, title="Ce soir", start_in_hours=1)
    r = api.get("/api/v1/home")
    assert r.status_code == 200 and r.json()["counts"]["active_events"] == 1
    assert api.get("/api/v1/events/counts").json() == {"concerts": 1}
    assert len(api.get("/api/v1/categories").json()) == 2
    assert api.get("/api/v1/areas").status_code == 200


def test_admin_stats_requires_admin(api, moderator, admin):
    api.force_authenticate(moderator)
    assert api.get("/api/v1/admin/stats").status_code == 403
    api.force_authenticate(admin)
    assert api.get("/api/v1/admin/stats").status_code == 200
