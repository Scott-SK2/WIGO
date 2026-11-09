"""QA-02 : API événements et isolation des droits entre organisateurs (RG-10)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from events.models import Event, EventStatus
from organizations.models import MemberRole, OrganizationMember

pytestmark = pytest.mark.django_db
E = "/api/v1/events"


def _payload(category_slug="concerts", venue_id=None, **extra):
    start = timezone.now() + timedelta(days=3)
    return {
        "title": "Mon concert",
        "description": "Une description complète de l'événement.",
        "languages": ["fr"],
        "primary_category": category_slug,
        "format": "ONSITE",
        "venue": venue_id,
        "pricing_type": "PAID",
        "price_min": "12.00",
        "price_max": "15.00",
        "ticketing_url": "https://www.eventbrite.be/e/123",
        "occurrences": [
            {
                "starts_at": start.isoformat(),
                "ends_at": (start + timedelta(hours=2)).isoformat(),
                "timezone": "Europe/Brussels",
            }
        ],
        **extra,
    }


def test_full_publication_flow_for_confirmed_account(
    api, confirmed_user, venue, category, ticketing_domains
):
    api.force_authenticate(confirmed_user)
    r = api.post(E, _payload(venue_id=venue.pk), format="json")
    assert r.status_code == 201, r.json()
    body = r.json()
    assert body["status"] == "DRAFT" and body["submission_errors"] == []
    event_id = body["id"]
    assert api.get(f"{E}/{body['slug']}").status_code == 200  # l'auteur voit son brouillon
    api.force_authenticate(None)
    assert api.get(f"{E}/{body['slug']}").status_code == 404  # RG-05 : invisible publiquement
    api.force_authenticate(confirmed_user)
    r = api.post(f"{E}/{event_id}/submit")
    assert r.status_code == 200 and r.json()["status"] == "PUBLISHED"
    api.force_authenticate(None)
    assert api.get(f"{E}/{body['slug']}").status_code == 200
    assert api.get(E).json()["results"][0]["slug"] == body["slug"]


def test_new_account_flow_goes_through_moderation(
    api, new_user, moderator, venue, category, ticketing_domains
):
    api.force_authenticate(new_user)
    event_id = api.post(E, _payload(venue_id=venue.pk), format="json").json()["id"]
    assert api.post(f"{E}/{event_id}/submit").json()["status"] == "PENDING_REVIEW"
    assert api.get("/api/v1/admin/moderation").status_code == 403  # pas modérateur

    api.force_authenticate(moderator)
    queue = api.get("/api/v1/admin/moderation").json()
    assert [i["id"] for i in queue["results"]] == [event_id]
    assert queue["results"][0]["trust_level"] == "NEW"
    r = api.post("/api/v1/admin/moderation", {"event": event_id, "action": "REJECT"})
    assert r.status_code == 400  # motif obligatoire
    r = api.post(
        "/api/v1/admin/moderation",
        {
            "event": event_id,
            "action": "REQUEST_CHANGES",
            "reason_code": "INCOMPLETE",
            "comment": "Ajoutez une affiche.",
        },
    )
    assert r.status_code == 200 and r.json()["status"] == "CHANGES_REQUESTED"
    assert r.json()["decisions"][0]["reason_label"].startswith("Informations")

    api.force_authenticate(new_user)
    assert api.get(f"{E}/{event_id}").json()["status"] == "CHANGES_REQUESTED"
    assert api.post(f"{E}/{event_id}/submit").json()["status"] == "PENDING_REVIEW"
    api.force_authenticate(moderator)
    assert (
        api.post("/api/v1/admin/moderation", {"event": event_id, "action": "APPROVE"}).json()[
            "status"
        ]
        == "PUBLISHED"
    )


def test_isolation_between_organizers(api, confirmed_user, other_user, make_event, venue):
    event = make_event(confirmed_user)
    api.force_authenticate(other_user)
    # Les événements d'autrui n'existent pas pour l'espace organisateur (404, aucune fuite)
    assert api.get(f"{E}/{event.id}").status_code == 404
    assert api.patch(f"{E}/{event.id}", {"title": "Piraté"}, format="json").status_code == 404
    assert api.post(f"{E}/{event.id}/cancel", {}).status_code == 404
    assert api.get(f"{E}/{event.id}/stats").status_code == 404
    assert api.delete(f"{E}/{event.id}").status_code == 404
    event.refresh_from_db()
    assert event.title == "Concert test"
    assert api.get(f"{E}/mine").json()["results"] == []


def test_organization_editor_rights(
    api, confirmed_user, other_user, new_user, organization, make_event
):
    event = make_event(confirmed_user, organization=organization)
    OrganizationMember.objects.create(
        organization=organization, user=other_user, role=MemberRole.EDITOR
    )
    api.force_authenticate(other_user)
    r = api.patch(
        f"{E}/{event.id}", {"description": "Description mise à jour par un éditeur."}, format="json"
    )
    assert r.status_code == 200
    assert len(api.get(f"{E}/mine").json()["results"]) == 1
    # Un éditeur ne gère pas les membres ; le propriétaire oui
    assert (
        api.post(
            f"/api/v1/organizations/{organization.slug}/members", {"email": new_user.email}
        ).status_code
        == 403
    )
    api.force_authenticate(confirmed_user)
    r = api.post(
        f"/api/v1/organizations/{organization.slug}/members",
        {"email": new_user.email, "role": "EDITOR"},
    )
    assert r.status_code == 200 and len(r.json()["members"]) == 3
    # Un non-membre ne peut pas publier au nom de l'organisation
    api.force_authenticate(new_user)
    OrganizationMember.objects.filter(user=new_user).delete()
    r = api.post(
        E,
        {"title": "X", "primary_category": "concerts", "organization": organization.slug},
        format="json",
    )
    assert r.status_code == 400


def test_validation_rules_on_write(api, confirmed_user, venue, category, other_category):
    api.force_authenticate(confirmed_user)
    base = _payload(venue_id=venue.pk)
    r = api.post(E, {**base, "ticketing_url": "http://insecure.example/x"}, format="json")
    assert r.status_code == 400 and "ticketing_url" in r.json()["error"]["details"]
    r = api.post(E, {**base, "ticketing_url": "https://127.0.0.1/x"}, format="json")
    assert r.status_code == 400
    r = api.post(E, {**base, "price_min": "20", "price_max": "10"}, format="json")
    assert r.status_code == 400
    r = api.post(E, {**base, "title": "x" * 161}, format="json")
    assert r.status_code == 400
    start = timezone.now()
    r = api.post(
        E,
        {**base, "occurrences": [{"starts_at": start.isoformat(), "ends_at": start.isoformat()}]},
        format="json",
    )
    assert r.status_code == 400
    r = api.post(
        E, {**base, "secondary_categories": ["expositions", "musique", "concerts"]}, format="json"
    )
    assert r.status_code == 400
    r = api.post(E, {**base, "age_policy": "MIN_AGE"}, format="json")
    assert r.status_code == 400


def test_draft_autosave_and_submit_errors(api, confirmed_user, category):
    api.force_authenticate(confirmed_user)
    r = api.post(
        E,
        {"title": "Brouillon étape 1", "primary_category": "concerts", "draft_step": 1},
        format="json",
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "DRAFT" and any("séance" in e for e in body["submission_errors"])
    r = api.post(f"{E}/{body['id']}/submit")
    assert r.status_code == 409 and r.json()["error"]["code"] == "business_rule_violation"
    assert api.delete(f"{E}/{body['id']}").status_code == 204
    assert not Event.objects.filter(pk=body["id"]).exists()


def test_major_edit_by_new_account_returns_to_moderation(api, new_user, make_event, far_venue):
    event = make_event(new_user)
    api.force_authenticate(new_user)
    r = api.patch(f"{E}/{event.id}", {"description": "Petite correction de texte."}, format="json")
    assert r.json()["status"] == "PUBLISHED"
    r = api.patch(f"{E}/{event.id}", {"venue": far_venue.pk}, format="json")
    assert r.json()["status"] == "PENDING_REVIEW"


def test_cancel_confirm_stats_and_favorites(api, confirmed_user, other_user, make_event):
    event = make_event(confirmed_user)
    api.force_authenticate(other_user)
    assert api.post("/api/v1/me/favorites", {"event": event.slug}).status_code == 201
    assert api.post("/api/v1/me/favorites", {"event": event.slug}).status_code == 201  # idempotent
    assert [e["slug"] for e in api.get("/api/v1/me/favorites").json()["results"]] == [event.slug]
    api.force_authenticate(None)
    api.get(f"{E}/{event.slug}")
    api.get(f"{E}/{event.slug}/ics")
    api.force_authenticate(confirmed_user)
    stats = api.get(f"{E}/{event.id}/stats").json()
    assert stats == {**stats, "views": 1, "favorites": 1, "calendar_adds": 1}
    assert api.post(f"{E}/{event.id}/confirm").json()["last_confirmed_at"]
    r = api.post(f"{E}/{event.id}/cancel", {"reason": "Grève"})
    assert r.json()["status"] == "CANCELLED"
    api.force_authenticate(other_user)
    assert api.delete(f"/api/v1/me/favorites/{event.slug}").status_code == 204
    assert api.get("/api/v1/me/favorites").json()["results"] == []


def test_favorites_merge_on_login(api, other_user, confirmed_user, make_event):
    e1 = make_event(confirmed_user, title="Un")
    e2 = make_event(confirmed_user, title="Deux")
    make_event(confirmed_user, title="Brouillon", status=EventStatus.DRAFT)
    api.force_authenticate(other_user)
    r = api.post(
        "/api/v1/me/favorites",
        {"events": [e1.slug, e2.slug, "brouillon", "inconnu"]},
        format="json",
    )
    assert r.status_code == 200
    assert {e["slug"] for e in r.json()["results"]} == {e1.slug, e2.slug}


def test_organization_profile_claim_and_transfer(api, confirmed_user, other_user, moderator, db):
    from organizations.models import Organization

    page = Organization.objects.create(name="Lieu connu", slug="lieu-connu", is_claimable=True)
    assert api.get("/api/v1/organizations/lieu-connu").json()["is_claimable"] is True
    api.force_authenticate(other_user)
    r = api.post("/api/v1/organizations/lieu-connu/claim", {"evidence": "contact@lieu-connu.be"})
    assert r.status_code == 201
    assert (
        api.post("/api/v1/organizations/lieu-connu/claim", {"evidence": "encore"}).status_code
        == 409
    )
    claim_id = r.json()["id"]
    api.force_authenticate(moderator)
    assert len(api.get("/api/v1/admin/claims").json()["results"]) == 1
    r = api.post(
        f"/api/v1/admin/claims/{claim_id}/decide", {"approve": True, "note": "Domaine vérifié"}
    )
    assert r.status_code == 200 and r.json()["status"] == "APPROVED"
    page.refresh_from_db()
    assert page.is_owner(other_user) and page.is_claimable is False  # RG-27
    api.force_authenticate(other_user)
    assert api.get("/api/v1/organizations/lieu-connu").json()["role"] == "OWNER"
    # création d'organisation par un utilisateur vérifié
    r = api.post("/api/v1/organizations", {"name": "Nouveau collectif", "type": "COLLECTIVE"})
    assert (
        r.status_code == 201
        and r.json()["role"] == "OWNER"
        and r.json()["slug"] == "nouveau-collectif"
    )
