from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.audit import log_action
from core.permissions import IsModerator
from core.throttles import AnonReportThrottle, ReportThrottle
from events import workflow
from events.models import Event, EventStatus
from organizations.models import OwnershipClaim
from organizations.serializers import ClaimSerializer
from organizations.services import decide_claim

from . import serializers, services
from .models import REASON_CODES, AuditLog, Report, ReportStatus


class ReportCreateView(generics.CreateAPIView):
    """POST /api/v1/reports — signalement, anonyme ou connecté (RG-16)."""

    serializer_class = serializers.ReportCreateSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ReportThrottle, AnonReportThrottle]

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        report = serializer.save(reporter=user)
        log_action(user, "report.create", report.target, after={"category": report.category})


class ModerationQueueView(APIView):
    """GET /api/v1/admin/moderation — file « À valider » ; POST — décision (ADM-01, ADM-02)."""

    permission_classes = [IsModerator]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "status",
                str,
                description="PENDING_REVIEW (défaut) | CHANGES_REQUESTED | REJECTED | PUBLISHED",
            )
        ],
        responses={200: serializers.ModerationQueueItemSerializer(many=True)},
    )
    def get(self, request):
        st = (request.query_params.get("status") or EventStatus.PENDING_REVIEW).upper()
        qs = (
            Event.objects.with_schedule()
            .filter(status=st)
            .select_related("primary_category", "venue__area", "organization", "owner_user")
            .prefetch_related(
                "media", "occurrences", "tags", "secondary_categories", "decisions__moderator"
            )
            .order_by("submitted_at", "created_at")
        )
        data = serializers.ModerationQueueItemSerializer(
            qs[:100], many=True, context={"request": request}
        ).data
        return Response(
            {
                "results": data,
                "reason_codes": [{"code": c, "label": lbl} for c, lbl in REASON_CODES],
            }
        )

    @extend_schema(
        request=serializers.ModerationActionSerializer,
        responses={200: serializers.ModerationQueueItemSerializer},
    )
    def post(self, request):
        s = serializers.ModerationActionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        event = get_object_or_404(Event, pk=d["event"])
        action = d["action"]
        if action == "APPROVE":
            workflow.approve(event, request.user, d.get("comment", ""))
        elif action == "REJECT":
            workflow.reject(event, request.user, d["reason_code"], d.get("comment", ""))
        elif action == "REQUEST_CHANGES":
            workflow.request_changes(event, request.user, d["reason_code"], d.get("comment", ""))
        elif action == "UNPUBLISH":
            workflow.unpublish(event, request.user, d["reason_code"], d.get("comment", ""))
        event = Event.objects.with_schedule().get(pk=event.pk)
        return Response(
            serializers.ModerationQueueItemSerializer(event, context={"request": request}).data
        )


class ReportListView(generics.ListAPIView):
    """GET /api/v1/admin/reports — signalements ouverts."""

    permission_classes = [IsModerator]
    serializer_class = serializers.ReportSerializer
    pagination_class = None

    def get_queryset(self):
        st = (self.request.query_params.get("status") or ReportStatus.OPEN).upper()
        return Report.objects.filter(status=st).select_related("event", "organization", "reporter")[
            :200
        ]


class ReportDecisionView(APIView):
    permission_classes = [IsModerator]

    @extend_schema(
        request=serializers.ReportDecisionSerializer, responses={200: serializers.ReportSerializer}
    )
    def post(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        s = serializers.ReportDecisionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        services.handle_report(
            report, request.user, s.validated_data["founded"], s.validated_data.get("note", "")
        )
        return Response(serializers.ReportSerializer(report).data)


class ClaimListView(generics.ListAPIView):
    """GET /api/v1/admin/claims — revendications en attente (CAT-03)."""

    permission_classes = [IsModerator]
    pagination_class = None
    serializer_class = ClaimSerializer

    def get_queryset(self):
        return OwnershipClaim.objects.filter(status="PENDING").select_related(
            "organization", "claimant"
        )

    def list(self, request, *args, **kwargs):
        rows = [
            {
                "id": str(c.id),
                "organization": {"slug": c.organization.slug, "name": c.organization.name},
                "claimant": c.claimant.email,
                "evidence": c.evidence,
                "created_at": c.created_at,
            }
            for c in self.get_queryset()
        ]
        return Response({"results": rows})


class ClaimDecisionView(APIView):
    permission_classes = [IsModerator]

    @extend_schema(request=serializers.ClaimDecisionSerializer, responses={200: ClaimSerializer})
    def post(self, request, pk):
        claim = get_object_or_404(OwnershipClaim, pk=pk)
        s = serializers.ClaimDecisionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        decide_claim(
            claim, request.user, s.validated_data["approve"], s.validated_data.get("note", "")
        )
        return Response(ClaimSerializer(claim).data)


class AuditLogView(generics.ListAPIView):
    """GET /api/v1/admin/audit — journal (ADM-05), réservé aux administrateurs."""

    permission_classes = [IsModerator]
    serializer_class = serializers.AuditLogSerializer

    def get_queryset(self):
        qs = AuditLog.objects.select_related("actor")
        target = self.request.query_params.get("target_id")
        if target:
            qs = qs.filter(target_id=target)
        action = self.request.query_params.get("action")
        if action:
            qs = qs.filter(action__startswith=action)
        return qs


class ReasonCodesView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses={200: {"type": "array"}})
    def get(self, request):
        return Response(
            [{"code": c, "label": lbl} for c, lbl in REASON_CODES], status=status.HTTP_200_OK
        )
