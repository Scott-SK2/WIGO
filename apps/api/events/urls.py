from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter(trailing_slash=False)
# L'ordre compte : l'UUID (gestion) est plus spécifique que le slug (public).
router.register("events", views.EventManageViewSet, basename="event-manage")
router.register("events", views.EventPublicViewSet, basename="event")

# La racine /events est servie par une vue combinée (GET public, POST organisateur).
router_urls = [u for u in router.urls if u.name not in ("event-manage-list", "event-list")]

urlpatterns = [
    path("home", views.HomeView.as_view(), name="home"),
    path("events", views.EventListCreateView.as_view(), name="event-list"),
    path("events/counts", views.CategoryCountsView.as_view(), name="event-counts"),
    path("me/favorites", views.FavoritesView.as_view(), name="me-favorites"),
    path("me/favorites/<slug:slug>", views.FavoritesView.as_view(), name="me-favorite-detail"),
    *router_urls,
]
