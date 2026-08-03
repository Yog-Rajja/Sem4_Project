"""Exercise the real Gemini and YouTube APIs and report on output quality.

The automated test suite mocks both providers, so it proves the plumbing is
correct but says nothing about what the live model actually returns. This
command closes that gap — run it once after adding your keys, and again as a
pre-flight check before demoing.

    python manage.py verify_ai
    python manage.py verify_ai --goal "Crack GATE in 8 months" --skip-youtube

It makes real API calls. Each roadmap is one Gemini request; the YouTube check
costs 100 quota units of the 10,000 daily allowance.
"""

import datetime as dt

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from common.exceptions import ServiceError

from apps.goals.services import resources as resources_service
from apps.goals.services import roadmap as roadmap_service

# Deliberately spread across goal shapes: exam prep, an open-ended career goal,
# a concrete skill, and one with nothing to "learn" at all. The few-shot example
# in the prompt is a savings goal, so the others test that it generalises.
SAMPLE_GOALS = [
    ("Crack GATE in 8 months", 240),
    ("Get a software engineering job", 180),
    ("Learn React and build a portfolio", 90),
    ("Save 2 lakh rupees for a bike in 10 months", 300),
]

# The free tier allows only 20 generate requests per day per model, so the
# default run checks the two most dissimilar goals (exam prep, and a savings
# goal with nothing to "learn") rather than spending a fifth of the day's
# allowance. Use --all before a demo, when it matters more.
QUICK_GOALS = [SAMPLE_GOALS[0], SAMPLE_GOALS[3]]

OK = "  [ok]   "
WARN = "  [warn] "
BAD = "  [FAIL] "


class Command(BaseCommand):
    help = "Run real Gemini and YouTube calls and report on the quality of the output."

    def add_arguments(self, parser):
        parser.add_argument("--goal", help="Check a single goal instead of the samples.")
        parser.add_argument(
            "--all",
            action="store_true",
            dest="run_all",
            help="Check all four sample goals instead of the usual two.",
        )
        parser.add_argument(
            "--skip-youtube", action="store_true", help="Skip the resource lookup."
        )

    # --- reporting helpers ------------------------------------------------
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.failures = 0
        self.warnings = 0

    def ok(self, message):
        self.stdout.write(self.style.SUCCESS(OK + message))

    def warn(self, message):
        self.warnings += 1
        self.stdout.write(self.style.WARNING(WARN + message))

    def bad(self, message):
        self.failures += 1
        self.stdout.write(self.style.ERROR(BAD + message))

    def expect(self, condition, good, bad, fatal=True):
        if condition:
            self.ok(good)
        elif fatal:
            self.bad(bad)
        else:
            self.warn(bad)

    # --- main -------------------------------------------------------------
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("\nConfiguration"))

        if settings.USE_MOCK_AI:
            self.bad(
                "USE_MOCK_AI is true — this would test the stub, not the real model. "
                "Set USE_MOCK_AI=false in backend/.env."
            )
            return

        self.expect(
            bool(settings.GEMINI_API_KEY),
            f"LLM provider: {settings.LLM_PROVIDER} ({settings.GEMINI_MODEL})",
            "No GEMINI_API_KEY set — add one to backend/.env.",
        )
        if self.failures:
            return

        self.expect(
            bool(settings.YOUTUBE_API_KEY),
            "YouTube API key present",
            "No YOUTUBE_API_KEY — milestones will fall back to the search link only.",
            fatal=False,
        )

        if options.get("goal"):
            goals = [(options["goal"], 180)]
        else:
            goals = SAMPLE_GOALS if options.get("run_all") else QUICK_GOALS

        self.stdout.write(
            f"  Will use {len(goals)} of today's 20 free generate requests "
            f"for this model."
        )
        first_query = None

        for text, horizon_days in goals:
            query = self.run_roadmap_checks(text, horizon_days)
            first_query = first_query or query

        if not options.get("skip_youtube") and settings.YOUTUBE_API_KEY and first_query:
            self.run_youtube_checks(first_query)

        self.summarise()

    # --- roadmap ----------------------------------------------------------
    def run_roadmap_checks(self, text, horizon_days):
        self.stdout.write(self.style.MIGRATE_HEADING(f"\nRoadmap — “{text}”"))

        today = dt.date.today()
        deadline = today + dt.timedelta(days=horizon_days)

        try:
            milestones = roadmap_service.generate_roadmap(text, deadline)
        except ServiceError as exc:
            self.bad(f"Generation failed: {exc.detail}")
            return None

        self.expect(
            4 <= len(milestones) <= 6,
            f"{len(milestones)} milestones",
            f"{len(milestones)} milestones (prompt asks for 4–6)",
            fatal=False,
        )

        task_counts = [len(m["tasks"]) for m in milestones]
        self.expect(
            all(3 <= n <= 5 for n in task_counts),
            f"Tasks per milestone: {task_counts}",
            f"Tasks per milestone outside 3–5: {task_counts}",
            fatal=False,
        )

        dated = [m["target_date"] for m in milestones if m["target_date"]]
        self.expect(
            len(dated) == len(milestones),
            "Every milestone has a target date",
            f"{len(milestones) - len(dated)} milestone(s) missing a target date",
            fatal=False,
        )
        self.expect(
            dated == sorted(dated),
            "Milestone dates increase in order",
            f"Milestone dates are out of order: {[d.isoformat() for d in dated]}",
        )
        if dated:
            self.expect(
                dated[0] >= today,
                "No milestone starts in the past",
                f"First milestone is in the past ({dated[0]})",
            )
            self.expect(
                dated[-1] <= deadline,
                f"Final milestone lands by the deadline ({dated[-1]})",
                f"Final milestone {dated[-1]} overruns the {deadline} deadline",
            )

        slipped = [
            (m["title"], t["title"])
            for m in milestones
            for t in m["tasks"]
            if t["due_date"] and m["target_date"] and t["due_date"] > m["target_date"]
        ]
        self.expect(
            not slipped,
            "Every task falls on or before its milestone date",
            f"{len(slipped)} task(s) due after their milestone: {slipped[:2]}",
        )

        undated_tasks = sum(1 for m in milestones for t in m["tasks"] if not t["due_date"])
        self.expect(
            undated_tasks == 0,
            "Every task has a due date",
            f"{undated_tasks} task(s) have no due date",
            fatal=False,
        )

        # search_query should name a topic to learn, not restate the action.
        queries = [m["search_query"] for m in milestones]
        action_like = [q for q in queries if q.lower().startswith(("finish", "complete", "do "))]
        self.expect(
            not action_like,
            "Search topics describe subjects, not actions",
            f"Search topics read like actions: {action_like}",
            fatal=False,
        )
        self.expect(
            all(2 <= len(q.split()) <= 8 for q in queries),
            "Search topics are a sensible length",
            f"Search topics look off: {[q for q in queries if not 2 <= len(q.split()) <= 8]}",
            fatal=False,
        )

        generic = [
            t["title"]
            for m in milestones
            for t in m["tasks"]
            if t["title"].lower().startswith(("task ", "step ", "continue"))
        ]
        self.expect(
            not generic,
            "No filler task titles",
            f"Filler task titles found: {generic[:3]}",
            fatal=False,
        )

        self.stdout.write("\n  Sample of what the model produced:")
        for m in milestones[:2]:
            date = m["target_date"].isoformat() if m["target_date"] else "no date"
            self.stdout.write(f"    · {m['title']}  ({date})")
            self.stdout.write(f"        topic: {m['search_query']}")
            for t in m["tasks"][:2]:
                due = t["due_date"].isoformat() if t["due_date"] else "no date"
                self.stdout.write(f"        - {t['title']}  ({due})")

        return queries[0] if queries else None

    # --- youtube ----------------------------------------------------------
    def run_youtube_checks(self, query):
        self.stdout.write(self.style.MIGRATE_HEADING(f"\nResources — “{query}”"))

        videos = resources_service._fetch_youtube(query)
        self.expect(
            bool(videos),
            f"YouTube returned {len(videos)} video(s)",
            "YouTube returned nothing — check the key and that the Data API v3 is enabled",
        )

        for video in videos:
            try:
                response = requests.head(video["url"], timeout=10, allow_redirects=True)
                reachable = response.status_code < 400
            except requests.RequestException:
                reachable = False
            self.expect(
                reachable,
                f"Link resolves: {video['title'][:58]}",
                f"Dead link: {video['url']}",
                fatal=False,
            )
            self.stdout.write(f"           {video['channel_title']} — {video['url']}")

        search_url = resources_service.google_search_url(query)
        self.expect(
            search_url.startswith("https://www.google.com/search?q="),
            "Google search fallback link built",
            "Search fallback link is malformed",
        )

    # --- summary ----------------------------------------------------------
    def summarise(self):
        self.stdout.write(self.style.MIGRATE_HEADING("\nSummary"))
        if self.failures:
            self.stdout.write(
                self.style.ERROR(
                    f"  {self.failures} failure(s), {self.warnings} warning(s) — "
                    f"worth fixing before you demo."
                )
            )
        elif self.warnings:
            self.stdout.write(
                self.style.WARNING(
                    f"  No failures, {self.warnings} warning(s) — "
                    f"cosmetic, safe to demo."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("  All checks passed. Ready to demo.\n"))
