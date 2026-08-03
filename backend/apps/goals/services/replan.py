"""Adaptive re-planning and daily planning.

Both take the user's *current* state and ask the model to rearrange it rather
than invent something new — so completion history, resources and edits all
survive. Every id the model returns is checked against the ids we sent, which
is what stops a hallucinated id from touching the database.
"""

import datetime as dt
import json
import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from common.exceptions import ServiceError

from ..models import Task
from . import llm
from .prompts import (
    DAILY_PLAN_SYSTEM_PROMPT,
    REPLAN_SYSTEM_PROMPT,
    build_daily_plan_user_prompt,
    build_replan_user_prompt,
)

logger = logging.getLogger(__name__)

MAX_DAILY_PICKS = 8


def _parse_date(value):
    if not value or not isinstance(value, str):
        return None
    try:
        return dt.date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


# --- Re-plan --------------------------------------------------------------

def _serialise_outstanding(goal) -> tuple[str, dict, dict]:
    """Describe the unfinished work, and index it so we can validate the reply."""
    milestones, tasks = {}, {}
    lines = []

    for milestone in goal.milestones.all():
        pending = [t for t in milestone.tasks.all() if not t.is_complete]
        if milestone.is_complete or not pending:
            continue
        milestones[milestone.id] = milestone
        lines.append(
            f'- milestone id={milestone.id} "{milestone.title}" '
            f"currently due {milestone.target_date or 'unscheduled'}"
        )
        for task in pending:
            tasks[task.id] = task
            lines.append(
                f'    - task id={task.id} "{task.title}" '
                f"currently due {task.due_date or 'unscheduled'}"
            )

    return "\n".join(lines), milestones, tasks


def _mock_replan(milestones, tasks, deadline):
    """Offline stub: spread the remaining work evenly between now and the end."""
    today = timezone.localdate()
    end = deadline or today + dt.timedelta(days=60)
    span = max((end - today).days, len(milestones))

    result = []
    for index, milestone in enumerate(milestones.values(), start=1):
        m_date = today + dt.timedelta(days=round(span * index / len(milestones)))
        pending = [t for t in milestone.tasks.all() if not t.is_complete]
        result.append(
            {
                "id": milestone.id,
                "target_date": m_date,
                "tasks": [
                    {
                        "id": task.id,
                        "due_date": min(
                            today + dt.timedelta(days=round(span * index / len(milestones)) - i),
                            m_date,
                        ),
                    }
                    for i, task in enumerate(reversed(pending))
                ],
            }
        )
    return result, "Spread the remaining work evenly across the time left."


def replan_goal(goal) -> dict:
    """Reschedule everything unfinished. Returns a summary and what changed."""
    payload, milestones, tasks = _serialise_outstanding(goal)
    if not milestones:
        raise ServiceError(
            "There is nothing left to reschedule — every milestone is done.",
            status_code=400,
            code="nothing_to_replan",
        )

    today = timezone.localdate()
    total, done = goal.task_counts()
    progress = round(done * 100 / total) if total else 0

    if settings.USE_MOCK_AI:
        proposed, summary = _mock_replan(milestones, tasks, goal.target_date)
    else:
        response = llm.complete_json(
            system=REPLAN_SYSTEM_PROMPT,
            user=build_replan_user_prompt(
                goal_title=goal.title,
                today=today.isoformat(),
                deadline=goal.target_date.isoformat() if goal.target_date else None,
                progress=progress,
                payload=payload,
            ),
            temperature=0.2,
        )
        proposed, summary = _validate_replan(response, milestones, tasks)

    changed = _apply_replan(proposed, milestones, tasks, today)
    return {
        "summary": summary,
        "milestones_rescheduled": changed["milestones"],
        "tasks_rescheduled": changed["tasks"],
    }


def _validate_replan(payload, milestones, tasks):
    if not isinstance(payload, dict) or not isinstance(payload.get("milestones"), list):
        raise ServiceError(
            "The AI response was not in the expected format.",
            status_code=502,
            code="schema_invalid",
        )

    proposed = []
    for raw in payload["milestones"]:
        if not isinstance(raw, dict):
            continue
        # An id we did not send is a hallucination — drop it rather than trust it.
        milestone = milestones.get(raw.get("id"))
        if milestone is None:
            logger.warning("Re-plan returned unknown milestone id %r", raw.get("id"))
            continue

        entry = {"id": milestone.id, "target_date": _parse_date(raw.get("target_date")),
                 "tasks": []}
        for raw_task in raw.get("tasks") or []:
            if not isinstance(raw_task, dict):
                continue
            task = tasks.get(raw_task.get("id"))
            if task is None or task.milestone_id != milestone.id:
                logger.warning("Re-plan returned unknown task id %r", raw_task.get("id"))
                continue
            entry["tasks"].append({"id": task.id, "due_date": _parse_date(raw_task.get("due_date"))})
        proposed.append(entry)

    if not proposed:
        raise ServiceError(
            "The AI could not produce a usable schedule. Try again, or adjust "
            "the dates yourself.",
            status_code=502,
            code="replan_unusable",
        )

    summary = payload.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        summary = "Rescheduled the remaining work."
    return proposed, summary.strip()[:255]


@transaction.atomic
def _apply_replan(proposed, milestones, tasks, today):
    """Write the new dates, clamping anything the model put in the past."""
    changed = {"milestones": 0, "tasks": 0}

    for entry in proposed:
        milestone = milestones[entry["id"]]
        new_date = entry["target_date"]
        if new_date:
            new_date = max(new_date, today)
            if milestone.target_date != new_date:
                milestone.target_date = new_date
                milestone.save(update_fields=["target_date"])
                changed["milestones"] += 1

        for raw_task in entry["tasks"]:
            task = tasks[raw_task["id"]]
            due = raw_task["due_date"]
            if not due:
                continue
            due = max(due, today)
            if milestone.target_date:
                due = min(due, milestone.target_date)
            if task.due_date != due:
                task.due_date = due
                task.save(update_fields=["due_date"])
                changed["tasks"] += 1

    return changed


# --- Plan my day ----------------------------------------------------------

def _serialise_candidates(candidates, today) -> str:
    lines = []
    for task in candidates:
        if task.due_date and task.due_date < today:
            when = f"OVERDUE by {(today - task.due_date).days} days"
        elif task.due_date == today:
            when = "due today"
        elif task.due_date:
            when = f"due in {(task.due_date - today).days} days"
        else:
            when = "no due date"
        lines.append(
            f'- id={task.id} "{task.title}" '
            f"[goal: {task.milestone.goal.title}] ({when})"
        )
    return "\n".join(lines)


def plan_day(user, minutes: int) -> dict:
    today = timezone.localdate()
    horizon = today + dt.timedelta(days=14)

    candidates = list(
        Task.objects.filter(milestone__goal__user=user, is_complete=False)
        .filter(due_date__isnull=False, due_date__lte=horizon)
        .select_related("milestone", "milestone__goal")
        .order_by("due_date")[:40]
    )
    if not candidates:
        # Nothing scheduled soon — fall back to anything outstanding at all.
        candidates = list(
            Task.objects.filter(milestone__goal__user=user, is_complete=False)
            .select_related("milestone", "milestone__goal")
            .order_by("order")[:20]
        )

    if not candidates:
        raise ServiceError(
            "You have no outstanding tasks to plan. Create a goal first.",
            status_code=400,
            code="nothing_to_plan",
        )

    by_id = {task.id: task for task in candidates}

    if settings.USE_MOCK_AI:
        budget, picks = minutes, []
        for task in candidates:
            if budget < 30:
                break
            picks.append({"id": task.id, "reason": "Due soonest", "estimated_minutes": 30})
            budget -= 30
        summary = f"{len(picks)} tasks that fit your {minutes} minutes today."
    else:
        response = llm.complete_json(
            system=DAILY_PLAN_SYSTEM_PROMPT,
            user=build_daily_plan_user_prompt(
                today=today.isoformat(),
                minutes=minutes,
                payload=_serialise_candidates(candidates, today),
            ),
            temperature=0.3,
        )
        picks, summary = _validate_daily_plan(response, by_id)

    return {
        "summary": summary,
        "available_minutes": minutes,
        "picks": [
            {
                "task": by_id[pick["id"]],
                "reason": pick["reason"],
                "estimated_minutes": pick["estimated_minutes"],
            }
            for pick in picks
        ],
    }


def _validate_daily_plan(payload, by_id):
    if not isinstance(payload, dict) or not isinstance(payload.get("picks"), list):
        raise ServiceError(
            "The AI response was not in the expected format.",
            status_code=502,
            code="schema_invalid",
        )

    picks, seen = [], set()
    for raw in payload["picks"][:MAX_DAILY_PICKS]:
        if not isinstance(raw, dict):
            continue
        task_id = raw.get("id")
        if task_id not in by_id or task_id in seen:
            logger.warning("Daily plan returned unusable task id %r", task_id)
            continue
        seen.add(task_id)

        try:
            estimate = int(raw.get("estimated_minutes") or 30)
        except (TypeError, ValueError):
            estimate = 30
        reason = raw.get("reason")
        picks.append(
            {
                "id": task_id,
                "reason": (reason.strip()[:120] if isinstance(reason, str) else "")
                or "Worth doing today",
                "estimated_minutes": max(5, min(estimate, 240)),
            }
        )

    if not picks:
        raise ServiceError(
            "The AI couldn't put a plan together. Try again in a moment.",
            status_code=502,
            code="daily_plan_unusable",
        )

    summary = payload.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        summary = "Here's a realistic plan for today."
    return picks, summary.strip()[:255]
