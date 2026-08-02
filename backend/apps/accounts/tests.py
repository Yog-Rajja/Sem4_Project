from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

User = get_user_model()


class RegisterTests(APITestCase):
    url = reverse("register")

    def test_register_returns_tokens_and_user(self):
        response = self.client.post(
            self.url,
            {
                "username": "manav",
                "email": "manav@example.com",
                "password": "SuperSecret123",
                "first_name": "Manav",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["username"], "manav")
        # The password must never come back out.
        self.assertNotIn("password", response.data["user"])

    def test_duplicate_username_is_rejected_case_insensitively(self):
        User.objects.create_user("manav", "a@example.com", "SuperSecret123")
        response = self.client.post(
            self.url,
            {"username": "MANAV", "email": "b@example.com", "password": "SuperSecret123"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.data)

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user("one", "taken@example.com", "SuperSecret123")
        response = self.client.post(
            self.url,
            {"username": "two", "email": "taken@example.com", "password": "SuperSecret123"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

    def test_weak_password_is_rejected(self):
        response = self.client.post(
            self.url,
            {"username": "manav", "email": "manav@example.com", "password": "pass"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data)


class LoginTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "manav", "manav@example.com", "SuperSecret123"
        )

    def test_login_returns_token_pair(self):
        response = self.client.post(
            reverse("login"),
            {"username": "manav", "password": "SuperSecret123"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_wrong_password_is_unauthorised(self):
        response = self.client.post(
            reverse("login"),
            {"username": "manav", "password": "wrong"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_refresh_issues_a_new_access_token(self):
        login = self.client.post(
            reverse("login"),
            {"username": "manav", "password": "SuperSecret123"},
            format="json",
        )
        response = self.client.post(
            reverse("token_refresh"), {"refresh": login.data["refresh"]}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_me_requires_authentication(self):
        self.assertEqual(self.client.get(reverse("me")).status_code, 401)

    def test_me_returns_the_signed_in_user(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "manav")
