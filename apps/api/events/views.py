from django.db.models import Count, Sum
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.audit import log_action
from core.pagination import CursorPagination
from core.permissions import HasVerifiedEmail
from core.throttles import SubmitThrottle

from . import ics, workflow
from .models import Event, EventDailyStat, EventMedia, EventStatus, Favorite
from .search import SearchParamsError, apply_filters
from .serializers import (
    DecisionSerializer,
    EventCardSerializer,
    EventDetailSerializer,
    EventOwnerSerializer,
    EventWriteSerializer,
    FavoriteMergeSerializer,
    FavoriteWriteSerializer,
    MediaSerializer,
    MediaUploadSerializer,
    StatsSerializer,
)

SEARCH_PARAMS = [
    OpenApiParameter(
        "q", str, description="Recherche texte (titre, description, tags, organisateur, lieu)"
    ),
    OpenApiParameter("area", str, description="Slug de commune ou de quartier"),
    OpenApiParameter("date", str, description="today | tomorrow | weekend | AAAA-MM-JJ"),
    OpenApiParameter("date_from", str),
    OpenApiParameter("date_to", str),
    OpenApiParameter("after", str, description="Heure de début minimale (ex. 18)"),
    OpenApiParameter("category", str, description="Slug de catégorie (inclut les sous-catégories)"),
    OpenApiParameter("free", bool),
    OpenApiParameter("paid", bool),
    OpenApiParameter("max_price", float),
    OpenApiParameter("lang", str, description="fr | nl | en"),
    OpenApiParameter("format", str, description="ONSITE | ONLINE | HYBRID"),
    OpenApiParameter(
        "include_online", bool, description="Inclure les événements en ligne (défaut : non)"
    ),
    OpenApiParameter("accessible", bool, description="Accès PMR"),
    OpenApiParameter("family", bool, description="En famille"),
    OpenApiParameter("lat", float),
    OpenApiParameter("lon", float),
    OpenApiParameter("radius_km", float),
    OpenApiParameter("sort", str, description="relevance | date | distance"),
    OpenApiParameter("cursor", str),
    OpenApiParameter("page_size", int),
]


class EventSearchPagination(CursorPagination):
    def get_ordering(self, request, queryset, view):
        return getattr(view, "current_ordering", ("next_start", "id"))


def _public_queryset(now=None):
    return (
        Event.objects.public(now)
        .select_related("primary_category", "venue__area", "organization", "owner_user")
        .prefetch_related("media")
    )


class EventPublicViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v1/events            recherche et liste paginée (SRC-01)
    GET /api/v1/events/{slug}     fiche publique
    GET /api/v1/events/{slug}/ics export calendrier
    """

    permission_classes = [permissions.AllowAny]
    pagination_class = EventSearchPagination
    lookup_field = "slug"
    lookup_value_regex = r"[a-z0-9][a-z0-9-]*"
    serializer_class = EventCardSerializer

    def get_queryset(self):
        return _public_queryset()

    @extend_schema(parameters=SEARCH_PARAMS, responses={200: EventCardSerializer(many=True)})
    def list(self, request, *args, **kwargs):
        try:
            qs, ordering = apply_filters(self.get_queryset(), request.query_params)
        except SearchParamsError as exc:
            raise ValidationError({"detail": str(exc)})
        self.current_ordering = ordering
        page = self.paginate_queryset(qs)
        data = EventCardSerializer(page, many=True, context={"request": request}).data
        return self.get_paginated_response(data)

    def get_object(self):
        event = get_object_or_404(
            Event.objects.with_schedule()
            .select_related("primary_category", "venue__area", "organization", "owner_user")
            .prefetch_related("media", "occurrences", "tags", "secondary_categories"),
            slug=self.kwargs["slug"],
        )
        # RG-05 : non approuvé = invisible, sauf pour l'organisateur et la modération.
        # RG-12 : annulé reste visible ; archivé reste visible (historique) mais signalé.
        if event.status in (EventStatus.PUBLISHED, EventStatus.CANCELLED, EventStatus.ARCHIVED):
            return event
        if event.can_edit(self.request.user):
            return event
        if self.request.user.is_authenticated:
            raise PermissionDenied("Cet événement n'est pas publié.")
        raise Http404

    @extend_schema(responses={200: EventDetailSerializer})
    def retrieve(self, request, *args, **kwargs):
        event = self.get_object()
        if event.status == EventStatus.PUBLISHED and not event.can_edit(request.user):
            EventDailyStat.bump(event, "views")
        return Response(EventDetailSerializer(event, context={"request": request}).data)

    @extend_schema(responses={(200, "text/calendar"): OpenApiTypes.STR})
    @action(detail=True, methods=["get"], url_path="ics")
    def calendar(self, request, slug=None):
        event = self.get_object()
        EventDailyStat.bump(event, "calendar_adds")
        body = ics.event_to_ics(event, ics.public_event_url(event, request.GET.get("lang", "fr")))
        response = HttpResponse(body, content_type="text/calendar; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="wigo-{event.slug}.ics"'
        return response

    @extend_schema(request=None, responses={302: None})
    @action(detail=True, methods=["get"], url_path="out")
    def ticketing_redirect(self, request, slug=None):
        """Compte les clics billetterie (RG-17 : un clic n'est pas une vente) puis redirige."""
        event = self.get_object()
        if not event.ticketing_url:
            return Response(status=status.HTTP_404_NOT_FOUND)
        EventDailyStat.bump(event, "ticket_clicks")
        from django.http import HttpResponseRedirect

        return HttpResponseRedirect(event.ticketing_url)


class EventManageViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    POST   /api/v1/events                brouillon (RG-02 : e-mail vérifié)
    GET    /api/v1/events/mine           mes événements (tous statuts)
    GET    /api/v1/events/{id}           vue organisateur
    PATCH  /api/v1/events/{id}           édition (RG-11 pour les modifications importantes)
    DELETE /api/v1/events/{id}           suppression d'un brouillon
    POST   /api/v1/events/{id}/submit | /cancel | /confirm
    GET    /api/v1/events/{id}/stats
    POST   /api/v1/events/{id}/media     upload d'un visuel ; DELETE /media/{media_id}
    """

    permission_classes = [permissions.IsAuthenticated, HasVerifiedEmail]
    lookup_field = "id"
    lookup_value_regex = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.action in ("create", "partial_update", "update"):
            return EventWriteSerializer
        return EventOwnerSerializer

    def get_queryset(self):
        qs = (
            Event.objects.with_schedule()
            .select_related("primary_category", "venue__area", "organization", "owner_user")
            .prefetch_related("media", "occurrences", "tags", "secondary_categories")
        )
        user = self.request.user
        if self.action == "mine" or not (user.is_moderator or user.is_superuser):
            from django.db.models import Q

            qs = qs.filter(Q(owner_user=user) | Q(organization__members__user=user)).distinct()
        return qs

    def _check_edit(self, event):
        if not event.can_edit(self.request.user):
            raise PermissionDenied("Vous n'avez pas les droits sur cet événement.")

    @extend_schema(responses={200: EventOwnerSerializer(many=True)})
    @action(detail=False, methods=["get"])
    def mine(self, request):
        qs = self.get_queryset().order_by("-updated_at")
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        page = self.paginate_queryset(qs)
        data = EventOwnerSerializer(page, many=True, context={"request": request}).data
        return self.get_paginated_response(data)

    def create(self, request, *args, **kwargs):
        s = EventWriteSerializer(data=request.data, context={"request": request})
        s.is_valid(raise_exception=True)
        event = s.save()
        log_action(request.user, "event.create", event, after={"title": event.title})
        event = self.get_queryset().get(pk=event.pk)
        return Response(
            EventOwnerSerializer(event, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        event = self.get_object()
        self._check_edit(event)
        return Response(EventOwnerSerializer(event, context={"request": request}).data)

    def partial_update(self, request, *args, **kwargs):
        event = self.get_object()
        self._check_edit(event)
        if event.status == EventStatus.ARCHIVED:
            raise PermissionDenied("Un événement archivé ne peut plus être modifié.")
        before = self._snapshot(event)
        s = EventWriteSerializer(
            event, data=request.data, partial=True, context={"request": request}
        )
        s.is_valid(raise_exception=True)
        event = s.save()
        after = self._snapshot(event)
        log_action(request.user, "event.update", event, after={"fields": list(request.data.keys())})
        workflow.after_edit(event, request.user, before, after)
        event = self.get_queryset().get(pk=event.pk)
        return Response(EventOwnerSerializer(event, context={"request": request}).data)

    def destroy(self, request, *args, **kwargs):
        event = self.get_object()
        self._check_edit(event)
        if event.status != EventStatus.DRAFT:
            raise PermissionDenied(
                "Seul un brouillon peut être supprimé ; annulez l'événement sinon."
            )
        log_action(request.user, "event.delete_draft", event, before={"title": event.title})
        event.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def _snapshot(event) -> dict:
        return {
            "venue_id": event.venue_id,
            "ticketing_url": event.ticketing_url,
            "primary_category_id": event.primary_category_id,
            "age_policy": event.age_policy,
            "pricing_type": event.pricing_type,
            "format": event.format,
            "occurrences": sorted(
                (o.starts_at, o.ends_at) for o in event.occurrences.all() if o.status != "CANCELLED"
            ),
        }

    def _transition(self, request, fn, **kwargs):
        event = self.get_object()
        self._check_edit(event)
        event = fn(event, request.user, **kwargs)
        event = self.get_queryset().get(pk=event.pk)
        return Response(EventOwnerSerializer(event, context={"request": request}).data)

    @extend_schema(request=None, responses={200: EventOwnerSerializer})
    @action(detail=True, methods=["post"], throttle_classes=[SubmitThrottle])
    def submit(self, request, id=None):
        return self._transition(request, workflow.submit)

    @extend_schema(request=DecisionSerializer, responses={200: EventOwnerSerializer})
    @action(detail=True, methods=["post"])
    def cancel(self, request, id=None):
        s = DecisionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        response = self._transition(
            request, workflow.cancel, reason=s.validated_data.get("reason", "")
        )
        from .tasks import notify_favorites_of_cancellation

        notify_favorites_of_cancellation.delay(str(id))
        return response

    @extend_schema(request=None, responses={200: EventOwnerSerializer})
    @action(detail=True, methods=["post"])
    def confirm(self, request, id=None):
        return self._transition(request, workflow.confirm_freshness)

    @extend_schema(request=None, responses={200: EventOwnerSerializer})
    @action(detail=True, methods=["post"], url_path="back-to-draft")
    def back_to_draft(self, request, id=None):
        return self._transition(request, workflow.back_to_draft)

    @extend_schema(responses={200: StatsSerializer})
    @action(detail=True, methods=["get"])
    def stats(self, request, id=None):
        event = self.get_object()
        self._check_edit(event)
        rows = event.daily_stats.order_by("date")
        totals = rows.aggregate(
            views=Sum("views"),
            ticket_clicks=Sum("ticket_clicks"),
            calendar_adds=Sum("calendar_adds"),
            shares=Sum("shares"),
        )
        data = {
            "views": totals["views"] or 0,
            "ticket_clicks": totals["ticket_clicks"] or 0,
            "favorites": event.favorites.count(),
            "calendar_adds": totals["calendar_adds"] or 0,
            "shares": totals["shares"] or 0,
            "per_day": [
                {
                    "date": r.date.isoformat(),
                    "views": r.views,
                    "ticket_clicks": r.ticket_clicks,
                    "favorites_added": r.favorites_added,
                    "calendar_adds": r.calendar_adds,
                }
                for r in rows
            ],
        }
        return Response(StatsSerializer(data).data)

    @extend_schema(request=MediaUploadSerializer, responses={201: MediaSerializer})
    @action(detail=True, methods=["post"])
    def media(self, request, id=None):
        event = self.get_object()
        self._check_edit(event)
        if event.media.count() >= 8:
            raise ValidationError({"detail": "8 visuels maximum."})
        s = MediaUploadSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        media = s.save(event=event)
        from .tasks import process_media

        process_media.delay(media.pk)
        media.refresh_from_db()
        return Response(
            MediaSerializer(media, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=None, responses={204: None})
    @action(detail=True, methods=["delete"], url_path=r"media/(?P<media_id>\d+)")
    def delete_media(self, request, id=None, media_id=None):
        event = self.get_object()
        self._check_edit(event)
        get_object_or_404(EventMedia, pk=media_id, event=event).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FavoritesView(APIView):
    """GET / POST / DELETE /api/v1/me/favorites (UI-05, fusion des favoris locaux)."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: EventCardSerializer(many=True)})
    def get(self, request):
        ids = Favorite.objects.filter(user=request.user).values_list("event_id", flat=True)
        qs = (
            Event.objects.with_schedule()
            .filter(pk__in=ids)
            .select_related("primary_category", "venue__area", "organization", "owner_user")
            .prefetch_related("media")
            .order_by("next_start", "id")
        )
        return Response(
            {"results": EventCardSerializer(qs, many=True, context={"request": request}).data}
        )

    @extend_schema(request=FavoriteWriteSerializer, responses={201: EventCardSerializer})
    def post(self, request):
        if "events" in request.data:  # fusion des favoris locaux
            s = FavoriteMergeSerializer(data=request.data)
            s.is_valid(raise_exception=True)
            events = Event.objects.published().filter(slug__in=s.validated_data["events"])
            for ev in events:
                _, created = Favorite.objects.get_or_create(user=request.user, event=ev)
                if created:
                    EventDailyStat.bump(ev, "favorites_added")
            return self.get(request)
        s = FavoriteWriteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        event = s.validated_data["event"]
        _, created = Favorite.objects.get_or_create(user=request.user, event=event)
        if created:
            EventDailyStat.bump(event, "favorites_added")
        event = Event.objects.with_schedule().get(pk=event.pk)
        return Response(
            EventCardSerializer(event, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=FavoriteWriteSerializer, responses={204: None})
    def delete(self, request, slug=None):
        slug = slug or request.data.get("event")
        Favorite.objects.filter(user=request.user, event__slug=slug).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class HomeView(APIView):
    """GET /api/v1/home — raccourcis de l'accueil (SCR-01) : ce soir, week-end, sélection WIGO."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        from engagement.models import WeekendSelection

        now = timezone.now()
        base = _public_queryset(now)
        ctx = {"request": request}

        def block(params, limit=8):
            try:
                qs, ordering = apply_filters(base, params, now)
            except SearchParamsError:
                return []
            return EventCardSerializer(qs.order_by(*ordering)[:limit], many=True, context=ctx).data

        selection = WeekendSelection.current()
        selection_cards = []
        if selection:
            sel_qs = base.filter(pk__in=selection.events.values_list("pk", flat=True))
            selection_cards = EventCardSerializer(
                sel_qs.order_by("next_start")[:8], many=True, context=ctx
            ).data
        return Response(
            {
                "tonight": block({"date": "today"}),
                "weekend": block({"date": "weekend"}),
                "free": block({"free": "1"}),
                "selection": selection_cards,
                "ongoing": EventCardSerializer(
                    base.filter(is_long=True, first_start__lte=now).order_by("last_end")[:8],
                    many=True,
                    context=ctx,
                ).data,
                "counts": {
                    "active_events": base.count(),
                    "today": base.filter(
                        pk__in=[c["id"] for c in block({"date": "today"}, 1000)]
                    ).count(),
                },
            }
        )


class CategoryCountsView(APIView):
    """Compteurs par catégorie pour les chips (SCR-01 / SCR-02)."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        rows = (
            Event.objects.public()
            .exclude(format="ONLINE")
            .values("primary_category__slug")
            .annotate(n=Count("id"))
            .order_by("-n")
        )
        return Response({r["primary_category__slug"]: r["n"] for r in rows})


class EventListCreateView(APIView):
    """GET /api/v1/events (recherche publique) et POST /api/v1/events (brouillon organisateur)."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(parameters=SEARCH_PARAMS, responses={200: EventCardSerializer(many=True)})
    def get(self, request):
        return EventPublicViewSet.as_view({"get": "list"})(request._request)

    @extend_schema(request=EventWriteSerializer, responses={201: EventOwnerSerializer})
    def post(self, request):
        return EventManageViewSet.as_view({"post": "create"})(request._request)
