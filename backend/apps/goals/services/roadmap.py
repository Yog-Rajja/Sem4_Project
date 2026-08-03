"""Roadmap generation: prompt the model, validate the JSON, hand back clean data.

The view layer never sees raw model output — only the normalized structure this
module guarantees.
"""

import datetime as dt
import logging

from django.conf import settings

from common.exceptions import ServiceError

from . import llm
from .prompts import (
    BREAKDOWN_SYSTEM_PROMPT,
    ROADMAP_SYSTEM_PROMPT,
    build_breakdown_user_prompt,
    build_roadmap_user_prompt,
)

logger = logging.getLogger(__name__)

MAX_MILESTONES = 12
MAX_TASKS_PER_MILESTONE = 15
MAX_SUBTASKS = 4


# --- Validation -----------------------------------------------------------

def _clean_str(value, max_length: int) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_length]


def _parse_date(value):
    """Return a date, or None. A malformed date is not worth failing a whole
    roadmap over — the user can fix one date far more easily than regenerate."""
    if not value or not isinstance(value, str):
        return None
    try:
        return dt.date.fromisoformat(value.strip()[:10])
    except ValueError:
        logger.debug("Discarding unparseable date from model: %r", value)
        return None


def validate_roadmap(payload) -> list[dict]:
    """Validate model output against the roadmap schema.

    Structure is enforced strictly; individual bad dates are dropped rather
    than rejected. Raises ServiceError if nothing usable survives.
    """
    if not isinstance(payload, dict):
        raise ServiceError(
            "The AI response was not in the expected format.",
            status_code=502,
            code="schema_invalid",
        )

    raw_milestones = payload.get("milestones")
    if not isinstance(raw_milestones, list) or not raw_milestones:
        raise ServiceError(
            "The AI did not return any milestones. Try rephrasing your goal, "
            "or build the roadmap manually.",
            status_code=502,
            code="schema_no_milestones",
        )

    milestones = []
    for index, raw in enumerate(raw_milestones[:MAX_MILESTONES]):
        if not isinstance(raw, dict):
            continue
        title = _clean_str(raw.get("title"), 255)
        if not title:
            continue

        raw_tasks = raw.get("tasks") if isinstance(raw.get("tasks"), list) else []
        tasks = []
        for t_index, raw_task in enumerate(raw_tasks[:MAX_TASKS_PER_MILESTONE]):
            if not isinstance(raw_task, dict):
                continue
            t_title = _clean_str(raw_task.get("title"), 255)
            if not t_title:
                continue
            tasks.append(
                {
                    "title": t_title,
                    "due_date": _parse_date(raw_task.get("due_date")),
                    "order": t_index,
                }
            )

        milestones.append(
            {
                "title": title,
                "target_date": _parse_date(raw.get("target_date")),
                # Fall back to the milestone title so the resource lookup always
                # has something to search for.
                "search_query": _clean_str(raw.get("search_query"), 255) or title,
                "order": index,
                "tasks": tasks,
            }
        )

    if not milestones:
        raise ServiceError(
            "The AI response had no usable milestones. Try again, or build "
            "the roadmap manually.",
            status_code=502,
            code="schema_no_valid_milestones",
        )
    return milestones


def validate_subtasks(payload, parent_due) -> list[dict]:
    if not isinstance(payload, dict) or not isinstance(payload.get("subtasks"), list):
        raise ServiceError(
            "The AI response was not in the expected format.",
            status_code=502,
            code="schema_invalid",
        )

    subtasks = []
    for index, raw in enumerate(payload["subtasks"][:MAX_SUBTASKS]):
        if not isinstance(raw, dict):
            continue
        title = _clean_str(raw.get("title"), 255)
        if not title:
            continue
        due = _parse_date(raw.get("due_date")) or parent_due
        subtasks.append({"title": title, "due_date": due, "order": index})

    if not subtasks:
        raise ServiceError(
            "The AI didn't return any usable steps. Try again.",
            status_code=502,
            code="schema_no_subtasks",
        )
    return subtasks


# --- Offline stub ---------------------------------------------------------

def _mock_roadmap(goal_text: str, target_date) -> list[dict]:
    """Deterministic roadmap for offline development (USE_MOCK_AI=true)."""
    today = dt.date.today()
    horizon = target_date or (today + dt.timedelta(days=90))
    span = max((horizon - today).days, 8)
    subject = goal_text.strip().rstrip(".")[:60] or "your goal"

    phases = [
        ("Understand the fundamentals", "beginner tutorial"),
        ("Build core skills with practice", "practice exercises"),
        ("Apply it to a real project", "project walkthrough"),
        ("Review, refine and finish strong", "advanced tips"),
    ]

    milestones = []
    for index, (phase, query_suffix) in enumerate(phases, start=1):
        m_date = today + dt.timedelta(days=round(span * index / len(phases)))
        tasks = []
        for t_index in range(3):
            offset = round(span * (index - 1) / len(phases)) + round(
                span / len(phases) * (t_index + 1) / 3
            )
            tasks.append(
                {
                    "title": f"{phase}: step {t_index + 1}",
                    "due_date": min(today + dt.timedelta(days=offset), m_date),
                    "order": t_index,
                }
            )
        milestones.append(
            {
                "title": phase,
                "target_date": m_date,
                "search_query": f"{subject} {query_suffix}",
                "order": index - 1,
                "tasks": tasks,
            }
        )
    return milestones


# --- Public API -----------------------------------------------------------

def generate_roadmap(goal_text: str, target_date=None, context: str | None = None) -> list[dict]:
    if settings.USE_MOCK_AI:
        logger.info("USE_MOCK_AI is on — returning stub roadmap")
        return _mock_roadmap(goal_text, target_date)

    payload = llm.complete_json(
        system=ROADMAP_SYSTEM_PROMPT,
        user=build_roadmap_user_prompt(
            goal_text=goal_text,
            today=dt.date.today().isoformat(),
            target_date=target_date.isoformat() if target_date else None,
            context=context,
        ),
        temperature=0.2,
    )
    return validate_roadmap(payload)


def generate_subtasks(task_title: str, goal_title: str, due_date=None) -> list[dict]:
    if settings.USE_MOCK_AI:
        base = due_date or (dt.date.today() + dt.timedelta(days=7))
        return [
            {"title": f"{task_title} — part {i + 1}",
             "due_date": base - dt.timedelta(days=(2 - i) * 2),
             "order": i}
            for i in range(3)
        ]

    payload = llm.complete_json(
        system=BREAKDOWN_SYSTEM_PROMPT,
        user=build_breakdown_user_prompt(
            task_title=task_title,
            goal_title=goal_title,
            today=dt.date.today().isoformat(),
            due_date=due_date.isoformat() if due_date else None,
        ),
        temperature=0.2,
    )
    return validate_subtasks(payload, parent_due=due_date)
