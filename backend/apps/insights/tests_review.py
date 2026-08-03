import datetime as dt
from unittest.mock import patch

from django.test import override_settings
from django.utils import timezone

from common.testing import AuthenticatedAPITestCase

from apps.focus.models import FocusSession
from apps.goals.models import Goal, Milestone, Task
from apps.insights.models import WeeklyReview
from apps.insights.review import collect_stats, week_bounds


class WeekBoundsTests(AuthenticatedAPITestCase):
    def test_week_runs_monday_to_sunday(self):
        start, end = week_bounds(dt.date(2026, 8, 5))  # a Wednesday
        self.assertEqual(start, dt.date(2026, 8, 3))
        self.assertEqual(end, dt.date(2026, 8, 9))
        self.assertEqual(start.weekday(), 0)


class CollectStatsTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.goal = Goal.objects.create(user=self.user, title="Learn Python")
        self.milestone = Milestone.objects.create(goal=self.goal, title="Basics")
        self.start, self.end = week_bounds()

    def complete_task(self, title, days_ago):
        task = Task.objects.create(milestone=self.milestone, title=title)
        task.is_complete = True
        task.save()
        Task.objects.filter(id=task.id).update(
            completed_at=timezone.now() - dt.timedelta(days=days_ago)
        )
        return task

    def test_counts_only_work_inside_the_window(self):
        self.complete_task("Inside the week", 0)
        self.complete_task("Long ago", 60)
        stats = collect_stats(self.user, self.start, self.end)
        self.assertEqual(stats["tasks_completed"], 1)
        self.assertEqual(stats["completed_titles"], ["Inside the week"])

    def test_groups_completions_by_goal(self):
        self.complete_task("One", 0)
        self.complete_task("Two", 0)
        stats = collect_stats(self.user, self.start, self.end)
        self.assertEqual(stats["per_goal"], {"Learn Python": 2})

    def test_includes_focus_time_and_overdue_work(self):
        FocusSession.objects.create(user=self.user, seconds_elapsed=1800)
        Task.objects.create(
            milestone=self.milestone,
            title="Late",
            due_date=timezone.localdate() - dt.timedelta(days=3),
        )
        stats = collect_stats(self.user, self.start, self.end)
        self.assertEqual(stats["focus_minutes"], 30)
        self.assertEqual(stats["overdue_count"], 1)
        self.assertEqual(stats["overdue_titles"], ["Late"])

    def test_another_users_work_is_excluded(self):
        foreign_goal = Goal.objects.create(user=self.other, title="Theirs")
        foreign_milestone = Milestone.objects.create(goal=foreign_goal, title="X")
        task = Task.objects.create(milestone=foreign_milestone, title="Not mine")
        task.is_complete = True
        task.save()

        self.assertEqual(collect_stats(self.user, self.start, self.end)["tasks_completed"], 0)


class WeeklyReviewAPITests(AuthenticatedAPITestCase):
    url = "/api/weekly-review/"

    def setUp(self):
        super().setUp()
        goal = Goal.objects.create(user=self.user, title="Learn Python")
        milestone = Milestone.objects.create(goal=goal, title="Basics")
        task = Task.objects.create(milestone=milestone, title="Read a chapter")
        task.is_complete = True
        task.save()

    def test_get_returns_nothing_before_one_is_generated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["review"])

    @override_settings(USE_MOCK_AI=True)
    def test_post_generates_and_caches(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["review"]["headline"])
        self.assertEqual(WeeklyReview.objects.count(), 1)

        # A second GET is served from the cache, not regenerated.
        cached = self.client.get(self.url)
        self.assertEqual(cached.data["review"]["id"], response.data["review"]["id"])

    @override_settings(USE_MOCK_AI=True)
    def test_regenerating_updates_rather_than_duplicates(self):
        self.client.post(self.url, {}, format="json")
        self.client.post(self.url, {}, format="json")
        self.assertEqual(WeeklyReview.objects.count(), 1)

    def test_the_model_is_given_the_real_numbers(self):
        """The prose is written by the AI; the figures are not."""
        captured = {}

        def fake(system, user, temperature=0.2, retries=1, attachments=None):
            captured["prompt"] = user
            return {
                "headline": "A good week",
                "summary": "You made progress.",
                "wins": ["One task done"],
                "slipped": [],
                "focus_next": ["Keep going"],
            }

        with patch("apps.insights.review.llm.complete_json", side_effect=fake):
            self.client.post(self.url, {}, format="json")

        self.assertIn("Tasks completed: 1", captured["prompt"])
        self.assertIn("Read a chapter", captured["prompt"])

    @override_settings(USE_MOCK_AI=True)
    def test_stats_are_stored_alongside_the_prose(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.data["review"]["stats"]["tasks_completed"], 1)

    def test_a_malformed_response_is_reported(self):
        with patch("apps.insights.review.llm.complete_json", return_value="nope"):
            response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 502)

    @override_settings(USE_MOCK_AI=True)
    def test_reviews_are_per_user(self):
        self.client.post(self.url, {}, format="json")
        self.as_other()
        self.assertIsNone(self.client.get(self.url).data["review"])

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, 401)
