from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from catalog.models import Area, Category
from core.enums import Language

from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=10)
    accept_terms = serializers.BooleanField(write_only=True)

    class Meta:
        model = User
        fields = ["email", "password", "display_name", "language", "accept_terms"]

    def validate_accept_terms(self, value):
        if not value:
            raise serializers.ValidationError("Vous devez accepter les CGU.")
        return value

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Un compte existe déjà avec cet e-mail.")
        return value

    def validate(self, attrs):
        validate_password(attrs["password"], user=User(email=attrs["email"]))
        return attrs

    def create(self, validated):
        validated.pop("accept_terms")
        password = validated.pop("password")
        return User.objects.create_user(password=password, **validated)


class MeSerializer(serializers.ModelSerializer):
    email_verified = serializers.BooleanField(source="is_email_verified", read_only=True)
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "display_name",
            "language",
            "email_verified",
            "trust_level",
            "roles",
            "created_at",
        ]
        read_only_fields = ["id", "email", "trust_level", "created_at"]

    def get_roles(self, user) -> list[str]:
        roles = []
        if user.is_superuser:
            roles.append("admin")
        if user.is_moderator:
            roles.append("moderator")
        if user.is_catalog_editor:
            roles.append("catalog_editor")
        return roles


class PreferencesSerializer(serializers.ModelSerializer):
    followed_areas = serializers.SlugRelatedField(
        many=True, slug_field="slug", queryset=Area.objects.all()
    )
    followed_categories = serializers.SlugRelatedField(
        many=True, slug_field="slug", queryset=Category.objects.filter(is_active=True)
    )

    class Meta:
        model = User
        fields = [
            "language",
            "followed_areas",
            "followed_categories",
            "notify_new_events",
            "notify_weekly_selection",
            "notify_favorite_reminders",
        ]


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class TokenSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=128)


class PasswordResetConfirmSerializer(TokenSerializer):
    password = serializers.CharField(min_length=10)

    def validate_password(self, value):
        validate_password(value)
        return value


class LanguageField(serializers.ChoiceField):
    def __init__(self, **kwargs):
        super().__init__(choices=Language.choices, **kwargs)
