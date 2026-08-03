from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import NotificationSetting, PushSubscription
from .serializers import NotificationSettingSerializer, PushSubscriptionSerializer


class NotificationSettingView(APIView):
    """Read and update delivery preferences, plus what the server supports."""

    def get(self, request):
        setting, _ = NotificationSetting.objects.get_or_create(user=request.user)
        return Response(
            {
                **NotificationSettingSerializer(setting).data,
                "push_supported": services.push_configured(),
                "email_supported": bool(settings.EMAIL_HOST_USER)
                or not settings.EMAIL_BACKEND.endswith("smtp.EmailBackend"),
                "vapid_public_key": settings.VAPID_PUBLIC_KEY,
                "devices": PushSubscription.objects.filter(user=request.user).count(),
            }
        )

    def patch(self, request):
        setting, _ = NotificationSetting.objects.get_or_create(user=request.user)
        serializer = NotificationSettingSerializer(
            setting, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PushSubscribeView(APIView):
    def post(self, request):
        serializer = PushSubscriptionSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"subscribed": True,
             "devices": PushSubscription.objects.filter(user=request.user).count()},
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request):
        endpoint = request.data.get("endpoint") or request.query_params.get("endpoint")
        queryset = PushSubscription.objects.filter(user=request.user)
        if endpoint:
            queryset = queryset.filter(endpoint=endpoint)
        removed, _ = queryset.delete()
        return Response({"removed": removed})


class SendTestNotificationView(APIView):
    """Send today's digest immediately, ignoring schedule and preferences.

    Without this there is no way to tell whether notifications are working
    except waiting until tomorrow morning.
    """

    def post(self, request):
        result = services.deliver_daily(request.user, force=True)
        return Response(
            {
                **result,
                "push_configured": services.push_configured(),
                "detail": _explain(result),
            }
        )


def _explain(result) -> str:
    parts = []
    if result.get("pushed"):
        parts.append(
            f"pushed to {result['pushed']} device{'s' if result['pushed'] != 1 else ''}"
        )
    if result.get("emailed"):
        parts.append("emailed")
    if not parts:
        return (
            "Nothing was sent. Allow notifications in your browser, or add SMTP "
            "settings to backend/.env for email."
        )
    return "Sent — " + " and ".join(parts) + "."


class DigestPreviewView(APIView):
    """What today's notification would say, without sending anything."""

    def get(self, request):
        return Response(services.build_digest(request.user))
