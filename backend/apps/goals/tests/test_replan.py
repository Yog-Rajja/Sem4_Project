import datetime as dt
from unittest.mock import patch

from django.test import override_settings
from django.utils import timezone

from common.testing import AuthenticatedAPITestCase

from apps.goals.models import Goal, Milestone, Task


class ReplanTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.today = timezone.localdate()
        self.goal = Goal.objects.create(
            user=self.user,
            title="Learn Python",
            target_date=self.today + dt.timedelta(days=60),
        )
        # A milestone that has already slipped into the past.
        self.late = Milestone.objects.create(
            goal=self.goal,
            title="Basics",
            order=0,
            target_date=self.today - dt.timedelta(days=10),
        )
        self.done_task = Task.objects.create(
            milestone=self.late, title="Finished already", is_complete=True,
            due_date=self.today - dt.timedelta(days=20),
        )
        self.pending = Task.objects.create(
            milestone=self.late, title="Still outstanding",
            due_date=self.today - dt.timedelta(days=12),
        )

    def url(self):
        return f"/api/goals/{self.goal.id}/replan/"

    @override_settings(USE_MOCK_AI=True)
    def test_replan_moves_overdue_work_into_the_future(self):
        response = self.client.post(self.url())
        self.assertEqual(response.status_code, 200)

        self.late.refresh_from_db()
        self.pending.refresh_from_db()
        self.assertGreaterEqual(self.late.target_date, self.today)
        self.assertGreaterEqual(self.pending.due_date, self.today)

    @override_settings(USE_MOCK_AI=True)
    def test_replan_never_touches_completed_work(self):
        original = self.done_task.due_date
        self.client.post(self.url())
        self.done_task.refresh_from_db()
        self.assertEqual(self.done_task.due_date, original)
        self.assertTrue(self.done_task.is_complete)

    @override_settings(USE_MOCK_AI=True)
    def test_replan_returns_a_summary_and_the_updated_goal(self):
        response = self.client.post(self.url())
        self.assertTrue(response.data["summary"])
        self.assertIn("milestones", response.data["goal"])
        self.assertGreaterEqual(response.data["milestones_rescheduled"], 1)

    @override_settings(USE_MOCK_AI=True)
    def test_replanning_a_finished_goal_is_rejected_clearly(self):
        self.pending.is_complete = True
        self.pending.save()
        response = self.client.post(self.url())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "nothing_to_replan")

    def test_hallucinated_ids_are_ignored(self):
        """A model returning ids we never sent must not be able to write."""
        fake = {
            "summary": "Rescheduled everything.",
            "milestones": [
                {"id": 999999, "target_date": (self.today + dt.timedelta(days=5)).isoformat(),
                 "tasks": []},
                {
                    "id": self.late.id,
                    "target_date": (self.today + dt.timedelta(days=20)).isoformat(),
                    "tasks": [
                        {"id": 888888, "due_date": (self.today + dt.timedelta(days=3)).isoformat()},
                        {"id": self.pending.id,
                         "due_date": (self.today + dt.timedelta(days=15)).isoformat()},
                    ],
                },
            ],
        }
        with patch("apps.goals.services.replan.llm.complete_json", return_value=fake):
            response = self.client.post(self.url())

        self.assertEqual(response.status_code, 200)
        self.late.refresh_from_db()
        self.pending.refresh_from_db()
        self.assertEqual(self.late.target_date, self.today + dt.timedelta(days=20))
        self.assertEqual(self.pending.due_date, self.today + dt.timedelta(days=15))

    def test_a_task_belonging_to_another_milestone_is_ignored(self):
        other_milestone = Milestone.objects.create(goal=self.goal, title="Later", order=1)
        stray = Task.objects.create(milestone=other_milestone, title="Elsewhere",
                                    due_date=self.today + dt.timedelta(days=40))
        fake = {
            "summary": "Rescheduled.",
            "milestones": [
                {
                    "id": self.late.id,
                    "target_date": (self.today + dt.timedelta(days=20)).isoformat(),
                    # Claims a task that lives under a different milestone.
                    "tasks": [{"id": stray.id,
                               "due_date": (self.today + dt.timedelta(days=2)).isoformat()}],
                }
            ],
        }
        with patch("apps.goals.services.replan.llm.complete_json", return_value=fake):
            self.client.post(self.url())

        stray.refresh_from_db()
        self.assertEqual(stray.due_date, self.today + dt.timedelta(days=40))

    def test_dates_in_the_past_are_clamped_to_today(self):
        fake = {
            "summary": "Rescheduled.",
            "milestones": [
                {
                    "id": self.late.id,
                    "target_date": (self.today - dt.timedelta(days=30)).isoformat(),
                    "tasks": [{"id": self.pending.id,
                               "due_date": (self.today - dt.timedelta(days=40)).isoformat()}],
                }
            ],
        }
        with patch("apps.goals.services.replan.llm.complete_json", return_value=fake):
            self.client.post(self.url())

        self.late.refresh_from_db()
        self.pending.refresh_from_db()
        self.assertEqual(self.late.target_date, self.today)
        self.assertEqual(self.pending.due_date, self.today)

    def test_a_task_cannot_be_pushed_past_its_milestone(self):
        fake = {
            "summary": "Rescheduled.",
            "milestones": [
                {
                    "id": self.late.id,
                    "target_date": (self.today + dt.timedelta(days=10)).isoformat(),
                    "tasks": [{"id": self.pending.id,
                               "due_date": (self.today + dt.timedelta(days=50)).isoformat()}],
                }
            ],
        }
        with patch("apps.goals.services.replan.llm.complete_json", return_value=fake):
            self.client.post(self.url())

        self.pending.refresh_from_db()
        self.assertEqual(self.pending.due_date, self.today + dt.timedelta(days=10))

    def test_an_unusable_response_is_reported(self):
        with patch("apps.goals.services.replan.llm.complete_json",
                   return_value={"milestones": [{"id": 999999}]}):
            response = self.client.post(self.url())
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.data["code"], "replan_unusable")

    @override_settings(USE_MOCK_AI=True)
    def test_another_user_cannot_replan_your_goal(self):
        self.as_other()
        self.assertEqual(self.client.post(self.url()).status_code, 404)


class PlanMyDayTests(AuthenticatedAPITestCase):
    url = "/api/plan-my-day/"

    def setUp(self):
        super().setUp()
        self.today = timezone.localdate()
        goal = Goal.objects.create(user=self.user, title="Learn Python")
        milestone = Milestone.objects.create(goal=goal, title="Basics")
        self.tasks = [
            Task.objects.create(
                milestone=milestone,
                title=f"Task {index}",
                due_date=self.today + dt.timedelta(days=index),
            )
            for index in range(5)
        ]

    @override_settings(USE_MOCK_AI=True)
    def test_returns_picks_that_fit_the_time_available(self):
        response = self.client.post(self.url, {"minutes": 90}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["summary"])
        total = sum(p["estimated_minutes"] for p in response.data["picks"])
        self.assertLessEqual(total, 90)

    @override_settings(USE_MOCK_AI=True)
    def test_picks_carry_the_full_task_and_a_reason(self):
        pick = self.client.post(self.url, {"minutes": 120}, format="json").data["picks"][0]
        self.assertIn("goal_title", pick["task"])
        self.assertTrue(pick["reason"])

    def test_rejects_an_implausible_time_budget(self):
        self.assertEqual(
            self.client.post(self.url, {"minutes": 5}, format="json").status_code, 400
        )
        self.assertEqual(
            self.client.post(self.url, {"minutes": 5000}, format="json").status_code, 400
        )

    @override_settings(USE_MOCK_AI=True)
    def test_a_user_with_nothing_to_do_gets_a_clear_message(self):
        self.as_other()
        response = self.client.post(self.url, {"minutes": 60}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "nothing_to_plan")

    def test_hallucinated_task_ids_are_dropped(self):
        fake = {
            "summary": "Here is your day.",
            "picks": [
                {"id": 999999, "reason": "invented", "estimated_minutes": 30},
                {"id": self.tasks[0].id, "reason": "Due soonest", "estimated_minutes": 45},
            ],
        }
        with patch("apps.goals.services.replan.llm.complete_json", return_value=fake):
            response = self.client.post(self.url, {"minutes": 120}, format="json")

        picks = response.data["picks"]
        self.assertEqual(len(picks), 1)
        self.assertEqual(picks[0]["task"]["id"], self.tasks[0].id)

    def test_duplicate_picks_are_collapsed(self):
        fake = {
            "summary": "Here is your day.",
            "picks": [
                {"id": self.tasks[0].id, "reason": "First", "estimated_minutes": 30},
                {"id": self.tasks[0].id, "reason": "Again", "estimated_minutes": 30},
            ],
        }
        with patch("apps.goals.services.replan.llm.complete_json", return_value=fake):
            response = self.client.post(self.url, {"minutes": 120}, format="json")
        self.assertEqual(len(response.data["picks"]), 1)

    def test_absurd_estimates_are_clamped(self):
        fake = {
            "summary": "Here is your day.",
            "picks": [{"id": self.tasks[0].id, "reason": "x", "estimated_minutes": 99999}],
        }
        with patch("apps.goals.services.replan.llm.complete_json", return_value=fake):
            response = self.client.post(self.url, {"minutes": 120}, format="json")
        self.assertEqual(response.data["picks"][0]["estimated_minutes"], 240)

    def test_only_your_own_tasks_are_candidates(self):
        foreign_goal = Goal.objects.create(user=self.other, title="Theirs")
        foreign_milestone = Milestone.objects.create(goal=foreign_goal, title="X")
        foreign_task = Task.objects.create(
            milestone=foreign_milestone, title="Not yours", due_date=self.today
        )

        captured = {}

        def fake_complete(system, user, temperature=0.2, retries=1):
            captured["prompt"] = user
            return {"summary": "ok",
                    "picks": [{"id": self.tasks[0].id, "reason": "x", "estimated_minutes": 30}]}

        with patch("apps.goals.services.replan.llm.complete_json", side_effect=fake_complete):
            self.client.post(self.url, {"minutes": 120}, format="json")

        self.assertNotIn(f"id={foreign_task.id}", captured["prompt"])
