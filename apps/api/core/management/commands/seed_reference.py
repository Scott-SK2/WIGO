"""
Données de référence (idempotent, utilisable en production) :
taxonomie FR/NL/EN, communes et quartiers de Bruxelles, liste blanche des billetteries.
"""

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand

from catalog.models import Area, AreaKind, Category, Tag, TicketingDomain, TicketingDomainStatus

# (slug, fr, nl, en, parent, icône, niche de lancement)
CATEGORIES = [
    ("musique", "Musique", "Muziek", "Music", None, "music", True),
    ("concerts", "Concerts", "Concerten", "Concerts", "musique", "mic", True),
    (
        "soirees",
        "Soirées & clubbing",
        "Feestjes & clubbing",
        "Parties & clubbing",
        "musique",
        "disc",
        True,
    ),
    ("festivals", "Festivals", "Festivals", "Festivals", "musique", "tent", True),
    (
        "arts-de-la-scene",
        "Arts de la scène",
        "Podiumkunsten",
        "Performing arts",
        None,
        "theater",
        True,
    ),
    ("theatre", "Théâtre", "Theater", "Theatre", "arts-de-la-scene", "drama", True),
    ("danse", "Danse", "Dans", "Dance", "arts-de-la-scene", "dance", True),
    (
        "humour",
        "Humour & stand-up",
        "Comedy & stand-up",
        "Comedy & stand-up",
        "arts-de-la-scene",
        "laugh",
        True,
    ),
    ("arts-visuels", "Arts visuels", "Beeldende kunst", "Visual arts", None, "palette", True),
    (
        "expositions",
        "Expositions",
        "Tentoonstellingen",
        "Exhibitions",
        "arts-visuels",
        "frame",
        True,
    ),
    ("cinema", "Cinéma", "Film", "Cinema", "arts-visuels", "film", True),
    ("vie-de-quartier", "Vie de quartier", "Buurtleven", "Neighbourhood life", None, "home", True),
    (
        "marches-brocantes",
        "Marchés & brocantes",
        "Markten & rommelmarkten",
        "Markets & flea markets",
        "vie-de-quartier",
        "basket",
        True,
    ),
    (
        "fetes-de-quartier",
        "Fêtes de quartier",
        "Buurtfeesten",
        "Street parties",
        "vie-de-quartier",
        "confetti",
        True,
    ),
    (
        "ateliers",
        "Ateliers & cours",
        "Workshops & cursussen",
        "Workshops & classes",
        "vie-de-quartier",
        "tools",
        False,
    ),
    (
        "decouverte",
        "Découverte & idées",
        "Ontdekken & ideeën",
        "Discovery & ideas",
        None,
        "compass",
        False,
    ),
    (
        "conferences",
        "Conférences & débats",
        "Lezingen & debatten",
        "Talks & debates",
        "decouverte",
        "speech",
        False,
    ),
    ("litterature", "Littérature", "Literatuur", "Literature", "decouverte", "book", False),
    (
        "visites",
        "Visites & patrimoine",
        "Bezoeken & erfgoed",
        "Tours & heritage",
        "decouverte",
        "landmark",
        False,
    ),
    ("gastronomie", "Food & drinks", "Food & drinks", "Food & drinks", None, "fork", False),
    ("famille", "En famille", "Met het gezin", "Family", None, "family", False),
    (
        "sport-bien-etre",
        "Sport & bien-être",
        "Sport & welzijn",
        "Sport & wellbeing",
        None,
        "heart",
        False,
    ),
]

TAGS = [
    ("plein-air", "Plein air", "Openlucht", "Open air"),
    ("jazz", "Jazz", "Jazz", "Jazz"),
    ("electro", "Électro", "Electro", "Electro"),
    ("rock", "Rock", "Rock", "Rock"),
    ("hip-hop", "Hip-hop", "Hiphop", "Hip-hop"),
    ("classique", "Classique", "Klassiek", "Classical"),
    ("vernissage", "Vernissage", "Vernissage", "Opening"),
    ("brocante", "Brocante", "Rommelmarkt", "Flea market"),
    ("queer", "Queer", "Queer", "Queer"),
    ("afterwork", "Afterwork", "Afterwork", "Afterwork"),
    ("stand-up", "Stand-up", "Stand-up", "Stand-up"),
    (
        "gratuit-sur-inscription",
        "Gratuit sur inscription",
        "Gratis op inschrijving",
        "Free with registration",
    ),
    ("accessible-pmr", "Accessible PMR", "Rolstoeltoegankelijk", "Wheelchair accessible"),
    ("en-anglais", "En anglais", "In het Engels", "In English"),
]

# (slug, fr, nl, codes postaux, lat, lon)
MUNICIPALITIES = [
    (
        "bruxelles-ville",
        "Bruxelles-Ville",
        "Brussel-Stad",
        ["1000", "1020", "1120", "1130"],
        50.8467,
        4.3525,
    ),
    ("schaerbeek", "Schaerbeek", "Schaarbeek", ["1030"], 50.8676, 4.3737),
    ("etterbeek", "Etterbeek", "Etterbeek", ["1040"], 50.8364, 4.3893),
    ("ixelles", "Ixelles", "Elsene", ["1050"], 50.8275, 4.3719),
    ("saint-gilles", "Saint-Gilles", "Sint-Gillis", ["1060"], 50.8266, 4.3454),
    ("anderlecht", "Anderlecht", "Anderlecht", ["1070"], 50.8365, 4.3129),
    (
        "molenbeek-saint-jean",
        "Molenbeek-Saint-Jean",
        "Sint-Jans-Molenbeek",
        ["1080"],
        50.8547,
        4.3386,
    ),
    ("koekelberg", "Koekelberg", "Koekelberg", ["1081"], 50.8625, 4.3261),
    (
        "berchem-sainte-agathe",
        "Berchem-Sainte-Agathe",
        "Sint-Agatha-Berchem",
        ["1082"],
        50.8637,
        4.2929,
    ),
    ("ganshoren", "Ganshoren", "Ganshoren", ["1083"], 50.8713, 4.3171),
    ("jette", "Jette", "Jette", ["1090"], 50.8777, 4.3264),
    ("evere", "Evere", "Evere", ["1140"], 50.8710, 4.4025),
    (
        "woluwe-saint-pierre",
        "Woluwe-Saint-Pierre",
        "Sint-Pieters-Woluwe",
        ["1150"],
        50.8367,
        4.4320,
    ),
    ("auderghem", "Auderghem", "Oudergem", ["1160"], 50.8155, 4.4267),
    (
        "watermael-boitsfort",
        "Watermael-Boitsfort",
        "Watermaal-Bosvoorde",
        ["1170"],
        50.7979,
        4.4155,
    ),
    ("uccle", "Uccle", "Ukkel", ["1180"], 50.8020, 4.3370),
    ("forest", "Forest", "Vorst", ["1190"], 50.8092, 4.3220),
    (
        "woluwe-saint-lambert",
        "Woluwe-Saint-Lambert",
        "Sint-Lambrechts-Woluwe",
        ["1200"],
        50.8468,
        4.4297,
    ),
    (
        "saint-josse-ten-noode",
        "Saint-Josse-ten-Noode",
        "Sint-Joost-ten-Node",
        ["1210"],
        50.8520,
        4.3700,
    ),
]

# (slug, fr, nl, en, commune, lat, lon)
NEIGHBOURHOODS = [
    ("dansaert", "Dansaert", "Dansaert", "Dansaert", "bruxelles-ville", 50.8505, 4.3450),
    ("marolles", "Marolles", "Marollen", "Marolles", "bruxelles-ville", 50.8375, 4.3470),
    ("sablon", "Sablon", "Zavel", "Sablon", "bruxelles-ville", 50.8410, 4.3560),
    (
        "grand-place",
        "Grand-Place & centre",
        "Grote Markt & centrum",
        "Grand-Place & centre",
        "bruxelles-ville",
        50.8467,
        4.3525,
    ),
    (
        "sainte-catherine",
        "Sainte-Catherine",
        "Sint-Katelijne",
        "Sainte-Catherine",
        "bruxelles-ville",
        50.8510,
        4.3480,
    ),
    ("laeken", "Laeken", "Laken", "Laeken", "bruxelles-ville", 50.8830, 4.3520),
    (
        "quartier-europeen",
        "Quartier européen",
        "Europese wijk",
        "European quarter",
        "bruxelles-ville",
        50.8430,
        4.3800,
    ),
    ("flagey", "Flagey", "Flagey", "Flagey", "ixelles", 50.8274, 4.3723),
    ("chatelain", "Châtelain", "Kastelein", "Châtelain", "ixelles", 50.8240, 4.3590),
    ("matonge", "Matongé", "Matonge", "Matonge", "ixelles", 50.8370, 4.3660),
    (
        "parvis-saint-gilles",
        "Parvis de Saint-Gilles",
        "Voorplein van Sint-Gillis",
        "Parvis de Saint-Gilles",
        "saint-gilles",
        50.8300,
        4.3450,
    ),
    (
        "place-jourdan",
        "Place Jourdan",
        "Jourdanplein",
        "Place Jourdan",
        "etterbeek",
        50.8390,
        4.3810,
    ),
    ("canal", "Canal", "Kanaal", "Canal", "molenbeek-saint-jean", 50.8560, 4.3410),
]

TICKETING_ALLOWLIST = [
    "eventbrite.be",
    "eventbrite.com",
    "eventbrite.fr",
    "ticketmaster.be",
    "shotgun.live",
    "weezevent.com",
    "billetweb.fr",
    "utick.be",
    "ticketmatic.com",
    "xing-events.com",
    "ancienne-belgique.be",
    "abconcerts.be",
    "botanique.be",
    "bozar.be",
    "flagey.be",
    "fuse.be",
    "kvs.be",
    "theatrenational.be",
    "wiels.org",
    "kaaitheater.be",
    "beursschouwburg.be",
    "lamonnaie.be",
    "demunt.be",
    "cinematek.be",
    "ticketing.brussels",
    "visit.brussels",
]
TICKETING_BLOCKED = ["bit.ly", "tinyurl.com", "t.co", "goo.gl", "cutt.ly"]


class Command(BaseCommand):
    help = (
        "Charge taxonomie, territoires de Bruxelles et liste blanche des billetteries (idempotent)."
    )

    def handle(self, *args, **options):
        by_slug = {}
        for slug, fr, nl, en, parent, icon, niche in CATEGORIES:
            cat, _ = Category.objects.update_or_create(
                slug=slug,
                defaults={
                    "name_fr": fr,
                    "name_nl": nl,
                    "name_en": en,
                    "icon": icon,
                    "is_launch_niche": niche,
                    "parent": by_slug.get(parent),
                    "order": len(by_slug),
                },
            )
            by_slug[slug] = cat
        for slug, fr, nl, en in TAGS:
            Tag.objects.update_or_create(
                slug=slug, defaults={"name_fr": fr, "name_nl": nl, "name_en": en}
            )

        region, _ = Area.objects.update_or_create(
            slug="bruxelles",
            defaults={
                "kind": AreaKind.REGION,
                "name_fr": "Région de Bruxelles-Capitale",
                "name_nl": "Brussels Hoofdstedelijk Gewest",
                "name_en": "Brussels-Capital Region",
                "centroid": Point(4.3525, 50.8467, srid=4326),
            },
        )
        munis = {}
        for order, (slug, fr, nl, codes, lat, lon) in enumerate(MUNICIPALITIES):
            munis[slug], _ = Area.objects.update_or_create(
                slug=slug,
                defaults={
                    "kind": AreaKind.MUNICIPALITY,
                    "name_fr": fr,
                    "name_nl": nl,
                    "name_en": fr,
                    "parent": region,
                    "postal_codes": codes,
                    "centroid": Point(lon, lat, srid=4326),
                    "order": order,
                },
            )
        for order, (slug, fr, nl, en, muni, lat, lon) in enumerate(NEIGHBOURHOODS):
            Area.objects.update_or_create(
                slug=slug,
                defaults={
                    "kind": AreaKind.NEIGHBOURHOOD,
                    "name_fr": fr,
                    "name_nl": nl,
                    "name_en": en,
                    "parent": munis[muni],
                    "centroid": Point(lon, lat, srid=4326),
                    "order": order,
                },
            )
        for domain in TICKETING_ALLOWLIST:
            TicketingDomain.objects.update_or_create(
                domain=domain, defaults={"status": TicketingDomainStatus.ALLOWLISTED}
            )
        for domain in TICKETING_BLOCKED:
            TicketingDomain.objects.update_or_create(
                domain=domain,
                defaults={"status": TicketingDomainStatus.BLOCKED, "note": "Raccourcisseur d'URL"},
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Référentiel chargé : {Category.objects.count()} catégories, {Tag.objects.count()} tags, "
                f"{Area.objects.count()} territoires, {TicketingDomain.objects.count()} domaines."
            )
        )
