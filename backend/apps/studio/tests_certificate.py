import datetime as dt
from unittest.mock import patch

from django.test import override_settings
from django.utils import timezone

from common.testing import AuthenticatedAPITestCase

from apps.goals.models import Goal, Milestone, Task
from apps.studio.models import Artifact
from apps.studio.services import certificate as certificate_service


class BuildCertificateTests(AuthenticatedAPITestCase):
    """Unit-level: the numbers must always be real, computed facts."""

    def setUp(self):
        super().setUp()
        self.user.first_name = "Manav"
        self.user.save()
        self.goal = Goal.objects.create(user=self.user, title="Learn Django")
        Goal.objects.filter(id=self.goal.id).update(
            created_at=timezone.now() - dt.timedelta(days=9)
        )
        self.goal.refresh_from_db()
        milestone = Milestone.objects.create(goal=self.goal, title="Basics")
        Milestone.objects.create(goal=self.goal, title="Advanced")
        for i in range(5):
            Task.objects.create(milestone=milestone, title=f"Task {i}", is_complete=True)

    @override_settings(USE_MOCK_AI=True)
    def test_computes_real_stats_from_the_goal(self):
        data = certificate_service.build_certificate(self.goal, self.user)
        self.assertEqual(data["total_tasks"], 5)
        self.assertEqual(data["milestone_count"], 2)
        self.assertEqual(data["days_taken"], 9)
        self.assertEqual(data["goal_title"], "Learn Django")
        self.assertEqual(data["recipient_name"], "Manav")
        self.assertTrue(data["tagline"])

    def test_a_broken_ai_still_produces_a_tagline(self):
        """The achievement already happened; a spent quota must not block it."""
        with patch(
            "apps.studio.services.certificate.llm.complete_json",
            side_effect=Exception("every provider exhausted"),
        ):
            data = certificate_service.build_certificate(self.goal, self.user)
        self.assertTrue(data["tagline"])
        self.assertIn(str(data["total_tasks"]), data["tagline"])

    def test_a_malformed_ai_response_falls_back_too(self):
        with patch(
            "apps.studio.services.certificate.llm.complete_json",
            return_value={"nonsense": True},
        ):
            data = certificate_service.build_certificate(self.goal, self.user)
        self.assertTrue(data["tagline"])

    def test_days_taken_is_never_zero(self):
        """A goal finished the same day it was created shouldn't divide oddly
        or read as "0 days"."""
        Goal.objects.filter(id=self.goal.id).update(created_at=timezone.now())
        self.goal.refresh_from_db()
        with override_settings(USE_MOCK_AI=True):
            data = certificate_service.build_certificate(self.goal, self.user)
        self.assertGreaterEqual(data["days_taken"], 1)

    def test_falls_back_to_username_with_no_first_name(self):
        self.user.first_name = ""
        self.user.save()
        with override_settings(USE_MOCK_AI=True):
            data = certificate_service.build_certificate(self.goal, self.user)
        self.assertEqual(data["recipient_name"], self.user.username)


@override_settings(USE_MOCK_AI=True)
class CertificateAPITests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.goal = Goal.objects.create(user=self.user, title="Learn Django")
        self.milestone = Milestone.objects.create(goal=self.goal, title="Basics")
        self.task = Task.objects.create(milestone=self.milestone, title="Only task")

    def url(self):
        return f"/api/goals/{self.goal.id}/certificate/"

    def complete(self):
        self.task.is_complete = True
        self.task.save()

    def test_cannot_claim_before_the_goal_is_finished(self):
        response = self.client.post(self.url())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "goal_not_complete")
        self.assertEqual(Artifact.objects.count(), 0)

    def test_a_goal_with_no_tasks_cannot_be_certified(self):
        empty = Goal.objects.create(user=self.user, title="Nothing here")
        response = self.client.post(f"/api/goals/{empty.id}/certificate/")
        self.assertEqual(response.status_code, 400)

    def test_claiming_a_finished_goal_creates_a_certificate(self):
        self.complete()
        response = self.client.post(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["kind"], Artifact.Kind.CERTIFICATE)
        self.assertEqual(response.data["export_format"], "png")
        self.assertEqual(response.data["data"]["total_tasks"], 1)

    def test_claiming_twice_updates_in_place_rather_than_duplicating(self):
        self.complete()
        self.client.post(self.url())
        self.client.post(self.url())
        self.assertEqual(
            Artifact.objects.filter(goal=self.goal, kind=Artifact.Kind.CERTIFICATE).count(),
            1,
        )

    def test_get_before_claiming_is_404(self):
        self.complete()
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["code"], "no_certificate")

    def test_get_after_claiming_returns_it(self):
        self.complete()
        self.client.post(self.url())
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["kind"], Artifact.Kind.CERTIFICATE)

    def test_another_user_cannot_claim_or_view_your_certificate(self):
        self.complete()
        self.client.post(self.url())
        self.as_other()
        self.assertEqual(self.client.get(self.url()).status_code, 404)
        self.assertEqual(self.client.post(self.url()).status_code, 404)

    def test_requires_authentication(self):
        self.complete()
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post(self.url()).status_code, 401)

    def test_certificate_cannot_be_requested_through_the_freeform_generator(self):
        """The general Studio prompt box must never be able to invent one."""
        self.complete()
        response = self.client.post(
            "/api/artifacts/generate/",
            {"prompt": "Give me a certificate please", "kind": "certificate"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("kind", response.data)

    def test_kinds_endpoint_lists_certificate_as_automatic(self):
        response = self.client.get("/api/artifacts/kinds/")
        row = next(r for r in response.data if r["kind"] == "certificate")
        self.assertTrue(row["automatic"])
        self.assertEqual(row["export_format"], "png")

    def test_uncompleting_a_task_after_claiming_blocks_a_fresh_claim(self):
        """Regenerating should still respect real state, not the last claim."""
        self.complete()
        self.client.post(self.url())
        self.task.is_complete = False
        self.task.save()
        response = self.client.post(self.url())
        self.assertEqual(response.status_code, 400)
