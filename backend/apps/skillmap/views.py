from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.goals.models import Goal, Milestone

from . import services
from .models import SkillMap


def _owned_goal(goal_id, user):
    return get_object_or_404(
        Goal.objects.prefetch_related(
            Prefetch("milestones", queryset=Milestone.objects.prefetch_related("tasks"))
        ),
        pk=goal_id,
        user=user,
    )


class SkillMapView(APIView):
    """GET the cached graph, with completion computed live against real
    tasks — never returns stale progress even though the structure is cached."""

    def get(self, request, goal_id):
        goal = _owned_goal(goal_id, request.user)
        skill_map = SkillMap.objects.filter(goal=goal).first()
        if skill_map is None:
            return Response({"generated": False, "nodes": [], "edges": []})

        return Response(
            {
                "generated": True,
                "nodes": services.merge_progress(goal, skill_map.nodes),
                "edges": skill_map.edges,
                "generated_at": skill_map.generated_at,
            }
        )


class SkillMapGenerateView(APIView):
    """Build (or rebuild) the graph. An explicit action, not automatic on
    every page load, since it spends an AI request."""

    def post(self, request, goal_id):
        goal = _owned_goal(goal_id, request.user)
        nodes, edges = services.generate_skill_map(goal)

        skill_map, _created = SkillMap.objects.update_or_create(
            goal=goal, defaults={"nodes": nodes, "edges": edges}
        )
        return Response(
            {
                "generated": True,
                "nodes": services.merge_progress(goal, skill_map.nodes),
                "edges": skill_map.edges,
                "generated_at": skill_map.generated_at,
            },
            status=status.HTTP_201_CREATED,
        )
