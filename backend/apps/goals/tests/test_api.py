import datetime as dt
from unittest.mock import patch

from django.test import override_settings
from rest_framework.test import APITestCase

from common.testing import AuthenticatedAPITestCase, results

from apps.goals.models import Goal, Milestone, Resource, Task
from apps.goals.services import resources as resources_service


def roadmap_payload():
    return [
        {
            "title": "Understand the fundamentals",
            "target_date": "2026-03-01",
            "search_query": "python basics",
            "order": 0,
            "tasks": [
                {"title": "Watch an intro course", "due_date": "2026-02-10", "order": 0},
                {"title": "Do the exercises", "due_date": "2026-02-20", "order": 1},
            ],
        },
        {
            "title": "Build something small",
            "target_date": "2026-04-01",
            "search_query": "python beginner projects",
            "order": 1,
            "tasks": [{"title": "Ship a CLI tool", "due_date": "2026-03-20", "order": 0}],
        },
    ]


class AuthenticationRequiredTests(APITestCase):
    def test_every_goal_endpoint_requires_a_token(self):
        for path in ("/api/goals/", "/api/tasks/", "/api/milestones/", "/api/dashboard/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 401)


class GoalCreationTests(AuthenticatedAPITestCase):
    def test_creates_a_goal_with_its_whole_roadmap_in_one_call(self):
        response = self.client.post(
            "/api/goals/",
            {
                "title": "Learn Python",
                "raw_input_text": "I want to learn Python in 3 months",
                "target_date": "2026-04-01",
                "milestones": roadmap_payload(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)

        goal = Goal.objects.get(id=response.data["id"])
        self.assertEqual(goal.user, self.user)
        self.assertEqual(goal.milestones.count(), 2)
        self.assertEqual(Task.objects.filter(milestone__goal=goal).count(), 3)
        self.assertEqual(response.data["total_tasks"], 3)
        self.assertEqual(response.data["progress"], 0)

    def test_milestone_order_follows_payload_position(self):
        payload = roadmap_payload()
        payload[0]["order"] = 99  # a stale order from the client must not win
        response = self.client.post(
            "/api/goals/", {"title": "Learn Python", "milestones": payload}, format="json"
        )
        orders = list(
            Milestone.objects.filter(goal_id=response.data["id"])
            .order_by("id")
            .values_list("order", flat=True)
        )
        self.assertEqual(orders, [0, 1])

    def test_a_goal_can_be_created_with_no_milestones(self):
        response = self.client.post(
            "/api/goals/", {"title": "Empty goal", "milestones": []}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["milestone_count"], 0)

    def test_search_query_defaults_to_the_milestone_title(self):
        payload = roadmap_payload()
        payload[0]["search_query"] = ""
        response = self.client.post(
            "/api/goals/", {"title": "Learn Python", "milestones": payload}, format="json"
        )
        milestone = Milestone.objects.get(goal_id=response.data["id"], order=0)
        self.assertEqual(milestone.search_query, "Understand the fundamentals")

    def test_a_goal_always_belongs_to_the_caller(self):
        """A client cannot assign a goal to somebody else by passing a user id."""
        response = self.client.post(
            "/api/goals/",
            {"title": "Learn Python", "user": self.other.id, "milestones": []},
            format="json",
        )
        self.assertEqual(Goal.objects.get(id=response.data["id"]).user, self.user)


class GoalGenerationTests(AuthenticatedAPITestCase):
    url = "/api/goals/generate/"

    @override_settings(USE_MOCK_AI=True)
    def test_generation_returns_a_preview(self):
        response = self.client.post(
            self.url, {"text": "Crack GATE in 8 months"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["milestones"])
        self.assertEqual(response.data["raw_input_text"], "Crack GATE in 8 months")

    @override_settings(USE_MOCK_AI=True)
    def test_generation_does_not_persist_anything(self):
        """An abandoned generation must not leave an orphan goal behind."""
        self.client.post(self.url, {"text": "Crack GATE in 8 months"}, format="json")
        self.assertEqual(Goal.objects.count(), 0)
        self.assertEqual(Milestone.objects.count(), 0)

    def test_short_input_is_rejected_before_reaching_the_model(self):
        with patch("apps.goals.services.roadmap.llm.complete_json") as mocked:
            response = self.client.post(self.url, {"text": "hi"}, format="json")
        self.assertEqual(response.status_code, 400)
        mocked.assert_not_called()

    def test_missing_text_is_rejected(self):
        self.assertEqual(self.client.post(self.url, {}, format="json").status_code, 400)

    def test_model_output_is_validated_before_it_reaches_the_client(self):
        with patch(
            "apps.goals.services.roadmap.llm.complete_json",
            return_value={"milestones": []},
        ):
            response = self.client.post(
                self.url, {"text": "Crack GATE in 8 months"}, format="json"
            )
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.data["code"], "schema_no_milestones")

    def test_a_service_failure_returns_a_readable_message(self):
        from common.exceptions import ServiceError

        with patch(
            "apps.goals.services.roadmap.llm.complete_json",
            side_effect=ServiceError("The AI took too long.", 504, "llm_timeout"),
        ):
            response = self.client.post(
                self.url, {"text": "Crack GATE in 8 months"}, format="json"
            )
        self.assertEqual(response.status_code, 504)
        self.assertEqual(response.data["detail"], "The AI took too long.")

    def test_a_valid_generation_passes_the_target_date_through(self):
        captured = {}

        def fake_generate(text, target_date=None):
            captured["target_date"] = target_date
            return [{"title": "M", "target_date": None, "search_query": "q",
                     "order": 0, "tasks": []}]

        with patch("apps.goals.views.roadmap_service.generate_roadmap", fake_generate):
            self.client.post(
                self.url,
                {"text": "Crack GATE in 8 months", "target_date": "2026-06-01"},
                format="json",
            )
        self.assertEqual(captured["target_date"], dt.date(2026, 6, 1))


class GoalDetailTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        response = self.client.post(
            "/api/goals/",
            {"title": "Learn Python", "milestones": roadmap_payload()},
            format="json",
        )
        self.goal_id = response.data["id"]

    def test_detail_nests_milestones_tasks_and_resources(self):
        response = self.client.get(f"/api/goals/{self.goal_id}/")
        self.assertEqual(response.status_code, 200)
        milestones = response.data["milestones"]
        self.assertEqual(len(milestones), 2)
        self.assertEqual(len(milestones[0]["tasks"]), 2)
        self.assertIn("resources", milestones[0])

    def test_progress_is_derived_from_completed_tasks(self):
        task = Task.objects.filter(milestone__goal_id=self.goal_id).first()
        self.client.patch(f"/api/tasks/{task.id}/", {"is_complete": True}, format="json")

        response = self.client.get(f"/api/goals/{self.goal_id}/")
        self.assertEqual(response.data["completed_tasks"], 1)
        self.assertEqual(response.data["total_tasks"], 3)
        self.assertEqual(response.data["progress"], 33)

    def test_deleting_a_goal_cascades(self):
        self.client.delete(f"/api/goals/{self.goal_id}/")
        self.assertEqual(Goal.objects.count(), 0)
        self.assertEqual(Milestone.objects.count(), 0)
        self.assertEqual(Task.objects.count(), 0)

    def test_another_user_cannot_read_or_delete_the_goal(self):
        self.as_other()
        self.assertEqual(self.client.get(f"/api/goals/{self.goal_id}/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/goals/{self.goal_id}/").status_code, 404)
        self.assertEqual(Goal.objects.count(), 1)

    def test_goal_list_only_shows_your_own_goals(self):
        self.as_other()
        self.assertEqual(results(self.client.get("/api/goals/")), [])


class MilestoneTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.goal = Goal.objects.create(user=self.user, title="Learn Python")
        self.first = Milestone.objects.create(goal=self.goal, title="First", order=0)
        self.second = Milestone.objects.create(goal=self.goal, title="Second", order=1)

    def test_rename_a_milestone(self):
        response = self.client.patch(
            f"/api/milestones/{self.first.id}/", {"title": "Renamed"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.first.refresh_from_db()
        self.assertEqual(self.first.title, "Renamed")

    def test_cannot_attach_a_milestone_to_someone_elses_goal(self):
        other_goal = Goal.objects.create(user=self.other, title="Not yours")
        response = self.client.post(
            "/api/milestones/", {"goal": other_goal.id, "title": "Sneaky"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_reorder_swaps_positions(self):
        response = self.client.post(
            "/api/milestones/reorder/",
            {"items": [{"id": self.first.id, "order": 1}, {"id": self.second.id, "order": 0}]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["updated"], 2)
        self.first.refresh_from_db()
        self.second.refresh_from_db()
        self.assertEqual((self.first.order, self.second.order), (1, 0))

    def test_reorder_ignores_rows_you_do_not_own(self):
        foreign = Milestone.objects.create(
            goal=Goal.objects.create(user=self.other, title="Theirs"), title="X", order=0
        )
        response = self.client.post(
            "/api/milestones/reorder/",
            {"items": [{"id": foreign.id, "order": 9}]},
            format="json",
        )
        self.assertEqual(response.data["updated"], 0)
        foreign.refresh_from_db()
        self.assertEqual(foreign.order, 0)

    def test_deleting_a_milestone_removes_its_tasks(self):
        Task.objects.create(milestone=self.first, title="Doomed")
        self.client.delete(f"/api/milestones/{self.first.id}/")
        self.assertEqual(Task.objects.count(), 0)


class ResourceEndpointTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        goal = Goal.objects.create(user=self.user, title="Learn Python")
        self.milestone = Milestone.objects.create(
            goal=goal, title="Basics", search_query="python basics"
        )

    def test_returns_resources_and_any_warning(self):
        def fake_fetch(milestone):
            resource = Resource.objects.create(
                milestone=milestone,
                title="Search the web",
                url=resources_service.google_search_url("python basics"),
                source=Resource.Source.GOOGLE_SEARCH,
            )
            return [resource], "Couldn't load videos right now."

        with patch(
            "apps.goals.views.resources_service.fetch_resources_for_milestone", fake_fetch
        ):
            response = self.client.post(f"/api/milestones/{self.milestone.id}/resources/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["resources"]), 1)
        self.assertIn("videos", response.data["warning"])

    def test_another_user_cannot_spend_quota_on_your_milestone(self):
        self.as_other()
        with patch(
            "apps.goals.views.resources_service.fetch_resources_for_milestone"
        ) as mocked:
            response = self.client.post(f"/api/milestones/{self.milestone.id}/resources/")
        self.assertEqual(response.status_code, 404)
        mocked.assert_not_called()


class TaskTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.goal = Goal.objects.create(user=self.user, title="Learn Python")
        self.other_goal = Goal.objects.create(user=self.user, title="Learn Django")
        self.milestone = Milestone.objects.create(goal=self.goal, title="Basics")
        other_milestone = Milestone.objects.create(goal=self.other_goal, title="Models")

        today = dt.date.today()
        self.overdue = Task.objects.create(
            milestone=self.milestone, title="Overdue", due_date=today - dt.timedelta(days=2)
        )
        self.today_task = Task.objects.create(
            milestone=self.milestone, title="Today", due_date=today
        )
        self.this_week = Task.objects.create(
            milestone=other_milestone, title="This week", due_date=today + dt.timedelta(days=3)
        )
        self.far_off = Task.objects.create(
            milestone=other_milestone, title="Far off", due_date=today + dt.timedelta(days=60)
        )
        self.undated = Task.objects.create(milestone=self.milestone, title="Undated")
        self.done = Task.objects.create(
            milestone=self.milestone, title="Done", is_complete=True
        )

    def test_list_carries_goal_context_for_the_cross_goal_view(self):
        rows = results(self.client.get("/api/tasks/"))
        self.assertTrue(all("goal_title" in row for row in rows))
        self.assertTrue(all("milestone_title" in row for row in rows))

    def test_undated_tasks_sort_last(self):
        rows = results(self.client.get("/api/tasks/?status=pending"))
        self.assertEqual(rows[-1]["title"], "Undated")

    def test_filter_by_goal(self):
        rows = results(self.client.get(f"/api/tasks/?goal={self.other_goal.id}"))
        self.assertEqual({r["title"] for r in rows}, {"This week", "Far off"})

    def test_filter_by_status(self):
        rows = results(self.client.get("/api/tasks/?status=complete"))
        self.assertEqual([r["title"] for r in rows], ["Done"])

    def test_filter_due_today(self):
        rows = results(self.client.get("/api/tasks/?due=today"))
        self.assertEqual([r["title"] for r in rows], ["Today"])

    def test_filter_overdue_excludes_completed_work(self):
        rows = results(self.client.get("/api/tasks/?due=overdue"))
        self.assertEqual([r["title"] for r in rows], ["Overdue"])

    def test_filter_next_seven_days(self):
        rows = results(self.client.get("/api/tasks/?due=week"))
        titles = {r["title"] for r in rows}
        self.assertIn("This week", titles)
        self.assertNotIn("Far off", titles)
        self.assertNotIn("Overdue", titles)

    def test_filters_combine(self):
        rows = results(
            self.client.get(f"/api/tasks/?goal={self.goal.id}&status=pending&due=today")
        )
        self.assertEqual([r["title"] for r in rows], ["Today"])

    def test_a_junk_filter_value_is_ignored_rather_than_erroring(self):
        response = self.client.get("/api/tasks/?goal=abc&due=whenever")
        self.assertEqual(response.status_code, 200)

    def test_complete_a_task(self):
        response = self.client.patch(
            f"/api/tasks/{self.today_task.id}/", {"is_complete": True}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.today_task.refresh_from_db()
        self.assertTrue(self.today_task.is_complete)

    def test_cannot_attach_a_task_to_someone_elses_milestone(self):
        foreign = Milestone.objects.create(
            goal=Goal.objects.create(user=self.other, title="Theirs"), title="X"
        )
        response = self.client.post(
            "/api/tasks/", {"milestone": foreign.id, "title": "Sneaky"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_another_user_sees_none_of_your_tasks(self):
        self.as_other()
        self.assertEqual(results(self.client.get("/api/tasks/")), [])


class TaskBreakdownTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        goal = Goal.objects.create(user=self.user, title="Learn Python")
        milestone = Milestone.objects.create(goal=goal, title="Basics")
        self.task = Task.objects.create(
            milestone=milestone, title="Build a REST API", due_date=dt.date(2026, 3, 10), order=0
        )

    @override_settings(USE_MOCK_AI=True)
    def test_breakdown_creates_subtasks_linked_to_the_parent(self):
        response = self.client.post(f"/api/tasks/{self.task.id}/breakdown/")
        self.assertEqual(response.status_code, 201)
        self.assertGreaterEqual(len(response.data), 2)

        subtasks = Task.objects.filter(parent=self.task)
        self.assertEqual(subtasks.count(), len(response.data))
        self.assertTrue(all(s.milestone_id == self.task.milestone_id for s in subtasks))

    @override_settings(USE_MOCK_AI=True)
    def test_subtasks_sort_after_their_parent(self):
        self.client.post(f"/api/tasks/{self.task.id}/breakdown/")
        orders = list(
            Task.objects.filter(parent=self.task).values_list("order", flat=True)
        )
        self.assertTrue(all(order > self.task.order for order in orders))

    @override_settings(USE_MOCK_AI=True)
    def test_deleting_the_parent_removes_its_subtasks(self):
        self.client.post(f"/api/tasks/{self.task.id}/breakdown/")
        self.client.delete(f"/api/tasks/{self.task.id}/")
        self.assertEqual(Task.objects.count(), 0)

    def test_another_user_cannot_break_down_your_task(self):
        self.as_other()
        response = self.client.post(f"/api/tasks/{self.task.id}/breakdown/")
        self.assertEqual(response.status_code, 404)


class DashboardTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        goal = Goal.objects.create(user=self.user, title="Learn Python")
        milestone = Milestone.objects.create(goal=goal, title="Basics")
        today = dt.date.today()

        Task.objects.create(milestone=milestone, title="Today", due_date=today)
        Task.objects.create(
            milestone=milestone, title="Overdue", due_date=today - dt.timedelta(days=1)
        )
        Task.objects.create(
            milestone=milestone, title="Upcoming", due_date=today + dt.timedelta(days=3)
        )
        Task.objects.create(
            milestone=milestone, title="Far off", due_date=today + dt.timedelta(days=30)
        )
        Task.objects.create(
            milestone=milestone,
            title="Already done",
            due_date=today,
            is_complete=True,
        )

    def test_dashboard_buckets_tasks_correctly(self):
        response = self.client.get("/api/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([t["title"] for t in response.data["today"]], ["Today"])
        self.assertEqual([t["title"] for t in response.data["overdue"]], ["Overdue"])
        self.assertEqual([t["title"] for t in response.data["upcoming"]], ["Upcoming"])

    def test_dashboard_stats(self):
        stats = self.client.get("/api/dashboard/").data["stats"]
        self.assertEqual(stats["total_goals"], 1)
        self.assertEqual(stats["total_tasks"], 5)
        self.assertEqual(stats["completed_tasks"], 1)
        self.assertEqual(stats["due_today"], 1)
        self.assertEqual(stats["overdue"], 1)

    def test_dashboard_is_empty_for_a_new_user(self):
        self.as_other()
        response = self.client.get("/api/dashboard/")
        self.assertEqual(response.data["stats"]["total_goals"], 0)
        self.assertEqual(response.data["today"], [])


class GoalModelTests(AuthenticatedAPITestCase):
    def test_progress_is_zero_with_no_tasks(self):
        goal = Goal.objects.create(user=self.user, title="Empty")
        self.assertEqual(goal.progress, 0)

    def test_progress_rounds_to_a_whole_percent(self):
        goal = Goal.objects.create(user=self.user, title="Learn Python")
        milestone = Milestone.objects.create(goal=goal, title="Basics")
        for index in range(3):
            Task.objects.create(
                milestone=milestone, title=f"Task {index}", is_complete=index == 0
            )
        self.assertEqual(goal.progress, 33)

    def test_progress_reaches_one_hundred(self):
        goal = Goal.objects.create(user=self.user, title="Learn Python")
        milestone = Milestone.objects.create(goal=goal, title="Basics")
        Task.objects.create(milestone=milestone, title="Only task", is_complete=True)
        self.assertEqual(goal.progress, 100)
