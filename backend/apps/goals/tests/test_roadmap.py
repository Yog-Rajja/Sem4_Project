import datetime as dt

from django.test import SimpleTestCase, override_settings

from common.exceptions import ServiceError

from apps.goals.services import roadmap


def milestone(**overrides):
    base = {
        "title": "Learn the basics",
        "target_date": "2026-03-01",
        "search_query": "python basics tutorial",
        "tasks": [{"title": "Watch an intro course", "due_date": "2026-02-10"}],
    }
    base.update(overrides)
    return base


class ValidateRoadmapTests(SimpleTestCase):
    def test_accepts_a_well_formed_payload(self):
        result = roadmap.validate_roadmap({"milestones": [milestone()]})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Learn the basics")
        self.assertEqual(result[0]["target_date"], dt.date(2026, 3, 1))
        self.assertEqual(result[0]["order"], 0)
        self.assertEqual(result[0]["tasks"][0]["due_date"], dt.date(2026, 2, 10))

    def test_orders_milestones_and_tasks_by_position(self):
        payload = {"milestones": [milestone(title="One"), milestone(title="Two")]}
        result = roadmap.validate_roadmap(payload)
        self.assertEqual([m["order"] for m in result], [0, 1])

    def test_rejects_a_non_dict_payload(self):
        with self.assertRaises(ServiceError):
            roadmap.validate_roadmap(["not", "a", "dict"])

    def test_rejects_a_payload_with_no_milestones_key(self):
        with self.assertRaises(ServiceError) as ctx:
            roadmap.validate_roadmap({"plan": []})
        self.assertEqual(ctx.exception.code, "schema_no_milestones")

    def test_rejects_an_empty_milestone_list(self):
        with self.assertRaises(ServiceError) as ctx:
            roadmap.validate_roadmap({"milestones": []})
        self.assertEqual(ctx.exception.code, "schema_no_milestones")

    def test_rejects_a_payload_where_every_milestone_is_unusable(self):
        with self.assertRaises(ServiceError) as ctx:
            roadmap.validate_roadmap({"milestones": [{"title": "  "}, "junk", 42]})
        self.assertEqual(ctx.exception.code, "schema_no_valid_milestones")

    def test_drops_untitled_milestones_but_keeps_the_rest(self):
        payload = {"milestones": [milestone(), {"title": ""}, milestone(title="Second")]}
        result = roadmap.validate_roadmap(payload)
        self.assertEqual([m["title"] for m in result], ["Learn the basics", "Second"])

    def test_drops_untitled_tasks(self):
        payload = {
            "milestones": [
                milestone(
                    tasks=[
                        {"title": "Keep me", "due_date": "2026-02-01"},
                        {"title": "   ", "due_date": "2026-02-02"},
                        "not a dict",
                    ]
                )
            ]
        }
        result = roadmap.validate_roadmap(payload)
        self.assertEqual([t["title"] for t in result[0]["tasks"]], ["Keep me"])

    def test_a_malformed_date_becomes_none_rather_than_failing_the_roadmap(self):
        """One bad date is far easier for a user to fix than a whole regeneration."""
        payload = {
            "milestones": [
                milestone(
                    target_date="next March",
                    tasks=[{"title": "Task", "due_date": "31/02/2026"}],
                )
            ]
        }
        result = roadmap.validate_roadmap(payload)
        self.assertIsNone(result[0]["target_date"])
        self.assertIsNone(result[0]["tasks"][0]["due_date"])
        self.assertEqual(result[0]["title"], "Learn the basics")

    def test_search_query_falls_back_to_the_title(self):
        result = roadmap.validate_roadmap({"milestones": [milestone(search_query="")]})
        self.assertEqual(result[0]["search_query"], "Learn the basics")

    def test_missing_tasks_key_yields_an_empty_task_list(self):
        payload = {"milestones": [{"title": "Solo", "target_date": "2026-03-01"}]}
        result = roadmap.validate_roadmap(payload)
        self.assertEqual(result[0]["tasks"], [])

    def test_caps_runaway_output(self):
        payload = {"milestones": [milestone() for _ in range(40)]}
        result = roadmap.validate_roadmap(payload)
        self.assertEqual(len(result), roadmap.MAX_MILESTONES)

    def test_caps_tasks_per_milestone(self):
        tasks = [{"title": f"Task {i}"} for i in range(40)]
        result = roadmap.validate_roadmap({"milestones": [milestone(tasks=tasks)]})
        self.assertEqual(len(result[0]["tasks"]), roadmap.MAX_TASKS_PER_MILESTONE)

    def test_overlong_strings_are_truncated_to_the_column_width(self):
        result = roadmap.validate_roadmap({"milestones": [milestone(title="x" * 500)]})
        self.assertEqual(len(result[0]["title"]), 255)


class ValidateSubtasksTests(SimpleTestCase):
    def test_accepts_a_well_formed_payload(self):
        payload = {"subtasks": [{"title": "Step one", "due_date": "2026-02-01"}]}
        result = roadmap.validate_subtasks(payload, parent_due=dt.date(2026, 2, 5))
        self.assertEqual(result[0]["title"], "Step one")
        self.assertEqual(result[0]["due_date"], dt.date(2026, 2, 1))

    def test_missing_due_date_inherits_the_parent(self):
        parent_due = dt.date(2026, 2, 5)
        result = roadmap.validate_subtasks({"subtasks": [{"title": "Step"}]}, parent_due)
        self.assertEqual(result[0]["due_date"], parent_due)

    def test_caps_the_number_of_subtasks(self):
        payload = {"subtasks": [{"title": f"Step {i}"} for i in range(10)]}
        result = roadmap.validate_subtasks(payload, None)
        self.assertEqual(len(result), roadmap.MAX_SUBTASKS)

    def test_rejects_a_payload_with_no_usable_subtasks(self):
        with self.assertRaises(ServiceError) as ctx:
            roadmap.validate_subtasks({"subtasks": [{"title": ""}]}, None)
        self.assertEqual(ctx.exception.code, "schema_no_subtasks")

    def test_rejects_a_malformed_payload(self):
        with self.assertRaises(ServiceError):
            roadmap.validate_subtasks({"steps": []}, None)


@override_settings(USE_MOCK_AI=True)
class MockGeneratorTests(SimpleTestCase):
    """The offline stub has to satisfy the same shape as a real generation,
    otherwise developing without keys would hide integration bugs."""

    def test_returns_a_usable_roadmap(self):
        result = roadmap.generate_roadmap("Learn React", dt.date.today() + dt.timedelta(days=90))
        self.assertGreaterEqual(len(result), 2)
        for entry in result:
            self.assertTrue(entry["title"])
            self.assertTrue(entry["search_query"])
            self.assertTrue(entry["tasks"])

    def test_milestone_dates_increase_and_respect_the_deadline(self):
        deadline = dt.date.today() + dt.timedelta(days=120)
        result = roadmap.generate_roadmap("Learn React", deadline)
        dates = [m["target_date"] for m in result]
        self.assertEqual(dates, sorted(dates))
        self.assertLessEqual(dates[-1], deadline)

    def test_tasks_never_fall_after_their_milestone(self):
        result = roadmap.generate_roadmap("Learn React", None)
        for entry in result:
            for task in entry["tasks"]:
                self.assertLessEqual(task["due_date"], entry["target_date"])

    def test_works_without_a_deadline(self):
        self.assertTrue(roadmap.generate_roadmap("Learn React", None))

    def test_subtask_generation_is_stubbed_too(self):
        result = roadmap.generate_subtasks("Build an API", "Learn Django", dt.date.today())
        self.assertGreaterEqual(len(result), 2)
