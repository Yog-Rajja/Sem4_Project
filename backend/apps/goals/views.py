import datetime as dt

from django.db import transaction
from django.db.models import F, Prefetch
from django.http import Http404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Goal, Milestone, Task
from .serializers import (
    GenerateRoadmapInputSerializer,
    GoalCreateSerializer,
    GoalDetailSerializer,
    GoalSerializer,
    MilestoneSerializer,
    PlanDayInputSerializer,
    PublicGoalSerializer,
    ReorderSerializer,
    ResourceSerializer,
    TaskListSerializer,
    TaskSerializer,
)
from .services import replan as replan_service
from .services import resources as resources_service
from .services import roadmap as roadmap_service

UPCOMING_WINDOW_DAYS = 7


class GoalViewSet(viewsets.ModelViewSet):
    """CRUD for goals, plus the AI roadmap generator."""

    def get_queryset(self):
        qs = Goal.objects.filter(user=self.request.user)
        if self.action in ("retrieve", "update", "partial_update"):
            qs = qs.prefetch_related(
                Prefetch(
                    "milestones",
                    queryset=Milestone.objects.prefetch_related("tasks", "resources"),
                )
            )
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return GoalCreateSerializer
        if self.action == "retrieve":
            return GoalDetailSerializer
        return GoalSerializer

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        """Generate a roadmap preview from natural language.

        Nothing is written to the database here — the frontend shows the result
        as an editable preview and POSTs it back to /api/goals/ when the user
        accepts it, so an abandoned generation leaves no orphan goal behind.
        """
        serializer = GenerateRoadmapInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        text = serializer.validated_data["text"]
        target_date = serializer.validated_data.get("target_date")

        # ServiceError from the AI layer is rendered as a clean JSON error by
        # common.exceptions.api_exception_handler.
        milestones = roadmap_service.generate_roadmap(text, target_date)

        return Response(
            {
                "title": text[:255],
                "raw_input_text": text,
                "target_date": target_date,
                "milestones": milestones,
            }
        )


    @action(detail=True, methods=["post"], url_path="replan")
    def replan(self, request, pk=None):
        """Reschedule the unfinished part of a roadmap around today's reality.

        Only dates move — titles, completion history and resources are left
        alone, so a re-plan is never destructive.
        """
        goal = self.get_object()
        result = replan_service.replan_goal(goal)
        goal.refresh_from_db()
        return Response(
            {**result, "goal": GoalDetailSerializer(goal, context={"request": request}).data}
        )


    @action(detail=True, methods=["post"], url_path="share")
    def share(self, request, pk=None):
        """Turn public sharing on or off for this roadmap."""
        goal = self.get_object()
        goal.is_shared = bool(request.data.get("shared", True))
        goal.save(update_fields=["is_shared"])
        return Response(
            {
                "is_shared": goal.is_shared,
                "share_token": str(goal.share_token) if goal.is_shared else None,
            }
        )


class PublicRoadmapView(APIView):
    """Read-only roadmap for anyone holding the link.

    Deliberately the only unauthenticated endpoint in the project: it takes an
    unguessable token, returns no identifiers, and 404s the moment sharing is
    switched off.
    """

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        goal = (
            Goal.objects.filter(share_token=token, is_shared=True)
            .select_related("user")
            .prefetch_related(
                Prefetch(
                    "milestones",
                    queryset=Milestone.objects.prefetch_related("tasks", "resources"),
                )
            )
            .first()
        )
        if goal is None:
            raise Http404("No shared roadmap here.")
        return Response(PublicGoalSerializer(goal).data)


class PlanMyDayView(APIView):
    """Pick today's realistic workload from across every goal."""

    def post(self, request):
        serializer = PlanDayInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = replan_service.plan_day(
            request.user, minutes=serializer.validated_data["minutes"]
        )
        return Response(
            {
                "summary": result["summary"],
                "available_minutes": result["available_minutes"],
                "picks": [
                    {
                        "task": TaskListSerializer(pick["task"]).data,
                        "reason": pick["reason"],
                        "estimated_minutes": pick["estimated_minutes"],
                    }
                    for pick in result["picks"]
                ],
            }
        )


class MilestoneViewSet(viewsets.ModelViewSet):
    serializer_class = MilestoneSerializer

    def get_queryset(self):
        return (
            Milestone.objects.filter(goal__user=self.request.user)
            .select_related("goal")
            .prefetch_related("tasks", "resources")
        )

    @action(detail=True, methods=["post"], url_path="resources")
    def resources(self, request, pk=None):
        """Fetch learning resources for one milestone, on demand.

        Lazy by design: called per milestone rather than for the whole roadmap,
        to stay well inside the YouTube API's daily quota.
        """
        milestone = self.get_object()
        found, warning = resources_service.fetch_resources_for_milestone(milestone)
        return Response(
            {
                "resources": ResourceSerializer(found, many=True).data,
                "warning": warning,
            }
        )

    @action(detail=False, methods=["post"], url_path="reorder")
    def reorder(self, request):
        return _apply_reorder(request, self.get_queryset())


class TaskViewSet(viewsets.ModelViewSet):
    """Cross-goal task list with filters, plus per-task CRUD."""

    def get_serializer_class(self):
        return TaskListSerializer if self.action == "list" else TaskSerializer

    def get_queryset(self):
        qs = Task.objects.filter(
            milestone__goal__user=self.request.user
        ).select_related("milestone", "milestone__goal")

        params = self.request.query_params

        goal_id = params.get("goal")
        if goal_id and goal_id.isdigit():
            qs = qs.filter(milestone__goal_id=int(goal_id))

        milestone_id = params.get("milestone")
        if milestone_id and milestone_id.isdigit():
            qs = qs.filter(milestone_id=int(milestone_id))

        task_status = params.get("status")
        if task_status == "complete":
            qs = qs.filter(is_complete=True)
        elif task_status == "pending":
            qs = qs.filter(is_complete=False)

        today = dt.date.today()
        due = params.get("due")
        if due == "today":
            qs = qs.filter(due_date=today)
        elif due == "week":
            qs = qs.filter(
                due_date__gte=today,
                due_date__lte=today + dt.timedelta(days=UPCOMING_WINDOW_DAYS),
            )
        elif due == "overdue":
            qs = qs.filter(due_date__lt=today, is_complete=False)

        if self.action == "list":
            # Pending first, then soonest due; undated tasks sort last.
            qs = qs.order_by(
                "is_complete", F("due_date").asc(nulls_last=True), "order", "id"
            )
        return qs

    @action(detail=True, methods=["post"], url_path="breakdown")
    def breakdown(self, request, pk=None):
        """P1: split one task into 2-4 subtasks using the roadmap plumbing."""
        task = self.get_object()
        subtasks = roadmap_service.generate_subtasks(
            task_title=task.title,
            goal_title=task.milestone.goal.title,
            due_date=task.due_date,
        )

        with transaction.atomic():
            start_order = task.order + 1
            created = Task.objects.bulk_create(
                [
                    Task(
                        milestone=task.milestone,
                        parent=task,
                        title=item["title"],
                        due_date=item["due_date"],
                        order=start_order + index,
                    )
                    for index, item in enumerate(subtasks)
                ]
            )
        return Response(
            TaskSerializer(created, many=True).data, status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["post"], url_path="reorder")
    def reorder(self, request):
        return _apply_reorder(request, self.get_queryset())


def _apply_reorder(request, queryset):
    """Shared reorder handler: bulk-update `order` for owned rows only."""
    serializer = ReorderSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    items = serializer.validated_data["items"]

    by_id = {obj.id: obj for obj in queryset.filter(id__in=[i["id"] for i in items])}
    to_update = []
    for item in items:
        obj = by_id.get(item["id"])
        if obj is not None:
            obj.order = item["order"]
            to_update.append(obj)

    if to_update:
        type(to_update[0]).objects.bulk_update(to_update, ["order"])
    return Response({"updated": len(to_update)})


class DashboardView(APIView):
    """Everything the dashboard needs, in one request."""

    def get(self, request):
        today = dt.date.today()
        week_end = today + dt.timedelta(days=UPCOMING_WINDOW_DAYS)

        owned = Task.objects.filter(
            milestone__goal__user=request.user
        ).select_related("milestone", "milestone__goal")

        today_tasks = owned.filter(due_date=today, is_complete=False)
        upcoming = owned.filter(
            due_date__gt=today, due_date__lte=week_end, is_complete=False
        ).order_by("due_date", "order")
        overdue = owned.filter(due_date__lt=today, is_complete=False).order_by("due_date")

        goals = Goal.objects.filter(user=request.user).prefetch_related("milestones")

        return Response(
            {
                "today": TaskListSerializer(today_tasks, many=True).data,
                "upcoming": TaskListSerializer(upcoming, many=True).data,
                "overdue": TaskListSerializer(overdue, many=True).data,
                "goals": GoalSerializer(goals, many=True).data,
                "stats": {
                    "total_goals": goals.count(),
                    "total_tasks": owned.count(),
                    "completed_tasks": owned.filter(is_complete=True).count(),
                    "due_today": today_tasks.count(),
                    "overdue": overdue.count(),
                },
            }
        )
