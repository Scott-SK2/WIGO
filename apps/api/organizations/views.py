from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.audit import log_action
from core.exceptions import BusinessRuleViolation
from core.permissions import HasVerifiedEmail

from . import serializers, services
from .models import MemberRole, Organization, OrganizationMember

User = get_user_model()


class OrganizationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET  /organizations/{slug}        profil public
    POST /organizations               création (propriétaire = créateur)
    POST /organizations/{slug}/claim  revendication
    """

    queryset = Organization.objects.filter(is_suspended=False)
    lookup_field = "slug"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), HasVerifiedEmail()]

    def get_serializer_class(self):
        if self.action in ("create", "partial_update", "update"):
            return serializers.OrganizationWriteSerializer
        if self.action == "claim":
            return serializers.ClaimSerializer
        if self.action == "members":
            return serializers.MemberSerializer
        user = getattr(self.request, "user", None)
        obj = getattr(self, "_obj", None)
        if (
            obj is not None
            and user
            and user.is_authenticated
            and (obj.role_of(user) or user.is_moderator)
        ):
            return serializers.OrganizationPrivateSerializer
        return serializers.OrganizationPublicSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            mine = self.request.query_params.get("mine")
            if mine and self.request.user.is_authenticated:
                return qs.filter(members__user=self.request.user)
            q = self.request.query_params.get("q")
            if q:
                qs = qs.filter(name__unaccent__icontains=q)
        return qs

    def retrieve(self, request, *args, **kwargs):
        self._obj = self.get_object()
        return Response(self.get_serializer(self._obj).data)

    def create(self, request, *args, **kwargs):
        s = serializers.OrganizationWriteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        org = services.create_organization(request.user, **s.validated_data)
        self._obj = org
        return Response(
            serializers.OrganizationPrivateSerializer(org, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        org = self.get_object()
        if not org.can_edit(request.user) and not request.user.is_moderator:
            return Response(
                {"detail": "Vous n'avez pas les droits sur cette organisation."},
                status=status.HTTP_403_FORBIDDEN,
            )
        s = serializers.OrganizationWriteSerializer(org, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        before = {k: getattr(org, k) for k in s.validated_data}
        s.save()
        log_action(request.user, "organization.update", org, before=before, after=s.validated_data)
        self._obj = org
        return Response(
            serializers.OrganizationPrivateSerializer(org, context={"request": request}).data
        )

    @extend_schema(
        request=serializers.ClaimSerializer, responses={201: serializers.ClaimSerializer}
    )
    @action(detail=True, methods=["post"])
    def claim(self, request, slug=None):
        org = self.get_object()
        s = serializers.ClaimSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        claim = services.submit_claim(org, request.user, s.validated_data["evidence"])
        return Response(serializers.ClaimSerializer(claim).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=serializers.MemberSerializer,
        responses={200: serializers.OrganizationPrivateSerializer},
    )
    @action(detail=True, methods=["post", "delete"])
    def members(self, request, slug=None):
        """ORG-03 : seul un propriétaire gère les membres."""
        org = self.get_object()
        if not org.is_owner(request.user):
            return Response(
                {"detail": "Réservé au propriétaire."}, status=status.HTTP_403_FORBIDDEN
            )
        s = serializers.MemberSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        target = get_object_or_404(User, email=s.validated_data["email"].lower())
        if request.method == "DELETE":
            if target == request.user and org.members.filter(role=MemberRole.OWNER).count() == 1:
                raise BusinessRuleViolation(
                    "Une organisation doit garder au moins un propriétaire."
                )
            org.members.filter(user=target).delete()
            log_action(
                request.user, "organization.member.remove", org, after={"email": target.email}
            )
        else:
            OrganizationMember.objects.update_or_create(
                organization=org, user=target, defaults={"role": s.validated_data["role"]}
            )
            log_action(
                request.user,
                "organization.member.add",
                org,
                after={"email": target.email, "role": s.validated_data["role"]},
            )
        self._obj = org
        return Response(
            serializers.OrganizationPrivateSerializer(org, context={"request": request}).data
        )
