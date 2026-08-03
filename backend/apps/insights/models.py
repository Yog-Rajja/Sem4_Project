from django.conf import settings
from django.db import models


class WeeklyReview(models.Model):
    """A generated retrospective for one week.

    Cached per week so opening the dashboard on Tuesday doesn't regenerate
    Monday's review — and so the user keeps a history they can look back on.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="weekly_reviews"
    )
    week_start = models.DateField(help_text="Monday of the week being reviewed.")

    headline = models.CharField(max_length=255)
    summary = models.TextField()
    wins = models.JSONField(default=list)
    slipped = models.JSONField(default=list)
    focus_next = models.JSONField(default=list)
    stats = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-week_start"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "week_start"], name="uniq_weekly_review"
            )
        ]

    def __str__(self):
        return f"Week of {self.week_start}"

    @property
    def owner_user_id(self):
        return self.user_id
