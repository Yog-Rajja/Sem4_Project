"""Weekly retrospective.

The numbers are computed here and handed to the model as facts; the model only
writes the prose. That way the review can never claim you finished nine tasks
when you finished two.
"""

import datetime as dt
import logging

from django.conf import settings
from django.utils import timezone

from common.exceptions import ServiceError

from apps.focus.models import FocusSession
from apps.focus.services import streaks
from apps.goals.models import Goal, Task
from apps.goals.services import llm

from .models import WeeklyReview

logger = logging.getLogger(__name__)

REVIEW_SYSTEM_PROMPT = """\
You write a short weekly retrospective for someone working towards their goals.

Reply with ONLY a JSON object. No prose, no markdown fences.

{
  "headline": "string - max 8 words, the week in one line",
  "summary": "string - 2 to 3 sentences, warm but honest, second person",
  "wins": ["string - max 12 words each, 1 to 3 of them"],
  "slipped": ["string - max 12 words each, 0 to 3 of them"],
  "focus_next": ["string - max 12 words each, 2 to 3 concrete priorities"]
}

Rules:
- You are given the real numbers. Never contradict them and never invent a \
figure that is not in the data.
- Be honest about a bad week without being harsh: name what slipped, then \
give a concrete way back. Never use guilt.
- A quiet week is allowed to be a quiet week. Do not manufacture wins.
- Speak to the person as "you". No corporate language, no exclamation marks.
- focus_next must reference their actual goals or overdue work by name.
"""


def week_bounds(reference: dt.date | None = None) -> tuple[dt.date, dt.date]:
    """Monday–Sunday of the week containing `reference` (default: last week)."""
    today = reference or timezone.localdate()
    this_monday = today - dt.timedelta(days=today.weekday())
    return this_monday, this_monday + dt.timedelta(days=6)


def collect_stats(user, start: dt.date, end: dt.date) -> dict:
    start_dt = timezone.make_aware(dt.datetime.combine(start, dt.time.min))
    end_dt = timezone.make_aware(dt.datetime.combine(end, dt.time.max))

    completed = list(
        Task.objects.filter(
            milestone__goal__user=user,
            completed_at__gte=start_dt,
            completed_at__lte=end_dt,
        ).select_related("milestone__goal")
    )

    sessions = FocusSession.objects.filter(
        user=user,
        mode=FocusSession.Mode.FOCUS,
        started_at__gte=start_dt,
        started_at__lte=end_dt,
        seconds_elapsed__gte=60,
    )
    focus_seconds = sum(sessions.values_list("seconds_elapsed", flat=True))

    today = timezone.localdate()
    overdue = list(
        Task.objects.filter(
            milestone__goal__user=user, is_complete=False, due_date__lt=today
        ).select_related("milestone__goal")[:10]
    )

    per_goal = {}
    for task in completed:
        title = task.milestone.goal.title
        per_goal[title] = per_goal.get(title, 0) + 1

    return {
        "week_start": start.isoformat(),
        "week_end": end.isoformat(),
        "tasks_completed": len(completed),
        "completed_titles": [t.title for t in completed[:12]],
        "per_goal": per_goal,
        "focus_minutes": round(focus_seconds / 60),
        "focus_sessions": sessions.count(),
        "overdue_count": len(overdue),
        "overdue_titles": [t.title for t in overdue[:6]],
        "streak": streaks(user)["current"],
        "active_goals": list(
            Goal.objects.filter(user=user).values_list("title", flat=True)[:8]
        ),
    }


def _mock_review(stats):
    return {
        "headline": "A steady week of progress",
        "summary": (
            f"You finished {stats['tasks_completed']} task(s) and logged "
            f"{stats['focus_minutes']} minutes of focus."
        ),
        "wins": [f"{stats['tasks_completed']} tasks completed"],
        "slipped": (
            [f"{stats['overdue_count']} tasks overdue"] if stats["overdue_count"] else []
        ),
        "focus_next": ["Clear the overdue work", "Book two focus sessions"],
    }


def _clean_list(value, cap=4):
    if not isinstance(value, list):
        return []
    return [str(item).strip()[:200] for item in value[:cap] if str(item).strip()]


def generate_review(user, week_start: dt.date, week_end: dt.date) -> WeeklyReview:
    stats = collect_stats(user, week_start, week_end)

    if settings.USE_MOCK_AI:
        payload = _mock_review(stats)
    else:
        lines = [
            f"Week: {stats['week_start']} to {stats['week_end']}",
            f"Tasks completed: {stats['tasks_completed']}",
            f"Focus time: {stats['focus_minutes']} minutes over "
            f"{stats['focus_sessions']} sessions",
            f"Current streak: {stats['streak']} days",
            f"Overdue right now: {stats['overdue_count']}",
        ]
        if stats["completed_titles"]:
            lines.append("Finished: " + "; ".join(stats["completed_titles"]))
        if stats["per_goal"]:
            lines.append(
                "By goal: "
                + "; ".join(f"{k} ({v})" for k, v in stats["per_goal"].items())
            )
        if stats["overdue_titles"]:
            lines.append("Overdue: " + "; ".join(stats["overdue_titles"]))
        if stats["active_goals"]:
            lines.append("Active goals: " + "; ".join(stats["active_goals"]))

        payload = llm.complete_json(
            system=REVIEW_SYSTEM_PROMPT,
            user="\n".join(lines) + "\n\nWrite the retrospective JSON.",
            temperature=0.5,
        )

    if not isinstance(payload, dict):
        raise ServiceError(
            "The AI response was not in the expected format.",
            status_code=502,
            code="schema_invalid",
        )

    review, _ = WeeklyReview.objects.update_or_create(
        user=user,
        week_start=week_start,
        defaults={
            "headline": str(payload.get("headline") or "Your week").strip()[:255],
            "summary": str(payload.get("summary") or "").strip()[:2000],
            "wins": _clean_list(payload.get("wins"), 3),
            "slipped": _clean_list(payload.get("slipped"), 3),
            "focus_next": _clean_list(payload.get("focus_next"), 3),
            "stats": stats,
        },
    )
    return review
