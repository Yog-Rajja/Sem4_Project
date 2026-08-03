"""Circle leaderboard.

Every number here is aggregated — a count, a percentage, a streak length.
Nothing that identifies *what* a member is working on ever leaves this
module, which is what keeps a circle a source of encouragement rather than a
window into someone else's private plans.
"""

import datetime as dt

from django.utils import timezone

from apps.focus.services import streaks
from apps.goals.models import Goal, Task


def member_stats(user) -> dict:
    week_start = timezone.localdate() - dt.timedelta(days=6)

    goals = list(Goal.objects.filter(user=user))
    total_tasks = done_tasks = 0
    for goal in goals:
        total, done = goal.task_counts()
        total_tasks += total
        done_tasks += done

    completed_this_week = Task.objects.filter(
        milestone__goal__user=user,
        is_complete=True,
        completed_at__date__gte=week_start,
    ).count()

    streak = streaks(user)

    return {
        "active_goals": len(goals),
        "total_tasks": total_tasks,
        "done_tasks": done_tasks,
        "overall_progress": round(done_tasks * 100 / total_tasks) if total_tasks else 0,
        "completed_this_week": completed_this_week,
        "streak_current": streak["current"],
        "streak_longest": streak["longest"],
    }


def circle_leaderboard(circle) -> list[dict]:
    memberships = circle.memberships.select_related("user").all()

    rows = []
    for membership in memberships:
        user = membership.user
        rows.append(
            {
                "user_id": user.id,
                "name": user.first_name or user.username,
                "is_you": None,  # filled in per-request by the caller
                "joined_at": membership.joined_at,
                "is_owner": user.id == circle.created_by_id,
                **member_stats(user),
            }
        )

    # Most active this week wins; a longer current streak breaks ties.
    rows.sort(key=lambda r: (-r["completed_this_week"], -r["streak_current"]))
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows
