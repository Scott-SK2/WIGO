from datetime import timedelta

import pytest
from django.contrib.gis.geos import Point
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.test import APIClient

from accounts.models import User
from catalog.models import Area, AreaKind, Category, TicketingDomain, TicketingDomainStatus, Venue
from core.enums import TrustLevel
from events.models import Event, EventOccurrence, EventStatus, PricingType
from organizations.models import MemberRole, Organization, OrganizationMember


@pytest.fixture
def api():
    return APIClient()


def _user(email, **kw):
    kw.setdefault("email_verified_at", timezone.now())
    return User.objects.create_user(email=email, password="Secret-password-123", **kw)


@pytest.fixture
def new_user(db):
    return _user("new@test.be", trust_level=TrustLevel.NEW)


@pytest.fixture
def confirmed_user(db):
    return _user("confirmed@test.be", trust_level=TrustLevel.CONFIRMED)


@pytest.fixture
def other_user(db):
    return _user("other@test.be", trust_level=TrustLevel.CONFIRMED)


@pytest.fixture
def unverified_user(db):
    return _user("unverified@test.be", email_verified_at=None)


@pytest.fixture
def moderator(db):
    return _user("modo@test.be", is_moderator=True, is_staff=True)


@pytest.fixture
def admin(db):
    return User.objects.create_superuser(email="admin@test.be", password="Secret-password-123")


@pytest.fixture
def category(db):
    parent = Category.objects.create(
        slug="musique", name_fr="Musique", name_nl="Muziek", name_en="Music"
    )
    return Category.objects.create(slug="concerts", name_fr="Concerts", parent=parent)


@pytest.fixture
def other_category(db):
    return Category.objects.create(slug="expositions", name_fr="Expositions")


@pytest.fixture
def area(db):
    region = Area.objects.create(slug="bruxelles", kind=AreaKind.REGION, name_fr="Bruxelles")
    muni = Area.objects.create(
        slug="ixelles",
        kind=AreaKind.MUNICIPALITY,
        name_fr="Ixelles",
        parent=region,
        centroid=Point(4.3719, 50.8275, srid=4326),
    )
    Area.objects.create(
        slug="flagey",
        kind=AreaKind.NEIGHBOURHOOD,
        name_fr="Flagey",
        parent=muni,
        centroid=Point(4.3723, 50.8274, srid=4326),
    )
    Area.objects.create(
        slug="uccle",
        kind=AreaKind.MUNICIPALITY,
        name_fr="Uccle",
        parent=region,
        centroid=Point(4.3370, 50.8020, srid=4326),
    )
    return muni


@pytest.fixture
def venue(db, area):
    return Venue.objects.create(
        name="Flagey",
        slug="flagey",
        street="Place Sainte-Croix",
        postal_code="1050",
        city="Bruxelles",
        area=Area.objects.get(slug="flagey"),
        location=Point(4.3723, 50.8274, srid=4326),
        accessibility={
            "wheelchair": True,
            "adapted_toilets": True,
            "hearing_loop": None,
            "sign_language": None,
            "sensory_friendly": None,
            "notes": "",
        },
    )


@pytest.fixture
def far_venue(db, area):
    return Venue.objects.create(
        name="Salle Uccle",
        slug="salle-uccle",
        postal_code="1180",
        city="Bruxelles",
        area=Area.objects.get(slug="uccle"),
        location=Point(4.3370, 50.8020, srid=4326),
        accessibility={"wheelchair": False},
    )


@pytest.fixture
def ticketing_domains(db):
    TicketingDomain.objects.create(domain="eventbrite.be", status=TicketingDomainStatus.ALLOWLISTED)
    TicketingDomain.objects.create(domain="bit.ly", status=TicketingDomainStatus.BLOCKED)


@pytest.fixture
def organization(db, confirmed_user):
    org = Organization.objects.create(
        name="Collectif Test", slug="collectif-test", trust_level=TrustLevel.CONFIRMED
    )
    OrganizationMember.objects.create(organization=org, user=confirmed_user, role=MemberRole.OWNER)
    return org


@pytest.fixture
def make_event(db, category, venue):
    def _make(
        owner,
        *,
        title="Concert test",
        status=EventStatus.PUBLISHED,
        start_in_hours=24,
        duration_hours=2,
        occurrences=1,
        venue_=None,
        format_="ONSITE",
        pricing=PricingType.FREE,
        organization=None,
        **fields,
    ):
        v = venue_ if venue_ is not None else (None if format_ == "ONLINE" else venue)
        event = Event.objects.create(
            owner_user=owner,
            organization=organization,
            title=title,
            slug=fields.pop("slug", None) or slugify(title),
            description=fields.pop("description", "Description de test suffisante."),
            primary_category=category,
            format=format_,
            venue=v,
            pricing_type=pricing,
            status=status,
            online_url="https://example.org/live" if format_ != "ONSITE" else "",
            published_at=timezone.now() if status == EventStatus.PUBLISHED else None,
            **fields,
        )
        start = timezone.now() + timedelta(hours=start_in_hours)
        for i in range(occurrences):
            s = start + timedelta(days=i)
            EventOccurrence.objects.create(
                event=event, starts_at=s, ends_at=s + timedelta(hours=duration_hours)
            )
        return event

    return _make


@pytest.fixture
def auth(api):
    def _auth(user):
        api.force_authenticate(user)
        return api

    return _auth
