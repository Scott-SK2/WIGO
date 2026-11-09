from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter(trailing_slash=False)
router.register("venues", views.VenueViewSet, basename="venue")

urlpatterns = [
    path("categories", views.CategoryListView.as_view(), name="category-list"),
    path("areas", views.AreaListView.as_view(), name="area-list"),
    *router.urls,
]
