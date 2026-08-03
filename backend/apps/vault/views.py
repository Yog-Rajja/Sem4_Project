from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.goals.services import roadmap as roadmap_service

from . import services
from .models import Document
from .serializers import DocumentSerializer


class DocumentViewSet(viewsets.ModelViewSet):
    """Document vault, plus the intelligence layer on top of it."""

    serializer_class = DocumentSerializer
    # Multipart for the upload itself; JSON for the analyse/to-goal actions,
    # which take an ordinary body rather than a file.
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        qs = Document.objects.filter(goal__user=self.request.user).select_related("goal")
        goal_id = self.request.query_params.get("goal")
        if goal_id and goal_id.isdigit():
            qs = qs.filter(goal_id=int(goal_id))
        return qs

    @action(detail=True, methods=["post"], url_path="analyse")
    def analyse(self, request, pk=None):
        """Read the file and extract meaning from it.

        Done on demand rather than at upload time: reading costs an API call,
        so the user decides when it is worth spending.
        """
        document = self.get_object()
        services.analyse(document)
        return Response(DocumentSerializer(document, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="to-goal")
    def to_goal(self, request, pk=None):
        """Turn a document into a roadmap preview.

        Returns a preview rather than saving, matching the New Goal flow — the
        user still edits and accepts before anything is written.
        """
        document = self.get_object()
        if not document.extracted_text:
            services.analyse(document)

        instruction = str(request.data.get("prompt") or "").strip()[:500]
        goal_text = instruction or (
            f"Work through {document.doc_type or 'this document'}: "
            f"{document.original_name}"
        )

        milestones = roadmap_service.generate_roadmap(
            goal_text=goal_text,
            target_date=None,
            context=document.extracted_text,
        )
        return Response(
            {
                "title": goal_text[:255],
                "raw_input_text": goal_text,
                "target_date": None,
                "milestones": milestones,
                "source_document": document.original_name,
            }
        )
