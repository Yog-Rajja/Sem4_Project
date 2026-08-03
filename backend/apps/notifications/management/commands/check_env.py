"""Compare backend/.env against backend/.env.example.

Every time a feature adds a setting, an existing .env silently lacks the new
key — which is invisible until the feature quietly does nothing. This lists
what is missing, what is empty, and what is no longer used.

Never prints a value.
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

# Keys that are genuinely optional; empty is a valid, deliberate choice.
OPTIONAL_WHEN_EMPTY = {
    "GROQ_API_KEY",
    "GROQ_MODEL",
    "DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT",
    "DEFAULT_FROM_EMAIL",
    "EMAIL_TIMEOUT",
    "GEMINI_IMAGE_MODEL",
}

# What stops working when each key is missing or blank.
CONSEQUENCE = {
    "GEMINI_API_KEY": "roadmap generation, studio and document reading",
    "YOUTUBE_API_KEY": "learning-resource videos (search links still work)",
    "EMAIL_HOST_USER": "sending email — digests print to the console instead",
    "EMAIL_HOST_PASSWORD": "sending email — digests print to the console instead",
    "VAPID_PUBLIC_KEY": "push notifications",
    "VAPID_PRIVATE_KEY": "push notifications",
    "DJANGO_SECRET_KEY": "nothing locally, but never deploy without it",
}


def read_keys(path: Path) -> dict[str, str]:
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


class Command(BaseCommand):
    help = "Report settings missing from backend/.env, without printing values."

    def handle(self, *args, **options):
        base = Path(settings.BASE_DIR)
        env_path, example_path = base / ".env", base / ".env.example"

        if not env_path.exists():
            self.stdout.write(
                self.style.ERROR(
                    f"\nNo {env_path} — copy .env.example to .env and fill it in.\n"
                )
            )
            return

        env, example = read_keys(env_path), read_keys(example_path)

        missing = [k for k in example if k not in env]
        empty = [
            k for k, v in env.items()
            if not v and k not in OPTIONAL_WHEN_EMPTY
        ]
        unknown = [k for k in env if k not in example]

        self.stdout.write(self.style.MIGRATE_HEADING("\nbackend/.env"))
        self.stdout.write(f"  {len(env)} keys set, {len(example)} in the example\n")

        if missing:
            self.stdout.write(self.style.ERROR("  Missing entirely:"))
            for key in missing:
                note = CONSEQUENCE.get(key)
                self.stdout.write(f"    - {key}" + (f"  → breaks {note}" if note else ""))
            self.stdout.write("")

        if empty:
            self.stdout.write(self.style.WARNING("  Present but empty:"))
            for key in empty:
                note = CONSEQUENCE.get(key)
                self.stdout.write(f"    - {key}" + (f"  → breaks {note}" if note else ""))
            self.stdout.write("")

        if unknown:
            self.stdout.write("  Set locally but not in the example (probably fine):")
            for key in unknown:
                self.stdout.write(f"    - {key}")
            self.stdout.write("")

        if not missing and not empty:
            self.stdout.write(self.style.SUCCESS("  Everything needed is set.\n"))
        else:
            self.stdout.write(
                "  Copy any missing lines from backend/.env.example, then "
                "restart the backend.\n"
            )
