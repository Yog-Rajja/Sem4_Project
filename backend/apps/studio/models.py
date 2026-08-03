from django.conf import settings
from django.db import models

from apps.goals.models import Goal


class Artifact(models.Model):
    """A generated document.

    One model covers every document type — the `kind` selects which schema
    `data` conforms to and which renderer the frontend uses. Adding a new type
    is a schema plus a template, not a new table.
    """

    class Kind(models.TextChoices):
        RESUME = "resume", "Résumé"
        DIET_PLAN = "diet_plan", "Diet plan"
        TIMETABLE = "timetable", "Study timetable"
        COVER_LETTER = "cover_letter", "Cover letter"
        PROJECT_REPORT = "project_report", "Project report"
        INVITATION = "invitation", "Invitation card"
        IMAGE = "image", "Generated image"
        CERTIFICATE = "certificate", "Certificate of completion"

    # Text documents export as vector PDF; visual ones export as PNG.
    PDF_KINDS = {Kind.RESUME, Kind.COVER_LETTER, Kind.PROJECT_REPORT}
    # Kinds whose output is a raster file produced upstream, not rendered here.
    FILE_KINDS = {Kind.IMAGE}

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="artifacts"
    )
    goal = models.ForeignKey(
        Goal,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="artifacts",
        help_text="Optional: the goal this document was made for.",
    )

    kind = models.CharField(max_length=32, choices=Kind.choices)
    title = models.CharField(max_length=255)
    prompt = models.TextField(blank=True, help_text="What the user originally asked for.")
    data = models.JSONField(default=dict)
    # Only used by IMAGE artifacts, where the model returns pixels rather than
    # structure. Everything else renders from `data` on the client.
    image = models.FileField(upload_to="artifacts/%Y/%m/", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["user", "-updated_at"])]

    def __str__(self):
        return f"{self.get_kind_display()} · {self.title}"

    @property
    def owner_user_id(self):
        return self.user_id

    @property
    def export_format(self) -> str:
        return "pdf" if self.kind in self.PDF_KINDS else "png"

    @property
    def image_url(self) -> str:
        return self.image.url if self.image else ""
