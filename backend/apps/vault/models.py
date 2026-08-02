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

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.original_name or os.path.basename(self.file.name)

    @property
    def owner_user_id(self):
        return self.goal.user_id
