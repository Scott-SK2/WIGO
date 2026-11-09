from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Area, Category, Tag, Venue


class LatLonField(serializers.Serializer):
    lat = serializers.FloatField()
    lon = serializers.FloatField()


class CategorySerializer(serializers.ModelSerializer):
    name = serializers.DictField(source="names", child=serializers.CharField(), read_only=True)
    parent = serializers.SlugRelatedField(slug_field="slug", read_only=True)

    class Meta:
        model = Category
        fields = ["slug", "name", "parent", "icon", "order", "is_launch_niche"]


class TagSerializer(serializers.ModelSerializer):
    name = serializers.DictField(source="names", child=serializers.CharField(), read_only=True)

    class Meta:
        model = Tag
        fields = ["slug", "name"]


class AreaSerializer(serializers.ModelSerializer):
    name = serializers.DictField(source="names", child=serializers.CharField(), read_only=True)
    parent = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    postal_codes = serializers.ListField(child=serializers.CharField(), read_only=True)
    centroid = serializers.SerializerMethodField()

    class Meta:
        model = Area
        fields = ["slug", "kind", "name", "parent", "postal_codes", "centroid"]

    @extend_schema_field(LatLonField(allow_null=True))
    def get_centroid(self, obj) -> dict | None:
        if obj.centroid is None:
            return None
        return {"lat": obj.centroid.y, "lon": obj.centroid.x}


class VenueSerializer(serializers.ModelSerializer):
    area = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    location = serializers.SerializerMethodField()
    address = serializers.CharField(source="address_line", read_only=True)

    class Meta:
        model = Venue
        fields = [
            "id",
            "name",
            "slug",
            "address",
            "street",
            "house_number",
            "postal_code",
            "city",
            "country",
            "area",
            "location",
            "accessibility",
            "website",
        ]

    @extend_schema_field(LatLonField(allow_null=True))
    def get_location(self, obj) -> dict | None:
        if obj.location is None:
            return None
        return {"lat": obj.location.y, "lon": obj.location.x}


class VenueWriteSerializer(serializers.ModelSerializer):
    """Création d'un lieu depuis le formulaire (étape 2). lat/lon fournis par le géocodage."""

    lat = serializers.FloatField(write_only=True, required=False, min_value=-90, max_value=90)
    lon = serializers.FloatField(write_only=True, required=False, min_value=-180, max_value=180)
    area = serializers.SlugRelatedField(
        slug_field="slug", queryset=Area.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Venue
        fields = [
            "name",
            "street",
            "house_number",
            "postal_code",
            "city",
            "country",
            "area",
            "lat",
            "lon",
            "accessibility",
            "website",
        ]

    def create(self, validated):
        from django.contrib.gis.geos import Point
        from django.utils import timezone
        from django.utils.text import slugify

        lat, lon = validated.pop("lat", None), validated.pop("lon", None)
        if lat is not None and lon is not None:
            validated["location"] = Point(lon, lat, srid=4326)
            validated["geocoded_at"] = timezone.now()
        base = slugify(f"{validated['name']}-{validated.get('postal_code', '')}") or "lieu"
        slug, i = base, 2
        while Venue.objects.filter(slug=slug).exists():
            slug, i = f"{base}-{i}", i + 1
        validated["slug"] = slug
        validated["created_by"] = self.context["request"].user
        return super().create(validated)
