from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import ArtifactViewSet, GoalCertificateView

router = SimpleRouter()
router.register("artifacts", ArtifactViewSet, basename="artifact")

urlpatterns = [
    path(
        "goals/<int:goal_id>/certificate/",
        GoalCertificateView.as_view(),
        name="goal-certificate",
    ),
    path("", include(router.urls)),
]
