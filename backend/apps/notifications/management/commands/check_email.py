"""Diagnose email delivery and, optionally, send a real test message.

    python manage.py check_email
    python manage.py check_email --to you@gmail.com

Exists because "the email didn't arrive" has half a dozen causes that all look
identical from the outside — no credentials, spaces in the app password, 2FA
not enabled, the wrong port, a blocked network. This names the actual one.
"""

import smtplib
import socket

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.management.base import BaseCommand

OK = "  [ok]   "
BAD = "  [FAIL] "
INFO = "  [info] "


class Command(BaseCommand):
    help = "Check the email configuration and optionally send a test message."

    def add_arguments(self, parser):
        parser.add_argument("--to", help="Send a real test message to this address.")

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("\nEmail configuration"))

        using_console = settings.EMAIL_BACKEND.endswith("console.EmailBackend")
        if using_console:
            self.stdout.write(
                self.style.WARNING(
                    BAD
                    + "No mailbox configured — mail is printed to this console, "
                    + "not sent."
                )
            )
            self.stdout.write(
                "\n  Add these to backend/.env, then restart the backend:\n"
            )
            self.stdout.write("    EMAIL_HOST_USER=your.address@gmail.com")
            self.stdout.write("    EMAIL_HOST_PASSWORD=your16charapppassword")
            self.stdout.write(
                "\n  The app password comes from "
                "https://myaccount.google.com/apppasswords"
            )
            self.stdout.write(
                "  (2-Step Verification must be on, or that page won't offer it).\n"
            )
            return

        self.stdout.write(OK + f"Host      : {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
        self.stdout.write(OK + f"TLS       : {settings.EMAIL_USE_TLS}")
        self.stdout.write(OK + f"Username  : {settings.EMAIL_HOST_USER}")
        self.stdout.write(
            OK + f"Password  : set, {len(settings.EMAIL_HOST_PASSWORD)} characters"
        )
        self.stdout.write(OK + f"From      : {settings.DEFAULT_FROM_EMAIL}")

        if len(settings.EMAIL_HOST_PASSWORD) != 16 and "gmail" in settings.EMAIL_HOST:
            self.stdout.write(
                self.style.WARNING(
                    INFO
                    + "A Gmail app password is 16 characters. Yours is "
                    + f"{len(settings.EMAIL_HOST_PASSWORD)} — if auth fails, that's why. "
                    + "(Spaces are stripped automatically.)"
                )
            )

        # --- connection ---
        self.stdout.write(self.style.MIGRATE_HEADING("\nConnecting"))
        try:
            connection = get_connection(fail_silently=False)
            connection.open()
            self.stdout.write(self.style.SUCCESS(OK + "Logged in to the mail server."))
            connection.close()
        except smtplib.SMTPAuthenticationError as exc:
            self.stdout.write(self.style.ERROR(BAD + "The server rejected the login."))
            self.stdout.write(f"    {exc.smtp_error.decode(errors='replace')[:200]}")
            self.stdout.write(
                "\n  Usually one of:\n"
                "    · the app password was revoked or mistyped\n"
                "    · you used your normal Google password (that never works)\n"
                "    · EMAIL_HOST_USER isn't the account the password belongs to\n"
            )
            return
        except (smtplib.SMTPException, socket.error, OSError) as exc:
            self.stdout.write(self.style.ERROR(BAD + f"Could not connect: {exc}"))
            self.stdout.write(
                "\n  Check the port (587 with TLS, or 465 with SSL) and whether "
                "your network or antivirus blocks outbound SMTP.\n"
            )
            return

        # --- send ---
        recipient = options.get("to")
        if not recipient:
            self.stdout.write(
                INFO + "Add --to you@example.com to send a real test message.\n"
            )
            return

        self.stdout.write(self.style.MIGRATE_HEADING(f"\nSending to {recipient}"))
        message = EmailMultiAlternatives(
            subject="Smart Companion — test message",
            body=(
                "This is a test from Smart Companion.\n\n"
                "If you're reading this, daily digests will arrive here too.\n"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        message.attach_alternative(
            "<p style='font-family:sans-serif'>This is a test from "
            "<strong>Smart Companion</strong>.<br>If you're reading this, daily "
            "digests will arrive here too.</p>",
            "text/html",
        )
        try:
            message.send(fail_silently=False)
        except Exception as exc:
            self.stdout.write(self.style.ERROR(BAD + f"Send failed: {exc}"))
            return

        self.stdout.write(self.style.SUCCESS(OK + "Sent."))
        self.stdout.write(
            INFO + "If it isn't in the inbox within a minute, check spam — "
            "the first message from a new sender often lands there.\n"
        )
