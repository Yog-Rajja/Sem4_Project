from rest_framework import serializers

from .models import NotificationSetting, PushSubscription


class NotificationSettingSerializer(serializers.ModelSerializer):
    # What digests will actually go to, once the blank-means-account-email
    # fallback is applied. Saves the UI reimplementing that rule.
    resolved_email = serializers.CharField(read_only=True)
    account_email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = NotificationSetting
        fields = [
            "push_daily", "email_daily", "email_address",
            "resolved_email", "account_email", "send_hour", "last_sent_on",
        ]
        read_only_fields = ["last_sent_on", "resolved_email", "account_email"]

    def validate_send_hour(self, value):
        if not 0 <= value <= 23:
            raise serializers.ValidationError("Pick an hour between 0 and 23.")
        return value

    def validate(self, attrs):
        # Turning email on with nowhere to send it would fail silently every
        # morning, so refuse it up front.
        instance = self.instance
        enabling = attrs.get(
            "email_daily", instance.email_daily if instance else False
        )
        address = attrs.get(
            "email_address", instance.email_address if instance else ""
        )
        account = instance.user.email if instance else ""
        if enabling and not (address or account):
            raise serializers.ValidationError(
                {"email_address": "Add an email address to receive digests."}
            )
        return attrs


class PushSubscriptionSerializer(serializers.Serializer):
    """Matches the shape the browser's PushSubscription serialises to."""

    endpoint = serializers.URLField(max_length=600)
    keys = serializers.DictField(child=serializers.CharField(max_length=255))

    def validate_keys(self, keys):
        for required in ("p256dh", "auth"):
            if not keys.get(required):
                raise serializers.ValidationError(f"Missing '{required}'.")
        return keys

    def save(self, **kwargs):
        user = self.context["request"].user
        keys = self.validated_data["keys"]
        agent = self.context["request"].META.get("HTTP_USER_AGENT", "")[:255]

        # A device that re-subscribes returns the same endpoint, so update in
        # place rather than accumulating duplicates.
        subscription, _ = PushSubscription.objects.update_or_create(
            endpoint=self.validated_data["endpoint"],
            defaults={
                "user": user,
                "p256dh": keys["p256dh"],
                "auth": keys["auth"],
                "user_agent": agent,
            },
        )
        return subscription
