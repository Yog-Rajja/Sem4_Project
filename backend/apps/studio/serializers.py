from rest_framework import serializers

from apps.goals.models import Goal

from .models import Artifact


class ArtifactSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    export_format = serializers.CharField(read_only=True)

    class Meta:
        model = Artifact
        fields = [
            "id", "kind", "kind_label", "title", "prompt", "data",
            "goal", "export_format", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "kind", "prompt", "created_at", "updated_at"]

    def validate_goal(self, goal: Goal):
        request = self.context.get("request")
        if goal and request and goal.user_id != request.user.id:
            raise serializers.ValidationError("That goal does not exist.")
        return goal


class ArtifactListSerializer(ArtifactSerializer):
    """List view omits `data` — a report body is far too heavy for a card."""

    class Meta(ArtifactSerializer.Meta):
        fields = [
            "id", "kind", "kind_label", "title", "goal",
            "export_format", "created_at", "updated_at",
        ]


class GenerateArtifactSerializer(serializers.Serializer):
    prompt = serializers.CharField(max_length=4000, trim_whitespace=True)
    # Omit to let the studio work out the type from the prompt.
    kind = serializers.ChoiceField(
        choices=Artifact.Kind.choices, required=False, allow_null=True
    )
    goal = serializers.PrimaryKeyRelatedField(
        queryset=Goal.objects.all(), required=False, allow_null=True
    )
    document = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Optional vault document to use as the source of facts.",
    )

    def validate_prompt(self, value):
        if len(value.strip()) < 8:
            raise serializers.ValidationError(
                "Tell us a bit more about what you need."
            )
        return value.strip()

    def validate_goal(self, goal):
        request = self.context.get("request")
        if goal and request and goal.user_id != request.user.id:
            raise serializers.ValidationError("That goal does not exist.")
        return goal
