"""Momentum: activity days, streaks and focus statistics.

Dates are bucketed in Python rather than in SQL. The volume is tiny (one
person's own history) and it keeps the behaviour identical on SQLite and
PostgreSQL, including the timezone conversion.
"""

import datetime as dt
from collections import defaultdict

from django.utils import timezone

from apps.goals.models import Task

from .models import FocusSession

# A session shorter than this is a mis-click, not work.
MIN_MEANINGFUL_SECONDS = 60
HEATMAP_DAYS = 119  # 17 weeks — a clean grid


def _local_date(value):
    return timezone.localtime(value).date()


def activity_by_day(user, since: dt.date | None = None) -> dict[dt.date, dict]:
    """Map each active local date to what happened on it."""
    buckets = defaultdict(lambda: {"tasks": 0, "focus_minutes": 0, "sessions": 0})

    completions = Task.objects.filter(
        milestone__goal__user=user, is_complete=True, completed_at__isnull=False
    ).values_list("completed_at", flat=True)
    for stamp in completions:
        day = _local_date(stamp)
        if since and day < since:
            continue
        buckets[day]["tasks"] += 1

    sessions = FocusSession.objects.filter(
        user=user,
        mode=FocusSession.Mode.FOCUS,
        seconds_elapsed__gte=MIN_MEANINGFUL_SECONDS,
    ).values_list("started_at", "seconds_elapsed")
    for stamp, seconds in sessions:
        day = _local_date(stamp)
        if since and day < since:
            continue
        buckets[day]["focus_minutes"] += round(seconds / 60)
        buckets[day]["sessions"] += 1

    return dict(buckets)


def streaks(user) -> dict:
    """Current and longest run of consecutive active days.

    Today not yet being active does not break the streak — it is still in
    progress until the day ends, which is why the walk may start at yesterday.
    """
    active = sorted(activity_by_day(user).keys())
    if not active:
        return {"current": 0, "longest": 0, "active_today": False, "last_active": None}

    active_set = set(active)
    today = timezone.localdate()
    active_today = today in active_set

    cursor = today if active_today else today - dt.timedelta(days=1)
    current = 0
    while cursor in active_set:
        current += 1
        cursor -= dt.timedelta(days=1)

    longest = run = 1
    for previous, day in zip(active, active[1:]):
        run = run + 1 if (day - previous).days == 1 else 1
        longest = max(longest, run)

    return {
        "current": current,
        "longest": max(longest, current),
        "active_today": active_today,
        "last_active": active[-1].isoformat(),
    }


def heatmap(user, days: int = HEATMAP_DAYS) -> list[dict]:
    """One row per day for the contribution-style grid."""
    today = timezone.localdate()
    start = today - dt.timedelta(days=days - 1)
    buckets = activity_by_day(user, since=start)

    rows = []
    for offset in range(days):
        day = start + dt.timedelta(days=offset)
        entry = buckets.get(day, {})
        tasks = entry.get("tasks", 0)
        minutes = entry.get("focus_minutes", 0)
        # A 0-4 intensity so the UI never has to invent thresholds.
        score = tasks + (minutes // 25)
        if score == 0:
            level = 0
        elif score <= 1:
            level = 1
        elif score <= 3:
            level = 2
        elif score <= 6:
            level = 3
        else:
            level = 4
        rows.append(
            {
                "date": day.isoformat(),
                "tasks": tasks,
                "focus_minutes": minutes,
                "level": level,
            }
        )
    return rows


def focus_stats(user) -> dict:
    today = timezone.localdate()
    week_start = today - dt.timedelta(days=6)
    buckets = activity_by_day(user, since=week_start)

    finished = FocusSession.objects.filter(
        user=user,
        mode=FocusSession.Mode.FOCUS,
        seconds_elapsed__gte=MIN_MEANINGFUL_SECONDS,
    )
    total_seconds = sum(finished.values_list("seconds_elapsed", flat=True))

    return {
        "today_minutes": buckets.get(today, {}).get("focus_minutes", 0),
        "today_sessions": buckets.get(today, {}).get("sessions", 0),
        "week_minutes": sum(day.get("focus_minutes", 0) for day in buckets.values()),
        "total_minutes": round(total_seconds / 60),
        "total_sessions": finished.count(),
    }
