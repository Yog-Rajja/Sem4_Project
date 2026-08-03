"""Send the daily digest to everyone who has asked for one.

Scheduled by the operating system rather than a task queue — there is exactly
one job and it runs once a day, so Celery and Redis would be two extra things
to deploy for no benefit.

Windows (Task Scheduler), daily at 08:00:
    schtasks /create /tn "SmartCompanionDigest" /sc daily /st 08:00 ^
      /tr "D:\\Sem4_Project\\.venv\\Scripts\\python.exe D:\\Sem4_Project\\backend\\manage.py notify_daily"

Linux/macOS (crontab -e):
    0 * * * * /path/to/.venv/bin/python /path/to/backend/manage.py notify_daily

Running hourly is fine: each user is only sent to once per day, and only once
their chosen hour has arrived.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.notifications import services

User = get_user_model()


class Command(BaseCommand):
    help = "Send the daily task digest by push and/or email."

    def add_arguments(self, parser):
        parser.add_argument("--user", help="Send to one username only.")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Ignore preferences, schedule and the already-sent guard.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be sent without sending it.",
        )

    def handle(self, *args, **options):
        users = User.objects.filter(is_active=True)
        if options.get("user"):
            users = users.filter(username=options["user"])

        if not services.push_configured():
            self.stdout.write(
                self.style.WARNING(
                    "VAPID keys not set — push will be skipped. "
                    "Run: manage.py generate_vapid_keys"
                )
            )

        sent = skipped = 0
        for user in users:
            if options.get("dry_run"):
                digest = services.build_digest(user)
                self.stdout.write(
                    f"  {user.username}: {digest['title']} — {digest['body'][:60]}"
                )
                continue

            result = services.deliver_daily(user, force=options.get("force", False))
            if result.get("skipped"):
                skipped += 1
                continue

            sent += 1
            self.stdout.write(
                f"  {user.username}: {result['title']} "
                f"(push {result['pushed']}, email {'yes' if result['emailed'] else 'no'})"
            )

        if not options.get("dry_run"):
            self.stdout.write(
                self.style.SUCCESS(f"\nDelivered to {sent} user(s), skipped {skipped}.")
            )
