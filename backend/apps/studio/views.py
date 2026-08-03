from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.studio.services.generate import generate_artifact
from apps.studio.services.schemas import SCHEMAS

from .models import Artifact
from .serializers import (
    ArtifactListSerializer,
    ArtifactSerializer,
    GenerateArtifactSerializer,
)


def _user_context(user) -> dict:
    """Facts the account already holds, so a CV isn't addressed to "Your Name"."""
    full_name = f"{user.first_name} {user.last_name}".strip()
    return {"Full name": full_name or user.username, "Email": user.email}


class ArtifactViewSet(viewsets.ModelViewSet):
    """Generated documents. One engine, many kinds."""

    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_serializer_class(self):
        return ArtifactListSerializer if self.action == "list" else ArtifactSerializer

    def get_queryset(self):
        qs = Artifact.objects.filter(user=self.request.user).select_related("goal")
        kind = self.request.query_params.get("kind")
        if kind in SCHEMAS:
            qs = qs.filter(kind=kind)
        return qs

    @action(detail=False, methods=["get"], url_path="kinds")
    def kinds(self, request):
        """What the studio can produce, and how each one exports."""
        return Response(
            [
                {
                    "kind": kind,
                    "label": spec["label"],
                    "export_format": "pdf" if kind in Artifact.PDF_KINDS else "png",
                }
                for kind, spec in SCHEMAS.items()
            ]
        )

    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        serializer = GenerateArtifactSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        prompt = serializer.validated_data["prompt"]
        goal = serializer.validated_data.get("goal")
        document_id = serializer.validated_data.get("document")

        # A vault document, once analysed, becomes the source of facts — this
        # is what stops the model inventing a CV for somebody who uploaded one.
        source_text = None
        if document_id:
            from apps.vault.models import Document

            document = Document.objects.filter(
                id=document_id, goal__user=request.user
            ).first()
            if document and document.extracted_text:
                source_text = document.extracted_text

        kind, data, title = generate_artifact(
            prompt=prompt,
            kind=serializer.validated_data.get("kind"),
            source_text=source_text,
            user_context=_user_context(request.user),
        )

        artifact = Artifact.objects.create(
            user=request.user,
            goal=goal,
            kind=kind,
            title=title,
            prompt=prompt,
            data=data,
        )
        return Response(
            ArtifactSerializer(artifact).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"], url_path="regenerate")
    def regenerate(self, request, pk=None):
        """Rebuild in place, optionally steered by a follow-up instruction."""
        artifact = self.get_object()
        tweak = str(request.data.get("instruction") or "").strip()[:1000]

        prompt = f"{artifact.prompt}\n\nAdditional instruction: {tweak}" if tweak else artifact.prompt
        _, data, title = generate_artifact(
            prompt=prompt, kind=artifact.kind, user_context=_user_context(request.user)
        )

        artifact.data = data
        artifact.title = title
        artifact.save(update_fields=["data", "title", "updated_at"])
        return Response(ArtifactSerializer(artifact).data)
