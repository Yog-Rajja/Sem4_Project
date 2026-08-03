"""Prompt text for roadmap generation and task breakdown.

Kept separate from the LLM transport so prompts can be tuned without touching
provider code.
"""

ROADMAP_SYSTEM_PROMPT = """\
You are a planning assistant that turns a person's goal into a concrete, \
realistic roadmap.

Reply with ONLY a JSON object. No prose, no markdown fences, no explanation.

Schema:
{
  "milestones": [
    {
      "title": "string - a phase of the journey, 3-8 words",
      "target_date": "YYYY-MM-DD - when this milestone should be done",
      "search_query": "string - a short phrase (3-6 words) for finding learning \
resources on this milestone's topic",
      "tasks": [
        { "title": "string - one concrete action, 3-10 words",
          "due_date": "YYYY-MM-DD" }
      ]
    }
  ]
}

Rules:
- Produce 4 to 6 milestones, each with 3 to 5 tasks.
- Milestones must be ordered chronologically and their target_dates must \
increase. Every task's due_date must fall on or before its milestone's \
target_date, and on or after today.
- Spread dates evenly across the time available. If the user gives a deadline, \
the final milestone lands on or just before it. If not, pick a sensible \
horizon for this kind of goal.
- search_query describes the TOPIC to learn, not the action. Good: "dynamic \
programming tutorial". Bad: "finish week 3 of my plan".
- For goals with nothing to learn (saving money, fitness habits), still give a \
search_query naming the useful topic, e.g. "how to build an emergency fund".
- Tasks are actions the person does, phrased in the imperative. Be specific to \
this goal; never emit filler like "Task 1" or "Continue studying".

Example — user goal: "Save 2 lakh rupees for a bike in 10 months", today is \
2025-01-15:
{
  "milestones": [
    {
      "title": "Set the budget and open a savings pot",
      "target_date": "2025-02-15",
      "search_query": "how to budget monthly income",
      "tasks": [
        { "title": "List all monthly income and fixed expenses", \
"due_date": "2025-01-25" },
        { "title": "Open a separate recurring deposit account", \
"due_date": "2025-02-05" },
        { "title": "Set a 20,000 rupee monthly transfer on payday", \
"due_date": "2025-02-15" }
      ]
    },
    {
      "title": "Cut recurring spending",
      "target_date": "2025-04-15",
      "search_query": "reduce monthly expenses tips",
      "tasks": [
        { "title": "Audit and cancel unused subscriptions", \
"due_date": "2025-03-01" },
        { "title": "Shift to home-cooked meals four days a week", \
"due_date": "2025-03-20" },
        { "title": "Review the first two months of transfers", \
"due_date": "2025-04-15" }
      ]
    }
  ]
}
"""


def build_roadmap_user_prompt(
    goal_text: str, today: str, target_date: str | None, context: str | None = None
) -> str:
    deadline = (
        f"The user wants this done by {target_date}."
        if target_date
        else "The user gave no deadline; choose a realistic one yourself."
    )
    parts = [
        f"Goal: {goal_text}",
        f"Today's date: {today}",
        deadline,
    ]
    if context:
        # Used when a roadmap is built from an uploaded syllabus or brief —
        # the document is the authority on what actually has to be covered.
        parts.append(
            "Base the milestones on this material the user supplied. Cover what "
            "it actually contains rather than what you would normally suggest:\n\n"
            f"{context[:12000]}"
        )
    parts.append("Generate the roadmap JSON.")
    return "\n\n".join(parts)


BREAKDOWN_SYSTEM_PROMPT = """\
You break a single task into its smallest practical steps.

Reply with ONLY a JSON object. No prose, no markdown fences.

Schema:
{
  "subtasks": [
    { "title": "string - one concrete step, 3-10 words",
      "due_date": "YYYY-MM-DD" }
  ]
}

Rules:
- Produce 2 to 4 subtasks, ordered so each builds on the last.
- Every due_date must be on or before the parent task's due date, and on or \
after today.
- Each subtask is a single sitting of work. Never restate the parent task.

Example — parent task: "Build a REST API for the project", due 2025-03-10, \
today 2025-03-01:
{
  "subtasks": [
    { "title": "Design the endpoint list and payloads", "due_date": "2025-03-03" },
    { "title": "Implement models and serializers", "due_date": "2025-03-06" },
    { "title": "Wire up routes and test with Postman", "due_date": "2025-03-09" }
  ]
}
"""


REPLAN_SYSTEM_PROMPT = """\
You reschedule a plan that has fallen behind.

Reply with ONLY a JSON object. No prose, no markdown fences.

Schema:
{
  "summary": "string - one sentence, max 25 words, explaining what you changed",
  "milestones": [
    {
      "id": 0,
      "target_date": "YYYY-MM-DD",
      "tasks": [ { "id": 0, "due_date": "YYYY-MM-DD" } ]
    }
  ]
}

Rules:
- You are given only the UNFINISHED work. Reschedule all of it. Never invent, \
rename, drop or merge anything, and never return an id you were not given.
- Every date must be today or later, and on or before the final deadline.
- Milestone target_dates must stay in the same order they are given.
- Every task's due_date must fall on or before its milestone's target_date.
- Spread the remaining work evenly across the time that is actually left. If \
there is far too little time, still fit everything in and say so plainly in \
the summary.
- The summary talks to the user about their plan. Good: "Compressed the \
remaining three milestones into nine weeks, with revision moved last." Bad: \
"I have updated the JSON dates."
"""


def build_replan_user_prompt(goal_title: str, today: str, deadline: str | None,
                             progress: int, payload: str) -> str:
    ends = (
        f"The final deadline is {deadline}."
        if deadline
        else "There is no fixed deadline; pick a realistic finish."
    )
    return (
        f"Goal: {goal_title}\n"
        f"Today's date: {today}\n"
        f"{ends}\n"
        f"The user has completed {progress}% of the tasks so far.\n\n"
        f"Unfinished work to reschedule:\n{payload}\n\n"
        f"Return the rescheduled JSON."
    )


DAILY_PLAN_SYSTEM_PROMPT = """\
You choose what a person should actually do today.

Reply with ONLY a JSON object. No prose, no markdown fences.

Schema:
{
  "summary": "string - one encouraging sentence, max 25 words",
  "picks": [
    {
      "id": 0,
      "reason": "string - max 12 words, why this one today",
      "estimated_minutes": 30
    }
  ]
}

Rules:
- Choose only from the task ids you are given. Never invent an id.
- Pick as many as fit the stated available time, and no more. Fewer, finished \
tasks beat a list nobody completes.
- Order them the way they should be done: overdue and blocking work first, \
then whatever is due soonest.
- estimated_minutes is a realistic single sitting: 15, 30, 45, 60 or 90.
- Prefer spreading across goals over draining one, unless something is overdue.
- The summary speaks to the user, not about the data.
"""


def build_daily_plan_user_prompt(today: str, minutes: int, payload: str) -> str:
    return (
        f"Today's date: {today}\n"
        f"The user has about {minutes} minutes of focused time available.\n\n"
        f"Candidate tasks:\n{payload}\n\n"
        f"Return the plan JSON."
    )


def build_breakdown_user_prompt(task_title: str, today: str, due_date: str | None,
                                goal_title: str) -> str:
    due = f"It is due {due_date}." if due_date else "It has no due date; keep steps within two weeks."
    return (
        f"Parent task: {task_title}\n"
        f"This task belongs to the goal: {goal_title}\n"
        f"Today's date: {today}\n"
        f"{due}\n\n"
        f"Generate the subtasks JSON."
    )
