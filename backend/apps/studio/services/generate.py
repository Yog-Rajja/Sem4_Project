"""Artifact generation: work out what the user wants, then build it.

Classification is deliberately cheap-first — an obvious request like "make me
a resume" is decided by keywords and never costs an API call. Only genuinely
ambiguous prompts fall through to the model.
"""

import datetime as dt
import logging

from django.conf import settings

from common.exceptions import ServiceError

from apps.goals.services import llm
from apps.studio.models import Artifact

from .schemas import SCHEMAS, derive_title

logger = logging.getLogger(__name__)

# Weighted keywords per kind. Longer, more specific phrases score higher.
KEYWORDS = {
    Artifact.Kind.RESUME: [
        ("resume", 3), ("résumé", 3), ("cv", 3), ("curriculum vitae", 4),
        ("bio data", 3), ("biodata", 3),
    ],
    Artifact.Kind.COVER_LETTER: [
        ("cover letter", 5), ("covering letter", 5), ("motivation letter", 4),
        ("application letter", 4), ("sop", 3), ("statement of purpose", 4),
    ],
    Artifact.Kind.DIET_PLAN: [
        ("diet", 3), ("meal plan", 4), ("meal chart", 4), ("nutrition", 3),
        ("食事", 2), ("calorie", 2), ("weight loss plan", 4), ("bulking", 3),
        ("food chart", 4), ("eating plan", 4),
    ],
    Artifact.Kind.TIMETABLE: [
        ("timetable", 4), ("time table", 4), ("study schedule", 4),
        ("study plan", 3), ("routine", 3), ("daily schedule", 4),
        ("weekly schedule", 4), ("revision schedule", 4),
    ],
    Artifact.Kind.PROJECT_REPORT: [
        ("project report", 5), ("report", 2), ("documentation", 3),
        ("synopsis", 3), ("thesis", 3), ("dissertation", 4), ("black book", 3),
    ],
    Artifact.Kind.INVITATION: [
        ("wedding card", 6), ("wedding invitation", 6), ("invitation card", 6),
        ("invite", 4), ("invitation", 5), ("shaadi", 4), ("marriage card", 6),
        ("engagement card", 6), ("birthday card", 6), ("anniversary card", 6),
        ("greeting card", 5), ("housewarming", 4), ("reception card", 5),
        ("card", 3), ("mehendi", 4), ("sangeet", 4), ("haldi", 4),
    ],
    Artifact.Kind.IMAGE: [
        ("generate an image", 6), ("create an image", 6), ("an image of", 5),
        ("a picture of", 5), ("illustration", 4), ("artwork", 4),
        ("wallpaper", 4), ("poster", 3), ("banner", 3), ("photo of", 4),
        ("draw", 3), ("render", 3),
    ],
}

CLASSIFY_SYSTEM_PROMPT = """\
You route a request to the right document type.

Reply with ONLY a JSON object: { "kind": "..." }

Allowed values:
- "resume" — a CV or résumé
- "cover_letter" — a letter accompanying an application
- "diet_plan" — meals, nutrition, eating schedule
- "timetable" — a study or daily schedule
- "project_report" — academic or project write-up
- "invitation" — a card inviting people to an occasion: wedding, engagement,
  birthday, housewarming, reception
- "image" — a picture, illustration, poster or artwork, where the point is the
  visual itself rather than any wording on it

Pick the single closest match. If the request is for something to look at
rather than something to read, prefer "invitation" when it announces an
occasion and "image" otherwise.
"""


def _keyword_guess(prompt: str):
    """Return (kind, score) for the best keyword match."""
    lowered = f" {prompt.lower()} "
    best, best_score = None, 0
    for kind, entries in KEYWORDS.items():
        score = sum(weight for term, weight in entries if term in lowered)
        if score > best_score:
            best, best_score = kind, score
    return best, best_score


def classify(prompt: str) -> str:
    kind, score = _keyword_guess(prompt)
    # A decisive keyword hit is more reliable than a model round-trip, and free.
    if kind and score >= 3:
        return kind

    if settings.USE_MOCK_AI:
        return kind or Artifact.Kind.RESUME

    try:
        response = llm.complete_json(
            system=CLASSIFY_SYSTEM_PROMPT,
            user=f"Request: {prompt}\n\nWhich document type?",
            temperature=0,
            retries=0,
        )
        guess = response.get("kind") if isinstance(response, dict) else None
        if guess in SCHEMAS:
            return guess
    except ServiceError:
        logger.warning("Classification call failed; falling back to keywords")

    if kind:
        return kind

    # Last resort. Previously this was always "resume", which meant an
    # unrecognised request — "make me a wedding card" — silently came back as a
    # CV. Anything that reads as an occasion or a visual now lands somewhere
    # sensible instead.
    lowered = prompt.lower()
    if any(word in lowered for word in ("card", "invit", "wedding", "birthday", "anniversary")):
        return Artifact.Kind.INVITATION
    if any(word in lowered for word in ("image", "picture", "poster", "design", "logo", "art")):
        return Artifact.Kind.IMAGE
    logger.info("Unclassifiable studio prompt, defaulting to resume: %r", prompt[:80])
    return Artifact.Kind.RESUME


def _build_system_prompt(kind: str) -> str:
    spec = SCHEMAS[kind]
    return (
        f"You produce a {spec['label']} as structured data.\n\n"
        f"Reply with ONLY a JSON object matching this shape. No prose, no "
        f"markdown fences.\n\n{spec['shape']}\n\n"
        f"Rules:\n{spec['guidance']}\n\n"
        f"Fill every field you reasonably can from the request. Leave a field "
        f"empty rather than inventing a fact about the person. Never use an "
        f"em dash anywhere in your reply; use a comma, a period, or a colon "
        f"instead."
    )


def _build_user_prompt(
    prompt: str, source_text: str | None, user_context: dict | None = None
) -> str:
    today = dt.date.today().strftime("%d %B %Y")
    parts = [f"Today's date: {today}", f"Request: {prompt}"]

    # The account already holds these, so using them is not invention — and
    # without it a CV comes out addressed to "Your Name".
    if user_context:
        known = [f"{key}: {value}" for key, value in user_context.items() if value]
        if known:
            parts.append(
                "Known details about the user — use these verbatim where the "
                "document calls for them:\n" + "\n".join(known)
            )

    if source_text:
        parts.append(
            "Use the following material the user supplied as the source of "
            f"facts. Prefer it over assumptions:\n\n{source_text[:12000]}"
        )
    parts.append("Return the JSON.")
    return "\n\n".join(parts)


def _mock_data(kind: str, prompt: str) -> dict:
    """Offline stubs shaped like the real thing, so the renderers can be
    developed and tested without burning quota."""
    subject = prompt.strip()[:60] or "your request"
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    if kind == Artifact.Kind.RESUME:
        return {
            "name": "Manav Sharma",
            "headline": "Final-year Computer Science student",
            "email": "manav@example.com",
            "phone": "+91 90000 00000",
            "location": "Pune, India",
            "links": [{"label": "GitHub", "url": "https://github.com/example"}],
            "summary": f"Computer science student focused on {subject}.",
            "experience": [
                {
                    "role": "Software Engineering Intern",
                    "organisation": "Example Technologies",
                    "period": "Jun 2025 – Aug 2025",
                    "bullets": [
                        "Built a REST API serving 20 endpoints.",
                        "Cut page load time by 40% through query optimisation.",
                    ],
                }
            ],
            "education": [
                {
                    "qualification": "B.E. Computer Engineering",
                    "institution": "Example Institute of Technology",
                    "period": "2022 – 2026",
                    "detail": "CGPA 8.6/10",
                }
            ],
            "projects": [
                {
                    "name": "Smart Companion",
                    "period": "2026",
                    "description": "AI goal-planning dashboard with roadmap generation.",
                    "tech": ["Django", "React", "Gemini"],
                }
            ],
            "skills": [
                {"group": "Languages", "items": ["Python", "JavaScript", "SQL"]},
                {"group": "Frameworks", "items": ["Django", "React"]},
            ],
            "achievements": ["Finalist, institute hackathon 2025"],
        }

    if kind == Artifact.Kind.DIET_PLAN:
        return {
            "title": f"Meal plan for {subject}",
            "goal_summary": "A balanced seven-day plan built from everyday foods.",
            "daily_calories": 2000,
            "macros": {"protein_g": 110, "carbs_g": 230, "fat_g": 60},
            "days": [
                {
                    "day": day,
                    "meals": [
                        {"slot": "Breakfast", "items": ["2 rotis", "1 bowl dal"], "calories": 450},
                        {"slot": "Lunch", "items": ["Rice 1 cup", "Paneer 150g"], "calories": 650},
                        {"slot": "Snack", "items": ["Banana", "Handful of almonds"], "calories": 250},
                        {"slot": "Dinner", "items": ["2 rotis", "Mixed vegetables"], "calories": 550},
                    ],
                }
                for day in days
            ],
            "notes": ["Drink 3 litres of water daily.", "Adjust portions to appetite."],
        }

    if kind == Artifact.Kind.TIMETABLE:
        return {
            "title": f"Weekly timetable for {subject}",
            "summary": "A realistic week with built-in breaks and one lighter day.",
            "days": [
                {
                    "day": day,
                    "blocks": [
                        {"start": "07:00", "end": "08:30", "activity": "Deep study", "detail": "Hardest topic first"},
                        {"start": "09:00", "end": "13:00", "activity": "College", "detail": ""},
                        {"start": "17:00", "end": "18:30", "activity": "Practice problems", "detail": ""},
                        {"start": "20:00", "end": "21:00", "activity": "Revision", "detail": "Yesterday's notes"},
                    ],
                }
                for day in days
            ],
            "notes": ["Keep Sunday evening free."],
        }

    if kind == Artifact.Kind.COVER_LETTER:
        return {
            "sender": {
                "name": "Manav Sharma",
                "email": "manav@example.com",
                "phone": "+91 90000 00000",
                "location": "Pune, India",
            },
            "recipient": "The Hiring Manager",
            "company": "Example Technologies",
            "role": subject,
            "date": dt.date.today().strftime("%d %B %Y"),
            "greeting": "Dear Hiring Manager,",
            "paragraphs": [
                f"I am writing to apply for the {subject} position.",
                "During my internship I built and shipped a REST API used across three teams.",
                "I would welcome the opportunity to discuss how I could contribute.",
            ],
            "closing": "Yours sincerely,",
        }

    if kind == Artifact.Kind.INVITATION:
        return {
            "occasion": "Wedding",
            "hosts": "Mr and Mrs Sharma",
            "headline": "Aarav & Diya",
            "sub_headline": "request the pleasure of your company",
            "date_text": "Sunday, 14 February 2027",
            "time_text": "11:00 AM onwards",
            "venue_name": "The Grand Palace",
            "venue_address": "MG Road, Pune",
            "message": "Together with our families, we invite you to share our joy.",
            "events": [
                {"name": "Mehendi", "when": "12 Feb, 5 PM", "where": "Residence"},
                {"name": "Sangeet", "when": "13 Feb, 7 PM", "where": "The Grand Palace"},
            ],
            "rsvp": "Rohan · +91 90000 00000",
            "footer_note": "We look forward to celebrating with you.",
            "theme": {"palette": "marigold", "motif": "floral"},
        }

    if kind == Artifact.Kind.IMAGE:
        return {
            "image_prompt": f"A flat vector illustration of {subject}, warm palette",
            "alt_text": f"Illustration of {subject}",
            "title": subject[:40] or "Generated image",
        }

    return {
        "title": f"Project Report on {subject}",
        "subtitle": "A final-year engineering project",
        "author": "Manav Sharma",
        "abstract": f"This report documents the design and implementation of {subject}.",
        "sections": [
            {"heading": "Introduction", "body": "The problem and its context.", "bullets": []},
            {"heading": "Methodology", "body": "The approach taken.", "bullets": ["Requirement analysis", "Iterative build"]},
            {"heading": "Implementation", "body": "How the system was built.", "bullets": []},
        ],
        "conclusion": "The system meets its stated objectives.",
        "references": [],
    }


def generate_artifact(
    prompt: str,
    kind: str | None = None,
    source_text: str | None = None,
    user_context: dict | None = None,
):
    """Returns (kind, validated_data, title)."""
    resolved = kind if kind in SCHEMAS else classify(prompt)

    if settings.USE_MOCK_AI:
        raw = _mock_data(resolved, prompt)
    else:
        raw = llm.complete_json(
            system=_build_system_prompt(resolved),
            user=_build_user_prompt(prompt, source_text, user_context),
            temperature=0.35,
        )

    if not isinstance(raw, dict):
        raise ServiceError(
            "The AI response was not in the expected format.",
            status_code=502,
            code="schema_invalid",
        )

    data = SCHEMAS[resolved]["validator"](raw)
    return resolved, data, derive_title(resolved, data)
