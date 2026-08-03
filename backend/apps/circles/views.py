import uuid

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Circle, CircleMembership
from .serializers import (
    CircleDetailSerializer,
    CircleListSerializer,
    CreateCircleSerializer,
    JoinCircleSerializer,
)


class CircleViewSet(viewsets.ModelViewSet):
    """Circles the current user belongs to.

    Membership is the permission model throughout: the queryset only ever
    contains circles you're in, so reaching for one you're not a member of is
    a 404, the same "you can't even see it exists" pattern used for goals.
    """

    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        return (
            Circle.objects.filter(memberships__user=self.request.user)
            .distinct()
            .prefetch_related("memberships__user")
        )

    def get_serializer_class(self):
        return CircleListSerializer if self.action == "list" else CircleDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = CreateCircleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            circle = Circle.objects.create(
                name=serializer.validated_data["name"], created_by=request.user
            )
            CircleMembership.objects.create(circle=circle, user=request.user)

        return Response(
            CircleDetailSerializer(circle, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        circle = self.get_object()  # 404 if not a member at all
        if circle.created_by_id != request.user.id:
            return Response(
                {"detail": "Only the person who created this circle can delete it."},
                status=status.HTTP_403_FORBIDDEN,
            )
        circle.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"], url_path="join")
    def join(self, request):
        serializer = JoinCircleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        circle = get_object_or_404(Circle, invite_token=serializer.validated_data["token"])
        # Idempotent: joining a circle you're already in just confirms it.
        CircleMembership.objects.get_or_create(circle=circle, user=request.user)

        return Response(CircleDetailSerializer(circle, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="leave")
    def leave(self, request, pk=None):
        circle = self.get_object()
        CircleMembership.objects.filter(circle=circle, user=request.user).delete()

        # An empty circle serves nobody — clean it up rather than leaving a
        # ghost row an invite link still points at. Queried directly rather
        # than via circle.memberships: get_queryset() prefetches that
        # relation, and a prefetched manager answers .exists() from its
        # cached snapshot rather than hitting the database again.
        if not CircleMembership.objects.filter(circle_id=circle.id).exists():
            circle.delete()

        return Response({"left": True})

    @action(detail=True, methods=["post"], url_path="regenerate-invite")
    def regenerate_invite(self, request, pk=None):
        circle = self.get_object()
        if circle.created_by_id != request.user.id:
            return Response(
                {"detail": "Only the person who created this circle can reset the invite link."},
                status=status.HTTP_403_FORBIDDEN,
            )
        circle.invite_token = uuid.uuid4()
        circle.save(update_fields=["invite_token"])
        return Response(CircleDetailSerializer(circle, context={"request": request}).data)
