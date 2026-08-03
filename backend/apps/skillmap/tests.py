from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from common.exceptions import ServiceError
from common.testing import AuthenticatedAPITestCase

from apps.goals.models import Goal, Milestone, Task

from . import services
from .models import SkillMap


class ValidateSkillMapTests(SimpleTestCase):
    def test_accepts_a_well_formed_graph(self):
        raw = {
            "nodes": [
                {"id": "arrays", "label": "Arrays", "milestone_index": 0},
                {"id": "sorting", "label": "Sorting", "milestone_index": 1},
            ],
            "edges": [{"from": "arrays", "to": "sorting"}],
        }
        nodes, edges = services.validate_skill_map(raw, milestone_count=2)
        self.assertEqual([n["id"] for n in nodes], ["arrays", "sorting"])
        self.assertEqual(edges, [{"from": "arrays", "to": "sorting"}])

    def test_rejects_a_non_dict_payload(self):
        with self.assertRaises(ServiceError):
            services.validate_skill_map(["not", "a", "dict"], milestone_count=3)

    def test_rejects_an_empty_node_list(self):
        with self.assertRaises(ServiceError) as ctx:
            services.validate_skill_map({"nodes": []}, milestone_count=3)
        self.assertEqual(ctx.exception.code, "schema_no_nodes")

    def test_drops_unlabelled_nodes(self):
        raw = {"nodes": [{"id": "a", "label": "Real"}, {"id": "b", "label": "  "}]}
        nodes, _ = services.validate_skill_map(raw, milestone_count=1)
        self.assertEqual(len(nodes), 1)

    def test_milestone_index_is_clamped_into_range(self):
        raw = {"nodes": [{"id": "a", "label": "A", "milestone_index": 99}]}
        nodes, _ = services.validate_skill_map(raw, milestone_count=3)
        self.assertEqual(nodes[0]["milestone_index"], 2)

    def test_a_missing_or_junk_milestone_index_defaults_to_zero(self):
        raw = {"nodes": [{"id": "a", "label": "A", "milestone_index": "not a number"}]}
        nodes, _ = services.validate_skill_map(raw, milestone_count=3)
        self.assertEqual(nodes[0]["milestone_index"], 0)

    def test_duplicate_ids_are_disambiguated_rather_than_merged(self):
        raw = {
            "nodes": [
                {"id": "dp", "label": "Dynamic programming basics"},
                {"id": "dp", "label": "Dynamic programming advanced"},
            ]
        }
        nodes, _ = services.validate_skill_map(raw, milestone_count=1)
        self.assertEqual(len(nodes), 2)
        self.assertNotEqual(nodes[0]["id"], nodes[1]["id"])

    def test_ids_are_slugified(self):
        raw = {"nodes": [{"id": "Dynamic Programming!!", "label": "DP"}]}
        nodes, _ = services.validate_skill_map(raw, milestone_count=1)
        self.assertEqual(nodes[0]["id"], "dynamic-programming")

    def test_an_edge_to_an_unknown_node_is_dropped(self):
        raw = {
            "nodes": [{"id": "a", "label": "A"}],
            "edges": [{"from": "a", "to": "ghost"}],
        }
        _, edges = services.validate_skill_map(raw, milestone_count=1)
        self.assertEqual(edges, [])

    def test_a_self_loop_is_dropped(self):
        raw = {
            "nodes": [{"id": "a", "label": "A"}],
            "edges": [{"from": "a", "to": "a"}],
        }
        _, edges = services.validate_skill_map(raw, milestone_count=1)
        self.assertEqual(edges, [])

    def test_a_duplicate_edge_is_collapsed(self):
        raw = {
            "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
            "edges": [{"from": "a", "to": "b"}, {"from": "a", "to": "b"}],
        }
        _, edges = services.validate_skill_map(raw, milestone_count=1)
        self.assertEqual(len(edges), 1)

    def test_a_direct_cycle_is_rejected(self):
        """The whole point: a "prerequisite" graph must stay acyclic."""
        raw = {
            "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
            "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "a"}],
        }
        _, edges = services.validate_skill_map(raw, milestone_count=1)
        self.assertEqual(edges, [{"from": "a", "to": "b"}])

    def test_a_longer_cycle_is_rejected(self):
        raw = {
            "nodes": [{"id": n, "label": n} for n in "abcd"],
            "edges": [
                {"from": "a", "to": "b"},
                {"from": "b", "to": "c"},
                {"from": "c", "to": "d"},
                {"from": "d", "to": "a"},  # closes the loop
            ],
        }
        _, edges = services.validate_skill_map(raw, milestone_count=1)
        self.assertEqual(len(edges), 3)
        self.assertNotIn({"from": "d", "to": "a"}, edges)

    def test_a_legitimate_diamond_is_not_mistaken_for_a_cycle(self):
        """a -> b -> d and a -> c -> d is valid branching, not a loop."""
        raw = {
            "nodes": [{"id": n, "label": n} for n in "abcd"],
            "edges": [
                {"from": "a", "to": "b"},
                {"from": "a", "to": "c"},
                {"from": "b", "to": "d"},
                {"from": "c", "to": "d"},
            ],
        }
        _, edges = services.validate_skill_map(raw, milestone_count=1)
        self.assertEqual(len(edges), 4)

    def test_node_and_edge_counts_are_capped(self):
        raw = {"nodes": [{"id": f"n{i}", "label": f"N{i}"} for i in range(40)]}
        nodes, _ = services.validate_skill_map(raw, milestone_count=1)
        self.assertEqual(len(nodes), services.MAX_NODES)


class MockSkillMapTests(SimpleTestCase):
    """The offline stub has to satisfy the same shape as a real generation."""

    def test_produces_at_least_two_nodes_per_milestone(self):
        nodes, edges = services._mock_skill_map(["Basics", "Advanced", "Projects"])
        self.assertGreaterEqual(len(nodes), 6)
        self.assertTrue(edges)

    def test_every_edge_references_a_real_node(self):
        nodes, edges = services._mock_skill_map(["Basics", "Advanced", "Projects", "Review"])
        ids = {n["id"] for n in nodes}
        for edge in edges:
            self.assertIn(edge["from"], ids)
            self.assertIn(edge["to"], ids)

    def test_has_at_least_one_branch_with_four_milestones(self):
        """Not just a straight chain — the whole point of a graph."""
        _, edges = services._mock_skill_map(["A", "B", "C", "D"])
        sources = [e["from"] for e in edges]
        # A branch means some node is the source of more than one edge.
        self.assertTrue(any(sources.count(s) > 1 for s in set(sources)))

    def test_handles_a_single_milestone(self):
        nodes, edges = services._mock_skill_map(["Only one"])
        self.assertTrue(nodes)


@override_settings(USE_MOCK_AI=True)
class SkillMapAPITests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.goal = Goal.objects.create(user=self.user, title="Learn DSA")
        self.m1 = Milestone.objects.create(goal=self.goal, title="Arrays", order=0)
        self.m2 = Milestone.objects.create(goal=self.goal, title="Trees", order=1)

    def base(self):
        return f"/api/goals/{self.goal.id}/skillmap/"

    def test_get_before_generating_says_so(self):
        response = self.client.get(self.base())
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["generated"])
        self.assertEqual(response.data["nodes"], [])

    def test_generating_requires_at_least_one_milestone(self):
        empty = Goal.objects.create(user=self.user, title="Nothing yet")
        response = self.client.post(f"/api/goals/{empty.id}/skillmap/generate/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "no_milestones")

    def test_generate_then_get_returns_the_same_graph(self):
        generated = self.client.post(self.base() + "generate/")
        self.assertEqual(generated.status_code, 201)
        self.assertTrue(generated.data["nodes"])

        fetched = self.client.get(self.base())
        self.assertEqual(fetched.status_code, 200)
        self.assertTrue(fetched.data["generated"])
        self.assertEqual(
            [n["id"] for n in fetched.data["nodes"]],
            [n["id"] for n in generated.data["nodes"]],
        )

    def test_every_node_carries_which_milestone_it_belongs_to(self):
        response = self.client.post(self.base() + "generate/")
        for node in response.data["nodes"]:
            self.assertIn(node["milestone_index"], (0, 1))
            self.assertIn("milestone_title", node)

    def test_node_progress_is_live_not_frozen_at_generation_time(self):
        """The core guarantee: completing a task afterwards must move the
        graph, without regenerating it."""
        self.client.post(self.base() + "generate/")

        task = Task.objects.create(milestone=self.m1, title="Read chapter 1")
        before = self.client.get(self.base())
        node_before = next(
            n for n in before.data["nodes"] if n["milestone_index"] == 0
        )
        self.assertEqual(node_before["progress"], 0)

        task.is_complete = True
        task.save()

        after = self.client.get(self.base())
        node_after = next(n for n in after.data["nodes"] if n["milestone_index"] == 0)
        self.assertEqual(node_after["progress"], 100)
        self.assertTrue(node_after["complete"])

    def test_regenerating_replaces_rather_than_duplicates(self):
        self.client.post(self.base() + "generate/")
        self.client.post(self.base() + "generate/")
        self.assertEqual(SkillMap.objects.filter(goal=self.goal).count(), 1)

    def test_another_user_cannot_see_or_generate_your_graph(self):
        self.client.post(self.base() + "generate/")
        self.as_other()
        self.assertEqual(self.client.get(self.base()).status_code, 404)
        self.assertEqual(self.client.post(self.base() + "generate/").status_code, 404)

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.base()).status_code, 401)

    def test_a_malformed_model_response_is_reported(self):
        with override_settings(USE_MOCK_AI=False):
            with patch(
                "apps.skillmap.services.llm.complete_json",
                return_value={"nodes": []},
            ):
                response = self.client.post(self.base() + "generate/")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.data["code"], "schema_no_nodes")
