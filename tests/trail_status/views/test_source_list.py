from django.test import TestCase
from django.urls import reverse


class TestSourceListView(TestCase):
    def test_NO_SOURCES(self):
        response = self.client.get(reverse("trail_status:source-list"))
        self.assertEqual(response.status_code, 200)