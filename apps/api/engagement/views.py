from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.audit import log_action
from core.permissions import IsAdmin, IsCatalogEditor, IsModerator
from core.throttles import NewsletterThrottle

from . import serializers
from .models import (
    ImportSource,
    NewsletterSubscription,
    SubscriptionStatus,
    WeekendSelection,
    WeekendSelectionItem,
)
from .tasks import run_import, send_newsletter_confirmation


class NewsletterSubscribeView(APIView):
    """POST /api/v1/newsletter — inscription avec double opt-in (RET-02)."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [NewsletterThrottle]

    @extend_schema(request=serializers.NewsletterSubscribeSerializer, responses={202: None})
    def post(self, request):
        s = serializers.NewsletterSubscribeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data
        data.pop("consent")
        email = data["email"].lower()
        sub, _ = NewsletterSubscription.objects.update_or_create(
            email=email,
            defaults={
                **data,
                "email": email,
                "consent_at": timezone.now(),
                "consent_source": "web",
            },
        )
        if sub.status != SubscriptionStatus.CONFIRMED:
            if sub.status == SubscriptionStatus.UNSUBSCRIBED:
                sub.status = SubscriptionStatus.PENDING
                sub.save(update_fields=["status"])
            send_newsletter_confirmation.delay(str(sub.pk))
        return Response(
            {"detail": "Vérifiez votre boîte e-mail pour confirmer."},
            status=status.HTTP_202_ACCEPTED,
        )


class NewsletterConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[OpenApiParameter("token", str, required=True)], responses={200: None}
    )
    def get(self, request):
        sub = get_object_or_404(
            NewsletterSubscription, confirm_token=request.query_params.get("token", "-")
        )
        if sub.status != SubscriptionStatus.CONFIRMED:
            sub.confirm()
        return Response({"detail": "Inscription confirmée.", "email": sub.email})


class NewsletterUnsubscribeView(APIView):
    """Désinscription en un clic (GET pour les liens d'e-mail, POST pour List-Unsubscribe)."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[OpenApiParameter("token", str, required=True)], responses={200: None}
    )
    def get(self, request):
        return self._do(request.query_params.get("token", "-"))

    @extend_schema(request=None, responses={200: None})
    def post(self, request):
        return self._do(request.data.get("token") or request.query_params.get("token", "-"))

    def _do(self, token):
        sub = get_object_or_404(NewsletterSubscription, unsubscribe_token=token)
        if sub.status != SubscriptionStatus.UNSUBSCRIBED:
            sub.unsubscribe()
        return Response({"detail": "Désinscription effectuée."})


class SelectionView(APIView):
    """GET/POST /api/v1/admin/selection — sélection du week-end (ADM-09)."""

    permission_classes = [IsModerator]

    @extend_schema(
        parameters=[OpenApiParameter("week_start", str)],
        responses={200: serializers.SelectionSerializer},
    )
    def get(self, request):
        week = request.query_params.get("week_start")
        if week:
            sel = WeekendSelection.objects.filter(week_start=week).first()
        else:
            sel = WeekendSelection.current() or WeekendSelection.objects.first()
        if sel is None:
            return Response({"detail": "Aucune sélection."}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializers.SelectionSerializer(sel, context={"request": request}).data)

    @extend_schema(
        request=serializers.SelectionWriteSerializer,
        responses={200: serializers.SelectionSerializer},
    )
    def post(self, request):
        s = serializers.SelectionWriteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        week = d.get("week_start") or WeekendSelection.week_start_for(timezone.localdate())
        week = WeekendSelection.week_start_for(week)
        sel, _ = WeekendSelection.objects.get_or_create(
            week_start=week, defaults={"editor": request.user}
        )
        for key in ("title", "intro", "send_status"):
            if key in d:
                setattr(sel, key, d[key])
        sel.editor = request.user
        sel.save()
        if "events" in d:
            sel.items.all().delete()
            for item in d["events"]:
                WeekendSelectionItem.objects.create(selection=sel, **item)
        log_action(
            request.user, "selection.update", sel, after={"events": len(d.get("events", []))}
        )
        return Response(serializers.SelectionSerializer(sel, context={"request": request}).data)


class PublicSelectionView(APIView):
    """GET /api/v1/selection — sélection publique de la semaine (badges « Sélection WIGO »)."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(responses={200: serializers.SelectionSerializer})
    def get(self, request):
        sel = WeekendSelection.current()
        if sel is None:
            return Response({"items": []})
        return Response(serializers.SelectionSerializer(sel, context={"request": request}).data)


class ImportsView(APIView):
    """GET/POST /api/v1/admin/imports — sources partenaires et déclenchement (CAT-02)."""

    permission_classes = [IsCatalogEditor]

    @extend_schema(responses={200: serializers.ImportSourceSerializer(many=True)})
    def get(self, request):
        qs = ImportSource.objects.prefetch_related("runs")
        return Response({"results": serializers.ImportSourceSerializer(qs, many=True).data})

    @extend_schema(request=serializers.ImportTriggerSerializer, responses={202: None})
    def post(self, request):
        s = serializers.ImportTriggerSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        source = get_object_or_404(ImportSource, slug=s.validated_data["source"], is_active=True)
        run_import.delay(source.pk, str(request.user.pk))
        log_action(request.user, "import.trigger", source)
        return Response(status=status.HTTP_202_ACCEPTED)


class AdminStatsView(APIView):
    """GET /api/v1/admin/stats — tableau KPI (ANA-01, §2.5)."""

    permission_classes = [IsAdmin]

    @extend_schema(responses={200: {"type": "object"}})
    def get(self, request):
        from django.db.models import Avg, F

        from accounts.models import User
        from events.models import Event, EventStatus
        from moderation.models import ModerationDecision
        from organizations.models import Organization

        decided = (
            ModerationDecision.objects.filter(action__in=["APPROVE", "REJECT", "REQUEST_CHANGES"])
            .annotate(delay=F("created_at") - F("event__submitted_at"))
            .aggregate(avg=Avg("delay"))
        )
        return Response(
            {
                "active_events": Event.objects.public().count(),
                "pending_review": Event.objects.filter(status=EventStatus.PENDING_REVIEW).count(),
                "organizers": Organization.objects.count()
                + User.objects.filter(events__isnull=False).distinct().count(),
                "newsletter_confirmed": NewsletterSubscription.objects.filter(
                    status=SubscriptionStatus.CONFIRMED
                ).count(),
                "avg_moderation_delay_hours": round(decided["avg"].total_seconds() / 3600, 1)
                if decided["avg"]
                else None,
            }
        )
