"""Routes /api/v1 — voir cahier des charges §9.2."""

from django.urls import include, path

from accounts.views import MePreferencesView

urlpatterns = [
    path("auth/", include("accounts.urls")),
    path("me/preferences", MePreferencesView.as_view(), name="me-preferences"),
    path("", include("catalog.urls")),
    path("", include("events.urls")),
    path("", include("organizations.urls")),
    path("", include("engagement.urls")),
    path("", include("moderation.urls")),
]
