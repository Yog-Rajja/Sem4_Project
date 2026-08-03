import datetime as dt

from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from . import review as review_service
from .models import WeeklyReview
from .services import build_alerts


class AlertsView(APIView):
    """Derived, always-current notification feed."""

    def get(self, request):
        alerts = build_alerts(request.user)
        return Response(
            {
                "alerts": alerts,
                "unread": sum(
                    1 for a in alerts if a["severity"] in ("critical", "warning")
                ),
            }
        )


class WeeklyReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeeklyReview
        fields = [
            "id", "week_start", "headline", "summary",
            "wins", "slipped", "focus_next", "stats", "created_at",
        ]


class WeeklyReviewView(APIView):
    """GET returns the cached review; POST regenerates it.

    Caching matters here: without it, every dashboard visit would spend an API
    call restating the same week.
    """

    def _week(self, request):
        raw = request.query_params.get("week") or request.data.get("week")
        reference = None
        if raw:
            try:
                reference = dt.date.fromisoformat(str(raw)[:10])
            except ValueError:
                reference = None
        return review_service.week_bounds(reference)

    def get(self, request):
        week_start, _ = self._week(request)
        review = WeeklyReview.objects.filter(
            user=request.user, week_start=week_start
        ).first()
        if review is None:
            return Response({"review": None, "week_start": week_start})
        return Response({"review": WeeklyReviewSerializer(review).data})

    def post(self, request):
        week_start, week_end = self._week(request)
        review = review_service.generate_review(request.user, week_start, week_end)
        return Response({"review": WeeklyReviewSerializer(review).data})
