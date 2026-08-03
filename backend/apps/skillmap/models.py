from django.db import models

from apps.goals.models import Goal


class SkillMap(models.Model):
    """The dependency graph for one goal.

    Structure (which nodes exist, which depend on which) is generated once by
    the AI and cached here — regenerating is an explicit action, not
    automatic, so it doesn't spend a request on every page load. Each node's
    *completion*, by contrast, is never stored: it is always read live off the
    milestone it points at, the same way Goal.progress is computed rather than
    stored, so the graph can never show stale progress.
    """

    goal = models.OneToOneField(Goal, on_delete=models.CASCADE, related_name="skill_map")
    nodes = models.JSONField(default=list)
    edges = models.JSONField(default=list)
    generated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Skill map for {self.goal_id}"

    @property
    def owner_user_id(self):
        return self.goal.user_id
