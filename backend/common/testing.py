"""Shared helpers for the test suite."""

import logging

from django.contrib.auth import get_user_model
from django.test.runner import DiscoverRunner
from rest_framework.test import APITestCase

User = get_user_model()


class QuietTestRunner(DiscoverRunner):
    """Silences log output during tests.

    Many tests deliberately drive failure paths — a dead YouTube call, a model
    returning junk — and the service layer logs a warning for each. Those lines
    are correct behaviour, not test noise worth reading.
    """

    def run_tests(self, *args, **kwargs):
        logging.disable(logging.CRITICAL)
        try:
            return super().run_tests(*args, **kwargs)
        finally:
            logging.disable(logging.NOTSET)


def results(response):
    """Unwrap a DRF list response whether or not pagination kicked in."""
    data = response.data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


class AuthenticatedAPITestCase(APITestCase):
    """API test case with a signed-in user, plus a second user for isolation
    checks. Authentication goes through force_authenticate rather than real
    tokens — JWT issuing is covered separately in the accounts tests."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="manav", email="manav@example.com", password="SuperSecret123"
        )
        self.other = User.objects.create_user(
            username="intruder", email="intruder@example.com", password="SuperSecret123"
        )
        self.client.force_authenticate(self.user)

    def as_other(self):
        self.client.force_authenticate(self.other)

    def as_owner(self):
        self.client.force_authenticate(self.user)
