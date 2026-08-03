from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.goals.models import Goal, Milestone, Resource
from apps.goals.services import resources as service

User = get_user_model()


def youtube_payload(count=2):
    return {
        "items": [
            {
                "id": {"videoId": f"vid{i}"},
                "snippet": {
                    "title": f"Great tutorial {i}",
                    "channelTitle": f"Channel {i}",
                    "thumbnails": {"medium": {"url": f"https://img.example/{i}.jpg"}},
                },
            }
            for i in range(count)
        ]
    }


class FakeResponse:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


@override_settings(YOUTUBE_API_KEY="test-key")
class FetchResourcesTests(TestCase):
    def setUp(self):
        user = User.objects.create_user("manav", "m@example.com", "SuperSecret123")
        goal = Goal.objects.create(user=user, title="Learn Django")
        self.milestone = Milestone.objects.create(
            goal=goal, title="ORM basics", search_query="django orm tutorial"
        )

    def test_stores_videos_and_always_adds_a_search_link(self):
        with patch.object(
            service.requests, "get", return_value=FakeResponse(200, youtube_payload(2))
        ):
            created, warning = service.fetch_resources_for_milestone(self.milestone)

        self.assertIsNone(warning)
        self.assertEqual(len(created), 3)  # 2 videos + 1 search link
        videos = [r for r in created if r.source == Resource.Source.YOUTUBE]
        self.assertEqual(len(videos), 2)
        self.assertEqual(videos[0].url, "https://www.youtube.com/watch?v=vid0")
        self.assertEqual(videos[0].channel_title, "Channel 0")
        self.assertEqual(videos[0].thumbnail_url, "https://img.example/0.jpg")

        search = [r for r in created if r.source == Resource.Source.GOOGLE_SEARCH]
        self.assertEqual(len(search), 1)
        self.assertIn("django+orm+tutorial", search[0].url)

    def test_marks_the_milestone_as_fetched(self):
        with patch.object(
            service.requests, "get", return_value=FakeResponse(200, youtube_payload(1))
        ):
            service.fetch_resources_for_milestone(self.milestone)
        self.milestone.refresh_from_db()
        self.assertIsNotNone(self.milestone.resources_fetched_at)

    def test_api_failure_still_yields_a_working_search_link(self):
        """A dead YouTube call must never leave a milestone with nothing."""
        with patch.object(service.requests, "get", return_value=FakeResponse(403, {})):
            created, warning = service.fetch_resources_for_milestone(self.milestone)

        self.assertIsNotNone(warning)
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].source, Resource.Source.GOOGLE_SEARCH)

    def test_network_error_is_swallowed(self):
        with patch.object(
            service.requests, "get", side_effect=service.requests.ConnectionError()
        ):
            created, warning = service.fetch_resources_for_milestone(self.milestone)
        self.assertIsNotNone(warning)
        self.assertEqual(len(created), 1)

    @override_settings(YOUTUBE_API_KEY="")
    def test_missing_api_key_skips_videos_without_erroring(self):
        created, warning = service.fetch_resources_for_milestone(self.milestone)
        self.assertIsNotNone(warning)
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].source, Resource.Source.GOOGLE_SEARCH)

    def test_html_entities_in_titles_are_decoded(self):
        """The API returns escaped text; rendering it raw shows "&amp;" to users."""
        payload = {
            "items": [
                {
                    "id": {"videoId": "abc"},
                    "snippet": {
                        "title": "Tips &amp; Tricks for GATE &#39;26",
                        "channelTitle": "Physics &amp; Maths",
                        "thumbnails": {},
                    },
                }
            ]
        }
        with patch.object(service.requests, "get", return_value=FakeResponse(200, payload)):
            created, _ = service.fetch_resources_for_milestone(self.milestone)

        video = next(r for r in created if r.source == Resource.Source.YOUTUBE)
        self.assertEqual(video.title, "Tips & Tricks for GATE '26")
        self.assertEqual(video.channel_title, "Physics & Maths")

    def test_items_without_a_video_id_are_skipped(self):
        payload = {"items": [{"id": {}, "snippet": {"title": "Broken"}}]}
        with patch.object(service.requests, "get", return_value=FakeResponse(200, payload)):
            created, _ = service.fetch_resources_for_milestone(self.milestone)
        self.assertEqual(len(created), 1)

    def test_refetching_replaces_rather_than_duplicates(self):
        with patch.object(
            service.requests, "get", return_value=FakeResponse(200, youtube_payload(2))
        ):
            service.fetch_resources_for_milestone(self.milestone)
            service.fetch_resources_for_milestone(self.milestone)

        self.assertEqual(self.milestone.resources.count(), 3)

    def test_falls_back_to_the_title_when_there_is_no_search_query(self):
        self.milestone.search_query = ""
        self.milestone.save()
        with patch.object(
            service.requests, "get", return_value=FakeResponse(200, youtube_payload(1))
        ) as mocked:
            service.fetch_resources_for_milestone(self.milestone)
        self.assertEqual(mocked.call_args.kwargs["params"]["q"], "ORM basics")

    def test_search_call_requests_only_a_handful_of_videos(self):
        """Each search.list costs 100 quota units, so keep the result set small."""
        with patch.object(
            service.requests, "get", return_value=FakeResponse(200, youtube_payload(1))
        ) as mocked:
            service.fetch_resources_for_milestone(self.milestone)
        self.assertLessEqual(mocked.call_args.kwargs["params"]["maxResults"], 3)


class GoogleSearchUrlTests(TestCase):
    def test_encodes_the_query(self):
        url = service.google_search_url("dynamic programming for GATE")
        self.assertEqual(
            url, "https://www.google.com/search?q=dynamic+programming+for+GATE"
        )
