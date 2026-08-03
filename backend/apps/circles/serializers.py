from rest_framework import serializers

from .models import Circle
from .services import circle_leaderboard


class CircleListSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(source="memberships.count", read_only=True)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Circle
        fields = ["id", "name", "created_at", "member_count", "is_owner"]

    def get_is_owner(self, obj):
        request = self.context.get("request")
        return bool(request and obj.created_by_id == request.user.id)


class CircleDetailSerializer(CircleListSerializer):
    invite_token = serializers.UUIDField(read_only=True)
    leaderboard = serializers.SerializerMethodField()

    class Meta(CircleListSerializer.Meta):
        fields = CircleListSerializer.Meta.fields + ["invite_token", "leaderboard"]

    def get_leaderboard(self, obj):
        request = self.context.get("request")
        rows = circle_leaderboard(obj)
        if request:
            for row in rows:
                row["is_you"] = row["user_id"] == request.user.id
        return rows


class CreateCircleSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, trim_whitespace=True)

    def validate_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Give the circle a slightly longer name.")
        return value.strip()


class JoinCircleSerializer(serializers.Serializer):
    token = serializers.UUIDField()
