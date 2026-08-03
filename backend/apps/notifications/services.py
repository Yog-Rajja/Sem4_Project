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
    """What the user needs to know today. Returns None-ish when there's
    nothing worth interrupting them for."""
    today = timezone.localdate()
    week_end = today + dt.timedelta(days=7)

    pending = Task.objects.filter(
        milestone__goal__user=user, is_complete=False
    ).select_related("milestone__goal")

    due_today = list(pending.filter(due_date=today).order_by("order")[:MAX_LISTED])
    overdue = list(pending.filter(due_date__lt=today).order_by("due_date")[:MAX_LISTED])
    upcoming_count = pending.filter(due_date__gt=today, due_date__lte=week_end).count()

    overdue_count = pending.filter(due_date__lt=today).count()
    today_count = pending.filter(due_date=today).count()

    if today_count:
        title = f"{today_count} task{'s' if today_count != 1 else ''} due today"
    elif overdue_count:
        title = f"{overdue_count} overdue task{'s' if overdue_count != 1 else ''}"
    elif upcoming_count:
        title = f"{upcoming_count} due this week"
    else:
        title = "Nothing due today"

    lines = [t.title for t in due_today] or [t.title for t in overdue]
    body = " · ".join(lines[:3]) if lines else "You're clear. Enjoy the breathing room."

    return {
        "has_content": bool(today_count or overdue_count),
        "title": title,
        "body": body,
        "today": [
            {"title": t.title, "goal": t.milestone.goal.title} for t in due_today
        ],
        "overdue": [
            {"title": t.title, "goal": t.milestone.goal.title,
             "days": (today - t.due_date).days}
            for t in overdue
        ],
        "counts": {
            "today": today_count,
            "overdue": overdue_count,
            "this_week": upcoming_count,
        },
        "goals": [
            {"title": goal.title, "progress": goal.progress}
            for goal in Goal.objects.filter(user=user)[:5]
        ],
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

    text = [f"Good morning {name},", "", digest["title"], ""]
    if digest["overdue"]:
        text.append("Overdue:")
        text += [f"  - {t['title']}  ({t['goal']}, {t['days']}d late)"
                 for t in digest["overdue"]]
        text.append("")
    if digest["today"]:
        text.append("Due today:")
        text += [f"  - {t['title']}  ({t['goal']})" for t in digest["today"]]
        text.append("")
    if digest["goals"]:
        text.append("Where your goals stand:")
        text += [f"  - {g['title']}: {g['progress']}%" for g in digest["goals"]]
        text.append("")
    text += [f"Open your dashboard: {app_url}/dashboard", "",
             "You can turn these off in Settings."]

    def rows(items, late=False):
        return "".join(
            f'<tr><td style="padding:6px 0;border-bottom:1px solid #eee">'
            f'<div style="font-size:14px;color:#18181b">{t["title"]}</div>'
            f'<div style="font-size:12px;color:#8b8b94">{t["goal"]}'
            + (f' · {t["days"]} days late' if late else "")
            + "</div></td></tr>"
            for t in items
        )

    html = f"""\
<div style="font-family:system-ui,-apple-system,'Segoe UI',sans-serif;max-width:560px;margin:0 auto;padding:24px">
  <p style="font-size:13px;color:#8b8b94;margin:0 0 4px">Smart Companion</p>
  <h1 style="font-size:20px;color:#18181b;margin:0 0 18px">{digest['title']}</h1>
  {'<p style="font-size:13px;font-weight:600;color:#ef4444;margin:18px 0 6px">Overdue</p><table style="width:100%;border-collapse:collapse">' + rows(digest['overdue'], True) + '</table>' if digest['overdue'] else ''}
  {'<p style="font-size:13px;font-weight:600;color:#18181b;margin:18px 0 6px">Due today</p><table style="width:100%;border-collapse:collapse">' + rows(digest['today']) + '</table>' if digest['today'] else ''}
  <p style="margin:26px 0 0">
    <a href="{app_url}/dashboard"
       style="background:#4f46e5;color:#fff;text-decoration:none;padding:10px 18px;border-radius:8px;font-size:14px;display:inline-block">
      Open dashboard
    </a>
  </p>
  <p style="font-size:11.5px;color:#8b8b94;margin-top:26px">
    You are receiving this because daily email is on in Settings.
  </p>
</div>"""
    return "\n".join(text), html


def send_email(user, digest: dict) -> bool:
    if not user.email:
        return False
    if not settings.EMAIL_HOST_USER and settings.EMAIL_BACKEND.endswith("smtp.EmailBackend"):
        logger.info("SMTP not configured; skipping email")
        return False

    text, html = _email_bodies(user, digest)
    message = EmailMultiAlternatives(
        subject=f"{digest['title']} — Smart Companion",
        body=text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    message.attach_alternative(html, "text/html")
    try:
        message.send(fail_silently=False)
        return True
    except Exception:
        logger.exception("Could not send digest email to %s", user.email)
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
    result = {"pushed": 0, "emailed": False, "title": digest["title"]}

    if force or setting.push_daily:
        result["pushed"] = send_push(user, digest)
    if force or setting.email_daily:
        result["emailed"] = send_email(user, digest)

    if not force:
        setting.last_sent_on = today
        setting.save(update_fields=["last_sent_on"])
    return result
