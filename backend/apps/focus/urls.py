from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import FocusSessionViewSet, MomentumView

router = SimpleRouter()
router.register("focus-sessions", FocusSessionViewSet, basename="focus-session")

urlpatterns = [
    path("momentum/", MomentumView.as_view(), name="momentum"),
    path("", include(router.urls)),
]
