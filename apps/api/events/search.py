"""
Recherche et filtres (§5.1, SRC-01 à SRC-06).
Paramètres documentés : q, area, date, date_from, date_to, after, category, free, paid, max_price,
lang, format, include_online, accessible, family, radius_km, lat, lon, sort, cursor.
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import Case, Exists, F, IntegerField, OuterRef, Q, Value, When
from django.db.models.functions import ExtractHour
from django.utils import timezone

from catalog.models import Area, Category

from .models import Event, EventFormat, EventOccurrence, OccurrenceStatus, PricingType

BRUSSELS = ZoneInfo(settings.WIGO_DEFAULT_TIMEZONE)
SEARCH_CONFIG = "wigo_simple"
ACTIVE_OCC = [OccurrenceStatus.SCHEDULED, OccurrenceStatus.SOLD_OUT, OccurrenceStatus.POSTPONED]


class SearchParamsError(ValueError):
    pass


def _truthy(v: str | None) -> bool:
    return str(v).lower() in {"1", "true", "yes", "on"}


def local_day_range(day: date, tz=BRUSSELS) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=tz)
    end = datetime.combine(day, time.max, tzinfo=tz)
    return start, end


def resolve_date_range(params, now: datetime) -> tuple[datetime | None, datetime | None]:
    """Ce soir / Demain / Ce week-end / date précise / plage."""
    today = now.astimezone(BRUSSELS).date()
    preset = (params.get("date") or "").lower()
    if preset in ("today", "tonight", "ce-soir", "aujourd-hui"):
        s, e = local_day_range(today)
        return max(s, now), e
    if preset in ("tomorrow", "demain"):
        return local_day_range(today + timedelta(days=1))
    if preset in ("weekend", "ce-week-end"):
        # vendredi 17h -> dimanche 23h59 ; si on est déjà dans le week-end, on part de maintenant
        days_to_friday = (4 - today.weekday()) % 7
        friday = today + timedelta(days=days_to_friday)
        if today.weekday() in (5, 6):
            friday = today - timedelta(days=today.weekday() - 4)
        start = datetime.combine(friday, time(17, 0), tzinfo=BRUSSELS)
        end = local_day_range(friday + timedelta(days=2))[1]
        return max(start, now), end
    if preset:
        try:
            return local_day_range(date.fromisoformat(preset))
        except ValueError:
            raise SearchParamsError(
                "Paramètre date invalide (today, tomorrow, weekend ou AAAA-MM-JJ)."
            )
    start = end = None
    if params.get("date_from"):
        try:
            start = local_day_range(date.fromisoformat(params["date_from"]))[0]
        except ValueError:
            raise SearchParamsError("date_from invalide.")
    if params.get("date_to"):
        try:
            end = local_day_range(date.fromisoformat(params["date_to"]))[1]
        except ValueError:
            raise SearchParamsError("date_to invalide.")
    return start, end


def build_search_query(q: str) -> SearchQuery:
    """Recherche par préfixe sur chaque terme (« jaz » trouve « jazz »), sans accents ni casse."""
    terms = [t for t in re.split(r"[^\w]+", q, flags=re.UNICODE) if t]
    if not terms:
        return SearchQuery(q, config=SEARCH_CONFIG, search_type="websearch")
    raw = " & ".join(f"'{t.replace(chr(39), '')}':*" for t in terms[:8])
    return SearchQuery(raw, config=SEARCH_CONFIG, search_type="raw")


def _occurrence_exists(**filters):
    return Exists(
        EventOccurrence.objects.filter(event=OuterRef("pk"), status__in=ACTIVE_OCC, **filters)
    )


def apply_filters(qs, params, now: datetime | None = None):
    """Applique les filtres à un queryset déjà `public()` (annoté). Retourne (qs, ordering)."""
    now = now or timezone.now()

    # --- texte (SRC-02) ---
    q = (params.get("q") or "").strip()
    if q:
        query = build_search_query(q)
        qs = qs.annotate(rank=SearchRank(F("search_vector"), query)).filter(search_vector=query)

    # --- territoire (SRC-05) ---
    area_slug = params.get("area")
    if area_slug:
        area = Area.objects.filter(slug=area_slug, is_active=True).first()
        if area is None:
            raise SearchParamsError("Quartier ou commune inconnu.")
        qs = qs.filter(venue__area_id__in=area.self_and_descendant_ids())

    # --- dates et heures (SRC-03) ---
    start, end = resolve_date_range(params, now)
    if start or end:
        f = {}
        if start:
            f["ends_at__gte"] = start
        if end:
            f["starts_at__lte"] = end
        qs = qs.filter(_occurrence_exists(**f))
    after = params.get("after")
    if after:
        try:
            hour = int(after.split(":")[0])
        except ValueError:
            raise SearchParamsError("after doit être une heure (ex. 18 ou 18:00).")
        qs = qs.filter(
            Exists(
                EventOccurrence.objects.filter(
                    event=OuterRef("pk"), status__in=ACTIVE_OCC, ends_at__gte=now
                )
                .annotate(h=ExtractHour("starts_at", tzinfo=BRUSSELS))
                .filter(h__gte=hour)
            )
        )

    # --- catégorie, prix, langue, format, accessibilité, famille (SRC-04) ---
    cat_slug = params.get("category")
    if cat_slug:
        cat = Category.objects.filter(slug=cat_slug, is_active=True).first()
        if cat is None:
            raise SearchParamsError("Catégorie inconnue.")
        ids = cat.descendant_ids()
        through = Event.secondary_categories.through
        qs = qs.filter(
            Q(primary_category_id__in=ids)
            | Exists(through.objects.filter(event_id=OuterRef("pk"), category_id__in=ids))
        )
    if _truthy(params.get("free")):
        qs = qs.filter(pricing_type__in=[PricingType.FREE, PricingType.PAY_WHAT_YOU_WANT])
    if _truthy(params.get("paid")):
        qs = qs.filter(pricing_type=PricingType.PAID)
    if params.get("max_price"):
        try:
            max_price = float(params["max_price"])
        except ValueError:
            raise SearchParamsError("max_price invalide.")
        qs = qs.filter(
            Q(pricing_type__in=[PricingType.FREE, PricingType.PAY_WHAT_YOU_WANT])
            | Q(price_min__lte=max_price)
        )
    if params.get("lang"):
        qs = qs.filter(languages__contains=[params["lang"]])
    fmt = (params.get("format") or "").upper()
    if fmt:
        if fmt not in EventFormat.values:
            raise SearchParamsError("format invalide (ONSITE, ONLINE, HYBRID).")
        qs = qs.filter(format=fmt)
    elif not _truthy(params.get("include_online")):
        qs = qs.exclude(format=EventFormat.ONLINE)  # RG-24
    if _truthy(params.get("accessible")):
        qs = qs.filter(venue__accessibility__wheelchair=True)
    if _truthy(params.get("family")):
        qs = qs.filter(is_family_friendly=True)

    # --- rayon et distance (SRC-05, RG-24) ---
    point = None
    if params.get("lat") and params.get("lon"):
        try:
            point = Point(float(params["lon"]), float(params["lat"]), srid=4326)
        except ValueError:
            raise SearchParamsError("lat / lon invalides.")
        qs = qs.annotate(distance=Distance("venue__location", point))
        if params.get("radius_km"):
            try:
                radius = float(params["radius_km"])
            except ValueError:
                raise SearchParamsError("radius_km invalide.")
            qs = qs.exclude(format=EventFormat.ONLINE).filter(
                venue__location__dwithin=(point, D(km=radius))
            )

    # --- tri (SRC-06) : ponctuels avant les événements longs (RG-23) ---
    qs = qs.annotate(
        long_group=Case(
            When(is_long=True, then=Value(1)), default=Value(0), output_field=IntegerField()
        )
    )
    sort = params.get("sort") or ("relevance" if q else "date")
    if sort == "relevance" and q:
        ordering = ("-rank", "next_start", "id")
    elif sort == "distance":
        if point is None:
            raise SearchParamsError("Le tri par distance requiert lat et lon.")
        ordering = ("distance", "next_start", "id")
    elif sort in ("date", "relevance"):
        ordering = ("long_group", "next_start", "id")
    else:
        raise SearchParamsError("sort invalide (relevance, date, distance).")
    return qs, ordering


def refresh_search_vector(event: Event) -> None:
    """Met à jour le vecteur de recherche (titre A, tags/organisateur/lieu B, description C)."""
    tags = " ".join(f"{t.name_fr} {t.name_nl} {t.name_en}" for t in event.tags.all())
    venue = event.venue.name if event.venue_id else ""
    cat = event.primary_category
    secondary = f"{cat.name_fr} {cat.name_nl} {cat.name_en} {event.organizer_name} {venue} {tags}"
    vector = (
        SearchVector(Value(event.title), weight="A", config=SEARCH_CONFIG)
        + SearchVector(Value(secondary), weight="B", config=SEARCH_CONFIG)
        + SearchVector(Value(event.description[:20000]), weight="C", config=SEARCH_CONFIG)
    )
    Event.objects.filter(pk=event.pk).update(search_vector=vector)
