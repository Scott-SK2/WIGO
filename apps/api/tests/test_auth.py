"""AUTH-01 à AUTH-06 : inscription, vérification, sessions, réinitialisation, export, suppression."""

import pytest
from django.core import mail

from accounts.models import AccountToken, TokenKind, User

pytestmark = pytest.mark.django_db
A = "/api/v1/auth"


def _register(api, email="alice@test.be"):
    return api.post(
        f"{A}/register",
        {
            "email": email,
            "password": "Mot-de-passe-solide-42",
            "language": "fr",
            "accept_terms": True,
        },
    )


def test_register_sends_verification_and_blocks_publication_until_verified(api, category):
    r = _register(api)
    assert r.status_code == 201
    user = User.objects.get(email="alice@test.be")
    assert user.email_verified_at is None
    assert len(mail.outbox) == 1 and "token=" in mail.outbox[0].body

    # RG-02 : pas de publication sans e-mail vérifié
    api.force_authenticate(user)
    r = api.post("/api/v1/events", {"title": "X", "primary_category": "concerts"})
    assert r.status_code == 403

    token = mail.outbox[0].body.split("token=")[1].split()[0]
    api.force_authenticate(None)
    r = api.post(f"{A}/verify-email", {"token": token})
    assert r.status_code == 200 and r.json()["email_verified"] is True
    assert api.post(f"{A}/verify-email", {"token": token}).status_code == 400  # usage unique


def test_register_validations(api):
    assert _register(api, "bad").status_code == 400
    r = api.post(f"{A}/register", {"email": "a@b.be", "password": "short", "accept_terms": True})
    assert r.status_code == 400
    r = api.post(
        f"{A}/register",
        {"email": "a@b.be", "password": "Mot-de-passe-solide-42", "accept_terms": False},
    )
    assert r.status_code == 400 and r.json()["error"]["code"] == "validation_error"
    _register(api)
    assert _register(api).status_code == 400  # doublon


def test_login_refresh_logout(api, confirmed_user):
    r = api.post(f"{A}/login", {"email": confirmed_user.email, "password": "Secret-password-123"})
    assert r.status_code == 200 and {"access", "refresh"} <= set(r.json())
    refresh = r.json()["refresh"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {r.json()['access']}")
    assert api.get(f"{A}/me").json()["email"] == confirmed_user.email
    r2 = api.post(f"{A}/refresh", {"refresh": refresh})
    assert r2.status_code == 200 and r2.json()["refresh"] != refresh  # rotation
    assert api.post(f"{A}/refresh", {"refresh": refresh}).status_code == 401  # ancien jeton révoqué
    new_refresh = r2.json()["refresh"]
    assert api.post(f"{A}/logout", {"refresh": new_refresh}).status_code == 204
    assert api.post(f"{A}/refresh", {"refresh": new_refresh}).status_code == 401


def test_login_wrong_password(api, confirmed_user):
    assert (
        api.post(f"{A}/login", {"email": confirmed_user.email, "password": "nope"}).status_code
        == 401
    )


def test_password_reset_flow(api, confirmed_user):
    assert api.post(f"{A}/password-reset", {"email": "unknown@test.be"}).status_code == 202
    assert len(mail.outbox) == 0
    assert api.post(f"{A}/password-reset", {"email": confirmed_user.email}).status_code == 202
    token = mail.outbox[0].body.split("token=")[1].split()[0]
    r = api.post(
        f"{A}/password-reset/confirm", {"token": token, "password": "Nouveau-mot-de-passe-77"}
    )
    assert r.status_code == 204
    assert (
        api.post(
            f"{A}/login", {"email": confirmed_user.email, "password": "Nouveau-mot-de-passe-77"}
        ).status_code
        == 200
    )


def test_expired_token_is_refused(api, confirmed_user):
    from datetime import timedelta

    from django.utils import timezone

    raw = AccountToken.issue(confirmed_user, TokenKind.EMAIL_VERIFY)
    AccountToken.objects.update(expires_at=timezone.now() - timedelta(minutes=1))
    assert api.post(f"{A}/verify-email", {"token": raw}).status_code == 400


def test_me_update_preferences_export_and_delete(api, confirmed_user, area, category, make_event):
    api.force_authenticate(confirmed_user)
    r = api.patch(f"{A}/me", {"display_name": "Léa", "language": "nl"})
    assert r.status_code == 200 and r.json()["language"] == "nl"
    r = api.patch(
        "/api/v1/me/preferences",
        {
            "followed_areas": ["ixelles"],
            "followed_categories": ["concerts"],
            "notify_weekly_selection": True,
        },
    )
    assert r.status_code == 200 and r.json()["followed_areas"] == ["ixelles"]
    event = make_event(confirmed_user)
    api.post("/api/v1/me/favorites", {"event": event.slug})
    export = api.get(f"{A}/me/export").json()
    assert export["account"]["email"] == confirmed_user.email
    assert export["favorites"] == [event.slug] and export["preferences"]["followed_areas"] == [
        "ixelles"
    ]
    assert api.delete(f"{A}/me").status_code == 204
    confirmed_user.refresh_from_db()
    assert confirmed_user.status == "DELETED" and "anonyme" in confirmed_user.email
    assert not confirmed_user.favorites.exists()
    event.refresh_from_db()
    assert event.pk  # l'événement reste pour l'historique public (annexe A.4)


def test_suspended_user_cannot_login(api, confirmed_user):
    from datetime import timedelta

    from django.utils import timezone

    confirmed_user.status = "SUSPENDED"
    confirmed_user.suspended_until = timezone.now() + timedelta(days=7)
    confirmed_user.save()
    assert (
        api.post(
            f"{A}/login", {"email": confirmed_user.email, "password": "Secret-password-123"}
        ).status_code
        == 401
    )
