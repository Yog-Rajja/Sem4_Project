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

        today = dt.date.today()

        # --- Upcoming workload (next 14 days) ---
        window = (
            tasks.filter(
                is_complete=False,
                due_date__gte=today,
                due_date__lte=today + dt.timedelta(days=TREND_DAYS - 1),
            )
            .values("due_date")
            .annotate(count=Count("id"))
        )
        counts = {row["due_date"]: row["count"] for row in window}

        workload = [
            {
                "date": (today + dt.timedelta(days=offset)).isoformat(),
                "label": (today + dt.timedelta(days=offset)).strftime("%d %b"),
                "count": counts.get(today + dt.timedelta(days=offset), 0),
            }
            for offset in range(TREND_DAYS)
        ]

        # --- Status breakdown (for Pie chart) ---
        in_progress = tasks.filter(is_complete=False, due_date__isnull=False, due_date__gte=today).count()
        not_started = total - completed - in_progress

        status_breakdown = [
            {"name": "Completed", "value": completed},
            {"name": "In Progress", "value": max(in_progress, 0)},
            {"name": "Not Started", "value": max(not_started, 0)},
        ]

        # --- Daily completions (past 14 days area chart) ---
        start_date = today - dt.timedelta(days=TREND_DAYS - 1)
        daily_qs = (
            tasks.filter(
                is_complete=True,
                completed_at__date__gte=start_date,
                completed_at__date__lte=today,
            )
            .values("completed_at__date")
            .annotate(count=Count("id"))
        )
        daily_map = {row["completed_at__date"]: row["count"] for row in daily_qs}

        daily_completions = [
            {
                "date": (start_date + dt.timedelta(days=i)).isoformat(),
                "label": (start_date + dt.timedelta(days=i)).strftime("%d %b"),
                "count": daily_map.get(start_date + dt.timedelta(days=i), 0),
            }
            for i in range(TREND_DAYS)
        ]

        # --- Streaks ---
        completion_dates = set(
            tasks.filter(is_complete=True, completed_at__isnull=False)
            .values_list("completed_at__date", flat=True)
            .distinct()
        )

        current_streak = 0
        check = today
        while check in completion_dates:
            current_streak += 1
            check -= dt.timedelta(days=1)

        best_streak = 0
        if completion_dates:
            sorted_dates = sorted(completion_dates)
            run = 1
            for i in range(1, len(sorted_dates)):
                if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
                    run += 1
                else:
                    best_streak = max(best_streak, run)
                    run = 1
            best_streak = max(best_streak, run)

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
                "status_breakdown": status_breakdown,
                "daily_completions": daily_completions,
                "streaks": {
                    "current": current_streak,
                    "best": best_streak,
                },
            }
        )
