# Smart Companion

An AI-powered personal goal management dashboard. You describe a goal in plain
English — *"Crack GATE in 8 months"*, *"Learn React"* — and the app generates an
editable roadmap of milestones, tasks and target dates, then attaches **real
learning resources** to each milestone so the plan tells you not just what to do
but where to learn it.

Built as a final-year engineering project.

---

## What it does

| Screen | What's there |
|---|---|
| `/dashboard` | Streak + focus strip, today's tasks, overdue, next 7 days, goal progress, **Plan my day** |
| `/goals` | Every goal as a progress card |
| `/goals/new` | Natural language → AI roadmap → **editable preview** → save |
| `/goals/:id` | Full roadmap: milestones, nested tasks, learning resources, documents, **Re-plan** |
| `/tasks` | Cross-goal task list, filterable by goal / status / due date |
| `/focus` | Pomodoro timer bound to a task, session history, streak + activity heatmap |
| `/studio` | Describe a document → AI builds it → download as PDF or PNG |
| `/r/:token` | Public read-only roadmap (no account needed) |
| `/analytics` | Overall completion, upcoming workload, per-goal progress |
| `/calendar` | A week-list of tasks grouped by day |

Plus a **command palette** on `⌘K` / `Ctrl K` (or `/`) for search and navigation,
an **alerts centre** in the top bar, and **dark mode**.

### Adaptive re-planning

The feature the rest of the app is built around. When a goal falls behind,
**Re-plan** sends only the *unfinished* work to the model and asks it to
redistribute it across the time that's actually left. Completed tasks, titles,
edits and learning resources are untouched — only dates move.

Every id the model returns is checked against the ids that were sent, so a
hallucinated id can never reach the database, and dates are clamped to today
and to their parent milestone regardless of what comes back.

### Plan my day

Tell it how long you have; it picks an ordered subset of tasks from across
every goal that genuinely fits, with a one-line reason each. You can tick them
off or start a focus session on one without leaving the dialog.

### Momentum

A day counts when you complete a task or log a focus session of at least a
minute. Streaks tolerate an idle *today* — the day isn't over yet — but break
on a genuinely missed day. Activity days are bucketed in Python rather than
SQL so SQLite and PostgreSQL agree on timezone boundaries.

### AI Studio

Describe what you need and the studio works out *what it is* before building
it. Seven types today — résumé, diet plan, study timetable, cover letter,
project report, invitation card and generated image — behind **one engine**:
each type is a JSON shape, prompt guidance and a validator, so adding another
is a registry entry rather than a new feature.

**Invitation cards are typeset, not painted.** A wedding card is drawn with CSS
and inline SVG — ornate borders, a palette inferred from your words ("orange" →
marigold), optional mehendi/sangeet events — and exported as PNG. That is
deliberate: image models render lettering unreliably, and a wedding card with a
misspelt name is worthless. Here the names, dates and venue are real text,
always correct and crisp when printed. Any emblem or logo is something you add
afterwards.

**Image generation** is wired to Gemini's image models for genuinely pictorial
requests. Note that image output is **not included in the Gemini free tier** —
the models appear in the model list but return a quota error indefinitely, so
this path needs billing enabled. Until then it fails with an explanation rather
than silently, and the artifact row is rolled back instead of being left as an
empty shell.

Intent is classified by weighted keywords first, so "make me a resume" never
costs an API call; only genuinely ambiguous prompts fall through to the model.

**Export formats are chosen to match the document, not for convenience.** Text
documents render through `@react-pdf/renderer` as **vector PDFs with selectable
text** — which is what lets an applicant tracking system actually read a CV.
The common shortcut of rasterising HTML to an image would produce a résumé that
ATS software scores as blank. Visual documents (diet plans, timetables) export
as PNG via `html-to-image`, since those get shared in a chat rather than parsed.

The résumé follows an **Oxford-style academic CV**: centred name with
letter-spacing, a single contact line, section headings in spaced capitals over
a hairline rule, and a narrow left-hand date column against the content. Set in
Times-Roman, one of the PDF standard-14 faces, so nothing is embedded and no
font is fetched at runtime.

The account's own name and email are passed in as known facts — otherwise a
generated CV comes out addressed to "Your Name", because the prompt forbids
inventing personal details.

### Notifications

Two channels, neither needing a third-party service or a task queue.

**Web push** reaches a phone's lock screen with the site closed, via the
browser's own push service (FCM on Android, APNs through Safari on iOS). Set it
up once:

```bash
.venv\Scripts\python.exe backend/manage.py generate_vapid_keys
```

Paste the pair into `backend/.env`. VAPID is just a signature proving the push
came from your server — there is no account to create anywhere.

**Email** uses Django's SMTP backend. Leave `EMAIL_HOST_USER` blank and mail
prints to the server console instead of sending, so the whole flow is
developable with no mailbox. For Gmail you need an
[App Password](https://myaccount.google.com/apppasswords), not your normal one.

Both are **off by default** and switched on per user in **Settings**, which
also has a *Send a test* button — otherwise there's no way to know it works
except waiting until tomorrow.

Delivery is one management command, scheduled by the OS:

```bash
.venv\Scripts\python.exe backend/manage.py notify_daily
```

Windows Task Scheduler, daily at 08:00:

```bash
schtasks /create /tn "SmartCompanionDigest" /sc daily /st 08:00 /tr "D:\Sem4_Project\.venv\Scripts\python.exe D:\Sem4_Project\backend\manage.py notify_daily"
```

Running it hourly is fine — each user is sent to once per day, and only once
their chosen hour has passed. That guard is what makes a dumb scheduler safe,
and it's why there's no Celery here: one job, once a day.

### Document intelligence

Upload a PDF, photo or text file to a goal, then have it read.

Text-bearing PDFs are extracted locally with **pypdf** — free, exact, no API
call. Only scanned pages and photographs fall through to Gemini's multimodal
reading, which means **there is no OCR engine to install**. Where both are
available the local text wins, since a model's transcription can drift.

You get a document type, a summary, key points and suggested actions — and then
**"Turn into a roadmap"**, which feeds the extracted text to the roadmap
generator so the milestones follow what the document actually says. Upload a
syllabus, get a revision plan whose milestones are its units.

Analysis is explicit rather than automatic on upload, because reading costs one
of the day's requests.

### Sharing

Any roadmap can be published to a read-only page at `/r/<token>`. This is the
only unauthenticated endpoint in the project: the token is an unguessable
UUID, the serializer exposes the plan but no ids, email or raw input, and
turning sharing off 404s the link immediately.

### Weekly review

A Monday retrospective. The figures are computed server-side and handed to the
model as facts — the model only writes the prose — so a review can never claim
you finished more than you did. Cached per week so opening the dashboard
doesn't regenerate it. A quiet week is allowed to read as a quiet week.

### Alerts

Derived on request, never stored, so an alert can't go stale and no job queue
is needed: overdue tasks, late milestones, goals behind their expected pace
(elapsed time vs. actual progress), stale goals, and a streak about to lapse.

**Roadmap generation** sends the goal to a Gemini Flash model at low temperature
with a JSON-only prompt and one few-shot example, then validates the response
against a fixed schema server-side. A parse failure retries once; if it still
fails you get a clear error and a *"Build it manually"* path rather than a hang.

**Learning resources** are deliberately *not* generated by the LLM — models
invent plausible-looking dead links, and a broken link in a live demo is worse
than no link. Instead each milestone carries a `search_query`, which drives a
real YouTube Data API `search.list` call, plus a constructed Google search URL
that costs no quota and can never 404. Resources are fetched lazily, one
milestone at a time.

---

## Tech stack

**Backend** — Django 5.1, Django REST Framework, `djangorestframework-simplejwt`,
SQLite (PostgreSQL supported via one env var), `requests`

**Frontend** — React 19 (Vite), Tailwind CSS v4, React Router, Axios,
React Hook Form, Framer Motion, Recharts

**External** — Google Gemini (roadmap generation), YouTube Data API v3 (resources)

No Celery, no Redis, no SMTP. AI calls run synchronously inside the
request/response cycle with a loading state on the frontend.

---

## Setup

### 1. Backend

```bash
python -m venv .venv
```

```bash
.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

Copy `backend/.env.example` to `backend/.env` and fill in your keys:

```bash
copy backend\.env.example backend\.env
```

| Variable | Where to get it |
|---|---|
| `GEMINI_API_KEY` | <https://aistudio.google.com/apikey> — free tier |
| `GEMINI_MODEL` | Defaults to `gemini-3.6-flash` — see the note below |
| `YOUTUBE_API_KEY` | Google Cloud console → enable *YouTube Data API v3* → create an API key |
| `DJANGO_SECRET_KEY` | Any long random string |

Then migrate and run:

```bash
.venv\Scripts\python.exe backend/manage.py migrate
```

```bash
.venv\Scripts\python.exe backend/manage.py runserver 127.0.0.1:8010
```

> Port **8010**, not the usual 8000 — 8000 was already taken on the dev machine.
> If you change it, update `VITE_API_BASE_URL` in `frontend/.env` to match.

### 2. Frontend

```bash
cd frontend && npm install
```

```bash
copy .env.example .env
```

```bash
npm run dev
```

Open <http://localhost:5173>, register an account, and create your first goal.

### Free-tier limits — read this before demoing

The Gemini free tier allows **20 generate requests per day, counted per
model**. That is the single most important operational fact about this
project. A demo that generates a roadmap, re-plans it, plans a day, reads a
document and builds two studio documents has already spent six.

Two things follow:

- **The allowance is per model.** If you exhaust one, change `GEMINI_MODEL` in
  `backend/.env` to another Flash model and you get a fresh 20. Verified
  working: `gemini-3.5-flash`, `gemini-3.6-flash`, `gemini-flash-latest`,
  `gemini-3.5-flash-lite`, `gemini-flash-lite-latest`, `gemini-3.1-flash-lite`.
- **Don't burn the allowance the morning of a demo.** `verify_ai` uses two
  requests by default (four with `--all`).

Separately: a newly created key gets **no** free-tier allocation for the
`gemini-2.0-*` family — the API returns `429` with `limit: 0`, which looks
like a rate limit but never resolves by waiting — and `gemini-2.5-flash`
returns `404` ("no longer available to new users").

### Checking your keys actually work

The test suite mocks Gemini and YouTube, so it proves the plumbing is right but
says nothing about what the live model returns. Once your keys are in, run:

```bash
.venv\Scripts\python.exe backend/manage.py verify_ai
```

It generates real roadmaps for four different kinds of goal (exam prep, an
open-ended career goal, a concrete skill, and a savings goal with nothing to
"learn") and checks the output: milestone dates increase, nothing lands after
your deadline or before today, every task falls within its milestone, search
topics name subjects rather than actions, and no filler task titles. It then
runs a real YouTube lookup and confirms each returned link resolves.

Costs one Gemini request per goal and 100 YouTube quota units of the daily
10,000. Worth running once after setup and again before you demo.

### Working without API keys

Set `USE_MOCK_AI=true` in `backend/.env` and roadmap generation returns a
deterministic local stub instead of calling Gemini — useful offline. Resource
lookup degrades on its own: with no `YOUTUBE_API_KEY` you still get the Google
search link, plus a note explaining that videos are unavailable.

---

## Tests

```bash
.venv\Scripts\python.exe backend/manage.py test
```

242 tests covering auth and JWT issuing, roadmap schema validation, LLM JSON
parsing and retry behaviour, resource discovery and its fallbacks, every API
endpoint and filter, progress calculation, streak and heatmap logic, alert
derivation, re-planning (including hallucinated-id rejection and date
clamping), daily planning, studio intent classification and schema coercion,
document preparation across file types, weekly-review aggregation, share-link
privacy, and per-user data isolation on every resource.

The suite needs no running server, no API keys and no network — the Gemini and
YouTube calls are mocked at the transport boundary, and uploads go to a
throwaway media root. It runs against a temporary database, so your development
data is untouched.

---

## API

All endpoints require `Authorization: Bearer <access>` except register/login.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/auth/register/` | Create account, returns token pair |
| `POST` | `/api/auth/login/` | Obtain token pair |
| `POST` | `/api/auth/refresh/` | Refresh an access token |
| `GET` | `/api/auth/me/` | Current user |
| `POST` | `/api/goals/generate/` | Goal text → roadmap **preview** (not persisted) |
| `GET/POST` | `/api/goals/` | List goals · create a goal with a nested roadmap |
| `GET/PATCH/DELETE` | `/api/goals/{id}/` | Goal detail with nested milestones |
| `POST` | `/api/milestones/{id}/resources/` | Fetch YouTube + search links for a milestone |
| `POST` | `/api/milestones/reorder/` | Bulk reorder |
| `GET` | `/api/tasks/` | Cross-goal tasks — `?goal=&status=&due=` |
| `POST` | `/api/tasks/{id}/breakdown/` | Split a task into 2–4 subtasks |
| `POST` | `/api/goals/{id}/replan/` | Reschedule the unfinished part of a roadmap |
| `POST` | `/api/plan-my-day/` | Pick today's workload for a time budget |
| `GET` | `/api/dashboard/` | Everything the dashboard needs, in one call |
| `GET` | `/api/analytics/overview/` | Chart-ready aggregates |
| `GET/POST` | `/api/focus-sessions/` | Start and list focus sessions |
| `POST` | `/api/focus-sessions/{id}/finish/` | Close a session with time actually spent |
| `GET` | `/api/momentum/` | Streaks, focus totals and the activity heatmap |
| `GET` | `/api/alerts/` | Derived notification feed |
| `GET/POST` | `/api/weekly-review/` | Cached retrospective · regenerate |
| `GET/POST/DELETE` | `/api/documents/` | Document vault |
| `POST` | `/api/documents/{id}/analyse/` | Read a document and extract meaning |
| `POST` | `/api/documents/{id}/to-goal/` | Turn a document into a roadmap preview |
| `GET` | `/api/artifacts/kinds/` | What the studio can build |
| `POST` | `/api/artifacts/generate/` | Prompt → generated document |
| `POST` | `/api/artifacts/{id}/regenerate/` | Rebuild, optionally with an instruction |
| `POST` | `/api/goals/{id}/share/` | Turn public sharing on or off |
| `GET` | `/api/public/roadmap/{token}/` | **Unauthenticated** read-only roadmap |

`generate/` returns a preview *without* writing to the database — the frontend
lets you edit it and POSTs the result to `/api/goals/`, so an abandoned
generation never leaves an orphan goal behind.

---

## Project structure

```
backend/
  config/            settings, urls, wsgi
  apps/
    accounts/        register / login / JWT
    goals/           Goal, Milestone, Task, Resource + AI generation
      services/      llm.py · roadmap.py · resources.py · prompts.py
    analytics/       chart aggregates
    vault/           document upload
  common/            pagination, permissions, error handling

frontend/src/
  pages/             one file per screen
  components/
    layout/          Sidebar, Topbar, PageShell, AppLayout
    goals/           RoadmapEditor, MilestoneCard, TaskItem, ResourceList
    dashboard/       TodayList, DeadlineList, GoalProgressCard
    charts/          Recharts wrappers
    ui/              buttons, inputs, modals, toasts
  lib/               api.js (axios + JWT interceptor), auth.js, format.js
```

### Swapping the LLM provider

Every model call goes through `complete_json()` in
`backend/apps/goals/services/llm.py`. Switching from Gemini to Groq is one env
var (`LLM_PROVIDER=groq`); adding a new provider is one function plus one entry
in the `_PROVIDERS` map. Nothing else in the codebase touches a provider SDK.

---

## Notes on cost

The YouTube Data API gives 10,000 quota units/day and a `search.list` call costs
100 — about 100 milestone lookups per day, comfortably enough for development
and a demo. That is why resources are fetched per milestone on demand rather
than eagerly for a whole roadmap. Gemini Flash's free tier covers roadmap
generation.
