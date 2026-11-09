import hashlib
import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from core.enums import Language, TrustLevel
from core.models import TimeStampedModel


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, email, password, **extra):
        if not email:
            raise ValueError("L'e-mail est obligatoire.")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.update(is_staff=True, is_superuser=True, is_moderator=True)
        extra.setdefault("email_verified_at", timezone.now())
        return self._create(email, password, **extra)


class UserStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Actif"
    SUSPENDED = "SUSPENDED", "Suspendu"
    BANNED = "BANNED", "Suspendu définitivement"
    DELETED = "DELETED", "Supprimé"


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """Utilisateur (§9.1) : UUID, e-mail unique, langue, quartiers et envies suivis, statut."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=80, blank=True)
    language = models.CharField(max_length=2, choices=Language.choices, default=Language.FR)
    status = models.CharField(max_length=10, choices=UserStatus.choices, default=UserStatus.ACTIVE)
    suspended_until = models.DateTimeField(null=True, blank=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)

    # Rôles transverses (§3). Les rôles d'organisation sont dans OrganizationMember.
    is_staff = models.BooleanField(default=False)
    is_moderator = models.BooleanField(default=False)
    is_catalog_editor = models.BooleanField(default=False)

    # Niveau de confiance en tant qu'organisateur individuel (§5.4)
    trust_level = models.CharField(
        max_length=10, choices=TrustLevel.choices, default=TrustLevel.NEW
    )

    # Préférences (SCR-13)
    followed_areas = models.ManyToManyField("catalog.Area", blank=True, related_name="followers")
    followed_categories = models.ManyToManyField(
        "catalog.Category", blank=True, related_name="followers"
    )
    notify_new_events = models.BooleanField(default=False)
    notify_weekly_selection = models.BooleanField(default=False)
    notify_favorite_reminders = models.BooleanField(default=False)

    last_activity_at = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"

    def __str__(self):
        return self.email

    @property
    def is_active(self) -> bool:  # type: ignore[override]
        if self.status == UserStatus.ACTIVE:
            return True
        if self.status == UserStatus.SUSPENDED and self.suspended_until:
            return self.suspended_until < timezone.now()
        return False

    @is_active.setter
    def is_active(self, value: bool):  # compat avec l'admin Django
        self.status = UserStatus.ACTIVE if value else UserStatus.BANNED

    @property
    def is_email_verified(self) -> bool:
        return self.email_verified_at is not None

    @property
    def public_name(self) -> str:
        return self.display_name or self.email.split("@")[0]


class TokenKind(models.TextChoices):
    EMAIL_VERIFY = "EMAIL_VERIFY", "Vérification e-mail"
    PASSWORD_RESET = "PASSWORD_RESET", "Réinitialisation"
    MAGIC_LINK = "MAGIC_LINK", "Lien magique"


class AccountToken(models.Model):
    """Jeton à usage unique, stocké haché, à durée de vie courte."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tokens")
    kind = models.CharField(max_length=16, choices=TokenKind.choices)
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["user", "kind"])]

    def __str__(self):
        return f"{self.kind} pour {self.user_id}"

    @staticmethod
    def hash(raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()

    @classmethod
    def issue(cls, user: User, kind: str) -> str:
        ttl_key = (
            "PASSWORD_TOKEN_TTL_HOURS"
            if kind == TokenKind.PASSWORD_RESET
            else "EMAIL_TOKEN_TTL_HOURS"
        )
        ttl = timedelta(hours=settings.WIGO_RULES[ttl_key])
        cls.objects.filter(user=user, kind=kind, used_at__isnull=True).update(
            used_at=timezone.now()
        )
        raw = secrets.token_urlsafe(32)
        cls.objects.create(
            user=user, kind=kind, token_hash=cls.hash(raw), expires_at=timezone.now() + ttl
        )
        return raw

    @classmethod
    def consume(cls, raw: str, kind: str) -> User | None:
        token = (
            cls.objects.select_related("user")
            .filter(token_hash=cls.hash(raw), kind=kind, used_at__isnull=True)
            .first()
        )
        if token is None or token.expires_at < timezone.now():
            return None
        token.used_at = timezone.now()
        token.save(update_fields=["used_at"])
        return token.user
