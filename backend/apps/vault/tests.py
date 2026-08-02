import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from common.testing import AuthenticatedAPITestCase, results

from apps.goals.models import Goal
from apps.vault.models import Document

MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class DocumentTests(AuthenticatedAPITestCase):
    """Uploads go to a throwaway media root so tests never touch backend/media."""

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.goal = Goal.objects.create(user=self.user, title="Learn Django")

    def upload(self, name="syllabus.txt", content=b"syllabus contents"):
        return self.client.post(
            "/api/documents/",
            {"goal": self.goal.id, "file": SimpleUploadedFile(name, content)},
            format="multipart",
        )

    def test_upload_records_the_original_name_and_size(self):
        response = self.upload()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["original_name"], "syllabus.txt")
        self.assertEqual(response.data["size_bytes"], len(b"syllabus contents"))
        self.assertTrue(response.data["file_url"].startswith("http"))

    def test_the_raw_file_path_is_not_exposed(self):
        response = self.upload()
        self.assertNotIn("file", response.data)

    def test_documents_can_be_filtered_by_goal(self):
        other_goal = Goal.objects.create(user=self.user, title="Learn React")
        self.upload()
        self.client.post(
            "/api/documents/",
            {"goal": other_goal.id, "file": SimpleUploadedFile("notes.txt", b"x")},
            format="multipart",
        )

        rows = results(self.client.get(f"/api/documents/?goal={self.goal.id}"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["original_name"], "syllabus.txt")

    def test_oversized_uploads_are_rejected(self):
        response = self.client.post(
            "/api/documents/",
            {
                "goal": self.goal.id,
                "file": SimpleUploadedFile("huge.bin", b"x" * (10 * 1024 * 1024 + 1)),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Document.objects.count(), 0)

    def test_cannot_attach_a_document_to_someone_elses_goal(self):
        foreign = Goal.objects.create(user=self.other, title="Theirs")
        response = self.client.post(
            "/api/documents/",
            {"goal": foreign.id, "file": SimpleUploadedFile("x.txt", b"x")},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Document.objects.count(), 0)

    def test_another_user_cannot_see_or_delete_your_documents(self):
        document_id = self.upload().data["id"]
        self.as_other()
        self.assertEqual(results(self.client.get("/api/documents/")), [])
        self.assertEqual(
            self.client.delete(f"/api/documents/{document_id}/").status_code, 404
        )

    def test_delete_removes_the_row(self):
        document_id = self.upload().data["id"]
        self.assertEqual(self.client.delete(f"/api/documents/{document_id}/").status_code, 204)
        self.assertEqual(Document.objects.count(), 0)

    def test_deleting_a_goal_cascades_to_its_documents(self):
        self.upload()
        self.client.delete(f"/api/goals/{self.goal.id}/")
        self.assertEqual(Document.objects.count(), 0)

    def test_documents_are_not_editable(self):
        document_id = self.upload().data["id"]
        response = self.client.patch(
            f"/api/documents/{document_id}/", {"original_name": "renamed"}, format="json"
        )
        self.assertEqual(response.status_code, 405)
