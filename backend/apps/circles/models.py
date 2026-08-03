import uuid

from django.conf import settings
from django.db import models


class Circle(models.Model):
    """A small group who can see each other's progress, not each other's goals.

    Only aggregate numbers are ever exposed about a member (see
    services.member_stats) — never a goal title, a task, or an email. The
    point is friendly accountability, not surveillance.
    """

    name = models.CharField(max_length=120)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="circles_created"
    )
    # Unguessable, like Goal.share_token — joining is "have the link", not
    # "guess the next id".
    invite_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def is_member(self, user) -> bool:
        return self.memberships.filter(user=user).exists()

    def is_owner(self, user) -> bool:
        return self.created_by_id == user.id and self.is_member(user)


class CircleMembership(models.Model):
    circle = models.ForeignKey(Circle, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="circle_memberships"
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["circle", "user"], name="uniq_circle_member")
        ]
        ordering = ["joined_at"]

    def __str__(self):
        return f"{self.user} in {self.circle}"

    @property
    def owner_user_id(self):
        return self.user_id
