from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import DocumentViewSet

# SimpleRouter (not DefaultRouter) because the goals router already owns the
# `api-root` view mounted at the same /api/ prefix.
router = SimpleRouter()
router.register("documents", DocumentViewSet, basename="document")

urlpatterns = [path("", include(router.urls))]
