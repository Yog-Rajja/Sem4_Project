"""Generate the VAPID key pair that web push requires.

VAPID is how a push service knows the notification really came from this
server. The pair is generated once and lives in backend/.env — no account with
Google, Mozilla or anyone else is involved.
"""

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.management.base import BaseCommand


def b64(data: bytes) -> str:
    """URL-safe base64 with padding stripped, as the web push spec requires."""
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


class Command(BaseCommand):
    help = "Generate a VAPID key pair for web push notifications."

    def handle(self, *args, **options):
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()

        private_value = private_key.private_numbers().private_value
        private_b64 = b64(private_value.to_bytes(32, "big"))

        public_b64 = b64(
            public_key.public_bytes(
                encoding=serialization.Encoding.X962,
                format=serialization.PublicFormat.UncompressedPoint,
            )
        )

        self.stdout.write(self.style.MIGRATE_HEADING("\nAdd these to backend/.env:\n"))
        self.stdout.write(f"VAPID_PUBLIC_KEY={public_b64}")
        self.stdout.write(f"VAPID_PRIVATE_KEY={private_b64}")
        self.stdout.write(
            self.style.WARNING(
                "\nKeep the private key secret. Changing it invalidates every "
                "existing subscription — devices would have to re-enable "
                "notifications.\n"
            )
        )
