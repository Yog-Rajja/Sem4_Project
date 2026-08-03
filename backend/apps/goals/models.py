import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Goal(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="goals"
    )
    title = models.CharField(max_length=255)
    raw_input_text = models.TextField(
        blank=True, help_text="The natural-language goal the user originally typed."
    )
    target_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Sharing is off until asked for, and the token is unguessable rather than
    # sequential so a shared roadmap can't be found by counting upwards.
    share_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    is_shared = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def owner_user_id(self):
        return self.user_id

    # --- Progress -------------------------------------------------------
    # Progress is always derived from tasks, never stored, so it cannot drift.
    def task_counts(self):
        agg = Task.objects.filter(milestone__goal=self).aggregate(
            total=models.Count("id"),
            done=models.Count("id", filter=models.Q(is_complete=True)),
        )
        return agg["total"] or 0, agg["done"] or 0

    @property
    def progress(self) -> int:
        total, done = self.task_counts()
        if not total:
            return 0
        return round(done * 100 / total)


class Milestone(models.Model):
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name="milestones")
    title = models.CharField(max_length=255)
    target_date = models.DateField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    search_query = models.CharField(
        max_length=255,
        blank=True,
        help_text="Short topic phrase used to look up learning resources.",
    )
    is_complete = models.BooleanField(default=False)
    resources_fetched_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.goal_id} · {self.title}"

    @property
    def owner_user_id(self):
        return self.goal.user_id


class Task(models.Model):
    milestone = models.ForeignKey(
        Milestone, on_delete=models.CASCADE, related_name="tasks"
    )
    # Subtasks produced by the P1 "break this down" action point at their parent.
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="subtasks",
    )
    title = models.CharField(max_length=255)
    due_date = models.DateField(null=True, blank=True)
    is_complete = models.BooleanField(default=False)
    # Stamped whenever is_complete flips on, cleared when it flips off. Streaks,
    # velocity and the activity heatmap are all built from this.
    completed_at = models.DateTimeField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Kept in save() rather than the serializer so the admin, the shell and
        # bulk flows all stamp the timestamp the same way.
        if self.is_complete and self.completed_at is None:
            self.completed_at = timezone.now()
        elif not self.is_complete and self.completed_at is not None:
            self.completed_at = None
            if kwargs.get("update_fields"):
                kwargs["update_fields"] = set(kwargs["update_fields"]) | {"completed_at"}
        elif self.is_complete and kwargs.get("update_fields"):
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"completed_at"}
        super().save(*args, **kwargs)

    @property
    def owner_user_id(self):
        return self.milestone.goal.user_id


class Resource(models.Model):
    class Source(models.TextChoices):
        YOUTUBE = "youtube", "YouTube"
        GOOGLE_SEARCH = "google_search", "Google Search"

    milestone = models.ForeignKey(
        Milestone, on_delete=models.CASCADE, related_name="resources"
    )
    title = models.CharField(max_length=255)
    url = models.URLField(max_length=500)
    source = models.CharField(max_length=20, choices=Source.choices)
    thumbnail_url = models.URLField(max_length=500, blank=True)
    channel_title = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["source", "id"]
        # Re-fetching resources for a milestone should not duplicate rows.
        constraints = [
            models.UniqueConstraint(
                fields=["milestone", "url"], name="uniq_resource_per_milestone"
            )
        ]

    def __str__(self):
        return self.title

    @property
    def owner_user_id(self):
        return self.milestone.goal.user_id
