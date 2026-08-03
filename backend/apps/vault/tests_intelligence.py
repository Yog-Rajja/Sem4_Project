import base64
import shutil
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from common.exceptions import ServiceError
from common.testing import AuthenticatedAPITestCase

from apps.goals.models import Goal
from apps.vault import services
from apps.vault.models import Document

MEDIA_ROOT = tempfile.mkdtemp()

# Smallest valid PDF that carries extractable text.
MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
    b"/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj\n"
    b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"5 0 obj<</Length 44>>stream\n"
    b"BT /F1 12 Tf 72 720 Td (Hello syllabus) Tj ET\n"
    b"endstream endobj\n"
    b"trailer<</Root 1 0 R>>\n"
)

PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class DocumentPreparationTests(AuthenticatedAPITestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.goal = Goal.objects.create(user=self.user, title="Learn Django")

    def make(self, name, content):
        return Document.objects.create(
            goal=self.goal,
            file=SimpleUploadedFile(name, content),
            original_name=name,
            size_bytes=len(content),
        )

    def test_plain_text_is_read_locally_with_no_attachment(self):
        text, attachment = services.prepare(self.make("notes.txt", b"Unit 1: Basics\n" * 40))
        self.assertIn("Unit 1", text)
        self.assertIsNone(attachment)

    def test_a_text_bearing_pdf_is_extracted_locally(self):
        """pypdf handles this for free — no API call, no OCR engine."""
        with patch.object(services, "_extract_pdf_text", return_value="Syllabus " * 60):
            text, attachment = services.prepare(self.make("syllabus.pdf", MINIMAL_PDF))
        self.assertIn("Syllabus", text)
        self.assertIsNone(attachment)

    def test_a_scanned_pdf_falls_through_to_multimodal_reading(self):
        with patch.object(services, "_extract_pdf_text", return_value=""):
            text, attachment = services.prepare(self.make("scan.pdf", MINIMAL_PDF))
        self.assertEqual(text, "")
        self.assertEqual(attachment["mime_type"], "application/pdf")
        self.assertTrue(attachment["data"])

    def test_images_are_sent_as_attachments(self):
        text, attachment = services.prepare(self.make("photo.png", PNG_BYTES))
        self.assertEqual(text, "")
        self.assertEqual(attachment["mime_type"], "image/png")

    def test_an_unreadable_file_type_is_rejected_clearly(self):
        with self.assertRaises(ServiceError) as ctx:
            services.prepare(self.make("archive.zip", b"PK\x03\x04" + b"\x00" * 40))
        self.assertEqual(ctx.exception.code, "unsupported_document")

    def test_an_oversized_image_is_rejected_before_the_api_call(self):
        oversized = self.make("huge.png", b"x" * 10)
        with patch.object(services, "_read_bytes", return_value=b"x" * (11 * 1024 * 1024)):
            with self.assertRaises(ServiceError) as ctx:
                services.prepare(oversized)
        self.assertEqual(ctx.exception.code, "document_too_large")


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class DocumentAnalysisTests(AuthenticatedAPITestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.goal = Goal.objects.create(user=self.user, title="Learn Django")
        self.document = Document.objects.create(
            goal=self.goal,
            file=SimpleUploadedFile("syllabus.txt", b"Unit 1: ORM\nUnit 2: Views\n" * 30),
            original_name="syllabus.txt",
        )

    @override_settings(USE_MOCK_AI=True)
    def test_analyse_populates_and_persists(self):
        response = self.client.post(f"/api/documents/{self.document.id}/analyse/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_analysed"])
        self.assertTrue(response.data["summary"])

        self.document.refresh_from_db()
        self.assertIsNotNone(self.document.analysed_at)
        self.assertIn("Unit 1", self.document.extracted_text)

    def test_analysis_stores_what_the_model_returned(self):
        payload = {
            "doc_type": "Syllabus",
            "summary": "A two-unit Django syllabus.",
            "key_points": ["Unit 1 covers the ORM", "Unit 2 covers views"],
            "suggested_actions": ["Create a revision goal"],
            "extracted_text": "",
        }
        with patch("apps.vault.services.llm.complete_json", return_value=payload):
            response = self.client.post(f"/api/documents/{self.document.id}/analyse/")

        self.assertEqual(response.data["doc_type"], "Syllabus")
        self.assertEqual(len(response.data["key_points"]), 2)
        self.assertEqual(response.data["suggested_actions"], ["Create a revision goal"])

    def test_locally_extracted_text_wins_over_the_model(self):
        """We already have the exact text; the model's transcription can drift."""
        payload = {
            "doc_type": "Syllabus",
            "summary": "s",
            "key_points": [],
            "suggested_actions": [],
            "extracted_text": "SOMETHING THE MODEL MADE UP",
        }
        with patch("apps.vault.services.llm.complete_json", return_value=payload):
            self.client.post(f"/api/documents/{self.document.id}/analyse/")

        self.document.refresh_from_db()
        self.assertNotIn("MADE UP", self.document.extracted_text)
        self.assertIn("Unit 1", self.document.extracted_text)

    def test_a_malformed_analysis_is_reported(self):
        with patch("apps.vault.services.llm.complete_json", return_value=["nope"]):
            response = self.client.post(f"/api/documents/{self.document.id}/analyse/")
        self.assertEqual(response.status_code, 502)

    def test_extracted_text_is_never_exposed_over_the_api(self):
        with override_settings(USE_MOCK_AI=True):
            response = self.client.post(f"/api/documents/{self.document.id}/analyse/")
        self.assertNotIn("extracted_text", response.data)

    @override_settings(USE_MOCK_AI=True)
    def test_another_user_cannot_analyse_your_document(self):
        self.as_other()
        response = self.client.post(f"/api/documents/{self.document.id}/analyse/")
        self.assertEqual(response.status_code, 404)

    @override_settings(USE_MOCK_AI=True)
    def test_document_to_goal_returns_a_preview_without_saving(self):
        response = self.client.post(
            f"/api/documents/{self.document.id}/to-goal/",
            {"prompt": "Revise this syllabus in 6 weeks"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["milestones"])
        self.assertEqual(response.data["source_document"], "syllabus.txt")
        # Same contract as /goals/generate/ — nothing is persisted yet.
        self.assertEqual(Goal.objects.filter(title__icontains="Revise").count(), 0)

    @override_settings(USE_MOCK_AI=True)
    def test_to_goal_analyses_first_if_it_has_not_been_read(self):
        self.assertFalse(self.document.is_analysed)
        self.client.post(f"/api/documents/{self.document.id}/to-goal/", {}, format="json")
        self.document.refresh_from_db()
        self.assertTrue(self.document.is_analysed)

    def test_to_goal_passes_the_document_text_to_the_generator(self):
        self.document.extracted_text = "Unit 1: ORM. Unit 2: Views."
        self.document.save()

        captured = {}

        def fake(goal_text, target_date=None, context=None):
            captured["context"] = context
            return [{"title": "M", "target_date": None, "search_query": "q",
                     "order": 0, "tasks": []}]

        with patch("apps.vault.views.roadmap_service.generate_roadmap", side_effect=fake):
            self.client.post(f"/api/documents/{self.document.id}/to-goal/", {}, format="json")

        self.assertIn("Unit 1: ORM", captured["context"])
