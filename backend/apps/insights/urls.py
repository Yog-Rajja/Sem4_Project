from django.urls import path

from .views import AlertsView, WeeklyReviewView

urlpatterns = [
    path("alerts/", AlertsView.as_view(), name="alerts"),
    path("weekly-review/", WeeklyReviewView.as_view(), name="weekly-review"),
]
