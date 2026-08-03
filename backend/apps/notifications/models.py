from django.conf import settings
from django.db import models


class NotificationSetting(models.Model):
    """Per-user delivery preferences.

    Off by default for both channels — a study app that starts messaging you
    without being asked is a study app people uninstall.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_setting",
    )
    push_daily = models.BooleanField(default=False)
    email_daily = models.BooleanField(default=False)
    # Where digests go. Blank means "use the account's own email", so the
    # common case needs no configuration, but a different inbox can be set.
    email_address = models.EmailField(blank=True)
    # Local hour (0-23) the digest should go out.
    send_hour = models.PositiveSmallIntegerField(default=8)
    # Guards against a re-run of the scheduler double-sending.
    last_sent_on = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Notifications for {self.user}"

    @property
    def owner_user_id(self):
        return self.user_id

    @property
    def any_enabled(self) -> bool:
        return self.push_daily or self.email_daily

    @property
    def resolved_email(self) -> str:
        """The address digests actually go to."""
        return (self.email_address or self.user.email or "").strip()


class PushSubscription(models.Model):
    """One browser/device that has granted notification permission.

    A user can have several — phone and laptop — so each endpoint is stored
    separately and pruned when the push service reports it has expired.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
    )
    endpoint = models.URLField(max_length=600, unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} · {self.endpoint[:40]}…"

    @property
    def owner_user_id(self):
        return self.user_id

    def as_subscription_info(self) -> dict:
        """The shape pywebpush expects."""
        return {
            "endpoint": self.endpoint,
            "keys": {"p256dh": self.p256dh, "auth": self.auth},
        }
