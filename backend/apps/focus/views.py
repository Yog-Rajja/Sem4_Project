from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import FocusSession
from .serializers import FinishSessionSerializer, FocusSessionSerializer


class FocusSessionViewSet(viewsets.ModelViewSet):
    serializer_class = FocusSessionSerializer
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        qs = FocusSession.objects.filter(user=self.request.user).select_related(
            "task", "task__milestone"
        )
        if self.request.query_params.get("running") == "true":
            qs = qs.filter(ended_at__isnull=True)
        return qs

    @action(detail=True, methods=["post"])
    def finish(self, request, pk=None):
        """Close a session with however much time was actually spent.

        The client owns the countdown, so it reports elapsed seconds; stopping
        early still records the work rather than discarding it.
        """
        session = self.get_object()
        if not session.is_running:
            return Response(
                {"detail": "That session has already finished."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = FinishSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session.finish(
            seconds_elapsed=serializer.validated_data["seconds_elapsed"],
            completed=serializer.validated_data["completed"],
        )
        return Response(FocusSessionSerializer(session).data)


class MomentumView(APIView):
    """Streaks, the activity heatmap and focus totals, in one call."""

    def get(self, request):
        return Response(
            {
                "streak": services.streaks(request.user),
                "focus": services.focus_stats(request.user),
                "heatmap": services.heatmap(request.user),
            }
        )
