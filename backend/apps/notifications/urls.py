from django.urls import path

from .views import (
    DigestPreviewView,
    NotificationSettingView,
    PushSubscribeView,
    SendTestNotificationView,
)

urlpatterns = [
    path("notifications/settings/", NotificationSettingView.as_view(), name="notification-settings"),
    path("notifications/subscribe/", PushSubscribeView.as_view(), name="push-subscribe"),
    path("notifications/test/", SendTestNotificationView.as_view(), name="notification-test"),
    path("notifications/preview/", DigestPreviewView.as_view(), name="notification-preview"),
]
