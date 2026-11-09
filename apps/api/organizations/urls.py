from rest_framework.routers import SimpleRouter

from .views import OrganizationViewSet

router = SimpleRouter(trailing_slash=False)
router.register("organizations", OrganizationViewSet, basename="organization")

urlpatterns = router.urls
