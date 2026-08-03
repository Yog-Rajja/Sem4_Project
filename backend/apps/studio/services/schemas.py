"""Document schemas, one per artifact kind.

Each entry carries the JSON shape the model must return, the prompt guidance
that produces it, and a validator that coerces whatever comes back into
something the renderer can trust. Adding a document type means adding one
entry here — nothing else in the pipeline changes.
"""

from apps.studio.models import Artifact

MAX_ITEMS = 24


# --- shared coercion helpers ---------------------------------------------

def text(value, limit=400) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    return value.strip()[:limit] if isinstance(value, str) else ""


def text_list(value, limit=200, cap=MAX_ITEMS) -> list[str]:
    if not isinstance(value, list):
        return []
    out = [text(item, limit) for item in value[:cap]]
    return [item for item in out if item]


def dict_list(value, cap=MAX_ITEMS) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [item for item in value[:cap] if isinstance(item, dict)]


def number(value, default=0) -> int:
    try:
        return max(0, int(float(value)))
    except (TypeError, ValueError):
        return default


# --- résumé ---------------------------------------------------------------

RESUME_SHAPE = """{
  "name": "string - full name",
  "headline": "string - e.g. 'Final-year Computer Science student'",
  "email": "string", "phone": "string", "location": "string",
  "links": [ { "label": "GitHub", "url": "https://…" } ],
  "summary": "string - 2 to 3 sentences, third person, no 'I'",
  "experience": [ { "role": "string", "organisation": "string",
                    "period": "string - e.g. 'Jun 2025 – Aug 2025'",
                    "bullets": ["string - achievement with a number where honest"] } ],
  "education": [ { "qualification": "string", "institution": "string",
                   "period": "string", "detail": "string - grade or focus" } ],
  "projects": [ { "name": "string", "period": "string",
                  "description": "string - one sentence",
                  "tech": ["string"] } ],
  "skills": [ { "group": "e.g. Languages", "items": ["string"] } ],
  "achievements": ["string"]
}"""

RESUME_GUIDANCE = """\
This is an Oxford-style academic CV: formal, understated, strictly factual. \
Reverse-chronological within every section.
- Never invent employers, grades, dates or numbers the user did not give. If \
something is unknown, leave the field empty rather than filling it plausibly.
- Bullets start with a past-tense verb and describe outcomes, not duties.
- Keep 3 to 5 bullets per role, one line each where possible.
- No first-person pronouns anywhere. No emoji, no icons, no self-praise \
adjectives like "passionate" or "hardworking".
- 4 to 6 skill groups at most."""


def validate_resume(raw: dict) -> dict:
    return {
        "name": text(raw.get("name"), 120) or "Your Name",
        "headline": text(raw.get("headline"), 160),
        "email": text(raw.get("email"), 120),
        "phone": text(raw.get("phone"), 60),
        "location": text(raw.get("location"), 120),
        "links": [
            {"label": text(item.get("label"), 40), "url": text(item.get("url"), 300)}
            for item in dict_list(raw.get("links"), 6)
            if text(item.get("url"), 300)
        ],
        "summary": text(raw.get("summary"), 700),
        "experience": [
            {
                "role": text(item.get("role"), 140),
                "organisation": text(item.get("organisation"), 160),
                "period": text(item.get("period"), 60),
                "bullets": text_list(item.get("bullets"), 300, 8),
            }
            for item in dict_list(raw.get("experience"), 10)
            if text(item.get("role"), 140) or text(item.get("organisation"), 160)
        ],
        "education": [
            {
                "qualification": text(item.get("qualification"), 160),
                "institution": text(item.get("institution"), 160),
                "period": text(item.get("period"), 60),
                "detail": text(item.get("detail"), 220),
            }
            for item in dict_list(raw.get("education"), 6)
            if text(item.get("qualification"), 160) or text(item.get("institution"), 160)
        ],
        "projects": [
            {
                "name": text(item.get("name"), 140),
                "period": text(item.get("period"), 60),
                "description": text(item.get("description"), 400),
                "tech": text_list(item.get("tech"), 40, 12),
            }
            for item in dict_list(raw.get("projects"), 8)
            if text(item.get("name"), 140)
        ],
        "skills": [
            {
                "group": text(item.get("group"), 60),
                "items": text_list(item.get("items"), 60, 20),
            }
            for item in dict_list(raw.get("skills"), 8)
            if text_list(item.get("items"), 60, 20)
        ],
        "achievements": text_list(raw.get("achievements"), 300, 8),
    }


# --- diet plan ------------------------------------------------------------

DIET_SHAPE = """{
  "title": "string",
  "goal_summary": "string - one sentence on what this plan is for",
  "daily_calories": 2000,
  "macros": { "protein_g": 0, "carbs_g": 0, "fat_g": 0 },
  "days": [ { "day": "Monday",
              "meals": [ { "slot": "Breakfast", "items": ["string"], "calories": 400 } ] } ],
  "notes": ["string - hydration, timing, substitutions"]
}"""

DIET_GUIDANCE = """\
- Exactly 7 days, Monday to Sunday, each with 4 to 5 meal slots \
(Breakfast, Mid-morning, Lunch, Snack, Dinner).
- 2 to 4 concrete food items per meal with rough quantities, e.g. \
"2 rotis", "150g paneer".
- Respect any cuisine, budget, allergy or vegetarian constraint in the request. \
Default to widely available Indian household foods unless told otherwise.
- Per-meal calories should roughly sum to daily_calories.
- This is general guidance, not medical advice. Do not address named medical \
conditions; if the request implies one, keep the plan conservative and say so \
in the notes."""


def validate_diet(raw: dict) -> dict:
    macros = raw.get("macros") if isinstance(raw.get("macros"), dict) else {}
    return {
        "title": text(raw.get("title"), 160) or "Meal plan",
        "goal_summary": text(raw.get("goal_summary"), 400),
        "daily_calories": number(raw.get("daily_calories"), 2000),
        "macros": {
            "protein_g": number(macros.get("protein_g")),
            "carbs_g": number(macros.get("carbs_g")),
            "fat_g": number(macros.get("fat_g")),
        },
        "days": [
            {
                "day": text(day.get("day"), 20),
                "meals": [
                    {
                        "slot": text(meal.get("slot"), 40),
                        "items": text_list(meal.get("items"), 160, 8),
                        "calories": number(meal.get("calories")),
                    }
                    for meal in dict_list(day.get("meals"), 8)
                    if text(meal.get("slot"), 40)
                ],
            }
            for day in dict_list(raw.get("days"), 7)
            if text(day.get("day"), 20)
        ],
        "notes": text_list(raw.get("notes"), 300, 8),
    }


# --- timetable ------------------------------------------------------------

TIMETABLE_SHAPE = """{
  "title": "string",
  "summary": "string - one sentence",
  "days": [ { "day": "Monday",
              "blocks": [ { "start": "07:00", "end": "08:30",
                            "activity": "string", "detail": "string" } ] } ],
  "notes": ["string"]
}"""

TIMETABLE_GUIDANCE = """\
- Exactly 7 days, Monday to Sunday.
- 4 to 7 blocks per day, in chronological order, using 24-hour HH:MM times \
that never overlap.
- Include realistic breaks, meals and at least one lighter day. A timetable \
nobody can follow is worse than none.
- Respect any college hours, job shifts or fixed commitments in the request."""


def validate_timetable(raw: dict) -> dict:
    return {
        "title": text(raw.get("title"), 160) or "Weekly timetable",
        "summary": text(raw.get("summary"), 400),
        "days": [
            {
                "day": text(day.get("day"), 20),
                "blocks": [
                    {
                        "start": text(block.get("start"), 8),
                        "end": text(block.get("end"), 8),
                        "activity": text(block.get("activity"), 120),
                        "detail": text(block.get("detail"), 200),
                    }
                    for block in dict_list(day.get("blocks"), 12)
                    if text(block.get("activity"), 120)
                ],
            }
            for day in dict_list(raw.get("days"), 7)
            if text(day.get("day"), 20)
        ],
        "notes": text_list(raw.get("notes"), 300, 8),
    }


# --- cover letter ---------------------------------------------------------

COVER_LETTER_SHAPE = """{
  "sender": { "name": "string", "email": "string", "phone": "string",
              "location": "string" },
  "recipient": "string - e.g. 'The Hiring Manager'",
  "company": "string",
  "role": "string",
  "date": "string - e.g. '3 August 2026'",
  "greeting": "string - e.g. 'Dear Hiring Manager,'",
  "paragraphs": ["string"],
  "closing": "string - e.g. 'Yours sincerely,'"
}"""

COVER_LETTER_GUIDANCE = """\
- Exactly 3 or 4 paragraphs: why this role, what you bring with evidence, \
what you would do in it, a brief close.
- Formal British register to match the CV. No bullet points, no headings.
- Never invent an achievement. Draw only on what the request supplies.
- Under 350 words in total."""


def validate_cover_letter(raw: dict) -> dict:
    sender = raw.get("sender") if isinstance(raw.get("sender"), dict) else {}
    return {
        "sender": {
            "name": text(sender.get("name"), 120) or "Your Name",
            "email": text(sender.get("email"), 120),
            "phone": text(sender.get("phone"), 60),
            "location": text(sender.get("location"), 120),
        },
        "recipient": text(raw.get("recipient"), 120) or "The Hiring Manager",
        "company": text(raw.get("company"), 160),
        "role": text(raw.get("role"), 160),
        "date": text(raw.get("date"), 40),
        "greeting": text(raw.get("greeting"), 120) or "Dear Hiring Manager,",
        "paragraphs": text_list(raw.get("paragraphs"), 1200, 6),
        "closing": text(raw.get("closing"), 60) or "Yours sincerely,",
    }


# --- project report -------------------------------------------------------

PROJECT_REPORT_SHAPE = """{
  "title": "string",
  "subtitle": "string",
  "author": "string",
  "abstract": "string - 3 to 5 sentences",
  "sections": [ { "heading": "string", "body": "string - 1 to 2 paragraphs",
                  "bullets": ["string"] } ],
  "conclusion": "string",
  "references": ["string"]
}"""

PROJECT_REPORT_GUIDANCE = """\
- 4 to 7 sections. For a software project prefer: Introduction, Objectives, \
Literature/Existing systems, Methodology, Implementation, Results, \
Future work.
- Formal academic register, third person, no marketing language.
- Bullets are optional per section; use them only where a list genuinely reads \
better than prose.
- References may be empty rather than invented. Never fabricate a citation."""


def validate_project_report(raw: dict) -> dict:
    return {
        "title": text(raw.get("title"), 200) or "Project Report",
        "subtitle": text(raw.get("subtitle"), 200),
        "author": text(raw.get("author"), 120),
        "abstract": text(raw.get("abstract"), 1500),
        "sections": [
            {
                "heading": text(section.get("heading"), 160),
                "body": text(section.get("body"), 2500),
                "bullets": text_list(section.get("bullets"), 300, 10),
            }
            for section in dict_list(raw.get("sections"), 12)
            if text(section.get("heading"), 160)
        ],
        "conclusion": text(raw.get("conclusion"), 1500),
        "references": text_list(raw.get("references"), 300, 20),
    }


# --- invitation card ------------------------------------------------------

INVITATION_SHAPE = """{
  "occasion": "string - e.g. 'Wedding', 'Engagement', 'Birthday', 'Housewarming'",
  "hosts": "string - who is inviting, may be empty",
  "headline": "string - the names or the person the card is about",
  "sub_headline": "string - e.g. 'are getting married' or 'turns 21'",
  "date_text": "string - written out, e.g. 'Sunday, 14 February 2027'",
  "time_text": "string - e.g. '11:00 AM onwards'",
  "venue_name": "string",
  "venue_address": "string",
  "message": "string - one warm line, max 20 words",
  "events": [ { "name": "Mehendi", "when": "13 Feb, 5 PM", "where": "Residence" } ],
  "rsvp": "string - name and number, may be empty",
  "footer_note": "string - short closing line, may be empty",
  "theme": {
    "palette": "one of: marigold, rose, royal, emerald, classic, midnight",
    "motif": "one of: floral, paisley, geometric, minimal"
  }
}"""

INVITATION_GUIDANCE = """\
- Fill only what the request supports. Never invent names, dates, venues or \
phone numbers — leave the field as an empty string instead.
- `events` is for multi-function celebrations (mehendi, haldi, sangeet, \
reception). Return an empty list if the request mentions only one event.
- Match `palette` to any colour the user names: orange/saffron/marigold → \
"marigold", pink/red → "rose", purple/gold → "royal", green → "emerald", \
navy/black → "midnight", otherwise "classic".
- Keep the tone warm and formal. No emoji.
- Do not attempt to describe logos, emblems or party symbols — the card is \
typeset, and any emblem is added by the user afterwards."""


def validate_invitation(raw: dict) -> dict:
    theme = raw.get("theme") if isinstance(raw.get("theme"), dict) else {}
    palettes = {"marigold", "rose", "royal", "emerald", "classic", "midnight"}
    motifs = {"floral", "paisley", "geometric", "minimal"}

    palette = text(theme.get("palette"), 20).lower()
    motif = text(theme.get("motif"), 20).lower()

    return {
        "occasion": text(raw.get("occasion"), 60) or "Celebration",
        "hosts": text(raw.get("hosts"), 200),
        "headline": text(raw.get("headline"), 120) or "You are invited",
        "sub_headline": text(raw.get("sub_headline"), 160),
        "date_text": text(raw.get("date_text"), 80),
        "time_text": text(raw.get("time_text"), 80),
        "venue_name": text(raw.get("venue_name"), 160),
        "venue_address": text(raw.get("venue_address"), 300),
        "message": text(raw.get("message"), 300),
        "events": [
            {
                "name": text(event.get("name"), 60),
                "when": text(event.get("when"), 80),
                "where": text(event.get("where"), 120),
            }
            for event in dict_list(raw.get("events"), 6)
            if text(event.get("name"), 60)
        ],
        "rsvp": text(raw.get("rsvp"), 200),
        "footer_note": text(raw.get("footer_note"), 160),
        "theme": {
            "palette": palette if palette in palettes else "classic",
            "motif": motif if motif in motifs else "floral",
        },
    }


# --- generated image ------------------------------------------------------

IMAGE_SHAPE = """{
  "image_prompt": "string - a rich, specific visual description for an image \
model: subject, style, composition, colour palette, lighting, aspect",
  "alt_text": "string - one sentence describing the finished image",
  "title": "string - 2 to 5 words naming the image"
}"""

IMAGE_GUIDANCE = """\
- Expand the user's request into a prompt an image model can work with: name \
the subject, the art style, the composition and the colour palette.
- Never include text, words, lettering or numbers in the image prompt. Image \
models render text badly, so any wording belongs on a typeset card instead.
- Do not describe real company, political or institutional logos and emblems."""


def validate_image_spec(raw: dict) -> dict:
    return {
        "image_prompt": text(raw.get("image_prompt"), 1200),
        "alt_text": text(raw.get("alt_text"), 400),
        "title": text(raw.get("title"), 120) or "Generated image",
    }


# --- registry -------------------------------------------------------------

SCHEMAS = {
    Artifact.Kind.RESUME: {
        "label": "Résumé",
        "shape": RESUME_SHAPE,
        "guidance": RESUME_GUIDANCE,
        "validator": validate_resume,
        "title_field": "name",
        "title_suffix": " — CV",
    },
    Artifact.Kind.DIET_PLAN: {
        "label": "Diet plan",
        "shape": DIET_SHAPE,
        "guidance": DIET_GUIDANCE,
        "validator": validate_diet,
        "title_field": "title",
    },
    Artifact.Kind.TIMETABLE: {
        "label": "Study timetable",
        "shape": TIMETABLE_SHAPE,
        "guidance": TIMETABLE_GUIDANCE,
        "validator": validate_timetable,
        "title_field": "title",
    },
    Artifact.Kind.COVER_LETTER: {
        "label": "Cover letter",
        "shape": COVER_LETTER_SHAPE,
        "guidance": COVER_LETTER_GUIDANCE,
        "validator": validate_cover_letter,
        "title_field": "role",
        "title_prefix": "Cover letter — ",
    },
    Artifact.Kind.PROJECT_REPORT: {
        "label": "Project report",
        "shape": PROJECT_REPORT_SHAPE,
        "guidance": PROJECT_REPORT_GUIDANCE,
        "validator": validate_project_report,
        "title_field": "title",
    },
    Artifact.Kind.INVITATION: {
        "label": "Invitation card",
        "shape": INVITATION_SHAPE,
        "guidance": INVITATION_GUIDANCE,
        "validator": validate_invitation,
        "title_field": "headline",
    },
    Artifact.Kind.IMAGE: {
        "label": "Generated image",
        "shape": IMAGE_SHAPE,
        "guidance": IMAGE_GUIDANCE,
        "validator": validate_image_spec,
        "title_field": "title",
    },
}


def derive_title(kind: str, data: dict) -> str:
    spec = SCHEMAS[kind]
    base = data.get(spec["title_field"]) or spec["label"]
    title = f"{spec.get('title_prefix', '')}{base}{spec.get('title_suffix', '')}"
    return title.strip()[:255] or spec["label"]
