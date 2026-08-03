import datetime as dt

from django.utils import timezone

from common.testing import AuthenticatedAPITestCase

from apps.focus.models import FocusSession
from apps.goals.models import Goal, Milestone, Task


class AlertTests(AuthenticatedAPITestCase):
    url = "/api/alerts/"

    def setUp(self):
        super().setUp()
        self.goal = Goal.objects.create(user=self.user, title="Learn Python")
        self.milestone = Milestone.objects.create(goal=self.goal, title="Basics")

    def kinds(self):
        return {a["kind"] for a in self.client.get(self.url).data["alerts"]}

    def test_a_clean_slate_produces_no_alerts(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["alerts"], [])
        self.assertEqual(response.data["unread"], 0)

    def test_overdue_tasks_raise_a_critical_alert(self):
        Task.objects.create(
            milestone=self.milestone,
            title="Late",
            due_date=timezone.localdate() - dt.timedelta(days=3),
        )
        alerts = self.client.get(self.url).data["alerts"]
        overdue = next(a for a in alerts if a["kind"] == "overdue_tasks")
        self.assertEqual(overdue["severity"], "critical")
        self.assertIn("1 overdue task", overdue["title"])

    def test_completed_tasks_are_not_overdue(self):
        Task.objects.create(
            milestone=self.milestone,
            title="Late but done",
            due_date=timezone.localdate() - dt.timedelta(days=3),
            is_complete=True,
        )
        self.assertNotIn("overdue_tasks", self.kinds())

    def test_an_overdue_milestone_is_reported(self):
        self.milestone.target_date = timezone.localdate() - dt.timedelta(days=2)
        self.milestone.save()
        alerts = self.client.get(self.url).data["alerts"]
        self.assertTrue(any(a["kind"].startswith("milestone_overdue_") for a in alerts))

    def test_a_goal_behind_pace_is_flagged(self):
        """Most of the time gone, almost none of the work done."""
        Goal.objects.filter(id=self.goal.id).update(
            created_at=timezone.now() - dt.timedelta(days=90),
            target_date=timezone.localdate() + dt.timedelta(days=10),
        )
        for index in range(10):
            Task.objects.create(milestone=self.milestone, title=f"Task {index}")

        alerts = self.client.get(self.url).data["alerts"]
        behind = next(a for a in alerts if a["kind"] == f"goal_behind_{self.goal.id}")
        self.assertEqual(behind["severity"], "warning")
        self.assertEqual(behind["path"], f"/goals/{self.goal.id}")

    def test_a_goal_on_pace_is_not_flagged(self):
        Goal.objects.filter(id=self.goal.id).update(
            created_at=timezone.now() - dt.timedelta(days=10),
            target_date=timezone.localdate() + dt.timedelta(days=90),
        )
        for index in range(10):
            Task.objects.create(
                milestone=self.milestone, title=f"Task {index}", is_complete=index < 5
            )
        self.assertNotIn(f"goal_behind_{self.goal.id}", self.kinds())

    def test_a_finished_goal_is_celebrated_not_scolded(self):
        Task.objects.create(milestone=self.milestone, title="Only task", is_complete=True)
        alerts = self.client.get(self.url).data["alerts"]
        done = next(a for a in alerts if a["kind"] == f"goal_complete_{self.goal.id}")
        self.assertEqual(done["severity"], "success")

    def test_a_stale_goal_is_surfaced(self):
        Goal.objects.filter(id=self.goal.id).update(
            created_at=timezone.now() - dt.timedelta(days=40)
        )
        Task.objects.create(milestone=self.milestone, title="Untouched")
        self.assertIn(f"goal_stale_{self.goal.id}", self.kinds())

    def test_a_streak_about_to_lapse_is_warned_about(self):
        # Active yesterday and the two days before, but nothing yet today.
        for days_ago in (1, 2, 3):
            session = FocusSession.objects.create(user=self.user, seconds_elapsed=1500)
            FocusSession.objects.filter(id=session.id).update(
                started_at=timezone.now() - dt.timedelta(days=days_ago)
            )
        alerts = self.client.get(self.url).data["alerts"]
        at_risk = next(a for a in alerts if a["kind"] == "streak_at_risk")
        self.assertIn("3-day streak", at_risk["title"])

    def test_no_streak_warning_when_already_active_today(self):
        FocusSession.objects.create(user=self.user, seconds_elapsed=1500)
        self.assertNotIn("streak_at_risk", self.kinds())

    def test_alerts_are_ordered_by_severity(self):
        Task.objects.create(
            milestone=self.milestone,
            title="Late",
            due_date=timezone.localdate() - dt.timedelta(days=1),
        )
        Task.objects.create(
            milestone=self.milestone, title="Today", due_date=timezone.localdate()
        )
        severities = [a["severity"] for a in self.client.get(self.url).data["alerts"]]
        rank = {"critical": 0, "warning": 1, "info": 2, "success": 3}
        self.assertEqual(severities, sorted(severities, key=lambda s: rank[s]))

    def test_unread_counts_only_things_needing_action(self):
        Task.objects.create(
            milestone=self.milestone,
            title="Late",
            due_date=timezone.localdate() - dt.timedelta(days=1),
        )
        Task.objects.create(
            milestone=self.milestone, title="Today", due_date=timezone.localdate()
        )
        response = self.client.get(self.url)
        self.assertEqual(response.data["unread"], 1)

    def test_another_users_problems_are_not_your_alerts(self):
        Task.objects.create(
            milestone=self.milestone,
            title="Late",
            due_date=timezone.localdate() - dt.timedelta(days=3),
        )
        self.as_other()
        self.assertEqual(self.client.get(self.url).data["alerts"], [])

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, 401)
