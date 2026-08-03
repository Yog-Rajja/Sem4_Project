"""Derived alerts.

Nothing here is stored or scheduled — every alert is computed from the current
state on request. That keeps the feature honest (an alert can never go stale)
and avoids needing a job queue for notifications.
"""

import datetime as dt

from django.utils import timezone

from apps.focus.services import streaks
from apps.goals.models import Goal, Milestone, Task

STALE_AFTER_DAYS = 14
# How far behind the expected pace a goal must fall before we say so.
BEHIND_TOLERANCE = 20


def _alert(kind, severity, title, message, path, action=None):
    return {
        "id": kind,
        "kind": kind,
        "severity": severity,  # critical | warning | info | success
        "title": title,
        "message": message,
        "path": path,
        "action": action,
    }


def expected_progress(goal, today: dt.date) -> int | None:
    """Where a goal *should* be, assuming even pacing between start and target."""
    if not goal.target_date:
        return None
    start = timezone.localtime(goal.created_at).date()
    total_days = (goal.target_date - start).days
    if total_days <= 0:
        return 100
    elapsed = (today - start).days
    return max(0, min(100, round(elapsed * 100 / total_days)))


def build_alerts(user) -> list[dict]:
    today = timezone.localdate()
    alerts = []

    tasks = Task.objects.filter(milestone__goal__user=user, is_complete=False)

    overdue = tasks.filter(due_date__lt=today).count()
    if overdue:
        alerts.append(
            _alert(
                "overdue_tasks",
                "critical",
                f"{overdue} overdue task{'s' if overdue != 1 else ''}",
                "These slipped past their due date. Reschedule them or tick them off.",
                "/tasks?due=overdue",
                "Review overdue",
            )
        )

    due_today = tasks.filter(due_date=today).count()
    if due_today:
        alerts.append(
            _alert(
                "due_today",
                "info",
                f"{due_today} task{'s' if due_today != 1 else ''} due today",
                "Still on the plan for today.",
                "/tasks?due=today",
                "Open today",
            )
        )

    overdue_milestones = (
        Milestone.objects.filter(
            goal__user=user, is_complete=False, target_date__lt=today
        )
        .select_related("goal")
        .order_by("target_date")[:3]
    )
    for milestone in overdue_milestones:
        days = (today - milestone.target_date).days
        alerts.append(
            _alert(
                f"milestone_overdue_{milestone.id}",
                "warning",
                f"“{milestone.title}” is {days} day{'s' if days != 1 else ''} late",
                f"In {milestone.goal.title}. Re-planning will spread the remaining work.",
                f"/goals/{milestone.goal_id}",
                "Re-plan goal",
            )
        )

    for goal in Goal.objects.filter(user=user).prefetch_related("milestones"):
        total, done = goal.task_counts()
        if not total:
            continue
        actual = round(done * 100 / total)

        if actual == 100:
            alerts.append(
                _alert(
                    f"goal_complete_{goal.id}",
                    "success",
                    f"“{goal.title}” is complete",
                    "Every task is done. Worth a moment before the next one.",
                    f"/goals/{goal.id}",
                    "View goal",
                )
            )
            continue

        expected = expected_progress(goal, today)
        if expected is not None and expected - actual >= BEHIND_TOLERANCE:
            alerts.append(
                _alert(
                    f"goal_behind_{goal.id}",
                    "warning",
                    f"“{goal.title}” is behind pace",
                    f"About {expected}% of the time has gone but you're {actual}% done. "
                    f"Re-plan to rebalance what's left.",
                    f"/goals/{goal.id}",
                    "Re-plan goal",
                )
            )

    stale_cutoff = timezone.now() - dt.timedelta(days=STALE_AFTER_DAYS)
    for goal in Goal.objects.filter(user=user, created_at__lt=stale_cutoff):
        total, done = goal.task_counts()
        if not total or done == total:
            continue
        latest = (
            Task.objects.filter(milestone__goal=goal, completed_at__isnull=False)
            .order_by("-completed_at")
            .values_list("completed_at", flat=True)
            .first()
        )
        if latest is None or latest < stale_cutoff:
            alerts.append(
                _alert(
                    f"goal_stale_{goal.id}",
                    "info",
                    f"No progress on “{goal.title}” for a while",
                    f"Nothing ticked off in {STALE_AFTER_DAYS} days. Still worth doing?",
                    f"/goals/{goal.id}",
                    "Open goal",
                )
            )

    streak = streaks(user)
    if streak["current"] >= 2 and not streak["active_today"]:
        alerts.append(
            _alert(
                "streak_at_risk",
                "warning",
                f"Your {streak['current']}-day streak ends tonight",
                "One task or one focus session keeps it alive.",
                "/focus",
                "Start a session",
            )
        )

    order = {"critical": 0, "warning": 1, "info": 2, "success": 3}
    alerts.sort(key=lambda a: order.get(a["severity"], 9))
    return alerts
