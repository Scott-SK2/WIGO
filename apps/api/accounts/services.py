from django.conf import settings
from django.utils import timezone

from .models import AccountToken, TokenKind, User
from .tasks import send_account_email


def send_verification_email(user: User) -> None:
    raw = AccountToken.issue(user, TokenKind.EMAIL_VERIFY)
    url = f"{settings.PUBLIC_WEB_URL}/{user.language}/compte/verification?token={raw}"
    send_account_email.delay(
        "verify", user.email, user.language, url, settings.WIGO_RULES["EMAIL_TOKEN_TTL_HOURS"]
    )


def send_password_reset_email(user: User) -> None:
    raw = AccountToken.issue(user, TokenKind.PASSWORD_RESET)
    url = f"{settings.PUBLIC_WEB_URL}/{user.language}/compte/mot-de-passe?token={raw}"
    send_account_email.delay(
        "reset", user.email, user.language, url, settings.WIGO_RULES["PASSWORD_TOKEN_TTL_HOURS"]
    )


def verify_email(raw_token: str) -> User | None:
    user = AccountToken.consume(raw_token, TokenKind.EMAIL_VERIFY)
    if user and user.email_verified_at is None:
        user.email_verified_at = timezone.now()
        user.save(update_fields=["email_verified_at"])
    return user


def export_user_data(user: User) -> dict:
    """RG-18 / annexe A.4 : export des données personnelles."""
    from events.models import Event, Favorite

    return {
        "account": {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "language": user.language,
            "created_at": user.created_at.isoformat(),
            "email_verified_at": user.email_verified_at.isoformat()
            if user.email_verified_at
            else None,
            "trust_level": user.trust_level,
        },
        "preferences": {
            "followed_areas": list(user.followed_areas.values_list("slug", flat=True)),
            "followed_categories": list(user.followed_categories.values_list("slug", flat=True)),
            "notify_new_events": user.notify_new_events,
            "notify_weekly_selection": user.notify_weekly_selection,
            "notify_favorite_reminders": user.notify_favorite_reminders,
        },
        "favorites": list(Favorite.objects.filter(user=user).values_list("event__slug", flat=True)),
        "events": list(
            Event.objects.filter(owner_user=user).values("id", "slug", "title", "status")
        ),
        "organizations": list(user.memberships.values("organization__slug", "role")),
    }


def anonymize_user(user: User) -> None:
    """Suppression de compte : anonymisation, les événements archivés restent (annexe A.4)."""
    from events.models import Favorite

    Favorite.objects.filter(user=user).delete()
    user.followed_areas.clear()
    user.followed_categories.clear()
    user.email = f"deleted-{user.id}@anonyme.wigo.invalid"
    user.display_name = ""
    user.status = "DELETED"
    user.set_unusable_password()
    user.save()
