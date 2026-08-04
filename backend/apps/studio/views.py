import base64

from django.conf import settings
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.goals.models import Goal
from apps.studio.services import certificate as certificate_service
from apps.studio.services import imagegen
from apps.studio.services.generate import generate_artifact
from apps.studio.services.schemas import SCHEMAS

from .models import Artifact
from .serializers import (
    ArtifactListSerializer,
    ArtifactSerializer,
    GenerateArtifactSerializer,
)


def _attach_image(artifact, image_prompt: str):
    """Render the image and store it against the artifact."""
    if settings.USE_MOCK_AI:
        # A 1x1 PNG keeps the offline path exercising the same plumbing.
        raw, mime = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        ), "image/png"
    else:
        raw, mime = imagegen.generate_image(image_prompt)

    extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(
        mime, "png"
    )
    artifact.image.save(
        f"artifact-{artifact.id}.{extension}", ContentFile(raw), save=True
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
        prompt_driven = [
            {
                "kind": kind,
                "label": spec["label"],
                "export_format": "pdf" if kind in Artifact.PDF_KINDS else "png",
                "automatic": False,
            }
            for kind, spec in SCHEMAS.items()
        ]
        # Certificates are never generated from a prompt — kept out of SCHEMAS
        # entirely so an explicit kind='certificate' can't reach the freeform
        # generation path — but still worth listing for discoverability.
        automatic = [
            {
                "kind": Artifact.Kind.CERTIFICATE,
                "label": "Certificate of completion",
                "export_format": "png",
                "automatic": True,
            }
        ]
        return Response(prompt_driven + automatic)

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

        # An image artifact needs a second call: the first turned the request
        # into a proper visual prompt, this one renders it. If image generation
        # isn't available the artifact is discarded rather than left as an
        # empty shell the user has to clean up.
        if kind == Artifact.Kind.IMAGE:
            try:
                _attach_image(artifact, data.get("image_prompt") or prompt)
            except Exception:
                artifact.delete()
                raise
        return Response(
            ArtifactSerializer(artifact, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
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

        if artifact.kind == Artifact.Kind.IMAGE:
            _attach_image(artifact, data.get("image_prompt") or prompt)

        return Response(
            ArtifactSerializer(artifact, context={"request": request}).data
        )


class GoalCertificateView(APIView):
    """Generate, refresh, or fetch the completion certificate for a goal.

    Lives in studio rather than goals — studio already depends on goals for
    the Artifact.goal FK, and keeping that dependency one-directional avoids
    a circular import between the two apps.
    """

    def get(self, request, goal_id):
        goal = get_object_or_404(Goal, pk=goal_id, user=request.user)
        artifact = Artifact.objects.filter(
            user=request.user, goal=goal, kind=Artifact.Kind.CERTIFICATE
        ).first()
        if artifact is None:
            return Response(
                {"detail": "No certificate yet.", "code": "no_certificate"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(ArtifactSerializer(artifact, context={"request": request}).data)

    def post(self, request, goal_id):
        goal = get_object_or_404(Goal, pk=goal_id, user=request.user)
        total, done = goal.task_counts()
        if not total or done < total:
            return Response(
                {
                    "detail": "This goal isn't finished yet. Every task needs "
                    "to be complete first.",
                    "code": "goal_not_complete",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = certificate_service.build_certificate(goal, request.user)
        # Upsert on (user, goal, kind) rather than creating a new row each
        # time, so refreshing a certificate never leaves duplicates behind.
        artifact, _created = Artifact.objects.update_or_create(
            user=request.user,
            goal=goal,
            kind=Artifact.Kind.CERTIFICATE,
            defaults={
                "title": f"{goal.title} - Certificate of Completion",
                "prompt": "",
                "data": data,
            },
        )
        return Response(ArtifactSerializer(artifact, context={"request": request}).data)
