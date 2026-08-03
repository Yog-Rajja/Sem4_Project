from django.db import transaction
from rest_framework import serializers

from .models import Goal, Milestone, Resource, Task


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = ["id", "title", "url", "source", "thumbnail_url", "channel_title"]
        read_only_fields = fields


class TaskSerializer(serializers.ModelSerializer):
    """Task as it appears nested under a milestone."""

    class Meta:
        model = Task
        fields = ["id", "milestone", "parent", "title", "due_date", "is_complete", "order"]
        read_only_fields = ["id"]

    def validate_milestone(self, milestone):
        request = self.context.get("request")
        if request and milestone.goal.user_id != request.user.id:
            raise serializers.ValidationError("That milestone does not exist.")
        return milestone


class TaskListSerializer(TaskSerializer):
    """Task as it appears in the cross-goal /api/tasks/ view, carrying enough
    context to render without a second request."""

    goal_id = serializers.IntegerField(source="milestone.goal_id", read_only=True)
    goal_title = serializers.CharField(source="milestone.goal.title", read_only=True)
    milestone_title = serializers.CharField(source="milestone.title", read_only=True)

    class Meta(TaskSerializer.Meta):
        fields = TaskSerializer.Meta.fields + ["goal_id", "goal_title", "milestone_title"]


class MilestoneSerializer(serializers.ModelSerializer):
    tasks = TaskSerializer(many=True, read_only=True)
    resources = ResourceSerializer(many=True, read_only=True)
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Milestone
        fields = [
            "id", "goal", "title", "target_date", "order", "search_query",
            "is_complete", "resources_fetched_at", "tasks", "resources", "progress",
        ]
        read_only_fields = ["id", "resources_fetched_at"]

    def get_progress(self, obj):
        tasks = list(obj.tasks.all())
        if not tasks:
            return 0
        return round(sum(1 for t in tasks if t.is_complete) * 100 / len(tasks))

    def validate_goal(self, goal):
        request = self.context.get("request")
        if request and goal.user_id != request.user.id:
            raise serializers.ValidationError("That goal does not exist.")
        return goal


# --- Nested write payloads (used by the "save this roadmap" call) ---------

class NestedTaskWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    due_date = serializers.DateField(required=False, allow_null=True)
    order = serializers.IntegerField(required=False, default=0)


class NestedMilestoneWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    target_date = serializers.DateField(required=False, allow_null=True)
    search_query = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    order = serializers.IntegerField(required=False, default=0)
    tasks = NestedTaskWriteSerializer(many=True, required=False, default=list)


class GoalSerializer(serializers.ModelSerializer):
    """Goal summary for list/card views."""

    progress = serializers.IntegerField(read_only=True)
    total_tasks = serializers.SerializerMethodField()
    completed_tasks = serializers.SerializerMethodField()
    milestone_count = serializers.SerializerMethodField()

    class Meta:
        model = Goal
        fields = [
            "id", "title", "raw_input_text", "target_date", "created_at",
            "progress", "total_tasks", "completed_tasks", "milestone_count",
        ]
        read_only_fields = ["id", "created_at"]

    def get_total_tasks(self, obj):
        return obj.task_counts()[0]

    def get_completed_tasks(self, obj):
        return obj.task_counts()[1]

    def get_milestone_count(self, obj):
        return obj.milestones.count()


class GoalCreateSerializer(GoalSerializer):
    """Creates a goal and, optionally, its whole roadmap in one transaction.

    This is what the New Goal screen posts after the user has edited the
    AI-generated preview.
    """

    milestones = NestedMilestoneWriteSerializer(many=True, required=False, default=list)

    class Meta(GoalSerializer.Meta):
        fields = GoalSerializer.Meta.fields + ["milestones"]

    @transaction.atomic
    def create(self, validated_data):
        milestones = validated_data.pop("milestones", [])
        goal = Goal.objects.create(user=self.context["request"].user, **validated_data)

        for m_index, milestone_data in enumerate(milestones):
            tasks = milestone_data.pop("tasks", [])
            milestone_data.setdefault("order", m_index)
            milestone_data["order"] = m_index
            if not milestone_data.get("search_query"):
                milestone_data["search_query"] = milestone_data["title"]
            milestone = Milestone.objects.create(goal=goal, **milestone_data)

            Task.objects.bulk_create(
                [
                    Task(
                        milestone=milestone,
                        title=task["title"],
                        due_date=task.get("due_date"),
                        order=t_index,
                    )
                    for t_index, task in enumerate(tasks)
                ]
            )
        return goal


class GoalDetailSerializer(GoalSerializer):
    milestones = MilestoneSerializer(many=True, read_only=True)

    class Meta(GoalSerializer.Meta):
        fields = GoalSerializer.Meta.fields + ["milestones"]


# --- AI endpoints ---------------------------------------------------------

class GenerateRoadmapInputSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=1000, trim_whitespace=True)
    target_date = serializers.DateField(required=False, allow_null=True)

    def validate_text(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError(
                "Describe your goal in a few more words so we can plan it properly."
            )
        return value.strip()


class PlanDayInputSerializer(serializers.Serializer):
    """How much focused time the user actually has today."""

    minutes = serializers.IntegerField(min_value=15, max_value=720, default=120)


class ReorderSerializer(serializers.Serializer):
    """`[{id, order}, ...]` — used for both milestone and task reordering."""

    class ItemSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        order = serializers.IntegerField(min_value=0)

    items = ItemSerializer(many=True)
