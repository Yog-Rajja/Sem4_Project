"""Learning-resource discovery for a milestone.

Deliberately does NOT ask the LLM for URLs — models invent plausible-looking
dead links, and a broken link in a live demo is worse than no link. Instead the
milestone's `search_query` drives a real YouTube Data API search, plus a
constructed Google search URL that costs nothing and can never 404.
"""

import logging
from urllib.parse import quote_plus

import requests
from django.conf import settings
from django.utils import timezone

from ..models import Resource

logger = logging.getLogger(__name__)

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
MAX_VIDEOS = 3


def google_search_url(query: str) -> str:
    return f"https://www.google.com/search?q={quote_plus(query)}"


def _fetch_youtube(query: str) -> list[dict]:
    """Return up to MAX_VIDEOS video dicts. Never raises — an empty list just
    means the milestone shows its Google link only."""
    if not settings.YOUTUBE_API_KEY:
        logger.info("YOUTUBE_API_KEY not set — skipping video lookup")
        return []

    try:
        resp = requests.get(
            YOUTUBE_SEARCH_URL,
            params={
                "key": settings.YOUTUBE_API_KEY,
                "q": query,
                "part": "snippet",
                "type": "video",
                "maxResults": MAX_VIDEOS,
                "safeSearch": "moderate",
                "relevanceLanguage": "en",
                # search.list costs 100 quota units; 10,000/day is plenty here.
            },
            timeout=15,
        )
    except requests.RequestException:
        logger.exception("YouTube request failed for %r", query)
        return []

    if resp.status_code != 200:
        logger.warning("YouTube API %s: %s", resp.status_code, resp.text[:300])
        return []

    videos = []
    for item in resp.json().get("items", []):
        video_id = (item.get("id") or {}).get("videoId")
        snippet = item.get("snippet") or {}
        if not video_id:
            continue
        thumbnails = snippet.get("thumbnails") or {}
        thumb = (
            thumbnails.get("medium")
            or thumbnails.get("high")
            or thumbnails.get("default")
            or {}
        )
        videos.append(
            {
                "title": (snippet.get("title") or "Untitled video")[:255],
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "source": Resource.Source.YOUTUBE,
                "thumbnail_url": thumb.get("url", "")[:500],
                "channel_title": (snippet.get("channelTitle") or "")[:255],
            }
        )
    return videos


def fetch_resources_for_milestone(milestone) -> tuple[list[Resource], str | None]:
    """Populate a milestone's resources. Returns (resources, warning).

    A warning is returned — not an error — when videos couldn't be fetched, so
    the UI can still show the Google link and explain what's missing.
    """
    query = (milestone.search_query or milestone.title).strip()
    if not query:
        return [], "This milestone has no search topic yet. Add one to find resources."

    videos = _fetch_youtube(query)
    warning = None
    if not videos:
        warning = (
            "Couldn't load videos right now — the web search link below still works."
        )

    entries = videos + [
        {
            "title": f"Search the web for “{query}”",
            "url": google_search_url(query),
            "source": Resource.Source.GOOGLE_SEARCH,
            "thumbnail_url": "",
            "channel_title": "",
        }
    ]

    # Replace rather than append, so a re-fetch refreshes instead of piling up.
    milestone.resources.all().delete()
    created = Resource.objects.bulk_create(
        [Resource(milestone=milestone, **entry) for entry in entries]
    )

    milestone.resources_fetched_at = timezone.now()
    milestone.save(update_fields=["resources_fetched_at"])

    return created, warning
