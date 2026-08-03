import datetime as dt

from django.contrib.auth import get_user_model
from django.utils import timezone

from common.testing import AuthenticatedAPITestCase, results

from apps.circles.models import Circle, CircleMembership
from apps.circles.services import member_stats
from apps.focus.models import FocusSession
from apps.goals.models import Goal, Milestone, Task

User = get_user_model()


class CreateCircleTests(AuthenticatedAPITestCase):
    url = "/api/circles/"

    def test_creating_a_circle_makes_you_its_first_member_and_owner(self):
        response = self.client.post(self.url, {"name": "GATE Warriors"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "GATE Warriors")
        self.assertEqual(response.data["member_count"], 1)
        self.assertTrue(response.data["is_owner"])
        self.assertTrue(response.data["invite_token"])

        circle = Circle.objects.get(id=response.data["id"])
        self.assertEqual(circle.created_by, self.user)
        self.assertTrue(circle.is_member(self.user))

    def test_a_short_name_is_rejected(self):
        response = self.client.post(self.url, {"name": "x"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_list_only_shows_circles_i_belong_to(self):
        self.client.post(self.url, {"name": "Mine"}, format="json")
        self.as_other()
        self.client.post(self.url, {"name": "Theirs"}, format="json")

        rows = results(self.client.get(self.url))
        self.assertEqual([r["name"] for r in rows], ["Theirs"])

    def test_retrieving_a_circle_i_am_not_in_is_404(self):
        response = self.client.post(self.url, {"name": "Mine"}, format="json")
        circle_id = response.data["id"]
        self.as_other()
        self.assertEqual(self.client.get(f"{self.url}{circle_id}/").status_code, 404)

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, 401)


class JoinLeaveTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        response = self.client.post("/api/circles/", {"name": "GATE Warriors"}, format="json")
        self.circle_id = response.data["id"]
        self.token = response.data["invite_token"]

    def test_another_user_can_join_with_the_token(self):
        self.as_other()
        response = self.client.post("/api/circles/join/", {"token": self.token}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["member_count"], 2)
        self.assertFalse(response.data["is_owner"])

    def test_an_unknown_token_is_a_404(self):
        response = self.client.post(
            "/api/circles/join/", {"token": "00000000-0000-0000-0000-000000000000"}, format="json"
        )
        self.assertEqual(response.status_code, 404)

    def test_a_malformed_token_is_rejected(self):
        response = self.client.post("/api/circles/join/", {"token": "not-a-uuid"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_joining_twice_is_idempotent(self):
        self.as_other()
        self.client.post("/api/circles/join/", {"token": self.token}, format="json")
        self.client.post("/api/circles/join/", {"token": self.token}, format="json")
        self.assertEqual(
            CircleMembership.objects.filter(circle_id=self.circle_id).count(), 2
        )

    def test_leaving_removes_membership(self):
        self.as_other()
        self.client.post("/api/circles/join/", {"token": self.token}, format="json")
        response = self.client.post(f"/api/circles/{self.circle_id}/leave/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(f"/api/circles/{self.circle_id}/").status_code, 404)

    def test_the_last_member_leaving_deletes_the_circle(self):
        self.client.post(f"/api/circles/{self.circle_id}/leave/", {}, format="json")
        self.assertFalse(Circle.objects.filter(id=self.circle_id).exists())

    def test_leaving_a_circle_you_are_not_in_is_a_no_op_not_an_error(self):
        self.as_other()
        response = self.client.post(f"/api/circles/{self.circle_id}/leave/", {}, format="json")
        self.assertEqual(response.status_code, 404)  # not a member -> 404, consistent


class DeleteAndInviteResetTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        response = self.client.post("/api/circles/", {"name": "GATE Warriors"}, format="json")
        self.circle_id = response.data["id"]
        self.token = response.data["invite_token"]
        self.as_other()
        self.client.post("/api/circles/join/", {"token": self.token}, format="json")
        self.as_owner()

    def test_only_the_owner_can_delete_the_circle(self):
        self.as_other()
        response = self.client.delete(f"/api/circles/{self.circle_id}/")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Circle.objects.filter(id=self.circle_id).exists())

    def test_the_owner_can_delete_it(self):
        response = self.client.delete(f"/api/circles/{self.circle_id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Circle.objects.filter(id=self.circle_id).exists())

    def test_deleting_removes_all_memberships(self):
        self.client.delete(f"/api/circles/{self.circle_id}/")
        self.assertEqual(CircleMembership.objects.filter(circle_id=self.circle_id).count(), 0)

    def test_only_the_owner_can_regenerate_the_invite(self):
        self.as_other()
        response = self.client.post(
            f"/api/circles/{self.circle_id}/regenerate-invite/", {}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_regenerating_the_invite_changes_the_token(self):
        response = self.client.post(
            f"/api/circles/{self.circle_id}/regenerate-invite/", {}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(str(response.data["invite_token"]), self.token)

    def test_the_old_token_stops_working_after_regeneration(self):
        self.client.post(f"/api/circles/{self.circle_id}/regenerate-invite/", {}, format="json")
        self.as_other()
        second_other = User.objects.create_user("third", "third@example.com", "SuperSecret123")
        self.client.force_authenticate(second_other)
        response = self.client.post("/api/circles/join/", {"token": self.token}, format="json")
        self.assertEqual(response.status_code, 404)


class LeaderboardTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        response = self.client.post("/api/circles/", {"name": "GATE Warriors"}, format="json")
        self.circle_id = response.data["id"]
        token = response.data["invite_token"]
        self.as_other()
        self.client.post("/api/circles/join/", {"token": token}, format="json")
        self.as_owner()

        # The owner (self.user) completes more tasks this week than self.other.
        self._complete_tasks(self.user, count=3, title_prefix="mine")
        self._complete_tasks(self.other, count=1, title_prefix="theirs")

    def _complete_tasks(self, user, count, title_prefix):
        goal = Goal.objects.create(user=user, title=f"{title_prefix} goal")
        milestone = Milestone.objects.create(goal=goal, title="M")
        for i in range(count):
            task = Task.objects.create(milestone=milestone, title=f"{title_prefix}-{i}")
            task.is_complete = True
            task.save()

    def test_leaderboard_lists_every_member(self):
        response = self.client.get(f"/api/circles/{self.circle_id}/")
        names = {row["name"] for row in response.data["leaderboard"]}
        self.assertEqual(len(response.data["leaderboard"]), 2)
        self.assertEqual(len(names), 2)

    def test_leaderboard_is_ranked_by_this_weeks_completions(self):
        response = self.client.get(f"/api/circles/{self.circle_id}/")
        board = response.data["leaderboard"]
        self.assertEqual(board[0]["rank"], 1)
        self.assertEqual(board[0]["completed_this_week"], 3)
        self.assertEqual(board[1]["completed_this_week"], 1)

    def test_is_you_is_marked_correctly_per_viewer(self):
        response = self.client.get(f"/api/circles/{self.circle_id}/")
        board = {row["user_id"]: row for row in response.data["leaderboard"]}
        self.assertTrue(board[self.user.id]["is_you"])
        self.assertFalse(board[self.other.id]["is_you"])

    def test_only_the_creator_is_flagged_as_owner_on_the_board(self):
        response = self.client.get(f"/api/circles/{self.circle_id}/")
        board = {row["user_id"]: row for row in response.data["leaderboard"]}
        self.assertTrue(board[self.user.id]["is_owner"])
        self.assertFalse(board[self.other.id]["is_owner"])

    def test_leaderboard_never_leaks_a_goal_title(self):
        response = self.client.get(f"/api/circles/{self.circle_id}/")
        body = str(response.data)
        self.assertNotIn("mine goal", body)
        self.assertNotIn("theirs goal", body)

    def test_leaderboard_never_leaks_an_email(self):
        response = self.client.get(f"/api/circles/{self.circle_id}/")
        self.assertNotIn(self.other.email, str(response.data))

    def test_leaderboard_never_leaks_a_task_title(self):
        response = self.client.get(f"/api/circles/{self.circle_id}/")
        body = str(response.data)
        self.assertNotIn("mine-0", body)
        self.assertNotIn("theirs-0", body)


class MemberStatsTests(AuthenticatedAPITestCase):
    def test_stats_reflect_real_totals(self):
        goal = Goal.objects.create(user=self.user, title="Learn Python")
        milestone = Milestone.objects.create(goal=goal, title="Basics")
        for i in range(4):
            Task.objects.create(
                milestone=milestone, title=f"T{i}", is_complete=(i < 2)
            )

        stats = member_stats(self.user)
        self.assertEqual(stats["active_goals"], 1)
        self.assertEqual(stats["total_tasks"], 4)
        self.assertEqual(stats["done_tasks"], 2)
        self.assertEqual(stats["overall_progress"], 50)

    def test_a_user_with_nothing_gets_zeroes_not_an_error(self):
        stats = member_stats(self.user)
        self.assertEqual(stats["overall_progress"], 0)
        self.assertEqual(stats["total_tasks"], 0)

    def test_streak_reflects_real_activity(self):
        FocusSession.objects.create(user=self.user, seconds_elapsed=1500)
        stats = member_stats(self.user)
        self.assertEqual(stats["streak_current"], 1)

    def test_completed_this_week_excludes_older_work(self):
        goal = Goal.objects.create(user=self.user, title="Old goal")
        milestone = Milestone.objects.create(goal=goal, title="M")
        old_task = Task.objects.create(milestone=milestone, title="Old", is_complete=True)
        Task.objects.filter(id=old_task.id).update(
            completed_at=timezone.now() - dt.timedelta(days=30)
        )
        self.assertEqual(member_stats(self.user)["completed_this_week"], 0)
