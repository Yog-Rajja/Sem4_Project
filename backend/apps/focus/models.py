from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.goals.models import Task


class FocusSession(models.Model):
    """One stretch of deliberate work, optionally bound to a task.

    Sessions are created when the timer starts and closed when it finishes or
    is abandoned, so an interrupted session is still an honest record of the
    time actually spent.
    """

    class Mode(models.TextChoices):
        FOCUS = "focus", "Focus"
        BREAK = "break", "Break"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="focus_sessions"
    )
    task = models.ForeignKey(
        Task,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="focus_sessions",
    )
    # Denormalised so the history still reads sensibly after a task is deleted.
    task_title = models.CharField(max_length=255, blank=True)

    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.FOCUS)
    planned_minutes = models.PositiveIntegerField(default=25)
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    seconds_elapsed = models.PositiveIntegerField(default=0)
    # False when the user stopped early; the elapsed time still counts.
    completed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-started_at"]
        indexes = [models.Index(fields=["user", "-started_at"])]

    def __str__(self):
        return f"{self.get_mode_display()} · {self.minutes} min"

    @property
    def owner_user_id(self):
        return self.user_id

    @property
    def minutes(self) -> int:
        return round(self.seconds_elapsed / 60)

    @property
    def is_running(self) -> bool:
        return self.ended_at is None

    def finish(self, seconds_elapsed: int, completed: bool):
        self.seconds_elapsed = max(0, seconds_elapsed)
        self.completed = completed
        self.ended_at = timezone.now()
        self.save(update_fields=["seconds_elapsed", "completed", "ended_at"])
