import datetime as dt

from django.utils import timezone

from common.testing import AuthenticatedAPITestCase, results

from apps.focus.models import FocusSession
from apps.focus.services import heatmap, streaks
from apps.goals.models import Goal, Milestone, Task


class FocusSessionTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        goal = Goal.objects.create(user=self.user, title="Learn Python")
        milestone = Milestone.objects.create(goal=goal, title="Basics")
        self.task = Task.objects.create(milestone=milestone, title="Read a chapter")

    def test_start_a_session_against_a_task(self):
        response = self.client.post(
            "/api/focus-sessions/",
            {"task": self.task.id, "planned_minutes": 25},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["task_title"], "Read a chapter")
        self.assertIsNone(response.data["ended_at"])

    def test_start_a_session_with_no_task(self):
        response = self.client.post("/api/focus-sessions/", {}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data["task"])

    def test_cannot_start_a_session_on_someone_elses_task(self):
        foreign = Task.objects.create(
            milestone=Milestone.objects.create(
                goal=Goal.objects.create(user=self.other, title="Theirs"), title="X"
            ),
            title="Not yours",
        )
        response = self.client.post(
            "/api/focus-sessions/", {"task": foreign.id}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_finishing_records_the_time_actually_spent(self):
        session_id = self.client.post(
            "/api/focus-sessions/", {"task": self.task.id}, format="json"
        ).data["id"]

        response = self.client.post(
            f"/api/focus-sessions/{session_id}/finish/",
            {"seconds_elapsed": 1500, "completed": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["minutes"], 25)
        self.assertTrue(response.data["completed"])
        self.assertIsNotNone(response.data["ended_at"])

    def test_stopping_early_still_banks_the_time(self):
        """Abandoned work is still work — discarding it would punish honesty."""
        session_id = self.client.post("/api/focus-sessions/", {}, format="json").data["id"]
        response = self.client.post(
            f"/api/focus-sessions/{session_id}/finish/",
            {"seconds_elapsed": 420, "completed": False},
            format="json",
        )
        self.assertEqual(response.data["minutes"], 7)
        self.assertFalse(response.data["completed"])

    def test_a_session_cannot_be_finished_twice(self):
        session_id = self.client.post("/api/focus-sessions/", {}, format="json").data["id"]
        payload = {"seconds_elapsed": 60, "completed": True}
        self.client.post(f"/api/focus-sessions/{session_id}/finish/", payload, format="json")
        second = self.client.post(
            f"/api/focus-sessions/{session_id}/finish/", payload, format="json"
        )
        self.assertEqual(second.status_code, 400)

    def test_absurd_durations_are_rejected(self):
        session_id = self.client.post("/api/focus-sessions/", {}, format="json").data["id"]
        response = self.client.post(
            f"/api/focus-sessions/{session_id}/finish/",
            {"seconds_elapsed": 60 * 60 * 24, "completed": True},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_running_filter(self):
        first = self.client.post("/api/focus-sessions/", {}, format="json").data["id"]
        self.client.post("/api/focus-sessions/", {}, format="json")
        self.client.post(
            f"/api/focus-sessions/{first}/finish/",
            {"seconds_elapsed": 300, "completed": True},
            format="json",
        )
        rows = results(self.client.get("/api/focus-sessions/?running=true"))
        self.assertEqual(len(rows), 1)

    def test_history_survives_the_task_being_deleted(self):
        session_id = self.client.post(
            "/api/focus-sessions/", {"task": self.task.id}, format="json"
        ).data["id"]
        self.task.delete()

        session = FocusSession.objects.get(id=session_id)
        self.assertIsNone(session.task_id)
        self.assertEqual(session.task_title, "Read a chapter")

    def test_another_user_sees_none_of_your_sessions(self):
        self.client.post("/api/focus-sessions/", {}, format="json")
        self.as_other()
        self.assertEqual(results(self.client.get("/api/focus-sessions/")), [])


class StreakTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        goal = Goal.objects.create(user=self.user, title="Learn Python")
        self.milestone = Milestone.objects.create(goal=goal, title="Basics")

    def complete_on(self, days_ago):
        task = Task.objects.create(milestone=self.milestone, title=f"T{days_ago}")
        task.is_complete = True
        task.save()
        Task.objects.filter(id=task.id).update(
            completed_at=timezone.now() - dt.timedelta(days=days_ago)
        )
        return task

    def test_no_activity_means_no_streak(self):
        self.assertEqual(streaks(self.user)["current"], 0)

    def test_consecutive_days_build_a_streak(self):
        for days_ago in (0, 1, 2):
            self.complete_on(days_ago)
        result = streaks(self.user)
        self.assertEqual(result["current"], 3)
        self.assertTrue(result["active_today"])

    def test_a_gap_breaks_the_streak(self):
        for days_ago in (0, 1, 3, 4):
            self.complete_on(days_ago)
        self.assertEqual(streaks(self.user)["current"], 2)

    def test_an_idle_today_does_not_break_a_live_streak(self):
        """The day is not over yet, so yesterday's streak still stands."""
        for days_ago in (1, 2, 3):
            self.complete_on(days_ago)
        result = streaks(self.user)
        self.assertEqual(result["current"], 3)
        self.assertFalse(result["active_today"])

    def test_longest_streak_is_remembered_after_it_breaks(self):
        for days_ago in (10, 11, 12, 13, 14):
            self.complete_on(days_ago)
        self.complete_on(0)
        result = streaks(self.user)
        self.assertEqual(result["current"], 1)
        self.assertEqual(result["longest"], 5)

    def test_a_focus_session_counts_as_activity(self):
        FocusSession.objects.create(user=self.user, seconds_elapsed=1500)
        self.assertEqual(streaks(self.user)["current"], 1)

    def test_a_trivial_session_does_not_count(self):
        FocusSession.objects.create(user=self.user, seconds_elapsed=5)
        self.assertEqual(streaks(self.user)["current"], 0)

    def test_uncompleting_a_task_removes_it_from_the_streak(self):
        task = self.complete_on(0)
        task.is_complete = False
        task.save()
        self.assertIsNone(Task.objects.get(id=task.id).completed_at)
        self.assertEqual(streaks(self.user)["current"], 0)

    def test_heatmap_has_a_row_per_day_and_grades_intensity(self):
        for _ in range(8):
            self.complete_on(0)
        rows = heatmap(self.user, days=30)
        self.assertEqual(len(rows), 30)
        self.assertEqual(rows[-1]["level"], 4)
        self.assertEqual(rows[0]["level"], 0)


class MomentumEndpointTests(AuthenticatedAPITestCase):
    def test_momentum_returns_all_three_sections(self):
        response = self.client.get("/api/momentum/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), {"streak", "focus", "heatmap"})

    def test_focus_totals_reflect_finished_sessions(self):
        session_id = self.client.post("/api/focus-sessions/", {}, format="json").data["id"]
        self.client.post(
            f"/api/focus-sessions/{session_id}/finish/",
            {"seconds_elapsed": 1800, "completed": True},
            format="json",
        )
        focus = self.client.get("/api/momentum/").data["focus"]
        self.assertEqual(focus["today_minutes"], 30)
        self.assertEqual(focus["total_sessions"], 1)

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/momentum/").status_code, 401)
