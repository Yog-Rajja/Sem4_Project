import logging

from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    """Raised by service-layer code (LLM, YouTube) for failures we can explain.

    `detail` is safe to show the user; `status_code` maps onto the HTTP response.
    """

    def __init__(self, detail: str, status_code: int = 502, code: str = "service_error"):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.code = code


def api_exception_handler(exc, context):
    """Turn ServiceError into a structured JSON body the frontend can render."""
    if isinstance(exc, ServiceError):
        from rest_framework.response import Response

        logger.warning("ServiceError in %s: %s", context.get("view"), exc.detail)
        return Response(
            {"detail": exc.detail, "code": exc.code},
            status=exc.status_code,
        )
    return drf_exception_handler(exc, context)
