from django.contrib import admin

from .models import Goal, Milestone, Resource, Task


class MilestoneInline(admin.TabularInline):
    model = Milestone
    extra = 0


class TaskInline(admin.TabularInline):
    model = Task
    extra = 0
    fk_name = "milestone"


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "target_date", "progress", "created_at")
    list_filter = ("user",)
    search_fields = ("title", "raw_input_text")
    inlines = [MilestoneInline]


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ("title", "goal", "order", "target_date", "is_complete")
    list_filter = ("is_complete",)
    inlines = [TaskInline]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "milestone", "due_date", "is_complete", "order")
    list_filter = ("is_complete",)
    search_fields = ("title",)


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "milestone", "source")
    list_filter = ("source",)
