"""Completion certificates.

Unlike every other Studio document, a certificate is not built from a freeform
user prompt — its facts (who, what, when, how much) are known and computed
server-side, the same way the weekly review keeps the AI away from the
numbers. The model is only ever asked for one celebratory line, and if every
provider is exhausted the certificate still generates with a canned line
instead — an achievement that already happened shouldn't be blocked by a
spent daily quota.
"""

import datetime as dt
import logging

from django.conf import settings
from django.utils import timezone

from apps.goals.models import Goal
from apps.goals.services import llm

logger = logging.getLogger(__name__)

TAGLINE_SYSTEM_PROMPT = """\
You write one celebratory line for a completion certificate.

Reply with ONLY a JSON object: { "tagline": "string" }

Rules:
- Base it only on the numbers given. Never invent a fact, number or detail \
that was not provided.
- Warm and understated, not corporate. No exclamation marks, no emoji.
- Maximum 18 words.
- Never use an em dash.

Example — given "12 tasks, 3 milestones, 21 days":
{ "tagline": "Twelve tasks, three milestones, twenty-one days of showing up." }
"""

FALLBACK_TAGLINES = [
    "Every task on the list, done.",
    "One goal, fully seen through.",
    "The plan held, and so did you.",
]


def _fallback_tagline(total_tasks: int, milestone_count: int) -> str:
    if total_tasks and milestone_count:
        return (
            f"{total_tasks} tasks across {milestone_count} "
            f"milestone{'s' if milestone_count != 1 else ''}, all done."
        )
    return FALLBACK_TAGLINES[total_tasks % len(FALLBACK_TAGLINES)]


def _write_tagline(total_tasks: int, milestone_count: int, days_taken: int) -> str:
    """Never raises — a certificate must generate even with no AI available."""
    if settings.USE_MOCK_AI:
        return _fallback_tagline(total_tasks, milestone_count)

    try:
        payload = llm.complete_json(
            system=TAGLINE_SYSTEM_PROMPT,
            user=(
                f"{total_tasks} tasks, {milestone_count} milestones, "
                f"{days_taken} days.\n\nWrite the tagline JSON."
            ),
            temperature=0.6,
            retries=0,
        )
        tagline = payload.get("tagline") if isinstance(payload, dict) else None
        if isinstance(tagline, str) and tagline.strip():
            return tagline.strip()[:160]
    except Exception:
        logger.info("Tagline generation failed; using the canned fallback")

    return _fallback_tagline(total_tasks, milestone_count)


def build_certificate(goal: Goal, user) -> dict:
    """Compute the real stats and return certificate data.

    Caller is responsible for confirming the goal is actually complete —
    this only describes it.
    """
    total_tasks, done_tasks = goal.task_counts()
    milestone_count = goal.milestones.count()

    created = timezone.localtime(goal.created_at).date()
    today = timezone.localdate()
    days_taken = max((today - created).days, 1)

    return {
        "recipient_name": (user.first_name or user.username).strip(),
        "goal_title": goal.title,
        "completed_date": today.isoformat(),
        "started_date": created.isoformat(),
        "days_taken": days_taken,
        "total_tasks": total_tasks,
        "milestone_count": milestone_count,
        "tagline": _write_tagline(total_tasks, milestone_count, days_taken),
    }
