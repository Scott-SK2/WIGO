from rest_framework import generics, mixins, permissions, viewsets

from core.permissions import HasVerifiedEmail

from .models import Area, Category, Venue
from .serializers import AreaSerializer, CategorySerializer, VenueSerializer, VenueWriteSerializer


class CategoryListView(generics.ListAPIView):
    """GET /api/v1/categories — taxonomie complète (liste plate avec parent)."""

    queryset = Category.objects.filter(is_active=True).select_related("parent")
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class AreaListView(generics.ListAPIView):
    """GET /api/v1/areas — communes et quartiers."""

    queryset = Area.objects.filter(is_active=True).select_related("parent")
    serializer_class = AreaSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class VenueViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Lieux existants (recherche par nom) et création (étape 2 du formulaire)."""

    queryset = Venue.objects.filter(is_active=True).select_related("area")
    pagination_class = None
    lookup_field = "slug"

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated(), HasVerifiedEmail()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        return VenueWriteSerializer if self.action == "create" else VenueSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(name__unaccent__icontains=q)
        return qs[:30]

    def create(self, request, *args, **kwargs):
        from rest_framework import status
        from rest_framework.response import Response

        s = VenueWriteSerializer(data=request.data, context={"request": request})
        s.is_valid(raise_exception=True)
        venue = s.save()
        return Response(VenueSerializer(venue).data, status=status.HTTP_201_CREATED)
