from rest_framework.response import Response
from rest_framework.views import APIView

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
