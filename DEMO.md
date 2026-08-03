# Demo script — Smart Companion

A 5–6 minute walkthrough. The order matters: it builds the story from *problem*
to *plan* to *proof*.

## Before you start

- [ ] `backend/.env` has a real `GEMINI_API_KEY` and `YOUTUBE_API_KEY`, and
      `USE_MOCK_AI=false`. **Check this** — the mock stub produces generic
      milestone titles that will undercut the whole demo.
- [ ] Run `python backend/manage.py verify_ai` — one command that confirms the
      keys work, the generated dates are sane, and the video links resolve. Do
      this the morning of, not the night before: it catches an expired key or
      an exhausted quota while you still have time to react.
- [ ] Backend running: `python backend/manage.py runserver 127.0.0.1:8010`
- [ ] Frontend running: `npm run dev` in `frontend/`
- [ ] Register a demo account beforehand and create **one** finished-looking
      goal with a few tasks ticked off, so the dashboard isn't empty when you
      open it. Generate your headline goal live.
- [ ] Browser zoom at 100%, window maximised.

---

## 1. The problem (20 seconds)

> "Every student has said 'I'm going to crack GATE' or 'I'm going to learn
> React'. The goal isn't the hard part — turning it into a dated plan is, and
> then knowing where to actually learn each piece. That's what this does."

Don't linger. Get to the product.

## 2. Dashboard (30 seconds)

Open `/dashboard`.

Point at, in order: today's tasks, overdue count, the next-7-days column, the
goal progress cards.

> "One screen: what's due now, what's coming, and how every goal is tracking."

## 3. The hero feature — generate a roadmap (2 minutes)

Click **New goal**. Type a goal *live* — don't use a saved one:

> `Crack GATE in 8 months while finishing my final year`

Set a target date. Click **Generate roadmap**.

While it's loading (a few seconds), narrate:

> "This is going to Gemini with a low-temperature, JSON-only prompt. The
> response gets validated against a fixed schema on the server before anything
> is saved — if the model returns something malformed we retry once, and if it
> still fails the user gets a clear error and can build the roadmap by hand
> instead of staring at a spinner."

When the preview lands, **edit something in front of them** — rename a
milestone, change a date, delete a task, reorder two milestones with the arrows.

> "It's a starting point, not a black box. Nothing has been saved yet — this
> whole preview is local state. If I walk away now, there's no orphan goal in
> the database."

Click **Save goal**.

## 4. Learning resources (1 minute)

On the goal detail page, pick a milestone and click **Find resources**.

> "Here's the design decision I'm most pleased with. I do *not* ask the model
> for URLs — language models confidently invent links that 404, and a broken
> link in a live demo is worse than no link at all. Instead the model gives each
> milestone a short search topic, and that drives a real YouTube Data API
> search. The Google search link next to it is constructed from the same topic
> — costs no API quota, and it can never break."

Click a video to show it's a real, working link.

> "It's lazy — one milestone at a time, not the whole roadmap. A search call
> costs 100 of the 10,000 daily quota units, so this stays inside the free tier."

## 5. Progress and tasks (1 minute)

Tick off two or three tasks. Point at the progress bar moving.

> "Progress is computed from completed versus total tasks — it's never stored,
> so it can't drift out of sync."

Click a task's **sparkle** icon → **Break this down**.

> "Same AI plumbing as the roadmap, smaller schema — one task in, two to four
> concrete steps out."

Go to `/tasks`. Filter by goal, then by *Overdue*.

> "Every task across every goal, in one list."

## 5b. The one they'll remember — adaptive re-plan (1 minute)

Still on the goal page, click **Re-plan**.

> "This is the part I think matters most. A plan you made two months ago is
> wrong by now — that's not a flaw, that's just life. So instead of making you
> redo it, I send only the *unfinished* work back to the model with today's
> date and the real deadline, and it redistributes what's left."

When the summary comes back, read it aloud — it's written for the user, not
about the data. Point at the milestone dates that moved.

> "Completed tasks don't move. Titles don't change. Resources stay. Only dates.
> And every id the model sends back is checked against the ids I sent it — a
> hallucinated id can't reach the database — with dates clamped to today and to
> their milestone regardless of what comes back."

Then hit `⌘K` (or `Ctrl K`) and type a goal name.

> "And the whole thing is navigable from the keyboard."

## 5c. Focus and streaks (45 seconds)

Open **Focus** from the sidebar. Start a 25-minute session against a task, then
stop it after a few seconds.

> "Stopping early still banks the time — I didn't want a tool that punishes you
> for being honest about a bad session. Anything under a minute is treated as a
> mis-click and ignored."

Point at the streak and the activity heatmap.

> "A day counts if you finish a task or log a session. Missing today doesn't
> break the streak — the day isn't over."

## 6. Analytics (30 seconds)

Open `/analytics`.

> "Overall completion, what the next fortnight looks like, and progress ranked
> by goal."

## 7. Close (20 seconds)

> "Django REST Framework with JWT on the back, React and Tailwind on the front.
> The whole AI layer sits behind a single function — switching from Gemini to
> Groq is one environment variable, because I didn't want the project welded to
> one provider."

---

## If something goes wrong

| Problem | What to do |
|---|---|
| Generation is slow or errors | Say *"this is a live API call"*, click **Regenerate**. If it fails twice, use **Build it manually** — it's a real feature, not a save |
| No videos appear | The Google search link still renders with a note. Point at it: *"designed to degrade — the plan never breaks because an API is down"* |
| Rate limited (429) | The error message says so explicitly. Fall back to a pre-made goal |
| Nothing loads at all | Check the backend is on **8010** and matches `VITE_API_BASE_URL` |

## Questions you'll probably get

**"How do you know the AI's dates are sensible?"**
The prompt constrains milestones to be chronological, tasks to fall on or before
their milestone's target date, and everything to sit between today and the
deadline. The server validates the structure; individual bad dates are dropped
rather than failing the whole roadmap. And the user can edit every date anyway.

**"What if the model returns invalid JSON?"**
Schema validation server-side, one retry with a stricter instruction, then a
clean error plus the manual path. It never hangs.

**"Why not store progress?"**
Derived values drift. Computing it from task counts means it's always right.

**"Why no background job queue?"**
Generation takes a few seconds and the user is actively waiting for it. Celery
and Redis would add two moving parts to deploy for no benefit at this scale.
The notification feed is derived on request rather than pushed, which is the
other place a queue would normally appear.

**"What stops the AI corrupting the plan when it re-plans?"**
It never gets write access. It returns ids and dates; the server accepts an id
only if it was in the payload it sent, confirms the task belongs to that
milestone, and clamps every date to today and to the milestone's target. There
are tests for each of those three cases, including a deliberately hallucinated
id.

**"How is the streak calculated?"**
From completion timestamps and focus sessions, bucketed into local dates in
Python so SQLite and PostgreSQL agree across timezone boundaries. An idle today
doesn't break it; a genuinely missed day does.
