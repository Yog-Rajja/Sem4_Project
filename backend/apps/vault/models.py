import os

from django.db import models

from apps.goals.models import Goal


def document_upload_path(instance, filename):
    return f"documents/goal_{instance.goal_id}/{filename}"


class Document(models.Model):
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name="documents")
    file = models.FileField(upload_to=document_upload_path)
    original_name = models.CharField(max_length=255, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    # --- Document intelligence ------------------------------------------
    # Populated on demand by POST /api/documents/{id}/analyse/, never on
    # upload — reading a file costs an API call, so the user asks for it.
    extracted_text = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    doc_type = models.CharField(
        max_length=60, blank=True, help_text="What the AI decided this is."
    )
    key_points = models.JSONField(default=list, blank=True)
    suggested_actions = models.JSONField(default=list, blank=True)
    analysed_at = models.DateTimeField(null=True, blank=True)

    @property
    def is_analysed(self) -> bool:
        return self.analysed_at is not None

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.original_name or os.path.basename(self.file.name)

    @property
    def owner_user_id(self):
        return self.goal.user_id
