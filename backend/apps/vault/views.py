from rest_framework import viewsets
from rest_framework.parsers import FormParser, MultiPartParser

from .models import Document
from .serializers import DocumentSerializer


class DocumentViewSet(viewsets.ModelViewSet):
    """P1 document vault: upload, list, download, delete. No folders or tags."""

    serializer_class = DocumentSerializer
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        qs = Document.objects.filter(goal__user=self.request.user).select_related("goal")
        goal_id = self.request.query_params.get("goal")
        if goal_id and goal_id.isdigit():
            qs = qs.filter(goal_id=int(goal_id))
        return qs
