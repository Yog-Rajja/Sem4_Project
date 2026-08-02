import datetime as dt

from common.testing import AuthenticatedAPITestCase

from apps.goals.models import Goal, Milestone, Task


class OverviewTests(AuthenticatedAPITestCase):
    url = "/api/analytics/overview/"

    def setUp(self):
        super().setUp()
        self.goal = Goal.objects.create(user=self.user, title="Learn Python")
        milestone = Milestone.objects.create(goal=self.goal, title="Basics")

        today = dt.date.today()
        Task.objects.create(milestone=milestone, title="Done", is_complete=True, due_date=today)
        Task.objects.create(milestone=milestone, title="Pending A", due_date=today)
        Task.objects.create(
            milestone=milestone, title="Pending B", due_date=today + dt.timedelta(days=2)
        )
        # Well outside the 14-day window.
        Task.objects.create(
            milestone=milestone, title="Far off", due_date=today + dt.timedelta(days=90)
        )

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, 401)

    def test_overall_totals(self):
        overall = self.client.get(self.url).data["overall"]
        self.assertEqual(overall["total"], 4)
        self.assertEqual(overall["completed"], 1)
        self.assertEqual(overall["pending"], 3)
        self.assertEqual(overall["progress"], 25)

    def test_per_goal_breakdown(self):
        per_goal = self.client.get(self.url).data["per_goal"]
        self.assertEqual(len(per_goal), 1)
        self.assertEqual(per_goal[0]["title"], "Learn Python")
        self.assertEqual(per_goal[0]["total"], 4)
        self.assertEqual(per_goal[0]["completed"], 1)
        self.assertEqual(per_goal[0]["progress"], 25)

    def test_per_goal_counts_are_not_inflated_by_joins(self):
        """Two milestones with tasks must not multiply the counts."""
        second = Milestone.objects.create(goal=self.goal, title="Advanced")
        Task.objects.create(milestone=second, title="Extra")

        per_goal = self.client.get(self.url).data["per_goal"]
        self.assertEqual(per_goal[0]["total"], 5)
        self.assertEqual(per_goal[0]["completed"], 1)

    def test_workload_covers_a_fortnight_of_pending_work(self):
        workload = self.client.get(self.url).data["workload"]
        self.assertEqual(len(workload), 14)

        today = dt.date.today().isoformat()
        by_date = {row["date"]: row["count"] for row in workload}
        # Two tasks due today, but the completed one is excluded.
        self.assertEqual(by_date[today], 1)
        self.assertEqual(sum(row["count"] for row in workload), 2)

    def test_workload_rows_are_chart_ready(self):
        row = self.client.get(self.url).data["workload"][0]
        self.assertEqual(set(row), {"date", "label", "count"})

    def test_a_user_with_no_data_gets_zeroes_rather_than_an_error(self):
        self.as_other()
        data = self.client.get(self.url).data
        self.assertEqual(data["overall"]["total"], 0)
        self.assertEqual(data["overall"]["progress"], 0)
        self.assertEqual(data["per_goal"], [])
        self.assertEqual(len(data["workload"]), 14)

    def test_another_users_tasks_are_excluded(self):
        foreign_goal = Goal.objects.create(user=self.other, title="Theirs")
        foreign_milestone = Milestone.objects.create(goal=foreign_goal, title="X")
        Task.objects.create(milestone=foreign_milestone, title="Not mine")

        self.assertEqual(self.client.get(self.url).data["overall"]["total"], 4)
