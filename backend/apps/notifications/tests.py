import datetime as dt
from unittest.mock import patch

from django.core import mail
from django.test import override_settings
from django.utils import timezone

from common.testing import AuthenticatedAPITestCase

from apps.goals.models import Goal, Milestone, Task
from apps.notifications import services
from apps.notifications.models import NotificationSetting, PushSubscription

SUBSCRIPTION = {
    "endpoint": "https://fcm.googleapis.com/fcm/send/abc123",
    "keys": {"p256dh": "BPublicKeyValue", "auth": "AuthSecret"},
}

VAPID = {
    "VAPID_PUBLIC_KEY": "test-public",
    "VAPID_PRIVATE_KEY": "test-private",
}


class DigestTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        goal = Goal.objects.create(user=self.user, title="Crack GATE")
        self.milestone = Milestone.objects.create(goal=goal, title="Fundamentals")
        self.today = timezone.localdate()

    def test_an_empty_account_has_nothing_to_say(self):
        digest = services.build_digest(self.user)
        self.assertFalse(digest["has_content"])
        self.assertEqual(digest["title"], "Nothing due today")

    def test_counts_today_and_overdue_separately(self):
        Task.objects.create(milestone=self.milestone, title="Today A", due_date=self.today)
        Task.objects.create(milestone=self.milestone, title="Today B", due_date=self.today)
        Task.objects.create(
            milestone=self.milestone, title="Late",
            due_date=self.today - dt.timedelta(days=2),
        )
        digest = services.build_digest(self.user)
        self.assertEqual(digest["counts"]["today"], 2)
        self.assertEqual(digest["counts"]["overdue"], 1)
        self.assertEqual(digest["title"], "2 tasks due today")
        self.assertTrue(digest["has_content"])

    def test_completed_work_is_never_nagged_about(self):
        Task.objects.create(
            milestone=self.milestone, title="Done",
            due_date=self.today - dt.timedelta(days=1), is_complete=True,
        )
        digest = services.build_digest(self.user)
        self.assertEqual(digest["counts"]["overdue"], 0)
        self.assertFalse(digest["has_content"])

    def test_overdue_leads_when_nothing_is_due_today(self):
        Task.objects.create(
            milestone=self.milestone, title="Late",
            due_date=self.today - dt.timedelta(days=3),
        )
        self.assertEqual(services.build_digest(self.user)["title"], "1 overdue task")

    def test_the_body_names_actual_tasks(self):
        Task.objects.create(
            milestone=self.milestone, title="Revise pointers", due_date=self.today
        )
        self.assertIn("Revise pointers", services.build_digest(self.user)["body"])

    def test_another_users_tasks_never_appear(self):
        foreign = Goal.objects.create(user=self.other, title="Theirs")
        foreign_milestone = Milestone.objects.create(goal=foreign, title="X")
        Task.objects.create(
            milestone=foreign_milestone, title="Not mine", due_date=self.today
        )
        self.assertEqual(services.build_digest(self.user)["counts"]["today"], 0)


class SettingsAPITests(AuthenticatedAPITestCase):
    url = "/api/notifications/settings/"

    def test_settings_are_created_on_first_read_and_default_to_off(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["push_daily"])
        self.assertFalse(response.data["email_daily"])
        self.assertEqual(response.data["send_hour"], 8)

    def test_preferences_can_be_updated(self):
        response = self.client.patch(
            self.url, {"email_daily": True, "send_hour": 7}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["email_daily"])
        self.assertEqual(NotificationSetting.objects.get(user=self.user).send_hour, 7)

    def test_an_impossible_hour_is_rejected(self):
        self.assertEqual(
            self.client.patch(self.url, {"send_hour": 25}, format="json").status_code, 400
        )

    def test_the_resolved_address_defaults_to_the_account(self):
        response = self.client.get(self.url)
        self.assertEqual(response.data["resolved_email"], self.user.email)
        self.assertEqual(response.data["account_email"], self.user.email)
        self.assertEqual(response.data["email_address"], "")

    def test_a_custom_address_can_be_set(self):
        response = self.client.patch(
            self.url, {"email_address": "elsewhere@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["resolved_email"], "elsewhere@example.com")

    def test_a_malformed_address_is_rejected(self):
        response = self.client.patch(
            self.url, {"email_address": "not-an-email"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_clearing_the_override_falls_back_to_the_account(self):
        self.client.patch(self.url, {"email_address": "x@example.com"}, format="json")
        response = self.client.patch(self.url, {"email_address": ""}, format="json")
        self.assertEqual(response.data["resolved_email"], self.user.email)

    def test_email_cannot_be_enabled_with_nowhere_to_send(self):
        """Otherwise it would fail silently every morning."""
        self.user.email = ""
        self.user.save()
        response = self.client.patch(self.url, {"email_daily": True}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email_address", response.data)

    @override_settings(**VAPID)
    def test_the_public_key_is_exposed_for_the_browser(self):
        response = self.client.get(self.url)
        self.assertEqual(response.data["vapid_public_key"], "test-public")
        self.assertTrue(response.data["push_supported"])

    @override_settings(VAPID_PUBLIC_KEY="", VAPID_PRIVATE_KEY="")
    def test_missing_keys_are_reported_rather_than_hidden(self):
        self.assertFalse(self.client.get(self.url).data["push_supported"])

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, 401)


class SubscriptionTests(AuthenticatedAPITestCase):
    url = "/api/notifications/subscribe/"

    def test_a_device_can_subscribe(self):
        response = self.client.post(self.url, SUBSCRIPTION, format="json")
        self.assertEqual(response.status_code, 201)
        subscription = PushSubscription.objects.get(user=self.user)
        self.assertEqual(subscription.p256dh, "BPublicKeyValue")

    def test_resubscribing_the_same_device_does_not_duplicate(self):
        self.client.post(self.url, SUBSCRIPTION, format="json")
        self.client.post(self.url, SUBSCRIPTION, format="json")
        self.assertEqual(PushSubscription.objects.count(), 1)

    def test_several_devices_are_kept_separately(self):
        self.client.post(self.url, SUBSCRIPTION, format="json")
        self.client.post(
            self.url,
            {**SUBSCRIPTION, "endpoint": "https://fcm.googleapis.com/fcm/send/second"},
            format="json",
        )
        self.assertEqual(PushSubscription.objects.filter(user=self.user).count(), 2)

    def test_a_payload_without_keys_is_rejected(self):
        response = self.client.post(
            self.url, {"endpoint": SUBSCRIPTION["endpoint"], "keys": {}}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_a_device_can_unsubscribe(self):
        self.client.post(self.url, SUBSCRIPTION, format="json")
        response = self.client.delete(
            self.url, {"endpoint": SUBSCRIPTION["endpoint"]}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PushSubscription.objects.count(), 0)

    def test_a_device_claimed_by_another_account_moves_to_it(self):
        """The same browser signing in as someone else must not keep pushing
        the previous user's tasks to it."""
        self.client.post(self.url, SUBSCRIPTION, format="json")
        self.as_other()
        self.client.post(self.url, SUBSCRIPTION, format="json")

        self.assertEqual(PushSubscription.objects.count(), 1)
        self.assertEqual(PushSubscription.objects.first().user, self.other)


@override_settings(**VAPID)
class PushDeliveryTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        goal = Goal.objects.create(user=self.user, title="Crack GATE")
        milestone = Milestone.objects.create(goal=goal, title="Fundamentals")
        Task.objects.create(
            milestone=milestone, title="Revise pointers", due_date=timezone.localdate()
        )
        PushSubscription.objects.create(
            user=self.user,
            endpoint=SUBSCRIPTION["endpoint"],
            p256dh="BPublicKeyValue",
            auth="AuthSecret",
        )

    def test_push_is_sent_to_each_device(self):
        with patch("pywebpush.webpush") as webpush:
            delivered = services.send_push(
                self.user, services.build_digest(self.user)
            )
        self.assertEqual(delivered, 1)
        webpush.assert_called_once()

    def test_the_payload_carries_the_digest(self):
        import json

        with patch("pywebpush.webpush") as webpush:
            services.send_push(self.user, services.build_digest(self.user))
        payload = json.loads(webpush.call_args.kwargs["data"])
        self.assertIn("due today", payload["title"])
        self.assertIn("Revise pointers", payload["body"])
        self.assertEqual(payload["url"], "/dashboard")

    def test_an_expired_subscription_is_pruned(self):
        from pywebpush import WebPushException

        class Gone:
            status_code = 410

        error = WebPushException("gone")
        error.response = Gone()

        with patch("pywebpush.webpush", side_effect=error):
            delivered = services.send_push(self.user, services.build_digest(self.user))

        self.assertEqual(delivered, 0)
        self.assertEqual(PushSubscription.objects.count(), 0)

    def test_a_transient_failure_keeps_the_subscription(self):
        from pywebpush import WebPushException

        class ServerError:
            status_code = 500

        error = WebPushException("boom")
        error.response = ServerError()

        with patch("pywebpush.webpush", side_effect=error):
            services.send_push(self.user, services.build_digest(self.user))

        self.assertEqual(PushSubscription.objects.count(), 1)

    @override_settings(VAPID_PUBLIC_KEY="", VAPID_PRIVATE_KEY="")
    def test_nothing_is_attempted_without_vapid_keys(self):
        with patch("pywebpush.webpush") as webpush:
            self.assertEqual(
                services.send_push(self.user, services.build_digest(self.user)), 0
            )
        webpush.assert_not_called()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class EmailDeliveryTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        goal = Goal.objects.create(user=self.user, title="Crack GATE")
        self.milestone = Milestone.objects.create(goal=goal, title="Fundamentals")
        Task.objects.create(
            milestone=self.milestone,
            title="Revise pointers",
            due_date=timezone.localdate(),
        )

    def test_an_email_is_sent_with_both_formats(self):
        sent = services.send_email(self.user, services.build_digest(self.user))
        self.assertTrue(sent)
        self.assertEqual(len(mail.outbox), 1)

        message = mail.outbox[0]
        self.assertIn("due today", message.subject)
        self.assertIn("Revise pointers", message.body)
        self.assertEqual(message.to, [self.user.email])
        self.assertTrue(message.alternatives)

    def test_a_user_with_no_address_anywhere_is_skipped(self):
        self.user.email = ""
        self.user.save()
        self.assertFalse(services.send_email(self.user, services.build_digest(self.user)))
        self.assertEqual(len(mail.outbox), 0)

    def test_the_account_address_is_used_by_default(self):
        services.send_email(self.user, services.build_digest(self.user))
        self.assertEqual(mail.outbox[0].to, [self.user.email])

    def test_a_configured_address_overrides_the_account_one(self):
        NotificationSetting.objects.update_or_create(
            user=self.user, defaults={"email_address": "elsewhere@example.com"}
        )
        services.send_email(self.user, services.build_digest(self.user))
        self.assertEqual(mail.outbox[0].to, ["elsewhere@example.com"])

    def test_an_override_works_even_with_no_account_address(self):
        self.user.email = ""
        self.user.save()
        NotificationSetting.objects.update_or_create(
            user=self.user, defaults={"email_address": "only@example.com"}
        )
        self.assertTrue(services.send_email(self.user, services.build_digest(self.user)))
        self.assertEqual(mail.outbox[0].to, ["only@example.com"])

    def test_the_email_lists_the_tasks_and_what_is_left(self):
        Task.objects.create(
            milestone=self.milestone,
            title="Fix the parser",
            due_date=timezone.localdate() - dt.timedelta(days=2),
        )
        services.send_email(self.user, services.build_digest(self.user))
        body = mail.outbox[0].body

        self.assertIn("Revise pointers", body)
        self.assertIn("Fix the parser", body)
        self.assertIn("OVERDUE", body)
        self.assertIn("DUE TODAY", body)
        self.assertIn("TASKS LEFT PER GOAL", body)
        self.assertIn("2 task(s) remaining in total", body)

    def test_the_html_part_lists_them_too(self):
        services.send_email(self.user, services.build_digest(self.user))
        html = mail.outbox[0].alternatives[0][0]
        self.assertIn("Revise pointers", html)
        self.assertIn("left of", html)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", **VAPID
)
class DeliverDailyTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        goal = Goal.objects.create(user=self.user, title="Crack GATE")
        milestone = Milestone.objects.create(goal=goal, title="Fundamentals")
        Task.objects.create(
            milestone=milestone, title="Revise pointers", due_date=timezone.localdate()
        )

    def test_nothing_is_sent_when_the_user_has_not_opted_in(self):
        result = services.deliver_daily(self.user)
        self.assertEqual(result["skipped"], "not enabled")
        self.assertEqual(len(mail.outbox), 0)

    def test_a_second_run_on_the_same_day_does_not_resend(self):
        """The scheduler may run hourly; the user should still get one digest."""
        NotificationSetting.objects.update_or_create(
            user=self.user, defaults={"email_daily": True, "send_hour": 0}
        )
        services.deliver_daily(self.user)
        self.assertEqual(len(mail.outbox), 1)

        second = services.deliver_daily(self.user)
        self.assertEqual(second["skipped"], "already sent today")
        self.assertEqual(len(mail.outbox), 1)

    def test_nothing_goes_out_before_the_chosen_hour(self):
        NotificationSetting.objects.update_or_create(
            user=self.user, defaults={"email_daily": True, "send_hour": 23}
        )
        result = services.deliver_daily(self.user)
        if timezone.localtime().hour < 23:
            self.assertEqual(result["skipped"], "too early")
            self.assertEqual(len(mail.outbox), 0)

    def test_force_ignores_preferences_and_the_schedule(self):
        result = services.deliver_daily(self.user, force=True)
        self.assertNotIn("skipped", result)
        self.assertTrue(result["emailed"])

    def test_forcing_does_not_consume_the_daily_slot(self):
        services.deliver_daily(self.user, force=True)
        self.assertIsNone(
            NotificationSetting.objects.get(user=self.user).last_sent_on
        )


class TestEndpointTests(AuthenticatedAPITestCase):
    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_the_test_button_sends_immediately(self):
        response = self.client.post("/api/notifications/test/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["emailed"])
        self.assertIn("Sent", response.data["detail"])

    def test_the_preview_shows_what_would_be_sent(self):
        response = self.client.get("/api/notifications/preview/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("title", response.data)
        self.assertIn("counts", response.data)
