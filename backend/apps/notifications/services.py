"""Building and delivering the daily digest.

Two channels, both free and neither needing a third-party service:

- **Web push** — the browser's own push service (FCM on Android, APNs via
  Safari on iOS). Real notifications on a phone's lock screen, even with the
  site closed. Needs a VAPID key pair, no account anywhere.
- **Email** — Django's SMTP backend against whatever mailbox the user
  configures.

Sending is triggered by `manage.py notify_daily`, scheduled by the operating
system. No Celery, no Redis — there is exactly one job and it runs once a day.
"""

import datetime as dt
import json
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from apps.goals.models import Goal, Task

from .models import NotificationSetting, PushSubscription

logger = logging.getLogger(__name__)

MAX_LISTED = 6


# --- digest ---------------------------------------------------------------

def build_digest(user) -> dict:
    """Everything the daily message needs: what's due, what's late, what's
    coming, and how much is left overall."""
    today = timezone.localdate()
    week_end = today + dt.timedelta(days=7)

    pending = Task.objects.filter(
        milestone__goal__user=user, is_complete=False
    ).select_related("milestone__goal")

    due_today = list(pending.filter(due_date=today).order_by("order")[:MAX_LISTED])
    overdue = list(pending.filter(due_date__lt=today).order_by("due_date")[:MAX_LISTED])
    this_week = list(
        pending.filter(due_date__gt=today, due_date__lte=week_end).order_by("due_date")[
            :MAX_LISTED
        ]
    )

    today_count = pending.filter(due_date=today).count()
    overdue_count = pending.filter(due_date__lt=today).count()
    week_count = pending.filter(due_date__gt=today, due_date__lte=week_end).count()
    remaining_total = pending.count()

    # Completed today, so the message can acknowledge progress rather than
    # only ever listing what is outstanding.
    done_today = Task.objects.filter(
        milestone__goal__user=user,
        is_complete=True,
        completed_at__date=today,
    ).count()

    if today_count:
        title = f"{today_count} task{'s' if today_count != 1 else ''} due today"
    elif overdue_count:
        title = f"{overdue_count} overdue task{'s' if overdue_count != 1 else ''}"
    elif week_count:
        title = f"{week_count} due this week"
    else:
        title = "Nothing due today"

    lines = [t.title for t in due_today] or [t.title for t in overdue] or [
        t.title for t in this_week
    ]
    if lines:
        body = " · ".join(lines[:3])
        if remaining_total:
            body += f" ({remaining_total} left in total)"
    else:
        body = "You're clear. Enjoy the breathing room."

    def as_rows(tasks, late=False):
        return [
            {
                "title": t.title,
                "goal": t.milestone.goal.title,
                "due": t.due_date.isoformat() if t.due_date else "",
                **({"days": (today - t.due_date).days} if late else {}),
            }
            for t in tasks
        ]

    goals = []
    for goal in Goal.objects.filter(user=user):
        total, done = goal.task_counts()
        if not total:
            continue
        goals.append(
            {
                "title": goal.title,
                "progress": goal.progress,
                "done": done,
                "total": total,
                "left": total - done,
            }
        )

    return {
        "has_content": bool(today_count or overdue_count),
        "title": title,
        "body": body,
        "today": as_rows(due_today),
        "overdue": as_rows(overdue, late=True),
        "this_week": as_rows(this_week),
        "counts": {
            "today": today_count,
            "overdue": overdue_count,
            "this_week": week_count,
            "remaining": remaining_total,
            "done_today": done_today,
        },
        "goals": goals[:6],
        "date": today.isoformat(),
    }


# --- web push -------------------------------------------------------------

def push_configured() -> bool:
    return bool(settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY)


def send_push(user, digest: dict) -> int:
    """Push to every device this user has registered. Returns how many got it.

    A subscription the push service rejects as gone (404/410) is deleted —
    otherwise dead endpoints accumulate forever.
    """
    if not push_configured():
        logger.info("VAPID keys not configured; skipping push")
        return 0

    from pywebpush import WebPushException, webpush

    payload = json.dumps(
        {
            "title": digest["title"],
            "body": digest["body"],
            "url": "/dashboard",
            "tag": f"daily-{digest['date']}",
        }
    )

    delivered = 0
    for subscription in PushSubscription.objects.filter(user=user):
        try:
            webpush(
                subscription_info=subscription.as_subscription_info(),
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{settings.VAPID_CONTACT_EMAIL}"},
                timeout=15,
            )
            subscription.last_used_at = timezone.now()
            subscription.save(update_fields=["last_used_at"])
            delivered += 1
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None)
            if status in (404, 410):
                logger.info("Pruning expired push subscription %s", subscription.id)
                subscription.delete()
            else:
                logger.warning("Push failed (%s): %s", status, exc)
    return delivered


# --- email ----------------------------------------------------------------

def _email_bodies(user, digest: dict) -> tuple[str, str]:
    name = user.first_name or user.username
    app_url = settings.APP_BASE_URL.rstrip("/")
    counts = digest["counts"]

    # --- plain text ---
    text = [f"Good morning {name},", "", digest["title"], ""]

    if counts["done_today"]:
        text += [f"Already done today: {counts['done_today']}", ""]

    if digest["overdue"]:
        text.append(f"OVERDUE ({counts['overdue']})")
        text += [
            f"  [ ] {t['title']}  ({t['goal']}, {t['days']} day(s) late)"
            for t in digest["overdue"]
        ]
        text.append("")
    if digest["today"]:
        text.append(f"DUE TODAY ({counts['today']})")
        text += [f"  [ ] {t['title']}  ({t['goal']})" for t in digest["today"]]
        text.append("")
    if digest["this_week"]:
        text.append(f"COMING THIS WEEK ({counts['this_week']})")
        text += [
            f"  [ ] {t['title']}  ({t['goal']}, due {t['due']})"
            for t in digest["this_week"]
        ]
        text.append("")

    if digest["goals"]:
        text.append("TASKS LEFT PER GOAL")
        text += [
            f"  {g['title']}: {g['left']} left of {g['total']} ({g['progress']}% done)"
            for g in digest["goals"]
        ]
        text.append("")

    text += [
        f"{counts['remaining']} task(s) remaining in total.",
        "",
        f"Open your dashboard: {app_url}/dashboard",
        "",
        "You can change the address or turn these off in Settings.",
    ]

    # --- html ---
    def rows(items, late=False, show_due=False):
        out = []
        for t in items:
            meta = t["goal"]
            if late:
                meta += f" · {t['days']} day{'s' if t['days'] != 1 else ''} late"
            elif show_due and t["due"]:
                meta += f" · due {t['due']}"
            out.append(
                '<tr><td style="padding:8px 0;border-bottom:1px solid #eeeeee">'
                '<div style="font-size:14px;color:#18181b">'
                '<span style="color:#c7c7cc">&#9744;</span>&nbsp;'
                f'{t["title"]}</div>'
                f'<div style="font-size:12px;color:#8b8b94;padding-left:20px">{meta}</div>'
                "</td></tr>"
            )
        return "".join(out)

    def section(label, items, colour, late=False, show_due=False):
        if not items:
            return ""
        return (
            f'<p style="font-size:12px;font-weight:700;letter-spacing:.06em;'
            f'text-transform:uppercase;color:{colour};margin:22px 0 4px">{label}</p>'
            '<table style="width:100%;border-collapse:collapse">'
            + rows(items, late, show_due)
            + "</table>"
        )

    goal_rows = "".join(
        '<tr>'
        f'<td style="padding:7px 0;font-size:13px;color:#18181b">{g["title"]}</td>'
        f'<td style="padding:7px 0;font-size:13px;color:#8b8b94;text-align:right;white-space:nowrap">'
        f'<strong style="color:#1d5c99">{g["left"]}</strong> left of {g["total"]}</td>'
        "</tr>"
        for g in digest["goals"]
    )

    html = f"""\
<div style="font-family:system-ui,-apple-system,'Segoe UI',sans-serif;max-width:580px;margin:0 auto;padding:26px;color:#18181b">
  <p style="font-size:12.5px;color:#8b8b94;margin:0 0 4px">Smart Companion</p>
  <h1 style="font-size:21px;margin:0 0 6px">{digest['title']}</h1>
  <p style="font-size:13px;color:#52525b;margin:0">
    Good morning {name}. {counts['remaining']} task{'s' if counts['remaining'] != 1 else ''} left in total
    {f", {counts['done_today']} already done today" if counts['done_today'] else ""}.
  </p>

  {section('Overdue', digest['overdue'], '#ef4444', late=True)}
  {section('Due today', digest['today'], '#18181b')}
  {section('Coming this week', digest['this_week'], '#8b8b94', show_due=True)}

  {'<p style="font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:#8b8b94;margin:24px 0 4px">Tasks left per goal</p><table style="width:100%;border-collapse:collapse">' + goal_rows + '</table>' if goal_rows else ''}

  <p style="margin:28px 0 0">
    <a href="{app_url}/dashboard"
       style="background:#1d5c99;color:#ffffff;text-decoration:none;padding:11px 20px;border-radius:8px;font-size:14px;display:inline-block">
      Open dashboard
    </a>
  </p>
  <p style="font-size:11.5px;color:#8b8b94;margin-top:26px;border-top:1px solid #eeeeee;padding-top:14px">
    Sent because the daily email is on in Settings, where you can also change
    the address or switch it off.
  </p>
</div>"""
    return "\n".join(text), html


def send_email(user, digest: dict) -> bool:
    """Send to the configured address, falling back to the account's own."""
    from .models import NotificationSetting

    setting, _ = NotificationSetting.objects.get_or_create(user=user)
    recipient = setting.resolved_email
    if not recipient:
        logger.info("No email address for %s; skipping", user)
        return False

    text, html = _email_bodies(user, digest)
    message = EmailMultiAlternatives(
        subject=f"{digest['title']} - Smart Companion",
        body=text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    message.attach_alternative(html, "text/html")
    try:
        message.send(fail_silently=False)
        return True
    except Exception:
        logger.exception("Could not send digest email to %s", recipient)
        return False


# --- orchestration --------------------------------------------------------

def deliver_daily(user, *, force: bool = False) -> dict:
    """Send whichever channels this user has switched on."""
    setting, _ = NotificationSetting.objects.get_or_create(user=user)
    today = timezone.localdate()

    if not force:
        if not setting.any_enabled:
            return {"skipped": "not enabled"}
        if setting.last_sent_on == today:
            return {"skipped": "already sent today"}
        if timezone.localtime().hour < setting.send_hour:
            return {"skipped": "too early"}

    digest = build_digest(user)
    result = {
        "pushed": 0,
        "emailed": False,
        "emailed_to": setting.resolved_email,
        "title": digest["title"],
    }

    if force or setting.push_daily:
        result["pushed"] = send_push(user, digest)
    if force or setting.email_daily:
        result["emailed"] = send_email(user, digest)

    if not force:
        setting.last_sent_on = today
        setting.save(update_fields=["last_sent_on"])
    return result
