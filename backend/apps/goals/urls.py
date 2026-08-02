from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DashboardView, GoalViewSet, MilestoneViewSet, TaskViewSet

router = DefaultRouter()
router.register("goals", GoalViewSet, basename="goal")
router.register("milestones", MilestoneViewSet, basename="milestone")
router.register("tasks", TaskViewSet, basename="task")

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("", include(router.urls)),
]
