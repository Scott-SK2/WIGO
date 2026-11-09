"""Jeu de démonstration : comptes, organisations, lieux et ~30 événements autour d'aujourd'hui."""

import random
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.contrib.gis.geos import Point
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from accounts.models import User
from catalog.models import Area, Category, Tag, Venue
from core.enums import TrustLevel
from engagement.models import ImportSource, WeekendSelection, WeekendSelectionItem
from events import workflow
from events.models import AgePolicy, Event, EventFormat, EventOccurrence, EventStatus, PricingType
from organizations.models import (
    MemberRole,
    Organization,
    OrganizationMember,
    OrganizationType,
    VerificationStatus,
)

TZ = ZoneInfo("Europe/Brussels")

VENUES = [
    ("Ancienne Belgique", "Boulevard Anspach", "110", "1000", "grand-place", 50.8485, 4.3486, True),
    ("Botanique", "Rue Royale", "236", "1210", "saint-josse-ten-noode", 50.8546, 4.3661, True),
    ("Flagey", "Place Sainte-Croix", "", "1050", "flagey", 50.8274, 4.3723, True),
    ("Bozar", "Rue Ravenstein", "23", "1000", "grand-place", 50.8440, 4.3598, True),
    ("Fuse", "Rue Blaes", "208", "1000", "marolles", 50.8370, 4.3464, False),
    ("Recyclart", "Rue de Manchester", "13", "1080", "canal", 50.8505, 4.3330, True),
    (
        "La Tricoterie",
        "Rue Théodore Verhaegen",
        "158",
        "1060",
        "saint-gilles",
        50.8260,
        4.3390,
        True,
    ),
    ("WIELS", "Avenue Van Volxem", "354", "1190", "forest", 50.8233, 4.3253, True),
    ("Place Flagey (plein air)", "Place Flagey", "", "1050", "flagey", 50.8278, 4.3720, True),
    (
        "Parvis de Saint-Gilles (plein air)",
        "Parvis de Saint-Gilles",
        "",
        "1060",
        "parvis-saint-gilles",
        50.8300,
        4.3450,
        True,
    ),
    (
        "Théâtre National Wallonie-Bruxelles",
        "Boulevard Émile Jacqmain",
        "111",
        "1000",
        "bruxelles-ville",
        50.8545,
        4.3555,
        True,
    ),
    ("Cinéma Nova", "Rue d'Arenberg", "3", "1000", "grand-place", 50.8480, 4.3560, False),
    ("Beursschouwburg", "Rue Auguste Orts", "20", "1000", "dansaert", 50.8490, 4.3475, True),
    (
        "Halles de Schaerbeek",
        "Rue Royale-Sainte-Marie",
        "22",
        "1030",
        "schaerbeek",
        50.8650,
        4.3730,
        True,
    ),
]

ORGS = [
    (
        "Ancienne Belgique",
        OrganizationType.VENUE,
        TrustLevel.VERIFIED,
        VerificationStatus.VERIFIED,
        "https://www.abconcerts.be",
    ),
    (
        "Botanique",
        OrganizationType.VENUE,
        TrustLevel.VERIFIED,
        VerificationStatus.VERIFIED,
        "https://botanique.be",
    ),
    (
        "Collectif Nuit Brique",
        OrganizationType.COLLECTIVE,
        TrustLevel.CONFIRMED,
        VerificationStatus.UNVERIFIED,
        "",
    ),
    (
        "Comité de quartier Flagey",
        OrganizationType.ASSOCIATION,
        TrustLevel.CONFIRMED,
        VerificationStatus.UNVERIFIED,
        "",
    ),
    (
        "WIELS",
        OrganizationType.VENUE,
        TrustLevel.VERIFIED,
        VerificationStatus.VERIFIED,
        "https://www.wiels.org",
    ),
]

# (titre, catégorie, tags, lieu, org, jours depuis aujourd'hui, heure, durée h, prix (type, min, max), billetterie, âge, famille, langues, description)
EVENTS = [
    (
        "Concert : Les Voisins du Dessus",
        "concerts",
        ["rock"],
        "Ancienne Belgique",
        "Ancienne Belgique",
        0,
        20,
        3,
        ("PAID", 22, 28),
        "https://www.abconcerts.be/",
        "ALL",
        False,
        ["fr", "nl"],
        "Rock bruxellois en version électrique, première partie à 20h, concert à 21h.",
    ),
    (
        "Jazz Station Session",
        "concerts",
        ["jazz"],
        "Flagey",
        None,
        0,
        19,
        2,
        ("PAID", 12, 12),
        "https://www.flagey.be/",
        "ALL",
        False,
        ["fr", "nl", "en"],
        "Session jazz hebdomadaire avec trio invité. Bar ouvert dès 18h.",
    ),
    (
        "Nuit Brique : électro au Fuse",
        "soirees",
        ["electro", "queer"],
        "Fuse",
        "Collectif Nuit Brique",
        1,
        23,
        7,
        ("PAID", 15, 20),
        "https://shotgun.live/",
        "ADULTS_ONLY",
        False,
        ["fr", "en"],
        "Line-up 100 % belge, deux salles, vestiaire gratuit. Entrée interdite aux moins de 18 ans.",
    ),
    (
        "Marché bio de Flagey",
        "marches-brocantes",
        ["plein-air"],
        "Place Flagey (plein air)",
        "Comité de quartier Flagey",
        1,
        8,
        6,
        ("FREE", None, None),
        "",
        "ALL",
        True,
        ["fr", "nl"],
        "Producteurs locaux, fleurs, fromages, huîtres et cafés : le rendez-vous du samedi matin.",
    ),
    (
        "Brocante du Parvis",
        "marches-brocantes",
        ["brocante", "plein-air"],
        "Parvis de Saint-Gilles (plein air)",
        None,
        2,
        7,
        7,
        ("FREE", None, None),
        "",
        "ALL",
        True,
        ["fr"],
        "Brocante de quartier, plus de 80 exposants, bar du comité et animations pour les enfants.",
    ),
    (
        "Stand-up : Open Mic du mardi",
        "humour",
        ["stand-up", "en-anglais"],
        "La Tricoterie",
        None,
        2,
        20,
        2,
        ("PWYW", None, None),
        "",
        "MIN_AGE",
        False,
        ["en", "fr"],
        "Dix humoristes, cinq minutes chacun, en anglais et en français. Participation libre au chapeau.",
    ),
    (
        "Exposition : Lumières du canal",
        "expositions",
        ["vernissage"],
        "WIELS",
        "WIELS",
        -10,
        11,
        8,
        ("PAID", 10, 12),
        "https://www.wiels.org/",
        "ALL",
        True,
        ["fr", "nl", "en"],
        "Exposition collective sur les transformations du quartier du canal. Ouvert du mercredi au dimanche.",
    ),
    (
        "Ciné-club : Nuit du court métrage",
        "cinema",
        [],
        "Cinéma Nova",
        None,
        3,
        20,
        4,
        ("PAID", 5, 8),
        "",
        "ALL",
        False,
        ["fr", "nl", "en"],
        "Sélection de courts métrages belges sous-titrés, discussion avec les réalisateurs.",
    ),
    (
        "Théâtre : Les Fenêtres",
        "theatre",
        [],
        "Théâtre National Wallonie-Bruxelles",
        None,
        4,
        20,
        2,
        ("PAID", 18, 25),
        "https://www.theatrenational.be/",
        "MIN_AGE",
        False,
        ["fr"],
        "Création 2026, mise en scène collective. Surtitrage NL le vendredi.",
    ),
    (
        "Afterwork au Botanique",
        "soirees",
        ["afterwork"],
        "Botanique",
        "Botanique",
        4,
        18,
        4,
        ("FREE", None, None),
        "",
        "ALL",
        False,
        ["fr", "nl"],
        "DJ set dans la rotonde, bar et food-truck. Entrée libre.",
    ),
    (
        "Balade urbaine : Marolles cachées",
        "visites",
        ["plein-air"],
        "Parvis de Saint-Gilles (plein air)",
        None,
        5,
        14,
        2,
        ("FREE", None, None),
        "https://www.eventbrite.be/",
        "ALL",
        True,
        ["fr"],
        "Visite guidée gratuite sur inscription, départ du Parvis. Prévoir de bonnes chaussures.",
    ),
    (
        "Atelier sérigraphie",
        "ateliers",
        [],
        "Recyclart",
        None,
        5,
        14,
        3,
        ("PAID", 25, 25),
        "https://www.eventbrite.be/",
        "MIN_AGE",
        False,
        ["fr", "nl"],
        "Initiation à la sérigraphie sur textile. Matériel fourni, apportez un t-shirt.",
    ),
    (
        "Concert symphonique : Brahms",
        "concerts",
        ["classique"],
        "Bozar",
        None,
        6,
        20,
        2,
        ("PAID", 15, 60),
        "https://www.bozar.be/",
        "ALL",
        False,
        ["fr", "nl", "en"],
        "Symphonie n° 4 de Brahms par l'Orchestre national de Belgique.",
    ),
    (
        "Fête de quartier Flagey",
        "fetes-de-quartier",
        ["plein-air"],
        "Place Flagey (plein air)",
        "Comité de quartier Flagey",
        6,
        14,
        9,
        ("FREE", None, None),
        "",
        "ALL",
        True,
        ["fr", "nl"],
        "Concerts, jeux pour enfants, repas de quartier et bal populaire en soirée.",
    ),
    (
        "Soirée hip-hop : Block Party",
        "soirees",
        ["hip-hop"],
        "Halles de Schaerbeek",
        None,
        7,
        21,
        5,
        ("PAID", 10, 15),
        "https://shotgun.live/",
        "MIN_AGE",
        False,
        ["fr"],
        "Battle de danse, showcases et DJ. Dès 16 ans.",
    ),
    (
        "Rencontre littéraire : auteurs belges",
        "litterature",
        [],
        "Beursschouwburg",
        None,
        8,
        19,
        2,
        ("FREE", None, None),
        "",
        "ALL",
        False,
        ["nl", "fr"],
        "Lecture et discussion avec trois auteurs, suivie d'une séance de dédicaces.",
    ),
    (
        "Débat : la ville à 30 km/h, cinq ans après",
        "conferences",
        [],
        "La Tricoterie",
        None,
        9,
        19,
        2,
        ("FREE", None, None),
        "https://www.eventbrite.be/",
        "ALL",
        False,
        ["fr"],
        "Table ronde avec urbanistes et habitants. Entrée libre, inscription conseillée.",
    ),
    (
        "Yoga en plein air",
        "sport-bien-etre",
        ["plein-air"],
        "Place Flagey (plein air)",
        None,
        10,
        9,
        1,
        ("PWYW", None, None),
        "",
        "ALL",
        True,
        ["fr", "en"],
        "Séance tous niveaux, apportez votre tapis. Annulé en cas de pluie.",
    ),
    (
        "Spectacle jeune public : Le Nuage",
        "famille",
        [],
        "Théâtre National Wallonie-Bruxelles",
        None,
        11,
        15,
        1,
        ("PAID", 8, 8),
        "https://www.theatrenational.be/",
        "ALL",
        True,
        ["fr"],
        "Théâtre d'objets dès 4 ans, 50 minutes.",
    ),
    (
        "Festival Brique & Nuit (3 jours)",
        "festivals",
        ["electro", "rock"],
        "Recyclart",
        "Collectif Nuit Brique",
        14,
        18,
        8,
        ("PAID", 30, 55),
        "https://shotgun.live/",
        "MIN_AGE",
        False,
        ["fr", "nl", "en"],
        "Trois soirs, douze groupes, un seul lieu. Pass 3 jours ou billet par soirée.",
    ),
    (
        "Projection-débat en ligne : archives du canal",
        "cinema",
        [],
        None,
        "WIELS",
        3,
        19,
        2,
        ("FREE", None, None),
        "",
        "ALL",
        False,
        ["fr"],
        "Projection en ligne suivie d'un échange avec l'équipe curatoriale.",
    ),
    (
        "Danse : Corps en chantier",
        "danse",
        [],
        "Halles de Schaerbeek",
        None,
        12,
        20,
        1,
        ("PAID", 14, 20),
        "https://www.ticketmaster.be/",
        "ALL",
        False,
        ["fr", "nl"],
        "Pièce pour six danseurs, 70 minutes sans entracte.",
    ),
    (
        "Vernissage : Jeunes photographes",
        "expositions",
        ["vernissage"],
        "Beursschouwburg",
        None,
        2,
        18,
        3,
        ("FREE", None, None),
        "",
        "ALL",
        False,
        ["nl", "fr", "en"],
        "Ouverture de l'exposition, drink offert. Exposition visible jusqu'à fin de mois.",
    ),
    (
        "Dîner de quartier : cuisines du monde",
        "gastronomie",
        [],
        "La Tricoterie",
        None,
        8,
        19,
        3,
        ("PAID", 12, 18),
        "",
        "ALL",
        True,
        ["fr"],
        "Repas partagé préparé par des habitants, réservation à l'entrée.",
    ),
]


class Command(BaseCommand):
    help = "Charge un jeu de démonstration complet (appelle seed_reference)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset", action="store_true", help="Supprime les événements de démo existants"
        )

    def handle(self, *args, **options):
        random.seed(42)
        call_command("seed_reference")
        if options["reset"]:
            Event.objects.filter(source="INTERNAL").delete()

        admin, _ = User.objects.get_or_create(
            email="admin@wigo.local",
            defaults={
                "display_name": "Admin WIGO",
                "is_staff": True,
                "is_superuser": True,
                "is_moderator": True,
                "is_catalog_editor": True,
                "email_verified_at": timezone.now(),
                "trust_level": TrustLevel.VERIFIED,
            },
        )
        if not admin.has_usable_password():
            admin.set_password("wigo-admin-2026")
            admin.save()
        moderator, _ = User.objects.get_or_create(
            email="modo@wigo.local",
            defaults={
                "display_name": "Modération",
                "is_staff": True,
                "is_moderator": True,
                "email_verified_at": timezone.now(),
            },
        )
        if not moderator.has_usable_password():
            moderator.set_password("wigo-modo-2026")
            moderator.save()
        organizers = {}
        for email, name, trust in [
            ("orga.confirme@wigo.local", "Léa Dubois", TrustLevel.CONFIRMED),
            ("orga.nouveau@wigo.local", "Sam Peeters", TrustLevel.NEW),
        ]:
            u, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    "display_name": name,
                    "trust_level": trust,
                    "email_verified_at": timezone.now(),
                },
            )
            if not u.has_usable_password():
                u.set_password("wigo-demo-2026")
                u.save()
            organizers[trust] = u

        orgs = {}
        for name, otype, trust, verif, site in ORGS:
            org, created = Organization.objects.get_or_create(
                slug=slugify(name),
                defaults={
                    "name": name,
                    "type": otype,
                    "trust_level": trust,
                    "verification_status": verif,
                    "website": site,
                    "description": f"{name} — page créée par l'équipe WIGO.",
                    "is_claimable": verif != VerificationStatus.VERIFIED,
                    "created_by": admin,
                },
            )
            if created:
                OrganizationMember.objects.create(
                    organization=org, user=organizers[TrustLevel.CONFIRMED], role=MemberRole.OWNER
                )
            orgs[name] = org

        areas = {a.slug: a for a in Area.objects.all()}
        venues = {}
        for name, street, number, pc, area, lat, lon, wheelchair in VENUES:
            venues[name], _ = Venue.objects.get_or_create(
                slug=slugify(name),
                defaults={
                    "name": name,
                    "street": street,
                    "house_number": number,
                    "postal_code": pc,
                    "city": "Bruxelles",
                    "area": areas.get(area),
                    "location": Point(lon, lat, srid=4326),
                    "geocoded_at": timezone.now(),
                    "accessibility": {
                        "wheelchair": wheelchair,
                        "adapted_toilets": wheelchair,
                        "hearing_loop": None,
                        "sign_language": None,
                        "sensory_friendly": None,
                        "notes": "",
                    },
                    "created_by": admin,
                },
            )

        cats = {c.slug: c for c in Category.objects.all()}
        tags = {t.slug: t for t in Tag.objects.all()}
        today = timezone.now().astimezone(TZ).date()
        created = 0
        for (
            title,
            cat,
            tag_slugs,
            venue,
            org,
            day_offset,
            hour,
            duration,
            pricing,
            ticket,
            age,
            family,
            langs,
            desc,
        ) in EVENTS:
            slug = slugify(title)
            if Event.objects.filter(slug=slug).exists():
                continue
            organization = orgs.get(org) if org else None
            owner = (
                organizers[TrustLevel.CONFIRMED]
                if organization or random.random() > 0.15
                else organizers[TrustLevel.NEW]
            )
            fmt = EventFormat.ONLINE if venue is None else EventFormat.ONSITE
            ptype = {
                "FREE": PricingType.FREE,
                "PAID": PricingType.PAID,
                "PWYW": PricingType.PAY_WHAT_YOU_WANT,
            }[pricing[0]]
            event = Event.objects.create(
                slug=slug,
                title=title,
                description=desc,
                languages=langs,
                primary_category=cats[cat],
                format=fmt,
                venue=venues.get(venue),
                online_url="https://meet.jit.si/wigo-demo" if fmt == EventFormat.ONLINE else "",
                pricing_type=ptype,
                price_min=pricing[1],
                price_max=pricing[2],
                ticketing_url=ticket,
                registration_required=bool(ticket) and ptype == PricingType.FREE,
                age_policy=AgePolicy(age),
                min_age=16 if age == "MIN_AGE" else None,
                is_family_friendly=family,
                owner_user=owner,
                organization=organization,
                source="INTERNAL",
                draft_step=5,
            )
            event.tags.set([tags[t] for t in tag_slugs if t in tags])
            start_day = today + timedelta(days=day_offset)
            if "3 jours" in title:
                for d in range(3):
                    s = datetime.combine(start_day + timedelta(days=d), time(hour, 0), tzinfo=TZ)
                    EventOccurrence.objects.create(
                        event=event, starts_at=s, ends_at=s + timedelta(hours=duration)
                    )
            elif "Exposition" in title:
                s = datetime.combine(start_day, time(hour, 0), tzinfo=TZ)
                EventOccurrence.objects.create(
                    event=event, starts_at=s, ends_at=s + timedelta(days=60, hours=duration)
                )
            else:
                s = datetime.combine(start_day, time(hour, 0), tzinfo=TZ)
                EventOccurrence.objects.create(
                    event=event, starts_at=s, ends_at=s + timedelta(hours=duration)
                )
                if (
                    cat in ("theatre", "danse", "humour") and random.random() > 0.5
                ):  # séances multiples (RG-13)
                    s2 = s + timedelta(days=1)
                    EventOccurrence.objects.create(
                        event=event, starts_at=s2, ends_at=s2 + timedelta(hours=duration)
                    )
            workflow.submit(event, actor=admin)
            created += 1

        # Deux événements laissés en attente pour la file de modération
        pending = Event.objects.filter(status=EventStatus.PENDING_REVIEW).count()

        # Sélection du week-end
        week = WeekendSelection.week_start_for(today)
        selection, sel_created = WeekendSelection.objects.get_or_create(
            week_start=week,
            defaults={"title": "Ce week-end à Bruxelles", "editor": admin, "send_status": "READY"},
        )
        if sel_created:
            for order, ev in enumerate(
                Event.objects.filter(status=EventStatus.PUBLISHED).order_by("?")[:6]
            ):
                WeekendSelectionItem.objects.create(selection=selection, event=ev, order=order)
                ev.visibility = "FEATURED"
                ev.save(update_fields=["visibility"])

        ImportSource.objects.get_or_create(
            slug="uitdatabank",
            defaults={
                "name": "UiTdatabank (publiq)",
                "kind": "uitdatabank",
                "licence": "À confirmer avec publiq",
                "attribution": "Source : UiTdatabank",
                "is_active": False,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Démo : {created} événements créés ({Event.objects.filter(status='PUBLISHED').count()} publiés, {pending} en modération). "
                "Comptes : admin@wigo.local / wigo-admin-2026, modo@wigo.local / wigo-modo-2026, "
                "orga.confirme@wigo.local et orga.nouveau@wigo.local / wigo-demo-2026."
            )
        )
