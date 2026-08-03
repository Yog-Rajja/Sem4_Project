from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import CircleViewSet

router = SimpleRouter()
router.register("circles", CircleViewSet, basename="circle")

urlpatterns = [path("", include(router.urls))]
