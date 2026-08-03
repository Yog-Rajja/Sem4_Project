"""Show which models in the fallback chain still answer.

    python manage.py check_llm            # cheap: config only, no API calls
    python manage.py check_llm --probe    # spends one tiny request per model

Exists because "the AI is unavailable" has several causes that look identical:
a retired model (404), a spent daily quota (429), an overloaded server (503),
or simply no key. This names which.
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.goals.services import llm

OK = "  [ok]    "
BAD = "  [dead]  "
SKIP = "  [skip]  "

PROVIDER_NOTES = {
    "gemini": "Google AI Studio · free tier is 20 requests/day PER MODEL",
    "groq": "api.groq.com · fast inference of open models",
    "xai": "api.x.ai · Grok (note: a different company to Groq)",
    "openrouter": "openrouter.ai · aggregator, has :free model variants",
}


class Command(BaseCommand):
    help = "Report which models in LLM_FALLBACK_CHAIN are usable."

    def add_arguments(self, parser):
        parser.add_argument(
            "--probe",
            action="store_true",
            help="Actually call each model. Costs one small request each.",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("\nAPI keys"))
        keys = {
            "gemini": settings.GEMINI_API_KEY,
            "groq": settings.GROQ_API_KEY,
            "xai": settings.XAI_API_KEY,
            "openrouter": settings.OPENROUTER_API_KEY,
        }
        for provider, key in keys.items():
            mark = OK if key else SKIP
            state = f"set ({len(key)} chars)" if key else "not set"
            self.stdout.write(f"{mark}{provider:<12} {state:<18} {PROVIDER_NOTES[provider]}")

        chain = llm.resolve_chain()
        self.stdout.write(self.style.MIGRATE_HEADING("\nFallback chain"))
        if not chain:
            self.stdout.write(
                self.style.ERROR(
                    "  Nothing usable — every entry lacks an API key or names an "
                    "unknown provider.\n"
                )
            )
            return

        for index, (provider, model) in enumerate(chain, start=1):
            self.stdout.write(f"  {index}. {provider}:{model}")

        if not options.get("probe"):
            self.stdout.write(
                "\n  Add --probe to actually call each one "
                "(costs a small request per model).\n"
            )
            return

        self.stdout.write(self.style.MIGRATE_HEADING("\nProbing"))
        alive = 0
        for provider, model in chain:
            try:
                llm.PROVIDERS[provider](
                    model,
                    "Reply with JSON only.",
                    'Reply with exactly: {"ok": true}',
                    0,
                    None,
                )
                self.stdout.write(self.style.SUCCESS(f"{OK}{provider}:{model}"))
                alive += 1
            except llm.ProviderError as exc:
                hint = ""
                if exc.status == 429:
                    hint = "  → daily quota spent; another model has its own allowance"
                elif exc.status == 404:
                    hint = "  → model retired or not available to this key"
                elif exc.status in (401, 403):
                    hint = "  → key rejected"
                self.stdout.write(
                    self.style.WARNING(f"{BAD}{provider}:{model}  {exc.message}{hint}")
                )
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f"{BAD}{provider}:{model}  {exc}"))

        self.stdout.write("")
        if alive:
            self.stdout.write(
                self.style.SUCCESS(
                    f"  {alive} of {len(chain)} usable — requests will use the "
                    f"first one that answers.\n"
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    "  Nothing in the chain responded. Add another provider key "
                    "to backend/.env, or wait for the daily quota to reset.\n"
                )
            )
