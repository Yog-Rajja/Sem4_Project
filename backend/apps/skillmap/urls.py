from django.urls import path

from .views import SkillMapGenerateView, SkillMapView

urlpatterns = [
    path("goals/<int:goal_id>/skillmap/", SkillMapView.as_view(), name="skillmap"),
    path(
        "goals/<int:goal_id>/skillmap/generate/",
        SkillMapGenerateView.as_view(),
        name="skillmap-generate",
    ),
]
