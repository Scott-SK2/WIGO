"""SRC-01 à SRC-06, UI-06 : recherche publique, filtres, tri, ICS, visibilité (RG-05, RG-07, RG-23, RG-24)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from events.models import EventStatus, PricingType

pytestmark = pytest.mark.django_db
URL = "/api/v1/events"


def titles(response):
    return [r["title"] for r in response.json()["results"]]


def test_only_published_and_not_finished_are_listed(api, make_event, confirmed_user):
    make_event(confirmed_user, title="Publié")
    make_event(confirmed_user, title="Brouillon", status=EventStatus.DRAFT)
    make_event(confirmed_user, title="En attente", status=EventStatus.PENDING_REVIEW)
    make_event(confirmed_user, title="Terminé", start_in_hours=-30)
    make_event(confirmed_user, title="Annulé", status=EventStatus.CANCELLED)
    r = api.get(URL)
    assert r.status_code == 200
    assert titles(r) == ["Publié"]


def test_today_includes_ongoing_long_event_after_punctual_ones(api, make_event, confirmed_user):
    make_event(confirmed_user, title="Expo longue", start_in_hours=-24 * 10, duration_hours=24 * 60)
    make_event(confirmed_user, title="Concert ce soir", start_in_hours=1)
    make_event(confirmed_user, title="Concert demain", start_in_hours=30)
    r = api.get(URL, {"date": "today"})
    got = titles(r)
    assert "Concert demain" not in got
    assert got[0] == "Concert ce soir" and got[-1] == "Expo longue"
    long_item = next(x for x in r.json()["results"] if x["title"] == "Expo longue")
    assert long_item["is_long"] is True


def test_online_events_excluded_by_default_and_from_radius(api, make_event, confirmed_user):
    make_event(confirmed_user, title="Webinaire", format_="ONLINE")
    make_event(confirmed_user, title="Sur place")
    assert titles(api.get(URL)) == ["Sur place"]
    assert set(titles(api.get(URL, {"include_online": "1"}))) == {"Sur place", "Webinaire"}
    assert titles(api.get(URL, {"format": "ONLINE"})) == ["Webinaire"]
    r = api.get(URL, {"lat": 50.8274, "lon": 4.3723, "radius_km": 2, "include_online": "1"})
    assert titles(r) == ["Sur place"]


def test_area_filter_includes_children(api, make_event, confirmed_user, far_venue):
    make_event(confirmed_user, title="À Flagey")
    make_event(confirmed_user, title="À Uccle", venue_=far_venue)
    assert titles(api.get(URL, {"area": "ixelles"})) == ["À Flagey"]
    assert titles(api.get(URL, {"area": "flagey"})) == ["À Flagey"]
    assert set(titles(api.get(URL, {"area": "bruxelles"}))) == {"À Flagey", "À Uccle"}
    assert api.get(URL, {"area": "nowhere"}).status_code == 400


def test_category_filter_follows_hierarchy(api, make_event, confirmed_user, other_category):
    make_event(confirmed_user, title="Concert")
    expo = make_event(confirmed_user, title="Expo")
    expo.primary_category = other_category
    expo.save()
    assert titles(api.get(URL, {"category": "musique"})) == ["Concert"]
    assert titles(api.get(URL, {"category": "concerts"})) == ["Concert"]
    assert titles(api.get(URL, {"category": "expositions"})) == ["Expo"]


def test_price_filters(api, make_event, confirmed_user):
    make_event(confirmed_user, title="Gratuit")
    make_event(
        confirmed_user, title="Payant 25", pricing=PricingType.PAID, price_min=25, price_max=30
    )
    make_event(confirmed_user, title="Payant 8", pricing=PricingType.PAID, price_min=8)
    assert titles(api.get(URL, {"free": "1"})) == ["Gratuit"]
    assert set(titles(api.get(URL, {"max_price": "10"}))) == {"Gratuit", "Payant 8"}
    assert set(titles(api.get(URL, {"paid": "1"}))) == {"Payant 25", "Payant 8"}


def test_distance_sort_and_radius(api, make_event, confirmed_user, far_venue):
    make_event(confirmed_user, title="Loin", venue_=far_venue, start_in_hours=2)
    make_event(confirmed_user, title="Près", start_in_hours=5)
    r = api.get(URL, {"lat": 50.8274, "lon": 4.3723, "sort": "distance"})
    assert titles(r) == ["Près", "Loin"]
    assert r.json()["results"][0]["distance_km"] == 0
    assert titles(api.get(URL, {"lat": 50.8274, "lon": 4.3723, "radius_km": 1})) == ["Près"]
    assert api.get(URL, {"sort": "distance"}).status_code == 400


def test_accent_insensitive_prefix_search(api, make_event, confirmed_user):
    make_event(confirmed_user, title="Marché bio de Flagey", description="Producteurs locaux")
    make_event(confirmed_user, title="Soirée électro")
    assert titles(api.get(URL, {"q": "marche"})) == ["Marché bio de Flagey"]
    assert titles(api.get(URL, {"q": "ÉLEC"})) == ["Soirée électro"]
    assert titles(api.get(URL, {"q": "producteur"})) == ["Marché bio de Flagey"]
    assert titles(api.get(URL, {"q": "zzzz"})) == []


def test_accessible_family_lang_filters(api, make_event, confirmed_user, far_venue):
    make_event(
        confirmed_user, title="Accessible famille", is_family_friendly=True, languages=["fr", "nl"]
    )
    make_event(confirmed_user, title="Autre", venue_=far_venue, languages=["en"])
    assert titles(api.get(URL, {"accessible": "1"})) == ["Accessible famille"]
    assert titles(api.get(URL, {"family": "true"})) == ["Accessible famille"]
    assert titles(api.get(URL, {"lang": "en"})) == ["Autre"]


def test_cursor_pagination_is_stable(api, make_event, confirmed_user):
    for i in range(5):
        make_event(confirmed_user, title=f"E{i}", start_in_hours=10 + i)
    r1 = api.get(URL, {"page_size": 2})
    assert titles(r1) == ["E0", "E1"] and r1.json()["next"]
    r2 = api.get(r1.json()["next"])
    assert titles(r2) == ["E2", "E3"]
    r3 = api.get(r2.json()["next"])
    assert titles(r3) == ["E4"] and r3.json()["next"] is None


def test_detail_visibility_rules(api, make_event, confirmed_user, other_user, auth):
    pending = make_event(confirmed_user, title="Pending", status=EventStatus.PENDING_REVIEW)
    cancelled = make_event(confirmed_user, title="Cancelled", status=EventStatus.CANCELLED)
    assert api.get(f"{URL}/{pending.slug}").status_code == 404  # RG-05, pas de fuite
    assert api.get(f"{URL}/{cancelled.slug}").status_code == 200  # RG-12
    assert api.get(f"{URL}/{cancelled.slug}").json()["status"] == "CANCELLED"
    auth(other_user)
    assert api.get(f"{URL}/{pending.slug}").status_code == 403
    auth(confirmed_user)
    assert api.get(f"{URL}/{pending.slug}").status_code == 200


def test_detail_payload_and_view_counter(api, make_event, confirmed_user):
    event = make_event(
        confirmed_user,
        ticketing_url="https://www.eventbrite.be/e/1",
        pricing=PricingType.PAID,
        price_min=10,
    )
    r = api.get(f"{URL}/{event.slug}")
    body = r.json()
    assert body["ticketing"]["external"] is True  # RG-17
    assert body["venue"]["location"]["lat"] == pytest.approx(50.8274)
    assert body["accessibility"]["wheelchair"] is True
    assert body["urls"]["canonical"].endswith(f"/fr/evenements/{event.slug}")
    assert event.daily_stats.get().views == 1


def test_ics_export(api, make_event, confirmed_user):
    event = make_event(confirmed_user, title="Concert, virgule; point-virgule", occurrences=2)
    r = api.get(f"{URL}/{event.slug}/ics")
    assert r.status_code == 200
    assert r["Content-Type"].startswith("text/calendar")
    body = r.content.decode()
    assert body.count("BEGIN:VEVENT") == 2
    assert "SUMMARY:Concert\\, virgule\\; point-virgule" in body
    assert "LOCATION:Flagey" in body
    assert body.endswith("END:VCALENDAR\r\n")


def test_invalid_params_return_400(api, db):
    assert api.get(URL, {"date": "foo"}).status_code == 400
    assert api.get(URL, {"sort": "foo"}).status_code == 400
    assert api.get(URL, {"format": "TV"}).status_code == 400


def test_weekend_preset_covers_friday_evening_to_sunday(api, make_event, confirmed_user):
    from events.search import BRUSSELS, resolve_date_range

    now = timezone.now()
    start, end = resolve_date_range({"date": "weekend"}, now)
    assert start >= now and end > start
    assert end.astimezone(BRUSSELS).weekday() == 6
    assert (end - start) < timedelta(days=8)
