import datetime as dt

from django.db.models import Count, Q
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.goals.models import Goal, Task

TREND_DAYS = 14


class OverviewView(APIView):
    """Aggregates for the analytics charts. One request, chart-ready shapes."""

    def get(self, request):
        tasks = Task.objects.filter(milestone__goal__user=request.user)
        total = tasks.count()
        completed = tasks.filter(is_complete=True).count()

        per_goal = (
            Goal.objects.filter(user=request.user)
            .annotate(
                total_tasks=Count("milestones__tasks", distinct=True),
                completed_tasks=Count(
                    "milestones__tasks",
                    filter=Q(milestones__tasks__is_complete=True),
                    distinct=True,
                ),
            )
            .order_by("created_at")
        )

        goals_data = [
            {
                "id": goal.id,
                "title": goal.title,
                "total": goal.total_tasks,
                "completed": goal.completed_tasks,
                "progress": (
                    round(goal.completed_tasks * 100 / goal.total_tasks)
                    if goal.total_tasks
                    else 0
                ),
            }
            for goal in per_goal
        ]

        # Upcoming workload: how many tasks fall due on each of the next 14 days.
        today = dt.date.today()
        window = tasks.filter(
            is_complete=False,
            due_date__gte=today,
            due_date__lte=today + dt.timedelta(days=TREND_DAYS - 1),
        ).values("due_date").annotate(count=Count("id"))
        counts = {row["due_date"]: row["count"] for row in window}

        workload = [
            {
                "date": (today + dt.timedelta(days=offset)).isoformat(),
                "label": (today + dt.timedelta(days=offset)).strftime("%d %b"),
                "count": counts.get(today + dt.timedelta(days=offset), 0),
            }
            for offset in range(TREND_DAYS)
        ]

        return Response(
            {
                "overall": {
                    "total": total,
                    "completed": completed,
                    "pending": total - completed,
                    "progress": round(completed * 100 / total) if total else 0,
                },
                "per_goal": goals_data,
                "workload": workload,
            }
        )
