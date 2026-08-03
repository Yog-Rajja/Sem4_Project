from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import ArtifactViewSet

router = SimpleRouter()
router.register("artifacts", ArtifactViewSet, basename="artifact")

urlpatterns = [path("", include(router.urls))]
