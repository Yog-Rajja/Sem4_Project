from rest_framework import serializers

from apps.goals.models import Goal

from .models import Document

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


class DocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    goal_title = serializers.CharField(source="goal.title", read_only=True)

    class Meta:
        model = Document
        fields = [
            "id", "goal", "goal_title", "file", "file_url",
            "original_name", "size_bytes", "uploaded_at",
        ]
        read_only_fields = ["id", "original_name", "size_bytes", "uploaded_at"]
        extra_kwargs = {"file": {"write_only": True}}

    def get_file_url(self, obj):
        request = self.context.get("request")
        url = obj.file.url
        return request.build_absolute_uri(url) if request else url

    def validate_goal(self, goal: Goal):
        request = self.context.get("request")
        if request and goal.user_id != request.user.id:
            raise serializers.ValidationError("That goal does not exist.")
        return goal

    def validate_file(self, uploaded):
        if uploaded.size > MAX_UPLOAD_BYTES:
            raise serializers.ValidationError("Files must be 10 MB or smaller.")
        return uploaded

    def create(self, validated_data):
        uploaded = validated_data["file"]
        validated_data["original_name"] = uploaded.name[:255]
        validated_data["size_bytes"] = uploaded.size
        return super().create(validated_data)
