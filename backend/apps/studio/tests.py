from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from common.exceptions import ServiceError
from common.testing import AuthenticatedAPITestCase, results

from apps.goals.models import Goal
from apps.studio.models import Artifact
from apps.studio.services import schemas
from apps.studio.services.generate import classify


class ClassifyTests(SimpleTestCase):
    """A decisive keyword should never cost an API call."""

    def test_obvious_requests_are_routed_without_the_model(self):
        cases = {
            "make me a resume for a backend role": Artifact.Kind.RESUME,
            "I need a CV": Artifact.Kind.RESUME,
            "write a cover letter for Google": Artifact.Kind.COVER_LETTER,
            "create a diet chart for weight loss": Artifact.Kind.DIET_PLAN,
            "build me a study timetable for GATE": Artifact.Kind.TIMETABLE,
            "generate my project report": Artifact.Kind.PROJECT_REPORT,
        }
        with patch("apps.studio.services.generate.llm.complete_json") as mocked:
            for prompt, expected in cases.items():
                with self.subTest(prompt=prompt):
                    self.assertEqual(classify(prompt), expected)
        mocked.assert_not_called()

    def test_card_requests_are_not_mistaken_for_a_cv(self):
        """Regression: "generate a wedding card" used to come back as a résumé,
        because anything unmatched fell through to resume."""
        cases = [
            "Let's generate a wedding card in orange",
            "make me a wedding card",
            "I need an invitation card for my sister's engagement",
            "birthday card for my friend",
            "shaadi card with marigold theme",
        ]
        with patch("apps.studio.services.generate.llm.complete_json") as mocked:
            for prompt in cases:
                with self.subTest(prompt=prompt):
                    self.assertEqual(classify(prompt), Artifact.Kind.INVITATION)
        mocked.assert_not_called()

    def test_image_requests_route_to_image(self):
        for prompt in [
            "generate an image of a sunset over mountains",
            "create an image of a temple in watercolour",
            "a picture of a marigold garland illustration",
        ]:
            with self.subTest(prompt=prompt):
                self.assertEqual(classify(prompt), Artifact.Kind.IMAGE)

    def test_the_last_resort_no_longer_silently_returns_a_cv(self):
        """Even with the model unavailable, an occasion request lands sensibly."""
        with patch(
            "apps.studio.services.generate.llm.complete_json",
            side_effect=ServiceError("down", 502, "llm_upstream_error"),
        ):
            self.assertEqual(
                classify("something nice for our anniversary"), Artifact.Kind.INVITATION
            )

    def test_cover_letter_beats_resume_when_both_words_appear(self):
        self.assertEqual(
            classify("a cover letter to go with my cv"), Artifact.Kind.COVER_LETTER
        )

    def test_an_ambiguous_prompt_falls_through_to_the_model(self):
        with patch(
            "apps.studio.services.generate.llm.complete_json",
            return_value={"kind": "timetable"},
        ) as mocked:
            self.assertEqual(classify("help me organise my week"), Artifact.Kind.TIMETABLE)
        mocked.assert_called_once()

    def test_a_nonsense_model_answer_is_ignored(self):
        with patch(
            "apps.studio.services.generate.llm.complete_json",
            return_value={"kind": "spreadsheet"},
        ):
            self.assertIn(classify("something vague"), schemas.SCHEMAS)


class SchemaValidationTests(SimpleTestCase):
    def test_resume_survives_a_hostile_payload(self):
        data = schemas.validate_resume(
            {
                "name": None,
                "experience": ["not a dict", {"role": "Intern", "bullets": "not a list"}],
                "skills": [{"group": "Languages", "items": ["Python"]}, {"items": []}],
                "links": [{"label": "GitHub"}, {"label": "X", "url": "https://x.com"}],
            }
        )
        self.assertEqual(data["name"], "Your Name")
        self.assertEqual(len(data["experience"]), 1)
        self.assertEqual(data["experience"][0]["bullets"], [])
        self.assertEqual(len(data["skills"]), 1)
        # A link with no url is unusable, so it is dropped.
        self.assertEqual(len(data["links"]), 1)

    def test_resume_never_returns_a_missing_section_as_none(self):
        data = schemas.validate_resume({})
        for field in ("experience", "education", "projects", "skills", "achievements"):
            self.assertEqual(data[field], [], field)

    def test_diet_plan_coerces_numbers(self):
        data = schemas.validate_diet(
            {
                "daily_calories": "2200",
                "macros": {"protein_g": "abc", "carbs_g": 250},
                "days": [{"day": "Monday", "meals": [{"slot": "Breakfast", "items": ["Oats"], "calories": "400"}]}],
            }
        )
        self.assertEqual(data["daily_calories"], 2200)
        self.assertEqual(data["macros"]["protein_g"], 0)
        self.assertEqual(data["macros"]["carbs_g"], 250)
        self.assertEqual(data["days"][0]["meals"][0]["calories"], 400)

    def test_timetable_drops_blocks_with_no_activity(self):
        data = schemas.validate_timetable(
            {
                "days": [
                    {
                        "day": "Monday",
                        "blocks": [
                            {"start": "07:00", "end": "08:00", "activity": "Study"},
                            {"start": "09:00", "end": "10:00"},
                        ],
                    }
                ]
            }
        )
        self.assertEqual(len(data["days"][0]["blocks"]), 1)

    def test_long_strings_are_truncated(self):
        data = schemas.validate_resume({"name": "x" * 500})
        self.assertEqual(len(data["name"]), 120)

    def test_invitation_clamps_an_unknown_theme(self):
        data = schemas.validate_invitation(
            {"headline": "Aarav & Diya", "theme": {"palette": "neon", "motif": "swirly"}}
        )
        self.assertEqual(data["theme"]["palette"], "classic")
        self.assertEqual(data["theme"]["motif"], "floral")

    def test_invitation_keeps_a_recognised_theme(self):
        data = schemas.validate_invitation(
            {"headline": "Aarav & Diya", "theme": {"palette": "MARIGOLD", "motif": "paisley"}}
        )
        self.assertEqual(data["theme"]["palette"], "marigold")
        self.assertEqual(data["theme"]["motif"], "paisley")

    def test_invitation_drops_unnamed_events(self):
        data = schemas.validate_invitation(
            {
                "headline": "Aarav & Diya",
                "events": [{"name": "Mehendi", "when": "12 Feb"}, {"when": "13 Feb"}],
            }
        )
        self.assertEqual(len(data["events"]), 1)

    def test_invitation_never_fabricates_missing_details(self):
        data = schemas.validate_invitation({"headline": "Aarav & Diya"})
        for field in ("date_text", "venue_name", "rsvp", "hosts"):
            self.assertEqual(data[field], "", field)

    def test_titles_are_derived_per_kind(self):
        self.assertEqual(
            schemas.derive_title(Artifact.Kind.RESUME, {"name": "Manav Sharma"}),
            "Manav Sharma CV",
        )
        self.assertEqual(
            schemas.derive_title(Artifact.Kind.COVER_LETTER, {"role": "Backend Intern"}),
            "Cover letter for Backend Intern",
        )

    def test_every_kind_has_a_complete_spec(self):
        for kind, spec in schemas.SCHEMAS.items():
            with self.subTest(kind=kind):
                for key in ("label", "shape", "guidance", "validator", "title_field"):
                    self.assertIn(key, spec)


@override_settings(USE_MOCK_AI=True)
class ArtifactAPITests(AuthenticatedAPITestCase):
    url = "/api/artifacts/generate/"

    def test_generate_infers_the_kind_and_saves(self):
        response = self.client.post(
            self.url, {"prompt": "Make me a resume for a backend internship"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["kind"], Artifact.Kind.RESUME)
        self.assertEqual(response.data["export_format"], "pdf")
        self.assertTrue(response.data["data"]["name"])
        self.assertEqual(Artifact.objects.count(), 1)

    def test_an_explicit_kind_overrides_the_classifier(self):
        response = self.client.post(
            self.url,
            {"prompt": "Make me a resume for a backend internship", "kind": "timetable"},
            format="json",
        )
        self.assertEqual(response.data["kind"], Artifact.Kind.TIMETABLE)

    def test_visual_documents_report_png(self):
        response = self.client.post(
            self.url, {"prompt": "Create a diet chart for weight loss"}, format="json"
        )
        self.assertEqual(response.data["kind"], Artifact.Kind.DIET_PLAN)
        self.assertEqual(response.data["export_format"], "png")

    def test_a_thin_prompt_is_rejected(self):
        response = self.client.post(self.url, {"prompt": "cv"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_an_artifact_can_be_attached_to_a_goal(self):
        goal = Goal.objects.create(user=self.user, title="Get a job")
        response = self.client.post(
            self.url,
            {"prompt": "Make me a resume for a backend role", "goal": goal.id},
            format="json",
        )
        self.assertEqual(response.data["goal"], goal.id)

    def test_cannot_attach_to_someone_elses_goal(self):
        foreign = Goal.objects.create(user=self.other, title="Theirs")
        response = self.client.post(
            self.url,
            {"prompt": "Make me a resume for a backend role", "goal": foreign.id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_list_omits_the_heavy_data_blob(self):
        self.client.post(self.url, {"prompt": "Make me a resume please"}, format="json")
        rows = results(self.client.get("/api/artifacts/"))
        self.assertEqual(len(rows), 1)
        self.assertNotIn("data", rows[0])

    def test_list_can_be_filtered_by_kind(self):
        self.client.post(self.url, {"prompt": "Make me a resume please"}, format="json")
        self.client.post(self.url, {"prompt": "Create a diet chart"}, format="json")
        rows = results(self.client.get("/api/artifacts/?kind=diet_plan"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["kind"], "diet_plan")

    def test_the_document_can_be_edited_after_generation(self):
        artifact_id = self.client.post(
            self.url, {"prompt": "Make me a resume please"}, format="json"
        ).data["id"]
        response = self.client.patch(
            f"/api/artifacts/{artifact_id}/",
            {"title": "Renamed", "data": {"name": "Edited Name"}},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Renamed")
        self.assertEqual(response.data["data"]["name"], "Edited Name")

    def test_regenerate_replaces_the_content_in_place(self):
        artifact_id = self.client.post(
            self.url, {"prompt": "Make me a resume please"}, format="json"
        ).data["id"]
        response = self.client.post(
            f"/api/artifacts/{artifact_id}/regenerate/",
            {"instruction": "Make it shorter"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Artifact.objects.count(), 1)

    def test_kinds_endpoint_lists_what_the_studio_can_make(self):
        response = self.client.get("/api/artifacts/kinds/")
        self.assertEqual(response.status_code, 200)
        # Prompt-driven kinds, plus the certificate listed as automatic-only
        # (see tests_certificate.py for that entry).
        self.assertEqual(len(response.data), len(schemas.SCHEMAS) + 1)
        by_kind = {row["kind"]: row for row in response.data}
        self.assertEqual(by_kind["resume"]["export_format"], "pdf")
        self.assertEqual(by_kind["timetable"]["export_format"], "png")
        self.assertFalse(by_kind["resume"]["automatic"])

    def test_another_user_sees_nothing(self):
        self.client.post(self.url, {"prompt": "Make me a resume please"}, format="json")
        self.as_other()
        self.assertEqual(results(self.client.get("/api/artifacts/")), [])

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/artifacts/").status_code, 401)

    def test_a_wedding_card_produces_an_invitation_end_to_end(self):
        response = self.client.post(
            self.url,
            {"prompt": "Generate a wedding card in orange for Aarav and Diya"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["kind"], Artifact.Kind.INVITATION)
        self.assertEqual(response.data["export_format"], "png")
        self.assertTrue(response.data["data"]["headline"])

    def test_image_generation_stores_a_file(self):
        response = self.client.post(
            self.url,
            {"prompt": "Generate an image of marigold garlands, flat illustration"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["kind"], Artifact.Kind.IMAGE)
        self.assertTrue(response.data["image_url"])

        artifact = Artifact.objects.get(id=response.data["id"])
        self.assertTrue(artifact.image)

    def test_a_failed_image_leaves_no_empty_artifact_behind(self):
        """If the image can't be produced, the row is rolled back rather than
        left as a shell the user has to tidy up."""
        with override_settings(USE_MOCK_AI=False):
            with patch(
                "apps.studio.services.generate.llm.complete_json",
                return_value={"image_prompt": "a marigold", "alt_text": "x", "title": "Marigold"},
            ):
                with patch(
                    "apps.studio.views.imagegen.generate_image",
                    side_effect=ServiceError(
                        "not on the free tier", 402, "image_generation_unavailable"
                    ),
                ):
                    response = self.client.post(
                        self.url,
                        {"prompt": "Generate an image of a marigold"},
                        format="json",
                    )

        self.assertEqual(response.status_code, 402)
        self.assertEqual(response.data["code"], "image_generation_unavailable")
        self.assertEqual(Artifact.objects.filter(kind=Artifact.Kind.IMAGE).count(), 0)

    def test_an_unusable_model_response_is_reported(self):
        with override_settings(USE_MOCK_AI=False):
            with patch(
                "apps.studio.services.generate.llm.complete_json",
                return_value=["not", "a", "dict"],
            ):
                response = self.client.post(
                    self.url, {"prompt": "Make me a resume please"}, format="json"
                )
        self.assertEqual(response.status_code, 502)
