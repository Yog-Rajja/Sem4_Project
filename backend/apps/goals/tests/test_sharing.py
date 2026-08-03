import uuid

from rest_framework.test import APITestCase

from common.testing import AuthenticatedAPITestCase

from apps.goals.models import Goal, Milestone, Task


class SharingTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.goal = Goal.objects.create(user=self.user, title="Crack GATE")
        milestone = Milestone.objects.create(goal=self.goal, title="Fundamentals", order=0)
        Task.objects.create(milestone=milestone, title="Read chapter 1", is_complete=True)
        Task.objects.create(milestone=milestone, title="Solve 20 problems")

    def public_url(self, token=None):
        return f"/api/public/roadmap/{token or self.goal.share_token}/"

    def test_goals_are_private_by_default(self):
        self.assertFalse(self.goal.is_shared)
        self.assertEqual(self.client.get(self.public_url()).status_code, 404)

    def test_sharing_can_be_turned_on_and_off(self):
        response = self.client.post(f"/api/goals/{self.goal.id}/share/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_shared"])
        self.assertTrue(response.data["share_token"])

        response = self.client.post(
            f"/api/goals/{self.goal.id}/share/", {"shared": False}, format="json"
        )
        self.assertFalse(response.data["is_shared"])
        self.assertIsNone(response.data["share_token"])

    def test_another_user_cannot_share_your_goal(self):
        self.as_other()
        self.assertEqual(
            self.client.post(f"/api/goals/{self.goal.id}/share/", {}, format="json").status_code,
            404,
        )

    def test_every_goal_gets_its_own_token(self):
        second = Goal.objects.create(user=self.user, title="Learn React")
        self.assertNotEqual(self.goal.share_token, second.share_token)


class PublicRoadmapTests(APITestCase):
    """Exercised with no credentials at all — this is the one open endpoint."""

    def setUp(self):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(
            "manav", "manav@example.com", "SuperSecret123", first_name="Manav"
        )
        self.goal = Goal.objects.create(
            user=user, title="Crack GATE", raw_input_text="secret original wording",
            is_shared=True,
        )
        milestone = Milestone.objects.create(goal=self.goal, title="Fundamentals", order=0)
        parent = Task.objects.create(milestone=milestone, title="Read chapter 1", is_complete=True)
        Task.objects.create(milestone=milestone, title="Subtask", parent=parent)
        Task.objects.create(milestone=milestone, title="Solve 20 problems")

    def url(self, token=None):
        return f"/api/public/roadmap/{token or self.goal.share_token}/"

    def test_a_shared_roadmap_is_readable_without_signing_in(self):
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Crack GATE")
        self.assertEqual(response.data["owner_name"], "Manav")
        self.assertEqual(len(response.data["milestones"]), 1)

    def test_progress_is_included(self):
        response = self.client.get(self.url())
        self.assertEqual(response.data["total_tasks"], 3)
        self.assertEqual(response.data["completed_tasks"], 1)

    def test_subtasks_are_not_duplicated_at_the_top_level(self):
        tasks = self.client.get(self.url()).data["milestones"][0]["tasks"]
        self.assertEqual([t["title"] for t in tasks], ["Read chapter 1", "Solve 20 problems"])

    def test_nothing_private_leaks(self):
        """A share link exposes the plan, not the person or the database."""
        response = self.client.get(self.url())
        body = str(response.data)
        self.assertNotIn("raw_input_text", response.data)
        self.assertNotIn("secret original wording", body)
        self.assertNotIn("id", response.data)
        self.assertNotIn("user", response.data)
        self.assertNotIn("manav@example.com", body)

    def test_unsharing_takes_the_link_down_immediately(self):
        self.goal.is_shared = False
        self.goal.save()
        self.assertEqual(self.client.get(self.url()).status_code, 404)

    def test_an_unknown_token_is_a_404(self):
        self.assertEqual(self.client.get(self.url(uuid.uuid4())).status_code, 404)

    def test_a_malformed_token_does_not_reach_the_view(self):
        self.assertEqual(self.client.get("/api/public/roadmap/not-a-uuid/").status_code, 404)
