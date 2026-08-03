from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health(_request):
    return JsonResponse({"status": "ok", "service": "smart-companion"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.goals.urls")),
    path("api/analytics/", include("apps.analytics.urls")),
    path("api/", include("apps.vault.urls")),
    path("api/", include("apps.focus.urls")),
    path("api/", include("apps.insights.urls")),
    path("api/", include("apps.studio.urls")),
    path("api/", include("apps.notifications.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
