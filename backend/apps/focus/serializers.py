from rest_framework import serializers

from apps.goals.models import Task

from .models import FocusSession


class FocusSessionSerializer(serializers.ModelSerializer):
    minutes = serializers.IntegerField(read_only=True)
    goal_id = serializers.IntegerField(source="task.milestone.goal_id", read_only=True)

    class Meta:
        model = FocusSession
        fields = [
            "id", "task", "task_title", "goal_id", "mode", "planned_minutes",
            "started_at", "ended_at", "seconds_elapsed", "minutes", "completed",
        ]
        read_only_fields = ["id", "started_at", "ended_at", "seconds_elapsed", "completed"]

    def validate_task(self, task: Task):
        request = self.context.get("request")
        if task and request and task.milestone.goal.user_id != request.user.id:
            raise serializers.ValidationError("That task does not exist.")
        return task

    def create(self, validated_data):
        task = validated_data.get("task")
        if task is not None:
            validated_data["task_title"] = task.title
        return FocusSession.objects.create(
            user=self.context["request"].user, **validated_data
        )


class FinishSessionSerializer(serializers.Serializer):
    seconds_elapsed = serializers.IntegerField(min_value=0, max_value=60 * 60 * 8)
    completed = serializers.BooleanField(default=False)
